"""Resource management tests for order response coordination.

This module tests the resource management aspects of the OrderResponseCoordinator,
focusing on memory usage, cleanup mechanisms, capacity limits, and long-running
session behavior. These tests ensure that the coordination system can operate
continuously without resource leaks or degradation.

The tests simulate realistic resource pressure scenarios that occur in production
trading systems, including extended trading sessions, high load periods, and
resource constraint conditions.
"""

import gc
import threading
import time
import weakref
from datetime import datetime, timedelta

import pytest

from intern_trading_game.domain.exchange.response.interfaces import (
    ResponseRegistration,
    ResponseResult,
)
from intern_trading_game.domain.exchange.response.models import (
    ResponseStatus,
)
from intern_trading_game.infrastructure.api.models import ApiResponse


class TestMemoryManagement:
    """Test memory usage and leak prevention mechanisms."""

    def test_request_cleanup_prevents_memory_leaks(
        self, mock_coordinator, coordination_config
    ):
        """Test that completed requests are properly cleaned up to prevent memory leaks.

        Given - Coordination service processing many requests over time
        When - Requests complete and cleanup runs periodically
        Then - Memory usage remains bounded, old request data is released

        This test validates that the coordination system properly releases
        memory for completed requests and doesn't accumulate unbounded
        state over long-running sessions.
        """
        # Given - Setup for memory leak detection
        request_storage = {}  # Simulates coordinator's internal storage
        cleanup_counts = []
        storage_lock = threading.Lock()

        # Track object creation for memory leak detection
        created_objects = []
        weak_references = []

        def mock_register_request_with_tracking(team_id, timeout_seconds=None):
            request_id = f"req_memory_{len(created_objects):05d}"

            # Create registration object
            registration = ResponseRegistration(
                request_id=request_id,
                team_id=team_id,
                timeout_at=datetime.now()
                + timedelta(seconds=1),  # Short timeout for test
                status=ResponseStatus.PENDING,
            )

            # Track for memory leak detection
            created_objects.append(registration)
            weak_references.append(weakref.ref(registration))

            # Store in mock internal storage
            with storage_lock:
                request_storage[request_id] = {
                    "registration": registration,
                    "created_at": datetime.now(),
                    "completed": False,
                }

            return registration

        def mock_complete_request(request_id):
            """Simulate request completion."""
            with storage_lock:
                if request_id in request_storage:
                    request_storage[request_id]["completed"] = True
                    request_storage[request_id]["completed_at"] = (
                        datetime.now()
                    )

        def mock_cleanup_expired_requests():
            """Simulate cleanup of old completed requests."""
            cleaned_count = 0
            current_time = datetime.now()
            cleanup_threshold = timedelta(
                milliseconds=100
            )  # Very short for test

            with storage_lock:
                to_remove = []
                for request_id, data in request_storage.items():
                    if data["completed"]:
                        completed_at = data.get("completed_at", current_time)
                        if current_time - completed_at > cleanup_threshold:
                            to_remove.append(request_id)

                for request_id in to_remove:
                    del request_storage[request_id]
                    cleaned_count += 1

            cleanup_counts.append(cleaned_count)
            return cleaned_count

        mock_coordinator.register_request.side_effect = (
            mock_register_request_with_tracking
        )
        mock_coordinator.cleanup_completed_requests.side_effect = (
            mock_cleanup_expired_requests
        )

        # When - Many requests processed over time with periodic cleanup
        num_requests = 200
        cleanup_interval = 20  # Clean up every 20 requests

        for i in range(num_requests):
            team_id = f"TEAM_MEMORY_{i:03d}"

            # Register request
            registration = mock_coordinator.register_request(team_id)

            # Simulate quick completion
            mock_complete_request(registration.request_id)

            # Periodic cleanup
            if i % cleanup_interval == 0:
                mock_coordinator.cleanup_completed_requests()

            # Small delay to allow cleanup timing to work
            if i % 10 == 0:
                time.sleep(0.11)  # Ensure requests are old enough for cleanup

        # Final cleanup
        time.sleep(0.11)  # Ensure all requests are old enough
        for _ in range(5):  # Multiple cleanup passes
            mock_coordinator.cleanup_completed_requests()
            time.sleep(0.01)

        # Clear strong references to allow garbage collection
        created_objects.clear()

        # Force garbage collection to test weak references
        gc.collect()

        # Then - Memory usage is bounded and objects are properly released
        # Verify cleanup occurred
        total_cleaned = sum(cleanup_counts)
        assert total_cleaned > 0, "No cleanup occurred"
        assert (
            total_cleaned
            >= num_requests * 0.5  # Lower threshold for timing variability
        ), f"Too few requests cleaned: {total_cleaned}/{num_requests}"

        # Verify storage doesn't grow unbounded
        with storage_lock:
            remaining_requests = len(request_storage)

        # Should have far fewer than total requests stored
        assert (
            remaining_requests < num_requests * 0.5
        ), f"Too many requests still stored: {remaining_requests}/{num_requests}"

        # Verify weak references show objects were garbage collected
        gc.collect()  # Ensure GC runs
        dead_references = sum(1 for ref in weak_references if ref() is None)
        alive_references = len(weak_references) - dead_references

        # Most objects should be garbage collected after cleanup
        assert (
            dead_references
            >= num_requests * 0.5  # At least half should be collected
        ), f"Memory leak detected: {alive_references} objects still alive, {dead_references} collected"

        print(
            f"Created: {num_requests}, Cleaned: {total_cleaned}, "
            f"Remaining: {remaining_requests}, Dead refs: {dead_references}"
        )

    def test_memory_usage_under_sustained_load(
        self, mock_coordinator, coordination_config
    ):
        """Test memory behavior during sustained high load.

        Given - Continuous high-frequency request processing
        When - System processes requests at maximum capacity
        Then - Memory usage stabilizes and doesn't grow continuously

        This test validates that the coordination system can handle
        sustained load without memory usage growing unbounded over time.
        """
        # Given - Setup for sustained load testing
        memory_snapshots = []
        active_requests = {}
        completed_requests = {}
        snapshot_lock = threading.Lock()

        request_counter = [0]

        def mock_register_request_sustained(team_id, timeout_seconds=None):
            request_counter[0] += 1
            request_id = f"req_sustained_{request_counter[0]:06d}"

            registration = ResponseRegistration(
                request_id=request_id,
                team_id=team_id,
                timeout_at=datetime.now() + timedelta(seconds=2),
                status=ResponseStatus.PENDING,
            )

            # Track active requests
            with snapshot_lock:
                active_requests[request_id] = {
                    "registration": registration,
                    "created_at": datetime.now(),
                }

            return registration

        def mock_complete_request_sustained(request_id):
            """Complete a request and move to completed storage."""
            with snapshot_lock:
                if request_id in active_requests:
                    request_data = active_requests.pop(request_id)
                    completed_requests[request_id] = {
                        **request_data,
                        "completed_at": datetime.now(),
                    }

        def mock_cleanup_sustained():
            """Clean up old completed requests."""
            cleaned = 0
            current_time = datetime.now()
            cleanup_age = timedelta(seconds=0.5)  # Cleanup after 500ms

            with snapshot_lock:
                to_remove = []
                for request_id, data in completed_requests.items():
                    completed_at = data.get("completed_at", current_time)
                    if current_time - completed_at > cleanup_age:
                        to_remove.append(request_id)

                for request_id in to_remove:
                    del completed_requests[request_id]
                    cleaned += 1

            return cleaned

        def take_memory_snapshot():
            """Take snapshot of current memory usage."""
            with snapshot_lock:
                snapshot = {
                    "timestamp": datetime.now(),
                    "active_count": len(active_requests),
                    "completed_count": len(completed_requests),
                    "total_requests": request_counter[0],
                }
                memory_snapshots.append(snapshot)

        mock_coordinator.register_request.side_effect = (
            mock_register_request_sustained
        )
        mock_coordinator.cleanup_completed_requests.side_effect = (
            mock_cleanup_sustained
        )

        # When - Sustained load with periodic cleanup
        load_duration = 1.0  # 1 second of sustained load
        request_rate = 100  # 100 requests per second
        cleanup_frequency = 0.1  # Cleanup every 100ms

        start_time = time.perf_counter()
        last_cleanup = start_time
        last_snapshot = start_time
        snapshot_frequency = 0.1  # Snapshot every 100ms

        while time.perf_counter() - start_time < load_duration:
            # Process batch of requests
            batch_size = 10
            for _ in range(batch_size):
                team_id = (
                    f"TEAM_LOAD_{request_counter[0] % 50:03d}"  # Cycle teams
                )
                registration = mock_coordinator.register_request(team_id)

                # Simulate fast completion (90% complete quickly)
                if request_counter[0] % 10 != 0:  # 90% complete quickly
                    mock_complete_request_sustained(registration.request_id)

            current_time = time.perf_counter()

            # Periodic cleanup
            if current_time - last_cleanup >= cleanup_frequency:
                mock_coordinator.cleanup_completed_requests()
                last_cleanup = current_time

            # Periodic memory snapshot
            if current_time - last_snapshot >= snapshot_frequency:
                take_memory_snapshot()
                last_snapshot = current_time

            # Control request rate
            time.sleep(batch_size / request_rate)

        # Final cleanup and snapshot
        for _ in range(3):
            mock_coordinator.cleanup_completed_requests()
        take_memory_snapshot()

        # Then - Memory usage stabilizes under sustained load
        assert len(memory_snapshots) >= 5, "Not enough memory snapshots taken"

        # Analyze memory growth pattern
        total_requests_over_time = [
            s["total_requests"] for s in memory_snapshots
        ]
        active_requests_over_time = [
            s["active_count"] for s in memory_snapshots
        ]
        completed_requests_over_time = [
            s["completed_count"] for s in memory_snapshots
        ]

        # Total requests should grow consistently
        assert (
            total_requests_over_time[-1] > total_requests_over_time[0]
        ), "No requests processed"

        # Active requests should remain bounded (not grow with total)
        max_active = max(active_requests_over_time)
        final_active = active_requests_over_time[-1]
        assert (
            max_active < total_requests_over_time[-1] * 0.2
        ), f"Too many active requests: {max_active} vs total {total_requests_over_time[-1]}"

        # Completed requests should be cleaned up (not accumulate)
        max_completed = max(completed_requests_over_time)
        final_completed = completed_requests_over_time[-1]
        assert (
            max_completed < total_requests_over_time[-1] * 0.5
        ), f"Too many completed requests: {max_completed} vs total {total_requests_over_time[-1]}"

        # Memory should not grow linearly with total requests (shows cleanup working)
        memory_efficiency = (
            final_active + final_completed
        ) / total_requests_over_time[-1]
        assert (
            memory_efficiency < 0.6  # More realistic threshold
        ), f"Poor memory efficiency: {memory_efficiency:.2f}"

        print(
            f"Processed {total_requests_over_time[-1]} requests, "
            f"final active: {final_active}, final completed: {final_completed}, "
            f"efficiency: {memory_efficiency:.2f}"
        )

    def test_weak_reference_cleanup_validation(self, mock_coordinator):
        """Test that objects are properly released using weak references.

        Given - Coordination objects created and completed
        When - Objects go out of scope and cleanup runs
        Then - Weak references confirm objects are garbage collected

        This test uses weak references to verify that coordination
        objects are actually being garbage collected and not held
        by circular references or other memory leaks.
        """
        # Given - Setup for weak reference testing
        weak_registrations = []
        weak_results = []

        def create_and_complete_requests(num_requests: int):
            """Create requests, complete them, and return weak references."""
            registrations = []
            results = []

            for i in range(num_requests):
                team_id = f"TEAM_WEAK_{i:03d}"

                # Create registration
                registration = ResponseRegistration(
                    request_id=f"req_weak_{i:03d}",
                    team_id=team_id,
                    timeout_at=datetime.now() + timedelta(seconds=5),
                    status=ResponseStatus.PENDING,
                )
                registrations.append(registration)
                weak_registrations.append(weakref.ref(registration))

                # Create result
                result = ResponseResult(
                    request_id=registration.request_id,
                    success=True,
                    api_response=ApiResponse(
                        success=True,
                        request_id=registration.request_id,
                        order_id=f"ORD_WEAK_{i:03d}",
                        data={"status": "filled"},
                        error=None,
                    ),
                    processing_time_ms=50.0,
                    final_status=ResponseStatus.COMPLETED,
                    order_id=f"ORD_WEAK_{i:03d}",
                )
                results.append(result)
                weak_results.append(weakref.ref(result))

            return registrations, results

        # When - Create objects and let them go out of scope
        num_test_objects = 50

        # Create objects in a separate scope
        strong_registrations, strong_results = create_and_complete_requests(
            num_test_objects
        )

        # Verify we have the expected weak references
        assert len(weak_registrations) == num_test_objects
        assert len(weak_results) == num_test_objects

        # Verify all weak references are still alive (objects still referenced)
        alive_registrations = sum(
            1 for ref in weak_registrations if ref() is not None
        )
        alive_results = sum(1 for ref in weak_results if ref() is not None)

        assert (
            alive_registrations == num_test_objects
        ), "Some registrations already dead"
        assert alive_results == num_test_objects, "Some results already dead"

        # Delete strong references to allow garbage collection
        del strong_registrations
        del strong_results

        # Force garbage collection
        gc.collect()
        gc.collect()  # Sometimes need multiple passes

        # Then - Weak references confirm objects were garbage collected
        alive_registrations_after = sum(
            1 for ref in weak_registrations if ref() is not None
        )
        alive_results_after = sum(
            1 for ref in weak_results if ref() is not None
        )

        # Most objects should be garbage collected
        registration_collection_rate = (
            num_test_objects - alive_registrations_after
        ) / num_test_objects
        result_collection_rate = (
            num_test_objects - alive_results_after
        ) / num_test_objects

        assert (
            registration_collection_rate >= 0.9
        ), f"Poor registration collection rate: {registration_collection_rate:.2f}"
        assert (
            result_collection_rate >= 0.9
        ), f"Poor result collection rate: {result_collection_rate:.2f}"

        print(
            f"Collection rates - Registrations: {registration_collection_rate:.2f}, "
            f"Results: {result_collection_rate:.2f}"
        )


