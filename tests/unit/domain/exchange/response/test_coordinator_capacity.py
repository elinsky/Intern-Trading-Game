"""Test capacity limit behavior for OrderResponseCoordinator.

This module tests how the coordinator handles capacity limits through
its public interface. Tests focus on observable behavior when the
service reaches maximum pending requests.
"""

import threading

import pytest

from intern_trading_game.domain.exchange.response.coordinator import (
    OrderResponseCoordinator,
)
from intern_trading_game.domain.exchange.response.models import (
    CoordinationConfig,
    ResponseStatus,
)
from intern_trading_game.infrastructure.api.models import ApiResponse


class TestCapacityLimits:
    """Test service behavior at capacity limits."""

    def test_max_pending_requests_enforced(self):
        """Test registration fails when at maximum capacity.

        Given - Coordinator configured with small capacity limit
        When - Teams submit more requests than capacity allows
        Then - Requests beyond limit are rejected immediately

        This protects the service from memory exhaustion during
        high-volume trading periods when many teams submit orders
        simultaneously.
        """
        # Given - Coordinator with capacity of 3 requests
        config = CoordinationConfig(
            max_pending_requests=3,
            default_timeout_seconds=5.0,
            cleanup_interval_seconds=0,  # No cleanup thread
        )
        coordinator = OrderResponseCoordinator(config)

        try:
            # Register 3 requests (at capacity)
            registrations = []
            for i in range(3):
                reg = coordinator.register_request(f"TEAM_{i:03d}")
                registrations.append(reg)
                assert reg.status == ResponseStatus.PENDING

            # When - Try to register 4th request (over capacity)
            with pytest.raises(RuntimeError) as exc_info:
                coordinator.register_request("TEAM_OVERFLOW")

            # Then - Clear error about capacity
            assert "Service overloaded" in str(exc_info.value)
            assert "3/3 pending requests" in str(exc_info.value)

        finally:
            coordinator.shutdown()

    def test_capacity_recovery_after_completions(self):
        """Test capacity frees up as requests complete.

        Given - Coordinator at maximum capacity
        When - Some requests complete successfully
        Then - New requests can be registered in freed slots

        This ensures the service can recover from temporary
        overload conditions as orders process through the pipeline.
        """
        # Given - Coordinator with capacity of 2
        config = CoordinationConfig(
            max_pending_requests=2,
            default_timeout_seconds=5.0,
            cleanup_interval_seconds=0,
        )
        coordinator = OrderResponseCoordinator(config)

        try:
            # Fill to capacity
            reg1 = coordinator.register_request("TEAM_001")
            _reg2 = coordinator.register_request("TEAM_002")

            # Verify at capacity
            with pytest.raises(RuntimeError) as exc_info:
                coordinator.register_request("TEAM_003")
            assert "Service overloaded" in str(exc_info.value)

            # When - Complete first request
            response = ApiResponse(
                success=True,
                request_id=reg1.request_id,
                order_id="ORD_001",
            )
            success = coordinator.notify_completion(
                request_id=reg1.request_id,
                api_response=response,
                order_id="ORD_001",
            )
            assert success is True

            # Get the result to remove from pending
            result = coordinator.wait_for_completion(reg1.request_id)
            assert result.success is True

            # Then - Can register new request in freed slot
            reg3 = coordinator.register_request("TEAM_003")
            assert reg3.status == ResponseStatus.PENDING

            # Still at capacity with reg2 and reg3
            with pytest.raises(RuntimeError):
                coordinator.register_request("TEAM_004")

        finally:
            coordinator.shutdown()

    def test_shutdown_prevents_new_registrations(self):
        """Test shutdown state prevents new requests.

        Given - Coordinator beginning shutdown sequence
        When - Teams try to submit new orders
        Then - All new registrations are rejected

        This ensures clean shutdown without accepting orders
        that cannot be processed.
        """
        # Given - Normal coordinator
        config = CoordinationConfig(
            max_pending_requests=10,
            default_timeout_seconds=5.0,
            cleanup_interval_seconds=0,
        )
        coordinator = OrderResponseCoordinator(config)

        # Register one request successfully
        reg1 = coordinator.register_request("TEAM_001")
        assert reg1.status == ResponseStatus.PENDING

        # When - Shutdown coordinator
        coordinator.shutdown()

        # Then - New registrations fail
        with pytest.raises(RuntimeError) as exc_info:
            coordinator.register_request("TEAM_002")
        assert "shutting down" in str(exc_info.value)

    def test_concurrent_capacity_limit_check(self):
        """Test thread-safe capacity enforcement.

        Given - Coordinator near capacity limit
        When - Multiple threads try to register simultaneously
        Then - Exactly capacity limit requests succeed

        This verifies the capacity check is atomic and thread-safe,
        preventing race conditions that could exceed limits.
        """
        # Given - Coordinator with capacity of 5
        config = CoordinationConfig(
            max_pending_requests=5,
            default_timeout_seconds=5.0,
            cleanup_interval_seconds=0,
        )
        coordinator = OrderResponseCoordinator(config)

        try:
            # Track results from concurrent registration attempts
            successful_registrations = []
            failed_registrations = []
            lock = threading.Lock()

            def try_register(team_num):
                """Attempt to register a request."""
                try:
                    reg = coordinator.register_request(f"TEAM_{team_num:03d}")
                    with lock:
                        successful_registrations.append(reg)
                except RuntimeError as e:
                    with lock:
                        failed_registrations.append((team_num, str(e)))

            # When - 10 threads try to register (capacity is 5)
            threads = []
            for i in range(10):
                thread = threading.Thread(
                    target=try_register, args=(i,), daemon=True
                )
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join(timeout=1.0)

            # Then - Exactly 5 succeed, 5 fail
            assert len(successful_registrations) == 5
            assert len(failed_registrations) == 5

            # All failures should be capacity errors
            for _team_num, error in failed_registrations:
                assert "Service overloaded" in error

        finally:
            coordinator.shutdown()
