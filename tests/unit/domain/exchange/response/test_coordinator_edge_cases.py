"""Test business scenarios and error handling for OrderResponseCoordinator.

This module tests realistic business scenarios that can occur in production
trading systems. All tests use only the public interface defined by
OrderResponseCoordinatorInterface.

The scenarios focus on operational concerns like timeouts, concurrent
validation, cleanup behavior, and graceful shutdown.
"""

import threading
import time

import pytest

from intern_trading_game.domain.exchange.response.coordinator import (
    OrderResponseCoordinator,
)
from intern_trading_game.domain.exchange.response.models import (
    CoordinationConfig,
)
from intern_trading_game.infrastructure.api.models import ApiError, ApiResponse


class TestValidationTimeouts:
    """Test scenarios involving validation timeouts."""

    def test_validation_processing_timeout(self):
        """Test timeout when validator thread is slow or stuck.

        Given - Validator thread stuck during rate limit calculation
        When - API waits for validation response longer than timeout
        Then - Coordinator returns timeout error to API

        This scenario can occur when the validator thread encounters
        a bug, deadlock, or extremely slow operation. The API must
        return a predictable timeout rather than hanging.
        """
        # Given - Coordinator with short timeout for testing
        config = CoordinationConfig(
            default_timeout_seconds=0.2,  # 200ms timeout
            cleanup_interval_seconds=30,  # Cleanup won't interfere
        )
        coordinator = OrderResponseCoordinator(config)

        try:
            # Register request from a market maker
            team_id = "TEAM_MM_001"
            registration = coordinator.register_request(team_id)
            request_id = registration.request_id

            # When - Wait for completion (validator never responds)
            result = coordinator.wait_for_completion(
                request_id, timeout_seconds=0.2
            )

            # Then - Should get timeout error
            assert result.success is False
            assert result.api_response.error.code == "PROCESSING_TIMEOUT"
            assert "exceeded time limit" in result.api_response.error.message
            assert (
                result.processing_time_ms >= 200
            )  # At least timeout duration

            # Business impact: API returns predictable error instead of hanging,
            # allowing bots to retry or take other action

        finally:
            coordinator.shutdown()

    def test_multiple_teams_concurrent_timeout(self):
        """Test multiple teams experiencing timeouts simultaneously.

        Given - Multiple teams submit orders during validator slowdown
        When - All requests timeout at once
        Then - Each team gets their own timeout response

        This tests that timeout handling is thread-safe and doesn't
        mix up responses between teams.
        """
        # Given - Coordinator with consistent timeout
        config = CoordinationConfig(
            default_timeout_seconds=0.3,  # 300ms
            cleanup_interval_seconds=30,
        )
        coordinator = OrderResponseCoordinator(config)

        try:
            # Multiple teams submit orders
            teams = ["TEAM_HFT_001", "TEAM_MM_002", "TEAM_ARB_003"]
            registrations = {}

            # Register all requests
            for team_id in teams:
                reg = coordinator.register_request(team_id)
                registrations[team_id] = reg

            # When - All wait for completion (validator is stuck)
            results = {}
            threads = []

            def wait_for_team(team_id, request_id):
                result = coordinator.wait_for_completion(
                    request_id, timeout_seconds=0.3
                )
                results[team_id] = result

            for team_id, reg in registrations.items():
                thread = threading.Thread(
                    target=wait_for_team,
                    args=(team_id, reg.request_id),
                    daemon=True,
                )
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join(timeout=1.0)

            # Then - Each team gets their own timeout
            assert len(results) == 3
            for team_id in teams:
                result = results[team_id]
                assert result.success is False
                assert result.api_response.error.code == "PROCESSING_TIMEOUT"
                # Verify it's the correct request
                assert result.request_id == registrations[team_id].request_id

        finally:
            coordinator.shutdown()


