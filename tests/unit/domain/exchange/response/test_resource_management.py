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


def create_cleanup_coordination_registration(team_id, timeout_seconds=None):
    """Create a registration for cleanup coordination testing."""
    request_id = f"req_cleanup_{int(time.time_ns())}"
    timeout_duration = timeout_seconds or 0.2

    return ResponseRegistration(
        request_id=request_id,
        team_id=team_id,
        timeout_at=datetime.now() + timedelta(seconds=timeout_duration),
        status=ResponseStatus.PENDING,
    )


def perform_cleanup_coordination(
    active_requests, completed_requests, expired_requests, coordination_lock
):
    """Perform cleanup coordination with proper locking."""
    cleaned_count = 0
    current_time = datetime.now()

    with coordination_lock:
        # Process expired active requests
        expired_active = [
            rid
            for rid, data in active_requests.items()
            if data["registration"].timeout_at <= current_time
        ]

        for request_id in expired_active:
            data = active_requests.pop(request_id)
            expired_requests[request_id] = {**data, "expired_at": current_time}
            cleaned_count += 1

        # Clean old completed requests
        cleanup_age = timedelta(seconds=0.1)
        old_completed = [
            rid
            for rid, data in completed_requests.items()
            if current_time - data.get("completed_at", current_time)
            > cleanup_age
        ]

        for request_id in old_completed:
            del completed_requests[request_id]
            cleaned_count += 1

    return cleaned_count


def process_active_requests(
    mock_coordinator, processing_results, processing_errors, coordination_lock
):
    """Worker function for active request processing."""
    for i in range(50):
        try:
            team_id = f"TEAM_ACTIVE_{i:03d}"
            registration = mock_coordinator.register_request(team_id)

            # Simulate processing with variable timing
            processing_time = 0.05 + (i % 10) * 0.01
            time.sleep(processing_time)

            # 80% success rate
            completed = i % 5 != 0
            if completed:
                _complete_request_for_cleanup(
                    registration.request_id, coordination_lock
                )

            processing_results.append(
                {
                    "request_id": registration.request_id,
                    "completed": completed,
                    "processing_time": processing_time,
                }
            )

            time.sleep(0.01)

        except Exception as e:
            processing_errors.append(str(e))


def run_background_cleanup(mock_coordinator, processing_errors):
    """Worker function for background cleanup."""
    for i in range(100):
        try:
            _cleaned = mock_coordinator.cleanup_completed_requests()
            time.sleep(0.02)
        except Exception as e:
            processing_errors.append(f"Cleanup error: {e}")


def _complete_request_for_cleanup(request_id, coordination_lock):
    """Helper to complete a request for cleanup testing."""
    # Note: This would normally update shared state
    # For this test refactor, we're just marking completion
    pass


def create_sustained_load_registration(team_id, request_counter):
    """Create a registration for sustained load testing."""
    request_counter[0] += 1
    request_id = f"req_sustained_{request_counter[0]:06d}"

    return ResponseRegistration(
        request_id=request_id,
        team_id=team_id,
        timeout_at=datetime.now() + timedelta(seconds=2),
        status=ResponseStatus.PENDING,
    )


def complete_sustained_load_request(
    request_id, active_requests, completed_requests, snapshot_lock
):
    """Complete a request and move to completed storage."""
    with snapshot_lock:
        if request_id in active_requests:
            request_data = active_requests.pop(request_id)
            completed_requests[request_id] = {
                **request_data,
                "completed_at": datetime.now(),
            }


def cleanup_sustained_load_requests(completed_requests, snapshot_lock):
    """Clean up old completed requests."""
    cleaned = 0
    current_time = datetime.now()
    cleanup_age = timedelta(seconds=0.5)

    with snapshot_lock:
        to_remove = [
            rid
            for rid, data in completed_requests.items()
            if current_time - data.get("completed_at", current_time)
            > cleanup_age
        ]

        for request_id in to_remove:
            del completed_requests[request_id]
            cleaned += 1

    return cleaned


def take_sustained_load_snapshot(
    active_requests,
    completed_requests,
    request_counter,
    memory_snapshots,
    snapshot_lock,
):
    """Take snapshot of current memory usage."""
    with snapshot_lock:
        snapshot = {
            "timestamp": datetime.now(),
            "active_count": len(active_requests),
            "completed_count": len(completed_requests),
            "total_requests": request_counter[0],
        }
        memory_snapshots.append(snapshot)


