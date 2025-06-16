"""Unit tests for proper per-second rate limiting behavior.

This module tests the core rate limiting functionality to ensure
that order counts reset properly every second and teams are isolated.
"""

from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
)
from intern_trading_game.domain.exchange.venue import ExchangeVenue
from intern_trading_game.services.order_validation import (
    OrderValidationService,
)


class TestRateLimitingBehavior:
    """Test core rate limiting behavior with time progression."""

    @pytest.fixture
    def mock_validator(self):
        """Create a mock validator."""
        return Mock(spec=ConstraintBasedOrderValidator)

    @pytest.fixture
    def mock_exchange(self):
        """Create a mock exchange."""
        return Mock(spec=ExchangeVenue)

    @pytest.fixture
    def mock_positions(self):
        """Create a mock position function."""
        return Mock(return_value={})

    @pytest.fixture
    def service(self, mock_validator, mock_exchange):
        """Create service for testing."""
        from intern_trading_game.domain.positions import (
            PositionManagementService,
        )

        position_service = PositionManagementService()
        return OrderValidationService(
            validator=mock_validator,
            exchange=mock_exchange,
            position_service=position_service,
        )

    def test_fresh_team_starts_with_zero_count(self, service):
        """Test that new teams start with count of 0.

        Given - New team that has never submitted orders
        When - Check order count
        Then - Returns 0
        """
        # Given - Fresh service and team
        team_id = "TEAM_001"
        current_time = 1000.0

        # When - Check order count
        count = service.get_order_count(team_id, current_time)

        # Then - Should be 0
        assert count == 0

    def test_increment_within_same_second(self, service):
        """Test that increments accumulate within the same second.

        Given - Team submits multiple orders in same second
        When - Check count after each increment
        Then - Count accumulates correctly
        """
        # Given - Team and single second timeframe
        team_id = "TEAM_001"
        current_time = 1000.5

        # When - Increment multiple times in same second
        service.increment_order_count(team_id, current_time)
        count1 = service.get_order_count(team_id, current_time)

        service.increment_order_count(team_id, current_time)
        count2 = service.get_order_count(team_id, current_time)

        service.increment_order_count(team_id, current_time)
        count3 = service.get_order_count(team_id, current_time)

        # Then - Count should accumulate
        assert count1 == 1
        assert count2 == 2
        assert count3 == 3

    def test_window_resets_on_new_second(self, service):
        """Test that count resets when entering a new second.

        Given - Team has submitted orders in previous second
        When - Check count in new second
        Then - Count resets to 0
        """
        # Given - Orders in first second
        team_id = "TEAM_001"
        time_second_1 = 1000.0
        time_second_2 = 1001.0

        # Submit 3 orders in first second
        service.increment_order_count(team_id, time_second_1)
        service.increment_order_count(team_id, time_second_1)
        service.increment_order_count(team_id, time_second_1)
        count_first_second = service.get_order_count(team_id, time_second_1)

        # When - Check count in new second
        count_new_second = service.get_order_count(team_id, time_second_2)

        # Then - Should reset
        assert count_first_second == 3
        assert count_new_second == 0

    def test_multiple_teams_isolated(self, service):
        """Test that different teams have isolated rate limit counts.

        Given - Multiple teams submit orders
        When - Each team increments their count
        Then - Counts are isolated per team
        """
        # Given - Multiple teams and same time
        team_a = "TEAM_A"
        team_b = "TEAM_B"
        current_time = 1000.0

        # When - Each team submits different amounts
        service.increment_order_count(team_a, current_time)
        service.increment_order_count(team_a, current_time)

        service.increment_order_count(team_b, current_time)

        # Then - Counts should be isolated
        count_a = service.get_order_count(team_a, current_time)
        count_b = service.get_order_count(team_b, current_time)

        assert count_a == 2
        assert count_b == 1

    def test_rapid_increments_same_second(self, service):
        """Test rapid increments within same second.

        Given - Many rapid increments in same second
        When - Check final count
        Then - All increments are counted
        """
        # Given - Team and single second
        team_id = "TEAM_001"
        current_time = 1000.123

        # When - Rapid increments (10 orders)
        for _ in range(10):
            service.increment_order_count(team_id, current_time)

        count = service.get_order_count(team_id, current_time)

        # Then - Should show all 10
        assert count == 10

    def test_cross_second_boundary_scenario(self, service):
        """Test orders across second boundary.

        Given - Orders at end of one second and start of next
        When - Check count during progression
        Then - Count resets properly at boundary
        """
        # Given - Orders near boundary
        team_id = "TEAM_001"
        time_1_9 = 1000.9  # End of second 1000
        time_2_1 = 1001.1  # Start of second 1001

        # Submit 3 orders at end of first second
        service.increment_order_count(team_id, time_1_9)
        service.increment_order_count(team_id, time_1_9)
        service.increment_order_count(team_id, time_1_9)

        # Check count during first second
        count_during_first = service.get_order_count(team_id, time_1_9)

        # Submit 2 orders in next second (this should reset window)
        service.increment_order_count(team_id, time_2_1)
        service.increment_order_count(team_id, time_2_1)

        # Check count during second second
        count_during_second = service.get_order_count(team_id, time_2_1)

        # Then - First second had 3, second second has 2
        assert count_during_first == 3
        assert count_during_second == 2

        # Previous window is no longer accessible (realistic behavior)
        count_old_window = service.get_order_count(team_id, time_1_9)
        assert count_old_window == 0  # Old window is gone


class TestRateLimitingEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def service(self):
        """Create service for edge case testing."""
        from intern_trading_game.domain.positions import (
            PositionManagementService,
        )

        position_service = PositionManagementService()
        return OrderValidationService(
            validator=Mock(),
            exchange=Mock(),
            position_service=position_service,
        )

    def test_exact_second_boundary(self, service):
        """Test behavior at exact second boundaries.

        Given - Order at end of second boundary
        When - Increment at exact next second
        Then - Window resets properly
        """
        # Given - Order at 1.999 seconds
        team_id = "TEAM_001"
        time_1_999 = 1000.999
        time_2_000 = 1001.000

        # Submit order at end of second
        service.increment_order_count(team_id, time_1_999)
        count_1 = service.get_order_count(team_id, time_1_999)

        # When - Check at exact next second
        count_2 = service.get_order_count(team_id, time_2_000)

        # Then - Should reset
        assert count_1 == 1
        assert count_2 == 0

    def test_large_time_gaps(self, service):
        """Test handling of large gaps between orders.

        Given - Order, then large time gap
        When - Check count after gap
        Then - Window resets properly
        """
        # Given - Order, then gap of hours
        team_id = "TEAM_001"
        time_start = 1000.0
        time_hours_later = 1000.0 + 3600  # 1 hour later

        # Submit order
        service.increment_order_count(team_id, time_start)
        count_initial = service.get_order_count(team_id, time_start)

        # When - Check after large gap
        count_later = service.get_order_count(team_id, time_hours_later)

        # Then - Should reset
        assert count_initial == 1
        assert count_later == 0

    def test_fractional_seconds_same_window(self, service):
        """Test that fractional seconds in same window work correctly.

        Given - Orders at different fractional points in same second
        When - Check count
        Then - All counted in same window
        """
        # Given - Different fractional times in same second
        team_id = "TEAM_001"
        time_1_1 = 1000.1
        time_1_5 = 1000.5
        time_1_9 = 1000.9

        # When - Submit orders at different fractions
        service.increment_order_count(team_id, time_1_1)
        service.increment_order_count(team_id, time_1_5)
        service.increment_order_count(team_id, time_1_9)

        count = service.get_order_count(team_id, time_1_9)

        # Then - All in same window
        assert count == 3

    def test_default_time_parameter(self, service):
        """Test that methods work without explicit time parameter.

        Given - Service methods called without time
        When - Operations performed
        Then - Uses current system time correctly
        """
        # Given - Team and no explicit time
        team_id = "TEAM_001"

        # When - Use methods without time parameter
        service.increment_order_count(team_id)  # Uses time.time()
        count = service.get_order_count(team_id)  # Uses time.time()

        # Then - Should work (count will be 1)
        assert count == 1
        # Note: This test may be flaky if it crosses second boundary
        # but demonstrates the interface works


class TestThreadSafety:
    """Test thread safety of rate limiting operations."""

    @pytest.fixture
    def service(self):
        """Create service for thread safety testing."""
        from intern_trading_game.domain.positions import (
            PositionManagementService,
        )

        position_service = PositionManagementService()
        return OrderValidationService(
            validator=Mock(),
            exchange=Mock(),
            position_service=position_service,
        )

    def test_concurrent_increments_same_team(self, service):
        """Test concurrent increments for same team are thread-safe.

        Given - Multiple threads incrementing same team
        When - Concurrent operations
        Then - All increments are counted correctly
        """
        import threading

        # Given - Team and shared state
        team_id = "TEAM_001"
        current_time = 1000.0
        num_threads = 5
        increments_per_thread = 10

        # When - Concurrent increments
        def increment_worker():
            for _ in range(increments_per_thread):
                service.increment_order_count(team_id, current_time)

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Then - All increments should be counted
        final_count = service.get_order_count(team_id, current_time)
        expected_count = num_threads * increments_per_thread

        assert final_count == expected_count
