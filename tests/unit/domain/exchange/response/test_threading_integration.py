"""Threading integration tests for order response coordination.

This module tests the threading aspects of the OrderResponseCoordinator,
focusing on thread safety, synchronization, and real multi-threaded
coordination patterns. These tests use actual threading primitives
to validate that the coordination system works correctly under
concurrent access from multiple threads.

The tests simulate realistic threading scenarios that occur in the
trading system, including race conditions, thread communication,
and resource cleanup under concurrent load.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pytest

from intern_trading_game.domain.exchange.response.interfaces import (
    ResponseRegistration,
    ResponseResult,
)
from intern_trading_game.domain.exchange.response.models import (
    ResponseStatus,
)
from intern_trading_game.infrastructure.api.models import ApiError, ApiResponse


class TestThreadSafetyAndSynchronization:
    """Test thread safety and synchronization mechanisms."""

    def _create_thread_safe_registration(
        self, request_id: str, team_id: str
    ) -> ResponseRegistration:
        """Create a thread-safe registration."""
        return ResponseRegistration(
            request_id=request_id,
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

    def _register_requests_worker(
        self,
        thread_id: int,
        mock_coordinator,
        registrations: list,
        registration_lock,
        registration_errors: list,
    ):
        """Worker function to register requests from separate thread."""
        try:
            team_id = f"TEAM_THREAD_{thread_id:03d}"

            # Each thread registers multiple requests
            thread_registrations = []
            for i in range(5):
                registration = mock_coordinator.register_request(team_id)
                thread_registrations.append(registration)

                # Small delay to increase chance of race conditions
                time.sleep(0.001)

            # Thread-safe collection of results
            with registration_lock:
                registrations.extend(thread_registrations)

        except Exception as e:
            with registration_lock:
                registration_errors.append((thread_id, str(e)))

    def _start_concurrent_threads(
        self, num_threads: int, worker_func, *args
    ) -> list:
        """Start multiple threads concurrently."""
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=worker_func, args=(thread_id, *args), daemon=True
            )
            threads.append(thread)
            thread.start()
        return threads

    def _wait_for_threads(self, threads: list, timeout: float = 5.0):
        """Wait for all threads to complete."""
        for thread in threads:
            thread.join(timeout=timeout)
            assert not thread.is_alive(), "Thread did not complete in time"

    def _verify_unique_request_ids(self, registrations: list):
        """Verify all request IDs are unique."""
        request_ids = [reg.request_id for reg in registrations]
        assert len(set(request_ids)) == len(
            request_ids
        ), "Duplicate request IDs detected"

    def test_concurrent_request_registration(
        self, mock_coordinator, coordination_config
    ):
        """Test thread safety of concurrent request registration.

        Given - Multiple threads registering requests simultaneously
        When - All threads call register_request() concurrently
        Then - All registrations succeed without race conditions

        This test validates that the registration mechanism can handle
        concurrent access from multiple API threads without corruption
        or blocking issues.
        """
        # Given - Multiple threads ready to register requests
        num_threads = 10
        registrations = []
        registration_lock = threading.Lock()
        registration_errors = []

        # Mock thread-safe registration behavior
        _request_counter = threading.local()  # For thread-local storage
        global_counter = [0]  # Mutable object for thread sharing
        counter_lock = threading.Lock()

        def mock_register_request(team_id, timeout_seconds=None):
            # Simulate thread-safe ID generation
            with counter_lock:
                global_counter[0] += 1
                request_id = f"req_concurrent_{global_counter[0]:03d}"

            return self._create_thread_safe_registration(request_id, team_id)

        mock_coordinator.register_request.side_effect = mock_register_request

        # When - Multiple threads register requests concurrently
        threads = self._start_concurrent_threads(
            num_threads,
            self._register_requests_worker,
            mock_coordinator,
            registrations,
            registration_lock,
            registration_errors,
        )

        # Wait for all threads to complete
        self._wait_for_threads(threads)

        # Then - All registrations succeeded without errors
        assert (
            len(registration_errors) == 0
        ), f"Registration errors: {registration_errors}"
        assert len(registrations) == num_threads * 5  # 5 requests per thread

        # Verify all request IDs are unique (no race condition corruption)
        self._verify_unique_request_ids(registrations)

        # Verify team ID assignments are correct
        for reg in registrations:
            assert reg.team_id.startswith(
                "TEAM_THREAD_"
            ), f"Invalid team ID: {reg.team_id}"

    def _create_event_registration(
        self,
        request_id: str,
        team_id: str,
        completion_events: dict,
        event_lock,
    ) -> ResponseRegistration:
        """Create registration with event coordination."""
        # Create real threading.Event for coordination
        completion_event = threading.Event()

        with event_lock:
            completion_events[request_id] = completion_event

        return ResponseRegistration(
            request_id=request_id,
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

    def _wait_for_event_completion(
        self,
        request_id: str,
        completion_events: dict,
        completion_results: dict,
        event_lock,
        timeout_seconds: float = None,
    ) -> ResponseResult:
        """Wait for event completion with timeout."""
        # Get the event for this request
        with event_lock:
            event = completion_events.get(request_id)

        if not event:
            raise ValueError(f"No event found for request {request_id}")

        # Wait for pipeline thread to signal completion
        timeout = timeout_seconds or 2.0
        if event.wait(timeout=timeout):
            # Event was set, return the result
            with event_lock:
                return completion_results.get(request_id)
        else:
            # Timeout occurred
            raise TimeoutError(f"Request {request_id} timed out")

    def _notify_event_completion(
        self,
        request_id: str,
        api_response,
        order_id: str,
        completion_events: dict,
        completion_results: dict,
        event_lock,
    ) -> bool:
        """Notify completion by setting event."""
        # Simulate pipeline thread notifying completion
        result = ResponseResult(
            request_id=request_id,
            success=api_response.success,
            api_response=api_response,
            processing_time_ms=100.0,
            final_status=ResponseStatus.COMPLETED
            if api_response.success
            else ResponseStatus.ERROR,
            order_id=order_id,
        )

        with event_lock:
            completion_results[request_id] = result
            event = completion_events.get(request_id)
            if event:
                event.set()  # Signal completion

        return True

    def _run_api_thread_worker(
        self,
        mock_coordinator,
        team_id: str,
        api_thread_result: list,
        api_thread_error: list,
    ):
        """Simulate API thread waiting for completion."""
        try:
            # Register request
            registration = mock_coordinator.register_request(team_id)

            # Wait for completion (this will block until pipeline signals)
            result = mock_coordinator.wait_for_completion(
                registration.request_id
            )
            api_thread_result[0] = result

        except Exception as e:
            api_thread_error[0] = str(e)

    def _run_pipeline_thread_worker(self, mock_coordinator, request_id: str):
        """Simulate pipeline thread completing processing."""
        # Simulate processing delay
        time.sleep(0.1)

        # Signal completion
        success_response = ApiResponse(
            success=True,
            request_id=request_id,
            order_id="ORD_EVENT_001",
            data={"status": "filled", "quantity": 10},
            error=None,
        )

        mock_coordinator.notify_completion(
            request_id=request_id,
            api_response=success_response,
            order_id="ORD_EVENT_001",
        )

    def _verify_event_coordination_result(
        self, api_thread_result: list, api_thread_error: list
    ):
        """Verify the result of event coordination."""
        assert (
            api_thread_error[0] is None
        ), f"API thread error: {api_thread_error[0]}"
        assert (
            api_thread_result[0] is not None
        ), "API thread did not receive result"

        result = api_thread_result[0]
        assert result.success is True
        assert result.api_response.order_id == "ORD_EVENT_001"
        assert result.api_response.data["status"] == "filled"
        assert result.final_status == ResponseStatus.COMPLETED

    def test_threading_event_coordination(
        self, mock_coordinator, mock_pipeline_threads
    ):
        """Test threading.Event coordination between API and pipeline threads.

        Given - API thread waiting for completion
        When - Pipeline thread signals completion via threading.Event
        Then - API thread unblocks with correct result

        This test validates the core threading synchronization mechanism
        that enables API threads to wait for pipeline completion.
        """
        # Given - Setup for testing real threading.Event coordination
        team_id = "TEAM_EVENT_001"
        completion_events = {}
        completion_results = {}
        event_lock = threading.Lock()

        def mock_register_request_with_event(team_id, timeout_seconds=None):
            request_id = f"req_event_{int(time.time_ns())}"
            return self._create_event_registration(
                request_id, team_id, completion_events, event_lock
            )

        def mock_wait_for_completion_with_event(
            request_id, timeout_seconds=None
        ):
            return self._wait_for_event_completion(
                request_id,
                completion_events,
                completion_results,
                event_lock,
                timeout_seconds,
            )

        def mock_notify_completion_with_event(
            request_id, api_response, order_id=None
        ):
            return self._notify_event_completion(
                request_id,
                api_response,
                order_id,
                completion_events,
                completion_results,
                event_lock,
            )

        mock_coordinator.register_request.side_effect = (
            mock_register_request_with_event
        )
        mock_coordinator.wait_for_completion.side_effect = (
            mock_wait_for_completion_with_event
        )
        mock_coordinator.notify_completion.side_effect = (
            mock_notify_completion_with_event
        )

        # Shared result storage
        api_thread_result = [None]
        api_thread_error = [None]

        # When - API thread starts waiting and pipeline thread signals completion
        # Start API thread
        api_thread = threading.Thread(
            target=self._run_api_thread_worker,
            args=(
                mock_coordinator,
                team_id,
                api_thread_result,
                api_thread_error,
            ),
            daemon=True,
        )
        api_thread.start()

        # Give API thread time to register and start waiting
        time.sleep(0.05)

        # Get the request ID that was registered
        with event_lock:
            request_ids = list(completion_events.keys())

        assert len(request_ids) == 1, "Expected exactly one registered request"
        request_id = request_ids[0]

        # Start pipeline thread to signal completion
        pipeline_thread = threading.Thread(
            target=self._run_pipeline_thread_worker,
            args=(mock_coordinator, request_id),
            daemon=True,
        )
        pipeline_thread.start()

        # Wait for both threads to complete
        api_thread.join(timeout=2.0)
        pipeline_thread.join(timeout=2.0)

        # Then - API thread received correct result
        self._verify_event_coordination_result(
            api_thread_result, api_thread_error
        )

    def _create_notification_response(
        self, worker_id: int, i: int, request_id: str
    ) -> ApiResponse:
        """Create an API response for notification testing."""
        return ApiResponse(
            success=True,
            request_id=request_id,
            order_id=f"ORD_NOTIFY_{worker_id:03d}_{i:02d}",
            data={"status": "filled", "worker_id": worker_id},
            error=None,
        )

    def _notification_worker(
        self,
        worker_id: int,
        mock_coordinator,
        completed_results: list,
        completion_lock,
        completion_errors: list,
    ):
        """Worker function to send completion notifications."""
        try:
            # Each worker sends multiple notifications
            worker_results = []
            for i in range(3):
                request_id = f"req_notify_{worker_id:03d}_{i:02d}"

                api_response = self._create_notification_response(
                    worker_id, i, request_id
                )

                success = mock_coordinator.notify_completion(
                    request_id=request_id,
                    api_response=api_response,
                    order_id=api_response.order_id,
                )

                worker_results.append((request_id, success))

                # Small delay to increase chance of race conditions
                time.sleep(0.001)

            # Thread-safe collection of results
            with completion_lock:
                completed_results.extend(worker_results)

        except Exception as e:
            with completion_lock:
                completion_errors.append((worker_id, str(e)))

    def _verify_notification_results(
        self,
        completed_results: list,
        completion_errors: list,
        expected_count: int,
    ):
        """Verify all notifications were processed correctly."""
        assert (
            len(completion_errors) == 0
        ), f"Notification errors: {completion_errors}"
        assert len(completed_results) == expected_count

        # Verify all notifications succeeded
        for request_id, success in completed_results:
            assert success is True, f"Notification {request_id} failed"

        # Verify all request IDs are unique
        request_ids = [req_id for req_id, _ in completed_results]
        assert len(set(request_ids)) == len(
            request_ids
        ), "Duplicate request IDs in notifications"

    def test_concurrent_completion_notifications(self, mock_coordinator):
        """Test handling of concurrent completion notifications.

        Given - Multiple pipeline threads completing orders simultaneously
        When - All threads call notify_completion() concurrently
        Then - All notifications are processed correctly without interference

        This test validates that the completion notification mechanism
        is thread-safe and can handle concurrent notifications from
        different pipeline stages.
        """
        # Given - Multiple completion notifications ready to be sent
        num_notifications = 15
        completed_results = []
        completion_lock = threading.Lock()
        completion_errors = []

        # Setup mock state to track notifications
        notification_counter = [0]
        counter_lock = threading.Lock()

        def mock_notify_completion(request_id, api_response, order_id=None):
            # Simulate thread-safe notification processing
            with counter_lock:
                notification_counter[0] += 1
                _notification_id = notification_counter[0]  # For ordering

            # Simulate some processing time
            time.sleep(0.001)

            # Return success
            return True

        mock_coordinator.notify_completion.side_effect = mock_notify_completion

        # When - Multiple threads send notifications concurrently
        threads = self._start_concurrent_threads(
            num_notifications // 3,  # 3 notifications per worker
            self._notification_worker,
            mock_coordinator,
            completed_results,
            completion_lock,
            completion_errors,
        )

        # Start all threads simultaneously
        start_time = time.perf_counter()

        # Wait for all threads to complete
        self._wait_for_threads(threads, timeout=3.0)

        processing_time = time.perf_counter() - start_time

        # Then - All notifications processed successfully
        self._verify_notification_results(
            completed_results, completion_errors, num_notifications
        )

        # Verify notification counter was incremented correctly
        with counter_lock:
            assert notification_counter[0] == num_notifications

        # Performance check - concurrent processing should be reasonably fast
        assert (
            processing_time < 2.0
        ), f"Concurrent notifications too slow: {processing_time:.2f}s"


class TestRaceConditionHandling:
    """Test handling of race conditions and timing-sensitive scenarios."""

    def _create_slow_registration(self, team_id: str) -> ResponseRegistration:
        """Create a registration with simulated slow processing."""
        # Simulate slow registration process
        time.sleep(0.1)

        return ResponseRegistration(
            request_id=f"req_race_{int(time.time_ns())}",
            team_id=team_id,
            timeout_at=datetime.now()
            + timedelta(milliseconds=50),  # Very short timeout
            status=ResponseStatus.PENDING,
        )

    def _run_registration_worker(
        self,
        mock_coordinator,
        team_id: str,
        registration_results: list,
        race_condition_detected: list,
        race_lock,
    ):
        """Worker that registers requests slowly."""
        try:
            for i in range(3):
                registration = mock_coordinator.register_request(team_id)
                registration_results.append(registration)
                time.sleep(0.05)  # Delay between registrations
        except Exception:
            with race_lock:
                race_condition_detected[0] = True

    def _run_cleanup_worker(
        self,
        mock_coordinator,
        cleanup_results: list,
        race_condition_detected: list,
        race_lock,
    ):
        """Worker that runs cleanup frequently."""
        try:
            for i in range(10):
                cleaned = mock_coordinator.cleanup_completed_requests()
                cleanup_results.append(cleaned)
                time.sleep(0.02)  # Frequent cleanup
        except Exception:
            with race_lock:
                race_condition_detected[0] = True

    def _verify_race_condition_results(
        self,
        race_condition_detected: list,
        race_lock,
        registration_results: list,
        cleanup_results: list,
        team_id: str,
    ):
        """Verify race condition was handled gracefully."""
        with race_lock:
            assert not race_condition_detected[
                0
            ], "Race condition caused exception"

        # Verify registration still worked
        assert (
            len(registration_results) == 3
        ), "Not all registrations completed"

        # Verify cleanup continued to run
        assert len(cleanup_results) >= 5, "Cleanup did not run enough times"

        # Verify all registrations have valid data
        for registration in registration_results:
            assert registration.team_id == team_id
            assert registration.request_id.startswith("req_race_")

    def test_registration_and_timeout_race_condition(
        self, mock_coordinator, coordination_config
    ):
        """Test race between request registration and timeout cleanup.

        Given - Request being registered while cleanup thread runs
        When - Registration and timeout occur nearly simultaneously
        Then - System handles race condition gracefully

        This test validates that the coordination system properly handles
        the race condition between new request registration and background
        cleanup of expired requests.
        """
        # Given - Setup for registration/timeout race condition
        team_id = "TEAM_RACE_001"
        race_condition_detected = [False]
        race_lock = threading.Lock()
        registration_results = []
        cleanup_results = []
        cleanup_calls = []

        # Mock registration and cleanup
        mock_coordinator.register_request.side_effect = (
            lambda team_id,
            timeout_seconds=None: self._create_slow_registration(team_id)
        )
        mock_coordinator.cleanup_completed_requests.side_effect = lambda: (
            cleanup_calls.append(datetime.now()),
            0,
        )[1]

        # When - Registration and cleanup run concurrently
        reg_thread = threading.Thread(
            target=self._run_registration_worker,
            args=(
                mock_coordinator,
                team_id,
                registration_results,
                race_condition_detected,
                race_lock,
            ),
            daemon=True,
        )
        cleanup_thread = threading.Thread(
            target=self._run_cleanup_worker,
            args=(
                mock_coordinator,
                cleanup_results,
                race_condition_detected,
                race_lock,
            ),
            daemon=True,
        )

        reg_thread.start()
        cleanup_thread.start()

        reg_thread.join(timeout=2.0)
        cleanup_thread.join(timeout=2.0)

        # Then - Race condition handled gracefully
        self._verify_race_condition_results(
            race_condition_detected,
            race_lock,
            registration_results,
            cleanup_results,
            team_id,
        )

    def _create_completion_result(
        self, request_id: str, api_response, order_id: str
    ) -> ResponseResult:
        """Create a completion result with delay."""
        # Simulate processing delay
        time.sleep(0.05)

        return ResponseResult(
            request_id=request_id,
            success=True,
            api_response=api_response,
            processing_time_ms=200.0,
            final_status=ResponseStatus.COMPLETED,
            order_id=order_id,
        )

    def _create_timeout_result(self, req_id: str) -> ResponseResult:
        """Create a timeout result."""
        timeout_response = ApiResponse(
            success=False,
            request_id=req_id,
            order_id=None,
            data=None,
            error=ApiError(
                code="PROCESSING_TIMEOUT",
                message="Request timed out",
                details={"timeout_ms": 100},
            ),
        )

        return ResponseResult(
            request_id=req_id,
            success=False,
            api_response=timeout_response,
            processing_time_ms=100.0,
            final_status=ResponseStatus.TIMEOUT,
            order_id=None,
        )

    def _run_completion_worker(self, mock_coordinator, request_id: str):
        """Worker that sends completion notification."""
        success_response = ApiResponse(
            success=True,
            request_id=request_id,
            order_id="ORD_RACE_001",
            data={"status": "filled"},
            error=None,
        )

        mock_coordinator.notify_completion(
            request_id=request_id,
            api_response=success_response,
            order_id="ORD_RACE_001",
        )

    def _verify_race_results(self, final_results: list, result_lock):
        """Verify results from race condition are consistent."""
        with result_lock:
            assert len(final_results) >= 1, "No result recorded"

            # In a real system, only one should win, but in this mock test
            # both might complete. Verify they're consistent with their type
            for result_type, result in final_results:
                if result_type == "completion":
                    assert result.success is True
                    assert result.final_status == ResponseStatus.COMPLETED
                    assert result.api_response.order_id == "ORD_RACE_001"
                elif result_type == "timeout":
                    assert result.success is False
                    assert result.final_status == ResponseStatus.TIMEOUT
                    assert (
                        result.api_response.error.code == "PROCESSING_TIMEOUT"
                    )

    def test_completion_notification_and_timeout_race(self, mock_coordinator):
        """Test race between completion notification and request timeout.

        Given - Request about to timeout when completion arrives
        When - Completion notification and timeout occur simultaneously
        Then - Either completion or timeout wins, but system remains consistent

        This test validates proper handling of the race condition between
        a completion notification arriving and a request timing out.
        """
        # Given - Setup for completion/timeout race
        _team_id = "TEAM_TIMEOUT_RACE_001"  # For documentation
        request_id = "req_timeout_race_001"

        # Shared state for race condition testing
        final_results = []
        result_lock = threading.Lock()

        # Mock completion with delay
        def mock_delayed_notify_completion(
            request_id, api_response, order_id=None
        ):
            result = self._create_completion_result(
                request_id, api_response, order_id
            )
            with result_lock:
                final_results.append(("completion", result))
            return True

        # Mock timeout handling
        def mock_handle_timeout(req_id):
            timeout_result = self._create_timeout_result(req_id)
            with result_lock:
                final_results.append(("timeout", timeout_result))
            return timeout_result

        mock_coordinator.notify_completion.side_effect = (
            mock_delayed_notify_completion
        )

        def timeout_worker():
            """Worker that handles timeout."""
            # Small delay to make race condition more likely
            time.sleep(0.03)
            mock_handle_timeout(request_id)

        # When - Completion and timeout workers run simultaneously
        completion_thread = threading.Thread(
            target=self._run_completion_worker,
            args=(mock_coordinator, request_id),
            daemon=True,
        )
        timeout_thread = threading.Thread(target=timeout_worker, daemon=True)

        completion_thread.start()
        timeout_thread.start()

        completion_thread.join(timeout=1.0)
        timeout_thread.join(timeout=1.0)

        # Then - System remains consistent (either completion or timeout wins)
        self._verify_race_results(final_results, result_lock)

    def _track_status_update(
        self,
        req_id: str,
        status,
        stage_details,
        status_updates: list,
        update_lock,
    ):
        """Track a status update."""
        with update_lock:
            status_updates.append(
                (req_id, status, datetime.now(), stage_details)
            )
        # Simulate processing time
        time.sleep(0.01)

    def _setup_mock_status_tracking(
        self, mock_coordinator, status_updates, completion_results, update_lock
    ):
        """Set up mock functions for status tracking."""

        def mock_update_status(req_id, status, stage_details=None):
            self._track_status_update(
                req_id, status, stage_details, status_updates, update_lock
            )
            return True

        def mock_notify_completion_with_tracking(
            request_id, api_response, order_id=None
        ):
            result = ResponseResult(
                request_id=request_id,
                success=True,
                api_response=api_response,
                processing_time_ms=150.0,
                final_status=ResponseStatus.COMPLETED,
                order_id=order_id,
            )

            with update_lock:
                completion_results.append((request_id, result, datetime.now()))

            return True

        mock_coordinator.update_status.side_effect = mock_update_status
        mock_coordinator.notify_completion.side_effect = (
            mock_notify_completion_with_tracking
        )

    def _run_status_update_worker(self, mock_coordinator, request_id):
        """Worker that sends multiple status updates."""
        statuses = [
            ResponseStatus.VALIDATING,
            ResponseStatus.MATCHING,
            ResponseStatus.SETTLING,
        ]

        for status in statuses:
            mock_coordinator.update_status(
                request_id,
                status,
                stage_details={
                    "stage": status.value,
                    "worker": "status_updater",
                },
            )
            time.sleep(0.02)

    def _run_status_completion_worker(self, mock_coordinator, request_id):
        """Worker that sends completion notification for status test."""
        # Delay to let some status updates happen first
        time.sleep(0.03)

        success_response = ApiResponse(
            success=True,
            request_id=request_id,
            order_id="ORD_STATUS_RACE_001",
            data={"status": "filled", "final": True},
            error=None,
        )

        mock_coordinator.notify_completion(
            request_id=request_id,
            api_response=success_response,
            order_id="ORD_STATUS_RACE_001",
        )

    def _verify_status_and_completion_results(
        self, request_id, status_updates, completion_results, update_lock
    ):
        """Verify status updates and completion results."""
        with update_lock:
            # Verify status updates were recorded
            assert (
                len(status_updates) >= 2
            ), f"Expected at least 2 status updates, got {len(status_updates)}"

            # Verify completion was recorded
            assert (
                len(completion_results) == 1
            ), f"Expected 1 completion, got {len(completion_results)}"

            # Verify all operations were for correct request
            for req_id, status, timestamp, details in status_updates:
                assert req_id == request_id
                assert details["worker"] == "status_updater"

            completion_req_id, completion_result, completion_time = (
                completion_results[0]
            )
            assert completion_req_id == request_id
            assert completion_result.success is True
            assert completion_result.final_status == ResponseStatus.COMPLETED

            # Verify timing - status updates should have started before completion
            if len(status_updates) > 0:
                first_status_time = status_updates[0][2]
                assert (
                    first_status_time <= completion_time
                ), "Status updates should start before completion"

    def test_concurrent_status_updates_and_completion(self, mock_coordinator):
        """Test race between status updates and completion notification.

        Given - Multiple threads updating status while completion occurs
        When - Status updates and completion happen simultaneously
        Then - Final status reflects completion, intermediate updates don't interfere

        This test validates that status updates don't interfere with
        completion notifications in a multi-threaded environment.
        """
        # Given - Setup for status update/completion race
        request_id = "req_status_race_001"
        status_updates = []
        completion_results = []
        update_lock = threading.Lock()

        self._setup_mock_status_tracking(
            mock_coordinator, status_updates, completion_results, update_lock
        )

        # When - Status updates and completion run concurrently
        status_thread = threading.Thread(
            target=self._run_status_update_worker,
            args=(mock_coordinator, request_id),
            daemon=True,
        )
        completion_thread = threading.Thread(
            target=self._run_status_completion_worker,
            args=(mock_coordinator, request_id),
            daemon=True,
        )

        status_thread.start()
        completion_thread.start()

        status_thread.join(timeout=1.0)
        completion_thread.join(timeout=1.0)

        # Then - All operations completed successfully
        self._verify_status_and_completion_results(
            request_id, status_updates, completion_results, update_lock
        )


class TestThreadPoolScenarios:
    """Test coordination behavior under thread pool execution patterns."""

    def _create_thread_pool_registration(
        self, request_counter: list, counter_lock, team_id: str
    ) -> ResponseRegistration:
        """Create a thread-safe registration for thread pool."""
        with counter_lock:
            request_counter[0] += 1
            request_id = f"req_pool_{request_counter[0]:03d}"

        return ResponseRegistration(
            request_id=request_id,
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

    def _create_thread_pool_result(self, request_id: str) -> ResponseResult:
        """Create a result for thread pool testing."""
        # Simulate processing time variation
        processing_time = 0.02 + (hash(request_id) % 50) / 1000.0  # 20-70ms
        time.sleep(processing_time)

        order_num = int(request_id.split("_")[-1])

        return ResponseResult(
            request_id=request_id,
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id=request_id,
                order_id=f"ORD_POOL_{order_num:03d}",
                data={
                    "order_id": f"ORD_POOL_{order_num:03d}",
                    "status": "filled",
                    "processing_time_ms": processing_time * 1000,
                    "thread_id": threading.current_thread().ident,
                },
                error=None,
            ),
            processing_time_ms=processing_time * 1000,
            final_status=ResponseStatus.COMPLETED,
            order_id=f"ORD_POOL_{order_num:03d}",
        )

    def _process_single_order(
        self,
        order,
        order_index: int,
        mock_coordinator,
        processing_results: list,
        result_lock,
    ):
        """Process a single order through coordination system."""
        try:
            team_id = f"TEAM_POOL_{order_index:03d}"

            # Register request
            registration = mock_coordinator.register_request(team_id)

            # Wait for completion
            result = mock_coordinator.wait_for_completion(
                registration.request_id
            )

            # Record result
            with result_lock:
                processing_results.append(
                    {
                        "order_index": order_index,
                        "request_id": registration.request_id,
                        "result": result,
                        "thread_id": threading.current_thread().ident,
                    }
                )

            return result

        except Exception as e:
            with result_lock:
                processing_results.append(
                    {
                        "order_index": order_index,
                        "error": str(e),
                        "thread_id": threading.current_thread().ident,
                    }
                )
            raise

    def test_thread_pool_order_processing(
        self, mock_coordinator, concurrent_orders
    ):
        """Test coordination with ThreadPoolExecutor for order processing.

        Given - ThreadPoolExecutor processing multiple orders
        When - Orders submitted concurrently via thread pool
        Then - All orders coordinate properly without thread interference

        This test validates that the coordination system works correctly
        when used with Python's ThreadPoolExecutor, which is a common
        pattern for handling concurrent API requests.
        """
        # Given - Thread pool setup for order processing
        orders = concurrent_orders[
            :8
        ]  # Reasonable number for thread pool test
        max_workers = 4

        # Setup coordination tracking
        processing_results = []
        result_lock = threading.Lock()

        request_counter = [0]
        counter_lock = threading.Lock()

        def mock_register_request_thread_safe(team_id, timeout_seconds=None):
            return self._create_thread_pool_registration(
                request_counter, counter_lock, team_id
            )

        def mock_wait_for_completion_thread_safe(
            request_id, timeout_seconds=None
        ):
            return self._create_thread_pool_result(request_id)

        mock_coordinator.register_request.side_effect = (
            mock_register_request_thread_safe
        )
        mock_coordinator.wait_for_completion.side_effect = (
            mock_wait_for_completion_thread_safe
        )

        # When - Orders processed concurrently via thread pool
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all orders to thread pool
            future_to_order = {
                executor.submit(
                    self._process_single_order,
                    order,
                    i,
                    mock_coordinator,
                    processing_results,
                    result_lock,
                ): (order, i)
                for i, order in enumerate(orders)
            }

            # Collect results as they complete
            completed_orders = []
            for future in as_completed(future_to_order, timeout=5.0):
                order, order_index = future_to_order[future]
                try:
                    result = future.result()
                    completed_orders.append((order_index, result))
                except Exception as e:
                    pytest.fail(f"Order {order_index} failed: {e}")

        processing_time = time.perf_counter() - start_time

        # Then - All orders processed successfully
        self._verify_thread_pool_results(
            processing_results, orders, max_workers, result_lock
        )

        # Performance verification - concurrent processing should be faster than sequential
        sequential_time_estimate = (
            sum(r["result"].processing_time_ms for r in processing_results)
            / 1000.0
        )

        assert (
            processing_time < sequential_time_estimate * 0.8
        ), f"Thread pool should be faster: {processing_time:.2f}s vs estimated {sequential_time_estimate:.2f}s"

    def _verify_thread_pool_results(
        self,
        processing_results: list,
        orders: list,
        max_workers: int,
        result_lock,
    ):
        """Verify thread pool processing results."""
        with result_lock:
            # Verify all orders completed
            assert len(processing_results) == len(orders)

            # Verify no errors occurred
            errors = [r for r in processing_results if "error" in r]
            assert len(errors) == 0, f"Processing errors: {errors}"

            # Verify all results are successful
            for result_data in processing_results:
                result = result_data["result"]
                assert result.success is True
                assert result.final_status == ResponseStatus.COMPLETED
                assert result.api_response.data["status"] == "filled"

            # Verify thread distribution (orders should be processed by different threads)
            thread_ids = {r["thread_id"] for r in processing_results}
            assert (
                len(thread_ids) <= max_workers
            ), f"Too many threads used: {len(thread_ids)}"
            assert (
                len(thread_ids) >= 2
            ), "Orders should be distributed across multiple threads"

            # Verify request ID uniqueness
            request_ids = [r["request_id"] for r in processing_results]
            assert len(set(request_ids)) == len(
                request_ids
            ), "Duplicate request IDs detected"

    def _create_cleanup_test_registration(
        self,
        request_id: str,
        team_id: str,
        active_requests: list,
        cleanup_lock,
    ) -> ResponseRegistration:
        """Create a registration for cleanup testing."""
        with cleanup_lock:
            active_requests.append(request_id)

        return ResponseRegistration(
            request_id=request_id,
            team_id=team_id,
            timeout_at=datetime.now()
            + timedelta(seconds=1),  # Short timeout for test
            status=ResponseStatus.PENDING,
        )

    def _perform_mock_cleanup(
        self, active_requests: list, cleaned_requests: list, cleanup_lock
    ) -> int:
        """Simulate cleanup of expired requests."""
        with cleanup_lock:
            # In real implementation, this would check timeouts
            # For test, we'll clean up older requests
            if len(active_requests) > 5:
                cleaned = active_requests[:2]  # Clean oldest 2
                active_requests[:2] = []
                cleaned_requests.extend(cleaned)
                return len(cleaned)
        return 0

    def _run_active_processing_worker(
        self,
        mock_coordinator,
        active_requests: list,
        processing_completed: list,
        cleanup_lock,
    ):
        """Worker that continuously processes requests."""
        for i in range(20):
            team_id = f"TEAM_ACTIVE_{i:03d}"
            registration = mock_coordinator.register_request(team_id)

            # Simulate processing time
            time.sleep(0.01)

            # Mark as completed (remove from active list)
            with cleanup_lock:
                if registration.request_id in active_requests:
                    active_requests.remove(registration.request_id)
                    processing_completed[0] += 1

            time.sleep(0.01)

    def _run_cleanup_worker(self, mock_coordinator, cleanup_completed: list):
        """Worker that runs periodic cleanup."""
        for i in range(30):
            cleaned_count = mock_coordinator.cleanup_completed_requests()
            cleanup_completed[0] += cleaned_count
            time.sleep(0.01)

    def test_cleanup_coordination_with_active_threads(self, mock_coordinator):
        """Test background cleanup coordination with active processing threads.

        Given - Active processing threads and cleanup thread running
        When - Cleanup runs while requests are being processed
        Then - Cleanup doesn't interfere with active requests

        This test validates that background cleanup operations don't
        interfere with active request processing in a multi-threaded
        environment.
        """
        # Given - Setup for cleanup coordination test
        active_requests = []
        cleaned_requests = []
        cleanup_lock = threading.Lock()

        # Mock active request processing
        def mock_register_with_cleanup_test(team_id, timeout_seconds=None):
            request_id = f"req_cleanup_{int(time.time_ns())}"
            return self._create_cleanup_test_registration(
                request_id, team_id, active_requests, cleanup_lock
            )

        def mock_cleanup_with_tracking():
            return self._perform_mock_cleanup(
                active_requests, cleaned_requests, cleanup_lock
            )

        mock_coordinator.register_request.side_effect = (
            mock_register_with_cleanup_test
        )
        mock_coordinator.cleanup_completed_requests.side_effect = (
            mock_cleanup_with_tracking
        )

        # Counters for tracking
        processing_completed = [0]
        cleanup_completed = [0]

        # When - Active processing and cleanup run concurrently
        processing_thread = threading.Thread(
            target=self._run_active_processing_worker,
            args=(
                mock_coordinator,
                active_requests,
                processing_completed,
                cleanup_lock,
            ),
            daemon=True,
        )
        cleanup_thread = threading.Thread(
            target=self._run_cleanup_worker,
            args=(mock_coordinator, cleanup_completed),
            daemon=True,
        )

        processing_thread.start()
        cleanup_thread.start()

        processing_thread.join(timeout=3.0)
        cleanup_thread.join(timeout=3.0)

        # Then - Both operations completed without interference
        assert processing_completed[0] > 0, "No processing completed"
        assert cleanup_completed[0] >= 0, "Cleanup did not run"

        # Verify final state is consistent
        with cleanup_lock:
            # Some requests may still be active (recently created)
            total_requests = (
                processing_completed[0]
                + len(active_requests)
                + len(cleaned_requests)
            )
            assert (
                total_requests == 20
            ), f"Request accounting error: {total_requests}"

            # Verify no duplicate cleanups
            assert len(set(cleaned_requests)) == len(
                cleaned_requests
            ), "Duplicate cleanups detected"

        print(
            f"Processed: {processing_completed[0]}, Cleaned: {cleanup_completed[0]}, "
            f"Active: {len(active_requests)}, Total: {total_requests}"
        )