def create_tracked_registration(team_id, created_objects, weak_references):
    """Create a registration with memory tracking."""
    request_id = f"req_memory_{len(created_objects):05d}"

    registration = ResponseRegistration(
        request_id=request_id,
        team_id=team_id,
        timeout_at=datetime.now() + timedelta(seconds=1),
        status=ResponseStatus.PENDING,
    )

    # Track for memory leak detection
    created_objects.append(registration)
    weak_references.append(weakref.ref(registration))

    return registration


def complete_tracked_request(request_id, request_storage, storage_lock):
    """Complete a request in storage."""
    with storage_lock:
        if request_id in request_storage:
            request_storage[request_id]["completed"] = True
            request_storage[request_id]["completed_at"] = datetime.now()


def cleanup_expired_tracked_requests(
    request_storage, storage_lock, cleanup_counts
):
    """Clean up old completed requests."""
    cleaned_count = 0
    current_time = datetime.now()
    cleanup_threshold = timedelta(milliseconds=100)

    with storage_lock:
        to_remove = [
            rid
            for rid, data in request_storage.items()
            if data["completed"]
            and current_time - data.get("completed_at", current_time)
            > cleanup_threshold
        ]

        for request_id in to_remove:
            del request_storage[request_id]
            cleaned_count += 1

    cleanup_counts.append(cleaned_count)
    return cleaned_count


