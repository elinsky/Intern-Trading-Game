"""Integration tests for OrderRateConstraint with real OrderValidationService.

Tests the interaction between the rate limiting constraint and the
actual rate limiting implementation to ensure proper enforcement.
"""

from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.models.order import (
    Order,
    OrderSide,
    OrderType,
)
from intern_trading_game.domain.exchange.validation.interfaces import (
    ValidationContext,
)
from intern_trading_game.domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintConfig,
    ConstraintType,
    OrderRateConstraint,
)
from intern_trading_game.domain.exchange.venue import ExchangeVenue
from intern_trading_game.infrastructure.api.models import TeamInfo
from intern_trading_game.services.order_validation import (
    OrderValidationService,
)


class TestRateConstraintWithRealService:
    """Test OrderRateConstraint with actual rate limiting service."""

    @pytest.fixture
    def mock_exchange(self):
        """Create mock exchange."""
        return Mock(spec=ExchangeVenue)

    @pytest.fixture
    def mock_positions(self):
        """Create mock position function."""
        return Mock(return_value={})

    @pytest.fixture
    def validator_with_rate_limit(self):
        """Create validator with rate limiting constraint."""
        validator = ConstraintBasedOrderValidator()

        # Configure rate limit: max 3 orders per second
        rate_constraint = ConstraintConfig(
            constraint_type=ConstraintType.ORDER_RATE,
            parameters={"max_orders_per_second": 3},
            error_code="RATE_LIMIT_EXCEEDED",
            error_message="Too many orders this second",
        )

        validator.load_constraints("test_role", [rate_constraint])
        return validator

    @pytest.fixture
    def service(self, validator_with_rate_limit, mock_exchange):
        """Create validation service with rate limiting."""
        from intern_trading_game.domain.positions import (
            PositionManagementService,
        )

        position_service = PositionManagementService()
        return OrderValidationService(
            validator=validator_with_rate_limit,
            exchange=mock_exchange,
            position_service=position_service,
        )

    @pytest.fixture
    def sample_order(self):
        """Create a sample order."""
        return Order(
            instrument_id="SPX-20240315-4500C",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.LIMIT,
            price=125.50,
            trader_id="TEAM_001",
        )

    @pytest.fixture
    def sample_team(self):
        """Create a sample team."""
        from datetime import datetime

        return TeamInfo(
            team_id="TEAM_001",
            team_name="Test Team",
            role="test_role",
            api_key="test-key",
            created_at=datetime.now(),
        )

    def test_rate_limit_allows_orders_under_limit(
        self, service, sample_order, sample_team
    ):
        """Test that orders under rate limit are accepted.

        Given - Rate limit of 3 orders per second
        When - Submit 2 orders in same second
        Then - Both orders are accepted
        """
        # Mock the time in service methods
        service.get_order_count = Mock(
            side_effect=[0, 1]
        )  # Progressive counts
        service.increment_order_count = Mock()

        # When - Submit 2 orders (under limit)
        result1 = service.validate_new_order(sample_order, sample_team)
        result2 = service.validate_new_order(sample_order, sample_team)

        # Then - Both should be accepted
        assert result1.status == "accepted"
        assert result2.status == "accepted"

    def test_rate_limit_blocks_excess_orders(
        self, service, sample_order, sample_team
    ):
        """Test that excess orders are blocked by rate limit.

        Given - Rate limit of 3 orders per second and 3 orders already submitted
        When - Submit 4th order in same second
        Then - 4th order is rejected with rate limit error
        """
        # Mock service to return count of 3 (at limit)
        service.get_order_count = Mock(return_value=3)
        service.increment_order_count = Mock()

        # When - Submit order when at limit
        result = service.validate_new_order(sample_order, sample_team)

        # Then - Should be rejected for rate limit
        assert result.status == "rejected"
        assert result.error_code == "RATE_LIMIT_EXCEEDED"
        assert "Too many orders this second" in result.error_message

    def test_rate_limit_allows_after_second_rollover(
        self, service, sample_order, sample_team
    ):
        """Test that rate limit resets after second rollover.

        Given - 3 orders submitted at t=1000 (at limit)
        When - Submit order at t=1001 (new second)
        Then - Order is accepted (limit reset)
        """
        # Mock the service to return 0 orders (reset in new second)
        service.get_order_count = Mock(return_value=0)
        service.increment_order_count = Mock()

        # When - Submit order (should be in new second with reset count)
        result = service.validate_new_order(sample_order, sample_team)

        # Then - Should be accepted (limit has reset)
        assert result.status == "accepted"

    def test_rate_limit_with_real_validation_context(
        self, validator_with_rate_limit, sample_order, sample_team
    ):
        """Test rate constraint works with real ValidationContext.

        Given - Real validation context with order count
        When - Validate against rate constraint
        Then - Constraint applies correctly
        """
        # Given - Real constraint and context
        rate_constraint = OrderRateConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.ORDER_RATE,
            parameters={"max_orders_per_second": 2},
            error_code="RATE_LIMIT",
            error_message="Rate limit exceeded",
        )

        # Test under limit
        context_under = ValidationContext(
            order=sample_order,
            trader_id=sample_team.team_id,
            trader_role=sample_team.role,
            current_positions={},
            orders_this_second=1,  # Under limit of 2
        )

        # Test at limit
        context_at_limit = ValidationContext(
            order=sample_order,
            trader_id=sample_team.team_id,
            trader_role=sample_team.role,
            current_positions={},
            orders_this_second=2,  # At limit of 2
        )

        # When - Check constraint
        result_under = rate_constraint.check(context_under, config)
        result_at_limit = rate_constraint.check(context_at_limit, config)

        # Then - Under limit passes, at limit fails
        assert result_under.is_valid is True
        assert result_at_limit.is_valid is False
        assert "Already submitted" in result_at_limit.error_detail

    def test_multiple_teams_independent_rate_limits(
        self, service, sample_order, sample_team
    ):
        """Test that different teams have independent rate limits.

        Given - Two teams with same rate limit
        When - One team hits limit, other submits order
        Then - Other team's order is not affected
        """
        # Given - Two teams
        team_a = sample_team
        team_b = TeamInfo(
            team_id="TEAM_002",
            team_name="Team B",
            role="test_role",
            api_key="test-key-b",
            created_at=sample_team.created_at,
        )

        # Mock service to show team A at limit, team B under limit
        def mock_get_count(team_id, current_time=None):
            if team_id == "TEAM_001":
                return 3  # Team A at limit
            else:
                return 1  # Team B under limit

        service.get_order_count = mock_get_count
        service.increment_order_count = Mock()

        # When - Each team submits order
        result_a = service.validate_new_order(sample_order, team_a)

        order_b = Order(
            instrument_id=sample_order.instrument_id,
            side=sample_order.side,
            quantity=sample_order.quantity,
            order_type=sample_order.order_type,
            price=sample_order.price,
            trader_id="TEAM_002",
        )
        result_b = service.validate_new_order(order_b, team_b)

        # Then - Team A blocked, Team B allowed
        assert result_a.status == "rejected"  # Team A at limit
        assert result_b.status == "accepted"  # Team B under limit