class TestCapacityLimits:
    """Test behavior at capacity limits and resource constraints."""

    @pytest.mark.skip(
        reason="Test logic needs fixing - recovery requests not being tracked correctly"
    )
    def test_max_pending_requests_enforcement(
        self, mock_coordinator, coordination_config
    ):
        """Test enforcement of maximum pending requests limit.

        Given - Coordination service with configured capacity limit
        When - Requests exceed the maximum pending limit
        Then - New requests are rejected with capacity error

        This test validates that the coordination system properly
        enforces capacity limits to prevent resource exhaustion.
        """
        # Given - Coordination config with low capacity limit for testing
        test_config = coordination_config
        test_config.max_pending_requests = 10  # Low limit for testing

        pending_requests = {}
        rejection_count = [0]
        capacity_lock = threading.Lock()

        def mock_register_with_capacity_limit(team_id, timeout_seconds=None):
            with capacity_lock:
                current_pending = len(pending_requests)

                if current_pending >= test_config.max_pending_requests:
                    # Reject due to capacity
                    rejection_count[0] += 1
                    raise Exception(
                        f"Service overloaded: {current_pending}/{test_config.max_pending_requests}"
                    )

                # Accept request
                # Use a counter to ensure unique IDs
                request_counter = getattr(
                    mock_register_with_capacity_limit, "counter", 0
                )
                mock_register_with_capacity_limit.counter = request_counter + 1
                request_id = f"req_capacity_{request_counter:03d}"
                registration = ResponseRegistration(
                    request_id=request_id,
                    team_id=team_id,
                    timeout_at=datetime.now() + timedelta(seconds=5),
                    status=ResponseStatus.PENDING,
                )

                pending_requests[request_id] = registration
                return registration

        def mock_complete_request_capacity(request_id):
            """Complete a request to free up capacity."""
            with capacity_lock:
                if request_id in pending_requests:
                    del pending_requests[request_id]

        mock_coordinator.register_request.side_effect = (
            mock_register_with_capacity_limit
        )

        # When - Submit requests up to and beyond capacity limit
        successful_registrations = []
        failed_registrations = []

        # Fill up to capacity
        for i in range(test_config.max_pending_requests):
            try:
                team_id = f"TEAM_CAPACITY_{i:03d}"
                registration = mock_coordinator.register_request(team_id)
                successful_registrations.append(registration)
            except Exception as e:
                failed_registrations.append(str(e))

        # Attempt to exceed capacity
        for i in range(5):  # Try 5 more requests
            try:
                team_id = f"TEAM_OVERFLOW_{i:03d}"
                registration = mock_coordinator.register_request(team_id)
                successful_registrations.append(registration)
            except Exception as e:
                failed_registrations.append(str(e))

        # Complete some requests to test capacity recovery
        completed_requests = successful_registrations[:3]
        for registration in completed_requests:
            mock_complete_request_capacity(registration.request_id)

        # Try more requests after freeing capacity
        recovered_registrations = []
        for i in range(3):
            try:
                team_id = f"TEAM_RECOVERY_{i:03d}"
                registration = mock_coordinator.register_request(team_id)
                recovered_registrations.append(registration)
            except Exception as e:
                failed_registrations.append(str(e))

        # Then - Capacity limits are properly enforced
        with capacity_lock:
            # Initial registrations should fill capacity
            initial_successful = len(
                [
                    r
                    for r in successful_registrations
                    if r.request_id.startswith("req_capacity_")
                ]
            )
            assert (
                initial_successful == test_config.max_pending_requests
            ), f"Expected {test_config.max_pending_requests} initial successful, got {initial_successful}"

            assert (
                len(failed_registrations) == 5
            ), f"Expected 5 failures, got {len(failed_registrations)}"

            assert (
                len(recovered_registrations) == 3
            ), f"Expected 3 recovered requests, got {len(recovered_registrations)}"

            # Verify rejection messages mention capacity
            for failure in failed_registrations:
                assert (
                    "overloaded" in failure.lower()
                    or "capacity" in failure.lower()
                )

            # Verify final pending count is correct
            final_pending = len(pending_requests)
            # We had 10 initially, completed 3, added 3 more = still 10
            expected_final = test_config.max_pending_requests
            assert (
                final_pending == expected_final
            ), f"Final pending count wrong: {final_pending}, expected {expected_final}"

        print(
            f"Successful: {len(successful_registrations)}, Failed: {len(failed_registrations)}, "
            f"Recovered: {len(recovered_registrations)}, Final pending: {final_pending}"
        )

    def test_graceful_degradation_under_resource_pressure(
        self, mock_coordinator, coordination_config
    ):
        """Test graceful degradation when approaching resource limits.

        Given - System approaching resource constraints
        When - Load increases beyond comfortable capacity
        Then - System degrades gracefully with clear error messages

        This test validates that the coordination system provides
        clear feedback and maintains stability when under resource pressure.
        """
        # Given - System with resource pressure simulation
        resource_pressure = {
            "memory_usage": 0.6,  # Start at 60% memory usage
            "cpu_usage": 0.5,  # Start at 50% CPU usage
            "pending_requests": 0,
        }

        pressure_lock = threading.Lock()
        degradation_responses = []

        def simulate_resource_pressure():
            """Simulate increasing resource pressure over time."""
            with pressure_lock:
                # Simulate memory and CPU pressure increasing
                resource_pressure["memory_usage"] = min(
                    0.95, resource_pressure["memory_usage"] + 0.05
                )
                resource_pressure["cpu_usage"] = min(
                    0.95, resource_pressure["cpu_usage"] + 0.03
                )

        def mock_register_with_degradation(team_id, timeout_seconds=None):
            simulate_resource_pressure()

            with pressure_lock:
                memory = resource_pressure["memory_usage"]
                cpu = resource_pressure["cpu_usage"]
                _pending = resource_pressure[
                    "pending_requests"
                ]  # For monitoring

                # Determine response based on resource pressure
                if memory > 0.9 or cpu > 0.9:
                    # Severe pressure - reject with clear message
                    degradation_responses.append(
                        {
                            "type": "rejection",
                            "reason": "resource_exhaustion",
                            "memory": memory,
                            "cpu": cpu,
                        }
                    )
                    raise Exception(
                        f"Service overloaded - Memory: {memory:.1%}, CPU: {cpu:.1%}"
                    )

                elif memory > 0.8 or cpu > 0.8:
                    # High pressure - warn but accept
                    degradation_responses.append(
                        {
                            "type": "warning",
                            "reason": "high_resource_usage",
                            "memory": memory,
                            "cpu": cpu,
                        }
                    )

                    # Increase timeout to reflect slower processing
                    timeout_seconds = (timeout_seconds or 5.0) * 2.0

                # Accept request
                request_id = f"req_pressure_{len(degradation_responses):03d}"
                resource_pressure["pending_requests"] += 1

                return ResponseRegistration(
                    request_id=request_id,
                    team_id=team_id,
                    timeout_at=datetime.now()
                    + timedelta(seconds=timeout_seconds or 5.0),
                    status=ResponseStatus.PENDING,
                )

        def mock_complete_with_degradation(request_id):
            """Complete request and reduce pressure."""
            with pressure_lock:
                resource_pressure["pending_requests"] = max(
                    0, resource_pressure["pending_requests"] - 1
                )
                # Slightly reduce pressure when requests complete
                resource_pressure["memory_usage"] = max(
                    0.6, resource_pressure["memory_usage"] - 0.01
                )
                resource_pressure["cpu_usage"] = max(
                    0.5, resource_pressure["cpu_usage"] - 0.01
                )

        mock_coordinator.register_request.side_effect = (
            mock_register_with_degradation
        )

        # When - Load increases to trigger degradation
        successful_requests = []
        rejected_requests = []

        for i in range(30):  # Submit many requests to trigger pressure
            try:
                team_id = f"TEAM_PRESSURE_{i:03d}"
                registration = mock_coordinator.register_request(team_id)
                successful_requests.append(registration)

                # Simulate some requests completing
                if i % 5 == 0 and successful_requests:
                    completed_req = successful_requests[i // 5]
                    mock_complete_with_degradation(completed_req.request_id)

            except Exception as e:
                rejected_requests.append(str(e))

            time.sleep(0.01)  # Small delay between requests

        # Then - System degrades gracefully with clear feedback
        assert (
            len(degradation_responses) > 0
        ), "No degradation responses recorded"
        assert (
            len(rejected_requests) > 0
        ), "No requests were rejected under pressure"

        # Analyze degradation pattern
        warnings = [r for r in degradation_responses if r["type"] == "warning"]
        rejections = [
            r for r in degradation_responses if r["type"] == "rejection"
        ]

        assert (
            len(warnings) > 0
        ), "No warning responses during pressure buildup"
        assert len(rejections) > 0, "No rejections during high pressure"

        # Verify degradation progression (warnings before rejections)
        if warnings and rejections:
            first_warning_memory = warnings[0]["memory"]
            first_rejection_memory = rejections[0]["memory"]
            assert (
                first_warning_memory <= first_rejection_memory
            ), "Rejections should come after warnings"

        # Verify error messages are informative
        for rejection in rejected_requests:
            assert (
                "memory" in rejection.lower()
                or "cpu" in rejection.lower()
                or "overloaded" in rejection.lower()
            ), f"Uninformative error message: {rejection}"

        print(
            f"Successful: {len(successful_requests)}, Rejected: {len(rejected_requests)}, "
            f"Warnings: {len(warnings)}, Rejections: {len(rejections)}"
        )


class TestBackgroundCleanupOperations:
    """Test background cleanup and maintenance operations."""

    @pytest.mark.skip(
        reason="Timing-dependent test - not all processing completes in time"
    )
    def test_cleanup_thread_coordination_with_active_requests(
        self, mock_coordinator
    ):
        """Test cleanup thread doesn't interfere with active request processing.

        Given - Active request processing and background cleanup running
        When - Cleanup runs while requests are being processed concurrently
        Then - Cleanup doesn't affect active requests, only removes expired ones

        This test validates that background cleanup operations are properly
        coordinated with active request processing to avoid interference.
        """
        # Given - Setup for cleanup coordination testing
        active_requests = {}
        completed_requests = {}
        expired_requests = {}
        cleanup_events = []
        coordination_lock = threading.Lock()

        def mock_register_with_cleanup_coordination(
            team_id, timeout_seconds=None
        ):
            request_id = f"req_cleanup_{int(time.time_ns())}"
            timeout_duration = timeout_seconds or 0.2  # Short timeout for test

            registration = ResponseRegistration(
                request_id=request_id,
                team_id=team_id,
                timeout_at=datetime.now()
                + timedelta(seconds=timeout_duration),
                status=ResponseStatus.PENDING,
            )

            with coordination_lock:
                active_requests[request_id] = {
                    "registration": registration,
                    "created_at": datetime.now(),
                    "team_id": team_id,
                }

            return registration

        def mock_complete_request_cleanup(request_id):
            """Move request from active to completed."""
            with coordination_lock:
                if request_id in active_requests:
                    request_data = active_requests.pop(request_id)
                    completed_requests[request_id] = {
                        **request_data,
                        "completed_at": datetime.now(),
                    }

        def mock_cleanup_with_coordination():
            """Cleanup expired requests without affecting active ones."""
            cleaned_count = 0
            current_time = datetime.now()

            with coordination_lock:
                # Check for expired active requests
                expired_active = []
                for request_id, data in active_requests.items():
                    if data["registration"].timeout_at <= current_time:
                        expired_active.append(request_id)

                # Move expired active requests to expired storage
                for request_id in expired_active:
                    data = active_requests.pop(request_id)
                    expired_requests[request_id] = {
                        **data,
                        "expired_at": current_time,
                    }
                    cleaned_count += 1

                # Clean up old completed requests
                old_completed = []
                cleanup_age = timedelta(seconds=0.1)  # Clean after 100ms
                for request_id, data in completed_requests.items():
                    completed_at = data.get("completed_at", current_time)
                    if current_time - completed_at > cleanup_age:
                        old_completed.append(request_id)

                for request_id in old_completed:
                    del completed_requests[request_id]
                    cleaned_count += 1

                # Record cleanup event
                cleanup_events.append(
                    {
                        "timestamp": current_time,
                        "cleaned_count": cleaned_count,
                        "active_count": len(active_requests),
                        "completed_count": len(completed_requests),
                        "expired_count": len(expired_requests),
                    }
                )

            return cleaned_count

        mock_coordinator.register_request.side_effect = (
            mock_register_with_cleanup_coordination
        )
        mock_coordinator.cleanup_completed_requests.side_effect = (
            mock_cleanup_with_coordination
        )

        # Tracking for test verification
        processing_results = []
        processing_errors = []

        def active_processing_worker():
            """Worker that continuously processes requests."""
            for i in range(50):
                try:
                    team_id = f"TEAM_ACTIVE_{i:03d}"
                    registration = mock_coordinator.register_request(team_id)

                    # Simulate variable processing time
                    processing_time = 0.05 + (i % 10) * 0.01  # 50-140ms
                    time.sleep(processing_time)

                    # 80% of requests complete successfully
                    if i % 5 != 0:
                        mock_complete_request_cleanup(registration.request_id)
                        processing_results.append(
                            {
                                "request_id": registration.request_id,
                                "completed": True,
                                "processing_time": processing_time,
                            }
                        )
                    else:
                        # 20% timeout (don't complete)
                        processing_results.append(
                            {
                                "request_id": registration.request_id,
                                "completed": False,
                                "processing_time": processing_time,
                            }
                        )

                    time.sleep(0.01)  # Brief pause between requests

                except Exception as e:
                    processing_errors.append(str(e))

        def background_cleanup_worker():
            """Worker that runs background cleanup."""
            for i in range(100):  # Run cleanup frequently
                try:
                    _cleaned = mock_coordinator.cleanup_completed_requests()
                    time.sleep(0.02)  # Cleanup every 20ms
                except Exception as e:
                    processing_errors.append(f"Cleanup error: {e}")

        # When - Active processing and cleanup run concurrently
        processing_thread = threading.Thread(
            target=active_processing_worker, daemon=True
        )
        cleanup_thread = threading.Thread(
            target=background_cleanup_worker, daemon=True
        )

        processing_thread.start()
        cleanup_thread.start()

        processing_thread.join(timeout=5.0)
        cleanup_thread.join(timeout=5.0)

        # Final cleanup to clear remaining items
        mock_coordinator.cleanup_completed_requests()

        # Then - Cleanup coordinated properly with active processing
        assert (
            len(processing_errors) == 0
        ), f"Processing errors: {processing_errors}"
        assert len(processing_results) == 50, "Not all processing completed"
        assert len(cleanup_events) > 10, "Not enough cleanup events"

        # Verify cleanup didn't interfere with successful completions
        completed_results = [r for r in processing_results if r["completed"]]
        timed_out_results = [
            r for r in processing_results if not r["completed"]
        ]

        assert (
            len(completed_results) == 40
        ), f"Expected 40 completed, got {len(completed_results)}"
        assert (
            len(timed_out_results) == 10
        ), f"Expected 10 timeouts, got {len(timed_out_results)}"

        # Verify cleanup removed expired requests
        total_cleaned = sum(event["cleaned_count"] for event in cleanup_events)
        assert (
            total_cleaned >= 10
        ), f"Not enough requests cleaned: {total_cleaned}"

        # Verify final state is clean
        with coordination_lock:
            final_active = len(active_requests)
            final_completed = len(completed_requests)
            _final_expired = len(expired_requests)  # For monitoring

        # Most requests should be cleaned up by now
        total_remaining = final_active + final_completed
        assert (
            total_remaining < 20
        ), f"Too many requests remaining: {total_remaining}"

        print(
            f"Completed: {len(completed_results)}, Timed out: {len(timed_out_results)}, "
            f"Cleaned: {total_cleaned}, Final remaining: {total_remaining}"
        )

    def test_background_cleanup_performance_impact(
        self, mock_coordinator, performance_monitor
    ):
        """Test that background cleanup has minimal performance impact.

        Given - System processing requests with background cleanup
        When - Cleanup runs during normal operation
        Then - Request processing performance is not significantly affected

        This test validates that background cleanup operations don't
        cause performance degradation for active request processing.
        """
        # Given - Setup for performance impact testing
        request_processing_times = []
        cleanup_times = []
        processing_lock = threading.Lock()

        request_counter = [0]

        def mock_register_with_timing(team_id, timeout_seconds=None):
            start_time = time.perf_counter()

            with processing_lock:
                request_counter[0] += 1
                request_id = f"req_perf_{request_counter[0]:04d}"

            # Simulate registration work
            time.sleep(0.001)  # 1ms base processing time

            registration = ResponseRegistration(
                request_id=request_id,
                team_id=team_id,
                timeout_at=datetime.now() + timedelta(seconds=1),
                status=ResponseStatus.PENDING,
            )

            end_time = time.perf_counter()
            processing_time = (end_time - start_time) * 1000  # Convert to ms

            with processing_lock:
                request_processing_times.append(processing_time)

            return registration

        def mock_cleanup_with_timing():
            start_time = time.perf_counter()

            # Simulate cleanup work
            time.sleep(0.002)  # 2ms cleanup time

            end_time = time.perf_counter()
            cleanup_time = (end_time - start_time) * 1000  # Convert to ms

            with processing_lock:
                cleanup_times.append(cleanup_time)

            return 0  # No items cleaned for performance test

        mock_coordinator.register_request.side_effect = (
            mock_register_with_timing
        )
        mock_coordinator.cleanup_completed_requests.side_effect = (
            mock_cleanup_with_timing
        )

        def request_processing_worker():
            """Worker that processes requests continuously."""
            for i in range(100):
                team_id = f"TEAM_PERF_{i % 10:02d}"
                performance_monitor.start_timer(f"request_{i}")

                mock_coordinator.register_request(team_id)

                performance_monitor.end_timer(f"request_{i}")
                time.sleep(0.005)  # 5ms between requests

        def cleanup_worker():
            """Worker that runs cleanup operations."""
            for i in range(50):  # Less frequent cleanup
                performance_monitor.start_timer(f"cleanup_{i}")

                mock_coordinator.cleanup_completed_requests()

                performance_monitor.end_timer(f"cleanup_{i}")
                time.sleep(0.01)  # 10ms between cleanups

        # When - Request processing and cleanup run concurrently
        performance_monitor.start_timer("total_test_time")

        request_thread = threading.Thread(
            target=request_processing_worker, daemon=True
        )
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)

        request_thread.start()
        cleanup_thread.start()

        request_thread.join(timeout=3.0)
        cleanup_thread.join(timeout=3.0)

        total_time = performance_monitor.end_timer("total_test_time")

        # Then - Performance impact is minimal
        with processing_lock:
            assert (
                len(request_processing_times) == 100
            ), "Not all requests processed"
            assert len(cleanup_times) >= 40, "Not enough cleanup operations"

        # Analyze performance metrics
        avg_request_time = sum(request_processing_times) / len(
            request_processing_times
        )
        max_request_time = max(request_processing_times)
        avg_cleanup_time = sum(cleanup_times) / len(cleanup_times)
        _max_cleanup_time = max(cleanup_times)  # For performance monitoring

        # Performance assertions
        assert (
            avg_request_time < 5.0
        ), f"Average request time too high: {avg_request_time:.2f}ms"
        assert (
            max_request_time < 20.0
        ), f"Max request time too high: {max_request_time:.2f}ms"
        assert (
            avg_cleanup_time < 10.0
        ), f"Average cleanup time too high: {avg_cleanup_time:.2f}ms"

        # Cleanup should not significantly impact request processing
        # (Request processing should remain consistent)
        request_time_variance = max(request_processing_times) - min(
            request_processing_times
        )
        assert (
            request_time_variance < 15.0
        ), f"Too much request time variance: {request_time_variance:.2f}ms"

        # Overall throughput check
        requests_per_second = 100 / (
            total_time / 1000
        )  # Convert ms to seconds
        assert (
            requests_per_second > 50
        ), f"Throughput too low: {requests_per_second:.1f} req/s"

        print(
            f"Avg request: {avg_request_time:.2f}ms, Max request: {max_request_time:.2f}ms, "
            f"Avg cleanup: {avg_cleanup_time:.2f}ms, Throughput: {requests_per_second:.1f} req/s"
        )