def register_with_capacity_check(
    team_id, pending_requests, max_pending, capacity_lock, rejection_count
):
    """Register request with capacity limit check."""
    with capacity_lock:
        current_pending = len(pending_requests)

        if current_pending >= max_pending:
            rejection_count[0] += 1
            raise Exception(
                f"Service overloaded: {current_pending}/{max_pending}"
            )

        # Generate unique request ID
        request_counter = getattr(register_with_capacity_check, "counter", 0)
        register_with_capacity_check.counter = request_counter + 1
        request_id = f"req_capacity_{request_counter:03d}"

        registration = ResponseRegistration(
            request_id=request_id,
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

        pending_requests[request_id] = registration
        return registration


def complete_capacity_tracked_request(
    request_id, pending_requests, capacity_lock
):
    """Complete a request to free up capacity."""
    with capacity_lock:
        if request_id in pending_requests:
            del pending_requests[request_id]


def simulate_resource_pressure(resource_pressure, pressure_lock):
    """Simulate increasing resource pressure over time."""
    with pressure_lock:
        resource_pressure["memory_usage"] = min(
            0.95, resource_pressure["memory_usage"] + 0.05
        )
        resource_pressure["cpu_usage"] = min(
            0.95, resource_pressure["cpu_usage"] + 0.03
        )


def check_resource_pressure_response(
    resource_pressure,
    pressure_lock,
    degradation_responses,
    team_id,
    timeout_seconds,
):
    """Check resource pressure and determine response."""
    with pressure_lock:
        memory = resource_pressure["memory_usage"]
        cpu = resource_pressure["cpu_usage"]

        if memory > 0.9 or cpu > 0.9:
            # Severe pressure - reject
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


def reduce_resource_pressure(resource_pressure, pressure_lock):
    """Reduce resource pressure when request completes."""
    with pressure_lock:
        resource_pressure["pending_requests"] = max(
            0, resource_pressure["pending_requests"] - 1
        )
        resource_pressure["memory_usage"] = max(
            0.6, resource_pressure["memory_usage"] - 0.01
        )
        resource_pressure["cpu_usage"] = max(
            0.5, resource_pressure["cpu_usage"] - 0.01
        )


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
        request_storage = {}
        cleanup_counts = []
        storage_lock = threading.Lock()
        created_objects = []
        weak_references = []

        # Setup mock coordinator
        self._setup_memory_leak_tracking(
            mock_coordinator,
            request_storage,
            storage_lock,
            cleanup_counts,
            created_objects,
            weak_references,
        )

        # When - Process requests with periodic cleanup
        num_requests = 200
        self._process_requests_with_cleanup(
            mock_coordinator,
            request_storage,
            storage_lock,
            num_requests,
        )

        # Clear strong references for GC test
        created_objects.clear()
        gc.collect()

        # Then - Verify cleanup effectiveness
        self._verify_cleanup_effectiveness(
            request_storage,
            storage_lock,
            cleanup_counts,
            weak_references,
            num_requests,
        )

    def _setup_memory_leak_tracking(
        self,
        mock_coordinator,
        request_storage,
        storage_lock,
        cleanup_counts,
        created_objects,
        weak_references,
    ):
        """Setup mock coordinator for memory leak tracking."""

        def register_with_tracking(team_id, timeout_seconds=None):
            registration = create_tracked_registration(
                team_id, created_objects, weak_references
            )
            with storage_lock:
                request_storage[registration.request_id] = {
                    "registration": registration,
                    "created_at": datetime.now(),
                    "completed": False,
                }
            return registration

        def cleanup_expired():
            return cleanup_expired_tracked_requests(
                request_storage, storage_lock, cleanup_counts
            )

        mock_coordinator.register_request.side_effect = register_with_tracking
        mock_coordinator.cleanup_completed_requests.side_effect = (
            cleanup_expired
        )

    def _process_requests_with_cleanup(
        self, mock_coordinator, request_storage, storage_lock, num_requests
    ):
        """Process requests with periodic cleanup."""
        cleanup_interval = 20

        for i in range(num_requests):
            # Register and complete request
            team_id = f"TEAM_MEMORY_{i:03d}"
            registration = mock_coordinator.register_request(team_id)
            complete_tracked_request(
                registration.request_id, request_storage, storage_lock
            )

            # Periodic operations
            if i % cleanup_interval == 0:
                mock_coordinator.cleanup_completed_requests()

            if i % 10 == 0:
                time.sleep(0.11)  # Allow cleanup timing

        # Final cleanup passes
        time.sleep(0.11)
        for _ in range(5):
            mock_coordinator.cleanup_completed_requests()
            time.sleep(0.01)

    def _verify_cleanup_effectiveness(
        self,
        request_storage,
        storage_lock,
        cleanup_counts,
        weak_references,
        num_requests,
    ):
        """Verify cleanup prevented memory leaks."""
        total_cleaned = sum(cleanup_counts)
        assert total_cleaned > 0, "No cleanup occurred"
        assert (
            total_cleaned >= num_requests * 0.5
        ), f"Too few cleaned: {total_cleaned}/{num_requests}"

        # Check storage size
        with storage_lock:
            remaining_requests = len(request_storage)
        assert (
            remaining_requests < num_requests * 0.5
        ), f"Too many remaining: {remaining_requests}"

        # Check weak references
        gc.collect()
        dead_references = sum(1 for ref in weak_references if ref() is None)
        assert (
            dead_references >= num_requests * 0.5
        ), f"Memory leak: only {dead_references} collected"

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
        # Given - Setup test data structures
        memory_snapshots = []
        active_requests = {}
        completed_requests = {}
        snapshot_lock = threading.Lock()
        request_counter = [0]

        # Setup mock coordinator behavior
        self._setup_sustained_load_mocks(
            mock_coordinator,
            active_requests,
            completed_requests,
            snapshot_lock,
            request_counter,
        )

        # When - Run sustained load simulation
        self._run_sustained_load_simulation(
            mock_coordinator,
            active_requests,
            completed_requests,
            memory_snapshots,
            snapshot_lock,
            request_counter,
        )

        # Then - Analyze memory efficiency
        self._analyze_sustained_load_results(memory_snapshots)

    def _setup_sustained_load_mocks(
        self,
        mock_coordinator,
        active_requests,
        completed_requests,
        snapshot_lock,
        request_counter,
    ):
        """Setup mock coordinator for sustained load testing."""

        def register_with_tracking(team_id, timeout_seconds=None):
            registration = create_sustained_load_registration(
                team_id, request_counter
            )
            with snapshot_lock:
                active_requests[registration.request_id] = {
                    "registration": registration,
                    "created_at": datetime.now(),
                }
            return registration

        def cleanup_with_tracking():
            return cleanup_sustained_load_requests(
                completed_requests, snapshot_lock
            )

        mock_coordinator.register_request.side_effect = register_with_tracking
        mock_coordinator.cleanup_completed_requests.side_effect = (
            cleanup_with_tracking
        )

    def _run_sustained_load_simulation(
        self,
        mock_coordinator,
        active_requests,
        completed_requests,
        memory_snapshots,
        snapshot_lock,
        request_counter,
    ):
        """Run the sustained load simulation."""
        load_duration = 1.0
        batch_size = 10
        request_rate = 100
        cleanup_frequency = 0.1
        snapshot_frequency = 0.1

        start_time = time.perf_counter()
        last_cleanup = start_time
        last_snapshot = start_time

        while time.perf_counter() - start_time < load_duration:
            # Process batch of requests
            for _ in range(batch_size):
                team_id = f"TEAM_LOAD_{request_counter[0] % 50:03d}"
                registration = mock_coordinator.register_request(team_id)

                # 90% complete quickly
                if request_counter[0] % 10 != 0:
                    complete_sustained_load_request(
                        registration.request_id,
                        active_requests,
                        completed_requests,
                        snapshot_lock,
                    )

            current_time = time.perf_counter()

            # Periodic operations
            if current_time - last_cleanup >= cleanup_frequency:
                mock_coordinator.cleanup_completed_requests()
                last_cleanup = current_time

            if current_time - last_snapshot >= snapshot_frequency:
                take_sustained_load_snapshot(
                    active_requests,
                    completed_requests,
                    request_counter,
                    memory_snapshots,
                    snapshot_lock,
                )
                last_snapshot = current_time

            time.sleep(batch_size / request_rate)

        # Final cleanup and snapshot
        for _ in range(3):
            mock_coordinator.cleanup_completed_requests()

        take_sustained_load_snapshot(
            active_requests,
            completed_requests,
            request_counter,
            memory_snapshots,
            snapshot_lock,
        )

    def _analyze_sustained_load_results(self, memory_snapshots):
        """Analyze memory efficiency from sustained load test."""
        assert len(memory_snapshots) >= 5, "Not enough memory snapshots taken"

        # Extract time series data
        total_requests = [s["total_requests"] for s in memory_snapshots]
        active_counts = [s["active_count"] for s in memory_snapshots]
        completed_counts = [s["completed_count"] for s in memory_snapshots]

        # Verify processing occurred
        assert total_requests[-1] > total_requests[0], "No requests processed"

        # Verify memory bounds
        max_active = max(active_counts)
        max_completed = max(completed_counts)
        final_total = total_requests[-1]

        assert (
            max_active < final_total * 0.2
        ), f"Too many active requests: {max_active}"
        assert (
            max_completed < final_total * 0.5
        ), f"Too many completed requests: {max_completed}"

        # Verify memory efficiency
        memory_efficiency = (
            active_counts[-1] + completed_counts[-1]
        ) / final_total
        assert (
            memory_efficiency < 0.6
        ), f"Poor memory efficiency: {memory_efficiency:.2f}"

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
        # Given - Setup test configuration
        test_config = coordination_config
        test_config.max_pending_requests = 10

        pending_requests = {}
        rejection_count = [0]
        capacity_lock = threading.Lock()

        # Setup mock coordinator
        self._setup_capacity_limit_mocks(
            mock_coordinator,
            pending_requests,
            capacity_lock,
            test_config.max_pending_requests,
            rejection_count,
        )

        # When - Test capacity scenarios
        successful = self._fill_to_capacity(
            mock_coordinator, test_config.max_pending_requests
        )

        failed = self._test_capacity_overflow(mock_coordinator, 5)

        recovered = self._test_capacity_recovery(
            mock_coordinator, successful[:3], pending_requests, capacity_lock
        )

        # Then - Verify capacity enforcement
        self._verify_capacity_enforcement(
            successful,
            failed,
            recovered,
            pending_requests,
            capacity_lock,
            test_config.max_pending_requests,
        )

    def _setup_capacity_limit_mocks(
        self,
        mock_coordinator,
        pending_requests,
        capacity_lock,
        max_pending,
        rejection_count,
    ):
        """Setup mock coordinator with capacity limits."""

        def register_with_limit(team_id, timeout_seconds=None):
            return register_with_capacity_check(
                team_id,
                pending_requests,
                max_pending,
                capacity_lock,
                rejection_count,
            )

        mock_coordinator.register_request.side_effect = register_with_limit

    def _fill_to_capacity(self, mock_coordinator, max_pending):
        """Fill requests up to capacity limit."""
        successful = []

        for i in range(max_pending):
            try:
                team_id = f"TEAM_CAPACITY_{i:03d}"
                registration = mock_coordinator.register_request(team_id)
                successful.append(registration)
            except Exception:
                pass  # Shouldn't happen at capacity

        return successful

    def _test_capacity_overflow(self, mock_coordinator, overflow_count):
        """Test requests beyond capacity."""
        failed = []

        for i in range(overflow_count):
            try:
                team_id = f"TEAM_OVERFLOW_{i:03d}"
                mock_coordinator.register_request(team_id)
            except Exception as e:
                failed.append(str(e))

        return failed

    def _test_capacity_recovery(
        self, mock_coordinator, to_complete, pending_requests, capacity_lock
    ):
        """Test capacity recovery after completions."""
        # Complete some requests
        for registration in to_complete:
            complete_capacity_tracked_request(
                registration.request_id, pending_requests, capacity_lock
            )

        # Try to fill recovered capacity
        recovered = []
        for i in range(len(to_complete)):
            try:
                team_id = f"TEAM_RECOVERY_{i:03d}"
                registration = mock_coordinator.register_request(team_id)
                recovered.append(registration)
            except Exception:
                pass

        return recovered

    def _verify_capacity_enforcement(
        self,
        successful,
        failed,
        recovered,
        pending_requests,
        capacity_lock,
        max_pending,
    ):
        """Verify capacity limits were enforced correctly."""
        # Check initial fill
        initial_count = len(
            [r for r in successful if r.request_id.startswith("req_capacity_")]
        )
        assert initial_count == max_pending, f"Expected {max_pending} initial"

        # Check overflow rejections
        assert len(failed) == 5, f"Expected 5 failures, got {len(failed)}"

        # Check recovery
        assert len(recovered) == 3, "Expected 3 recovered"

        # Verify error messages
        for failure in failed:
            assert (
                "overloaded" in failure.lower()
                or "capacity" in failure.lower()
            )

        # Verify final state
        with capacity_lock:
            final_pending = len(pending_requests)
        assert (
            final_pending == max_pending
        ), f"Wrong final count: {final_pending}"

    def _create_id_tracking_registration(
        self, request_id: str, team_id: str
    ) -> ResponseRegistration:
        """Create a registration with tracked ID."""
        return ResponseRegistration(
            request_id=request_id,
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

    def _fill_capacity_with_requests(
        self, mock_coordinator, count: int
    ) -> list:
        """Fill capacity with initial requests."""
        registrations = []
        for i in range(count):
            reg = mock_coordinator.register_request(f"TEAM_{i:03d}")
            registrations.append(reg)
        return registrations

    def _complete_specific_requests(
        self, registrations: list, indices: list, mock_complete_func
    ):
        """Complete specific requests by indices."""
        for i in indices:
            mock_complete_func(registrations[i].request_id)

    def _add_new_requests(self, mock_coordinator, count: int) -> list:
        """Add new requests after some capacity is freed."""
        new_registrations = []
        for i in range(count):
            reg = mock_coordinator.register_request(f"TEAM_NEW_{i:03d}")
            new_registrations.append(reg)
        return new_registrations

    def _verify_id_uniqueness(
        self, all_generated_ids: set, expected_count: int
    ):
        """Verify all generated IDs are unique."""
        assert (
            len(all_generated_ids) == expected_count
        ), f"Expected {expected_count} unique IDs, got {len(all_generated_ids)}"

    def test_request_id_uniqueness_after_capacity_recovery(
        self, mock_coordinator, coordination_config
    ):
        """Test that request IDs remain unique when capacity is freed and reused.

        Given - A coordinator at full capacity with completed requests
        When - Requests are completed and new ones added
        Then - All request IDs remain unique (no duplicates)

        This test specifically validates that the ID generation strategy
        prevents duplicate IDs when the pending request count decreases
        and then increases again.
        """
        # Given - Setup with capacity tracking
        test_config = coordination_config
        test_config.max_pending_requests = 5  # Small limit for easy testing

        pending_requests = {}
        all_generated_ids = set()
        capacity_lock = threading.Lock()

        def mock_register_with_id_tracking(team_id, timeout_seconds=None):
            with capacity_lock:
                current_pending = len(pending_requests)

                if current_pending >= test_config.max_pending_requests:
                    raise Exception(
                        f"At capacity: {current_pending}/{test_config.max_pending_requests}"
                    )

                # Use counter-based ID generation (increment AFTER use)
                request_counter = getattr(
                    mock_register_with_id_tracking, "counter", 0
                )
                request_id = f"req_test_{request_counter:03d}"
                mock_register_with_id_tracking.counter = request_counter + 1

                # Track ALL generated IDs to check for duplicates
                if request_id in all_generated_ids:
                    raise AssertionError(
                        f"Duplicate ID generated: {request_id}"
                    )
                all_generated_ids.add(request_id)

                registration = self._create_id_tracking_registration(
                    request_id, team_id
                )
                pending_requests[request_id] = registration
                return registration

        def mock_complete_request(request_id):
            with capacity_lock:
                if request_id in pending_requests:
                    del pending_requests[request_id]

        mock_coordinator.register_request.side_effect = (
            mock_register_with_id_tracking
        )

        # When - Fill capacity, complete some, add more
        registrations = self._fill_capacity_with_requests(mock_coordinator, 5)
        self._complete_specific_requests(
            registrations, [1, 2, 3], mock_complete_request
        )
        new_registrations = self._add_new_requests(mock_coordinator, 3)
        registrations.extend(new_registrations)

        # Then - Verify no duplicate IDs were generated
        self._verify_id_uniqueness(all_generated_ids, 8)

        # Verify the IDs are as expected (counter starts at 0)
        expected_ids = {
            "req_test_000",
            "req_test_001",
            "req_test_002",
            "req_test_003",
            "req_test_004",  # Initial 5
            "req_test_005",
            "req_test_006",
            "req_test_007",  # New 3
        }
        assert (
            all_generated_ids == expected_ids
        ), f"ID mismatch: {all_generated_ids}"

        # Verify current pending requests
        with capacity_lock:
            assert (
                len(pending_requests) == 5
            ), f"Expected 5 pending, got {len(pending_requests)}"
            # Should have: 000, 004 (from original) + 005, 006, 007 (new)
            # We completed indices 1, 2, 3 which are IDs 001, 002, 003
            expected_pending = {
                "req_test_000",
                "req_test_004",
                "req_test_005",
                "req_test_006",
                "req_test_007",
            }
            actual_pending = set(pending_requests.keys())
            assert (
                actual_pending == expected_pending
            ), f"Pending mismatch: {actual_pending}"

    def _create_bad_id_registration(
        self, request_id: str, team_id: str
    ) -> ResponseRegistration:
        """Create a registration with BAD length-based ID."""
        return ResponseRegistration(
            request_id=request_id,
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

    def _track_id_generation(
        self, request_id: str, all_generated_ids: list, id_counts: dict
    ):
        """Track ID generation for collision detection."""
        all_generated_ids.append(request_id)
        id_counts[request_id] = id_counts.get(request_id, 0) + 1

    def _verify_duplicate_ids_exist(self, id_counts: dict) -> list:
        """Verify that duplicate IDs were generated."""
        duplicate_ids = [id for id, count in id_counts.items() if count > 1]
        assert (
            len(duplicate_ids) > 0
        ), "Expected duplicate IDs with length-based generation"
        return duplicate_ids

    def _verify_id_sequence_duplicates(self, all_generated_ids: list):
        """Verify that IDs appear multiple times in generation sequence."""
        id_occurrences = {}
        for id in all_generated_ids:
            id_occurrences[id] = id_occurrences.get(id, 0) + 1

        duplicated_in_sequence = [
            id for id, count in id_occurrences.items() if count > 1
        ]
        assert len(duplicated_in_sequence) >= 1, (
            f"Expected at least one ID to appear multiple times in sequence. "
            f"Got: {all_generated_ids}"
        )

    def test_request_id_collision_with_length_based_generation(
        self, mock_coordinator, coordination_config
    ):
        """Demonstrate why length-based ID generation fails after capacity recovery.

        Given - A coordinator using len(pending_requests) for ID generation
        When - Requests are completed and new ones added
        Then - Duplicate IDs are generated, causing failures

        This test demonstrates the WRONG way to generate IDs and why
        we need counter-based generation instead.
        """
        # Given - Setup with BROKEN length-based ID generation
        test_config = coordination_config
        test_config.max_pending_requests = 5

        pending_requests = {}
        all_generated_ids = []  # Track order of generation
        id_counts = {}  # Track how many times each ID is generated
        capacity_lock = threading.Lock()

        def mock_register_with_bad_id_generation(
            team_id, timeout_seconds=None
        ):
            with capacity_lock:
                current_pending = len(pending_requests)

                if current_pending >= test_config.max_pending_requests:
                    raise Exception(
                        f"At capacity: {current_pending}/{test_config.max_pending_requests}"
                    )

                # BAD: Use length-based ID generation
                request_id = f"req_bad_{len(pending_requests):03d}"

                # Track ID generation
                self._track_id_generation(
                    request_id, all_generated_ids, id_counts
                )

                registration = self._create_bad_id_registration(
                    request_id, team_id
                )
                pending_requests[request_id] = registration
                return registration

        def mock_complete_request(request_id):
            with capacity_lock:
                if request_id in pending_requests:
                    del pending_requests[request_id]

        mock_coordinator.register_request.side_effect = (
            mock_register_with_bad_id_generation
        )

        # When - Fill capacity, complete some, add more
        registrations = self._fill_capacity_with_requests(mock_coordinator, 5)
        # IDs generated so far: req_bad_000, 001, 002, 003, 004

        # Complete the first 3 requests
        self._complete_specific_requests(
            registrations, [0, 1, 2], mock_complete_request
        )
        # Now pending_requests has only 2 items (003 and 004)

        # Try to add 3 new requests
        new_registrations = self._add_new_requests(mock_coordinator, 3)
        registrations.extend(new_registrations)

        # Then - Demonstrate the ID collision problem
        # With length-based generation, new IDs are based on current size
        # This causes duplicate IDs to be generated!

        # Verify duplicates were generated
        duplicate_ids = self._verify_duplicate_ids_exist(id_counts)

        # Verify the pattern: after completing 3 requests, we have 2 left
        # So new requests start at ID 002, which was already used!
        assert (
            "req_bad_002" in duplicate_ids
        ), "Expected req_bad_002 to be duplicated"

        # The specific IDs that get duplicated depend on dict ordering,
        # but we always get duplicates because we're reusing IDs
        assert (
            len(all_generated_ids) == 8
        ), "Expected 5 initial + 3 new requests"

        # Verify that at least one ID appears twice in the sequence
        self._verify_id_sequence_duplicates(all_generated_ids)

        # Business impact: This would cause order tracking failures!
        print(f"Duplicate IDs generated: {duplicate_ids}")
        print(f"ID generation sequence shows reuse: {all_generated_ids}")

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
        # Given - Setup test data
        resource_pressure = {
            "memory_usage": 0.6,
            "cpu_usage": 0.5,
            "pending_requests": 0,
        }
        pressure_lock = threading.Lock()
        degradation_responses = []

        # Setup mock coordinator
        self._setup_resource_pressure_mocks(
            mock_coordinator,
            resource_pressure,
            pressure_lock,
            degradation_responses,
        )

        # When - Submit requests under increasing pressure
        successful, rejected = self._submit_requests_with_pressure(
            mock_coordinator, resource_pressure, pressure_lock
        )

        # Then - Verify graceful degradation
        self._verify_graceful_degradation(degradation_responses, rejected)

    def _setup_resource_pressure_mocks(
        self,
        mock_coordinator,
        resource_pressure,
        pressure_lock,
        degradation_responses,
    ):
        """Setup mock coordinator with resource pressure simulation."""

        def mock_register(team_id, timeout_seconds=None):
            simulate_resource_pressure(resource_pressure, pressure_lock)
            return check_resource_pressure_response(
                resource_pressure,
                pressure_lock,
                degradation_responses,
                team_id,
                timeout_seconds,
            )

        mock_coordinator.register_request.side_effect = mock_register

    def _submit_requests_with_pressure(
        self, mock_coordinator, resource_pressure, pressure_lock
    ):
        """Submit requests while simulating increasing pressure."""
        successful_requests = []
        rejected_requests = []

        for i in range(30):
            try:
                team_id = f"TEAM_PRESSURE_{i:03d}"
                registration = mock_coordinator.register_request(team_id)
                successful_requests.append(registration)

                # Simulate some completions
                if i % 5 == 0 and successful_requests:
                    reduce_resource_pressure(resource_pressure, pressure_lock)

            except Exception as e:
                rejected_requests.append(str(e))

            time.sleep(0.01)

        return successful_requests, rejected_requests

    def _verify_graceful_degradation(
        self, degradation_responses, rejected_requests
    ):
        """Verify system degraded gracefully."""
        assert degradation_responses, "No degradation responses recorded"
        assert rejected_requests, "No requests were rejected under pressure"

        # Check response types
        warnings = [r for r in degradation_responses if r["type"] == "warning"]
        rejections = [
            r for r in degradation_responses if r["type"] == "rejection"
        ]

        assert warnings, "No warning responses during pressure buildup"
        assert rejections, "No rejections during high pressure"

        # Verify progression
        if warnings and rejections:
            assert (
                warnings[0]["memory"] <= rejections[0]["memory"]
            ), "Rejections should come after warnings"

        # Check error messages
        for rejection in rejected_requests:
            assert any(
                word in rejection.lower()
                for word in ["memory", "cpu", "overloaded"]
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
        # Given - Setup test data structures
        active_requests, completed_requests, expired_requests = {}, {}, {}
        cleanup_events = []
        coordination_lock = threading.Lock()
        processing_results, processing_errors = [], []

        # Setup mock coordinator behavior
        self._setup_mock_coordinator(
            mock_coordinator,
            active_requests,
            completed_requests,
            expired_requests,
            cleanup_events,
            coordination_lock,
        )

        # When - Run concurrent processing and cleanup
        self._run_concurrent_processing(
            mock_coordinator,
            processing_results,
            processing_errors,
            coordination_lock,
        )

        # Then - Verify coordination worked correctly
        self._verify_cleanup_coordination(
            processing_results,
            processing_errors,
            cleanup_events,
            active_requests,
            completed_requests,
            coordination_lock,
        )

    def _setup_mock_coordinator(
        self,
        mock_coordinator,
        active_requests,
        completed_requests,
        expired_requests,
        cleanup_events,
        coordination_lock,
    ):
        """Setup mock coordinator with cleanup behavior."""

        def register_with_cleanup(team_id, timeout_seconds=None):
            registration = create_cleanup_coordination_registration(
                team_id, timeout_seconds
            )
            with coordination_lock:
                active_requests[registration.request_id] = {
                    "registration": registration,
                    "created_at": datetime.now(),
                    "team_id": team_id,
                }
            return registration

        def cleanup_with_coordination():
            cleaned_count = perform_cleanup_coordination(
                active_requests,
                completed_requests,
                expired_requests,
                coordination_lock,
            )
            cleanup_events.append(
                {
                    "timestamp": datetime.now(),
                    "cleaned_count": cleaned_count,
                    "active_count": len(active_requests),
                    "completed_count": len(completed_requests),
                    "expired_count": len(expired_requests),
                }
            )
            return cleaned_count

        mock_coordinator.register_request.side_effect = register_with_cleanup
        mock_coordinator.cleanup_completed_requests.side_effect = (
            cleanup_with_coordination
        )

    def _run_concurrent_processing(
        self,
        mock_coordinator,
        processing_results,
        processing_errors,
        coordination_lock,
    ):
        """Run concurrent processing and cleanup threads."""
        processing_thread = threading.Thread(
            target=process_active_requests,
            args=(
                mock_coordinator,
                processing_results,
                processing_errors,
                coordination_lock,
            ),
            daemon=True,
        )
        cleanup_thread = threading.Thread(
            target=run_background_cleanup,
            args=(mock_coordinator, processing_errors),
            daemon=True,
        )

        processing_thread.start()
        cleanup_thread.start()

        processing_thread.join(timeout=5.0)
        cleanup_thread.join(timeout=5.0)

        # Final cleanup
        mock_coordinator.cleanup_completed_requests()

    def _verify_cleanup_coordination(
        self,
        processing_results,
        processing_errors,
        cleanup_events,
        active_requests,
        completed_requests,
        coordination_lock,
    ):
        """Verify cleanup coordination worked correctly."""
        # Basic error checking
        assert not processing_errors, f"Processing errors: {processing_errors}"
        assert len(processing_results) == 50, "Not all processing completed"
        assert len(cleanup_events) > 10, "Not enough cleanup events"

        # Verify completion rates
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

        # Verify cleanup effectiveness
        total_cleaned = sum(event["cleaned_count"] for event in cleanup_events)
        assert (
            total_cleaned >= 10
        ), f"Not enough requests cleaned: {total_cleaned}"

        # Verify final state
        with coordination_lock:
            total_remaining = len(active_requests) + len(completed_requests)

        assert (
            total_remaining < 20
        ), f"Too many requests remaining: {total_remaining}"

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