class TestConcurrentValidation:
    """Test concurrent order validation scenarios."""

    def test_concurrent_order_validation(self):
        """Test multiple teams submitting orders simultaneously.

        Given - High-frequency trading period with many teams active
        When - 20+ validation requests arrive at once
        Then - All get proper responses with no cross-contamination

        This scenario occurs during market open or news events when
        multiple trading teams submit orders simultaneously. The
        coordinator must maintain clean isolation between requests.
        """
        # Given - Standard configuration
        config = CoordinationConfig(
            default_timeout_seconds=2.0,
            max_pending_requests=100,
            cleanup_interval_seconds=30,
        )
        coordinator = OrderResponseCoordinator(config)

        try:
            # Simulate 25 teams submitting orders concurrently
            num_teams = 25
            results = {}
            errors = []
            result_lock = threading.Lock()

            def submit_order_for_team(team_num):
                """Simulate one team's order submission."""
                try:
                    team_id = f"TEAM_{team_num:03d}"

                    # Register request
                    registration = coordinator.register_request(team_id)

                    # Simulate validator processing with variable time
                    time.sleep(0.01 + (team_num % 5) * 0.002)  # 10-18ms

                    # Create validation response
                    if team_num % 10 == 0:  # 10% rejection rate
                        response = ApiResponse(
                            success=False,
                            request_id=registration.request_id,
                            order_id=None,
                            error=ApiError(
                                code="POSITION_LIMIT_EXCEEDED",
                                message=f"Team {team_id} at position limit",
                            ),
                        )
                    else:
                        response = ApiResponse(
                            success=True,
                            request_id=registration.request_id,
                            order_id=f"ORD_{team_num:06d}",
                        )

                    # Notify completion
                    coordinator.notify_completion(
                        request_id=registration.request_id,
                        api_response=response,
                        order_id=response.order_id,
                    )

                    # Wait for result
                    result = coordinator.wait_for_completion(
                        registration.request_id
                    )

                    with result_lock:
                        results[team_id] = result

                except Exception as e:
                    with result_lock:
                        errors.append((team_num, str(e)))

            # When - All teams submit concurrently
            threads = []
            for i in range(num_teams):
                thread = threading.Thread(
                    target=submit_order_for_team, args=(i,), daemon=True
                )
                threads.append(thread)
                thread.start()

            # Wait for all to complete
            for thread in threads:
                thread.join(timeout=5.0)

            # Then - All teams got correct responses
            assert len(errors) == 0, f"Errors: {errors}"
            assert len(results) == num_teams

            # Verify no cross-contamination
            for team_id, result in results.items():
                team_num = int(team_id.split("_")[1])
                if team_num % 10 == 0:
                    # Should be rejected
                    assert result.success is False
                    assert team_id in result.api_response.error.message
                else:
                    # Should be accepted
                    assert result.success is True
                    expected_order_id = f"ORD_{team_num:06d}"
                    assert result.api_response.order_id == expected_order_id

        finally:
            coordinator.shutdown()

    def test_coordinator_cleanup_during_operation(self):
        """Test cleanup thread behavior during active trading.

        Given - Long-running system with periodic cleanup
        When - Cleanup runs while requests are being processed
        Then - Active requests unaffected, old ones cleaned

        This verifies that the background cleanup thread doesn't
        interfere with active request processing while still
        freeing memory from completed requests.
        """
        # Given - Config with aggressive cleanup for testing
        config = CoordinationConfig(
            default_timeout_seconds=2.0,
            max_pending_requests=50,
            cleanup_interval_seconds=0.2,  # Cleanup every 200ms
        )
        coordinator = OrderResponseCoordinator(config)

        try:
            completed_requests = []
            active_request = None

            # Phase 1: Complete some requests that cleanup will remove
            for i in range(5):
                team_id = f"TEAM_OLD_{i:03d}"
                reg = coordinator.register_request(team_id)

                # Complete immediately
                response = ApiResponse(
                    success=True,
                    request_id=reg.request_id,
                    order_id=f"ORD_OLD_{i:03d}",
                )
                coordinator.notify_completion(
                    request_id=reg.request_id,
                    api_response=response,
                    order_id=response.order_id,
                )

                # Get result to move to completed state
                result = coordinator.wait_for_completion(reg.request_id)
                completed_requests.append((reg.request_id, result))

            # Wait for cleanup to run at least once
            time.sleep(0.3)

            # Phase 2: Process new request while cleanup might be running
            team_id = "TEAM_ACTIVE_001"
            active_reg = coordinator.register_request(team_id)
            active_request = active_reg.request_id

            # Start processing in background
            def complete_active_request():
                time.sleep(0.1)  # Simulate processing
                response = ApiResponse(
                    success=True,
                    request_id=active_request,
                    order_id="ORD_ACTIVE_001",
                )
                coordinator.notify_completion(
                    request_id=active_request,
                    api_response=response,
                    order_id=response.order_id,
                )

            completion_thread = threading.Thread(
                target=complete_active_request, daemon=True
            )
            completion_thread.start()

            # When - Wait for active request while cleanup runs
            result = coordinator.wait_for_completion(active_request)

            # Then - Active request completes successfully
            assert result.success is True
            assert result.api_response.order_id == "ORD_ACTIVE_001"

            # Verify cleanup didn't interfere
            completion_thread.join(timeout=1.0)

            # Old requests were cleaned but that's internal state
            # We only verify the behavior we can observe

        finally:
            coordinator.shutdown()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_completion_signaled_but_no_result_stored(self):
        """Test when completion event is set but no result stored.

        Given - Threading bug where event fires without result
        When - API thread wakes up from wait
        Then - RuntimeError with clear message

        This edge case helps identify threading bugs where the
        completion event is triggered without properly storing
        the result first.
        """
        # Given - Coordinator setup
        config = CoordinationConfig(
            default_timeout_seconds=2.0,
            cleanup_interval_seconds=30,
        )
        coordinator = OrderResponseCoordinator(config)

        try:
            # Register request
            team_id = "TEAM_FAIL_001"
            registration = coordinator.register_request(team_id)
            request_id = registration.request_id

            # Access internal state to simulate the bug
            # In real scenario, this would be a threading race condition
            # where the event gets set without storing result
            with coordinator._lock:
                pending_request = coordinator._pending_requests.get(request_id)
                if pending_request:
                    # Simulate event being set without result in cache
                    pending_request.completion_event.set()
                    # Ensure no result in cache
                    if request_id in coordinator._response_cache:
                        del coordinator._response_cache[request_id]

            # When - Wait for completion finds event set but no result
            with pytest.raises(RuntimeError) as exc_info:
                coordinator.wait_for_completion(request_id)

            # Then - Clear error message for debugging
            assert "No result found for completed request" in str(
                exc_info.value
            )
            assert request_id in str(exc_info.value)

        finally:
            coordinator.shutdown()

    def test_graceful_shutdown_with_pending_validations(self):
        """Test coordinator shutdown with requests in flight.

        Given - System shutdown initiated while validations pending
        When - Coordinator shutdown() called
        Then - Pending requests handled gracefully, threads join

        This ensures clean daily shutdown procedures without
        hanging threads or lost requests.
        """
        # Given - Coordinator with pending requests
        config = CoordinationConfig(
            default_timeout_seconds=2.0,
            cleanup_interval_seconds=1.0,  # Cleanup thread active
        )
        coordinator = OrderResponseCoordinator(config)

        # Register some requests that won't complete
        pending_requests = []
        for i in range(3):
            team_id = f"TEAM_SHUTDOWN_{i:03d}"
            reg = coordinator.register_request(team_id)
            pending_requests.append(reg)

        # Start threads waiting for completion
        wait_threads = []
        results = {}

        def wait_for_request(request_id):
            try:
                result = coordinator.wait_for_completion(
                    request_id, timeout_seconds=5.0
                )
                results[request_id] = result
            except Exception as e:
                results[request_id] = f"Error: {e}"

        for reg in pending_requests:
            thread = threading.Thread(
                target=wait_for_request, args=(reg.request_id,), daemon=True
            )
            wait_threads.append(thread)
            thread.start()

        # Give threads time to start waiting
        time.sleep(0.1)

        # When - Shutdown coordinator
        start_shutdown = time.time()
        coordinator.shutdown()
        shutdown_duration = time.time() - start_shutdown

        # Then - Shutdown completes quickly
        assert shutdown_duration < 2.0, f"Shutdown took {shutdown_duration}s"

        # Wait threads should complete (with timeout)
        for thread in wait_threads:
            thread.join(timeout=3.0)
            assert not thread.is_alive(), "Wait thread still running"

        # All requests should have timed out
        assert len(results) == 3
        for request_id, result in results.items():
            if isinstance(result, str):
                # Got an error during shutdown
                assert "Error:" in result
            else:
                # Got timeout result
                assert result.success is False
                assert result.api_response.error.code == "PROCESSING_TIMEOUT"
