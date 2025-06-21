"""Order response coordination service implementation.

This module implements the OrderResponseCoordinator service that bridges
synchronous REST API responses with asynchronous order processing pipelines.
It manages request lifecycles, thread synchronization, and resource cleanup
to ensure API clients receive timely and accurate responses.

The implementation follows thread-safe patterns suitable for high-concurrency
trading environments with multiple API threads and pipeline threads operating
simultaneously.

Examples
--------
>>> # Basic usage in API endpoint
>>> coordinator = OrderResponseCoordinator(config)
>>> registration = coordinator.register_request("TEAM_001")
>>> # Submit to pipeline...
>>> result = await coordinator.wait_for_completion(registration.request_id)
>>> return result.api_response
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from ....infrastructure.api.models import ApiError, ApiResponse
from .interfaces import (
    OrderResponseCoordinatorInterface,
    ResponseRegistration,
    ResponseResult,
)
from .models import (
    CoordinationConfig,
    PendingRequest,
    ResponseStatus,
)

logger = logging.getLogger(__name__)


class OrderResponseCoordinator(OrderResponseCoordinatorInterface):
    """Concrete implementation of order response coordination service.

    This service manages the coordination between synchronous REST API
    requests and asynchronous order processing pipelines. It provides
    thread-safe request tracking, timeout management, and resource cleanup
    to ensure reliable order processing in a multi-threaded environment.

    The coordinator maintains internal state for pending requests and
    implements event-based signaling to enable API threads to wait for
    pipeline completion efficiently.

    Attributes
    ----------
    config : CoordinationConfig
        Configuration parameters for timeout, capacity, and cleanup settings
    _lock : threading.RLock
        Reentrant lock protecting internal state modifications
    _pending_requests : Dict[str, PendingRequest]
        Active requests awaiting completion, keyed by request_id
    _completion_results : Dict[str, ResponseResult]
        Temporary storage for completion results until retrieved by API thread
    _request_counter : int
        Atomic counter for generating unique request IDs
    _cleanup_thread : Optional[threading.Thread]
        Background thread for expired request cleanup
    _shutdown : bool
        Flag indicating service shutdown in progress

    Notes
    -----
    This implementation uses threading.RLock for all synchronization to
    prevent deadlocks when methods call other methods. The lock is held
    for minimal time to reduce contention in high-concurrency scenarios.

    The service implements automatic cleanup of expired requests to prevent
    memory leaks during long-running trading sessions. Cleanup runs in a
    background thread at configurable intervals.

    TradingContext
    --------------
    In trading systems, this coordinator is critical for:
    - Ensuring every order gets a response (no lost orders)
    - Meeting latency SLAs for algorithmic trading
    - Preventing memory exhaustion during high-volume periods
    - Providing clear timeout behavior for system overload scenarios

    Examples
    --------
    >>> # Initialize coordinator with custom config
    >>> config = CoordinationConfig(
    ...     default_timeout_seconds=3.0,
    ...     max_pending_requests=5000
    ... )
    >>> coordinator = OrderResponseCoordinator(config)
    >>>
    >>> # Register and wait for order processing
    >>> registration = coordinator.register_request("TEAM_HFT_001")
    >>> # ... submit to pipeline ...
    >>> result = await coordinator.wait_for_completion(registration.request_id)
    """

    def __init__(self, config: Optional[CoordinationConfig] = None):
        """Initialize the order response coordinator.

        Parameters
        ----------
        config : Optional[CoordinationConfig], default=None
            Configuration for coordinator behavior. If None, uses defaults.
        """
        self.config = config or CoordinationConfig()
        self._lock = threading.RLock()
        self._pending_requests: Dict[str, PendingRequest] = {}
        self._completion_results: Dict[str, ResponseResult] = {}
        self._request_counter = 0
        self._shutdown = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_event = threading.Event()

        # Start background cleanup thread if configured
        if self.config.cleanup_interval_seconds > 0:
            self._start_cleanup_thread()

    def register_request(
        self, team_id: str, timeout_seconds: Optional[float] = None
    ) -> ResponseRegistration:
        """Register a new request for coordination tracking.

        Creates a new coordination entry for an incoming order request,
        allocating the necessary tracking resources and generating a
        unique identifier for pipeline correlation.

        Parameters
        ----------
        team_id : str
            ID of the trading team submitting the request
        timeout_seconds : Optional[float], default=None
            Maximum time to wait for processing completion. If None,
            uses config.default_timeout_seconds

        Returns
        -------
        ResponseRegistration
            Registration handle containing request_id and metadata

        Raises
        ------
        RuntimeError
            If service is shutting down or at capacity limit

        Notes
        -----
        This method is thread-safe and designed for concurrent access
        from multiple API threads. Request IDs are guaranteed unique
        within the lifetime of the coordinator instance.

        TradingContext
        --------------
        Registration represents the contract between the API and the
        trading system. The timeout establishes the maximum time a
        trading algorithm will wait for order confirmation.
        """
        with self._lock:
            # Check shutdown state
            if self._shutdown:
                raise RuntimeError("Coordinator is shutting down")

            # Check capacity limit
            if len(self._pending_requests) >= self.config.max_pending_requests:
                raise RuntimeError(
                    f"Service overloaded: {len(self._pending_requests)}/{self.config.max_pending_requests} "
                    "pending requests"
                )

            # Generate unique request ID
            self._request_counter += 1
            timestamp = int(time.time_ns())
            request_id = f"{self.config.request_id_prefix}_{timestamp}_{self._request_counter:06d}"

            # Calculate timeout
            timeout_duration = (
                timeout_seconds or self.config.default_timeout_seconds
            )
            timeout_at = datetime.now() + timedelta(seconds=timeout_duration)

            # Create pending request
            pending_request = PendingRequest(
                request_id=request_id,
                team_id=team_id,
                status=ResponseStatus.PENDING,
                completion_event=threading.Event(),
                registered_at=datetime.now(),
                timeout_at=timeout_at,
            )

            # Store pending request
            self._pending_requests[request_id] = pending_request

            # Create registration result
            registration = ResponseRegistration(
                request_id=request_id,
                team_id=team_id,
                timeout_at=timeout_at,
                status=ResponseStatus.PENDING,
            )

            logger.debug(
                f"Registered request {request_id} for team {team_id}, "
                f"timeout at {timeout_at.isoformat()}"
            )

            return registration

    def wait_for_completion(
        self, request_id: str, timeout_seconds: Optional[float] = None
    ) -> ResponseResult:
        """Wait for request processing to complete and return final result.

        Blocks the calling thread until the specified request completes
        processing through the pipeline, returning the final result that
        should be sent to the API client.

        Parameters
        ----------
        request_id : str
            Unique identifier for the request to wait for
        timeout_seconds : Optional[float], default=None
            Maximum time to wait. If None, uses remaining time until
            request timeout_at

        Returns
        -------
        ResponseResult
            Complete result containing formatted API response

        Raises
        ------
        ValueError
            If request_id is not found or invalid
        TimeoutError
            If wait exceeds timeout (should not happen normally due
            to internal timeout handling)

        Notes
        -----
        This method is designed to be called from async contexts but
        uses thread-based synchronization internally. The actual wait
        is performed using threading.Event.wait() which releases the
        GIL, allowing other threads to proceed.

        TradingContext
        --------------
        The wait time directly impacts the trading system's responsiveness.
        Market makers need fast responses to adjust quotes, while more
        complex orders may require longer processing times.
        """
        # Get pending request
        with self._lock:
            pending_request = self._pending_requests.get(request_id)
            if not pending_request:
                raise ValueError(f"Request {request_id} not found")

        # Calculate timeout
        if timeout_seconds is None:
            # Use remaining time until request timeout
            remaining_time = (
                pending_request.timeout_at - datetime.now()
            ).total_seconds()
            timeout_seconds = max(0.1, remaining_time)  # Minimum 100ms

        # Wait for completion event
        start_time = time.perf_counter()

        # Release lock before waiting to avoid blocking other threads
        if pending_request.completion_event.wait(timeout=timeout_seconds):
            # Event was set, get the result
            with self._lock:
                # Get the completion result
                result = self._completion_results.get(request_id)
                if result:
                    # Clean up completed request
                    del self._pending_requests[request_id]
                    del self._completion_results[request_id]
                    return result
                else:
                    # This shouldn't happen - event set but no result
                    raise RuntimeError(
                        f"No result found for completed request {request_id}"
                    )

        # Timeout occurred - create timeout response
        elapsed_time = (time.perf_counter() - start_time) * 1000

        timeout_result = ResponseResult(
            request_id=request_id,
            success=False,
            api_response=ApiResponse(
                success=False,
                request_id=request_id,
                order_id=None,
                data=None,
                error=ApiError(
                    code="PROCESSING_TIMEOUT",
                    message="Order processing exceeded time limit",
                    details={
                        "timeout_ms": int(timeout_seconds * 1000),
                        "elapsed_ms": int(elapsed_time),
                        "stage": pending_request.current_stage,
                    },
                ),
            ),
            processing_time_ms=elapsed_time,
            final_status=ResponseStatus.TIMEOUT,
        )

        # Update request status
        with self._lock:
            if request_id in self._pending_requests:
                self._pending_requests[
                    request_id
                ].status = ResponseStatus.TIMEOUT
                # Clean up timed out request
                del self._pending_requests[request_id]

        return timeout_result

    def notify_completion(
        self,
        request_id: str,
        api_response: ApiResponse,
        order_id: Optional[str] = None,
    ) -> bool:
        """Notify coordinator that request processing has completed.

        Called by pipeline threads to signal that processing is complete
        and provide the final result that should be returned to the
        waiting API client.

        Parameters
        ----------
        request_id : str
            Unique identifier for the completed request
        api_response : ApiResponse
            Complete API response formatted for return to client
        order_id : Optional[str], default=None
            Exchange-assigned order ID if order was created

        Returns
        -------
        bool
            True if notification was successfully processed, False if
            request was not found or already completed

        Notes
        -----
        This method is thread-safe and idempotent. Multiple calls for
        the same request_id will return True but only the first will
        update the state.

        TradingContext
        --------------
        Completion notification is the critical handoff point between
        the asynchronous processing pipeline and the synchronous API.
        Fast, reliable notification is essential for meeting SLAs.
        """
        with self._lock:
            # Check if request exists
            pending_request = self._pending_requests.get(request_id)
            if not pending_request:
                logger.warning(
                    f"Completion notification for unknown request {request_id}"
                )
                return False

            # Check if already completed
            if pending_request.status.is_terminal():
                logger.debug(
                    f"Request {request_id} already in terminal state {pending_request.status}"
                )
                return True  # Idempotent

            # Calculate processing time
            processing_time_ms = (
                datetime.now() - pending_request.registered_at
            ).total_seconds() * 1000

            # Create result
            result = ResponseResult(
                request_id=request_id,
                success=api_response.success,
                api_response=api_response,
                processing_time_ms=processing_time_ms,
                final_status=ResponseStatus.COMPLETED
                if api_response.success
                else ResponseStatus.ERROR,
                order_id=order_id,
            )

            # Update request state
            pending_request.status = result.final_status
            pending_request.order_id = order_id

            # Store result for retrieval
            self._completion_results[request_id] = result

            # Signal waiting thread
            pending_request.completion_event.set()

            logger.debug(
                f"Completed request {request_id} with status {result.final_status} "
                f"in {processing_time_ms:.1f}ms"
            )

            return True

    def update_status(
        self,
        request_id: str,
        status: ResponseStatus,
        stage_details: Optional[Dict] = None,
    ) -> bool:
        """Update the internal processing status of a request.

        Called by pipeline threads to indicate progression through
        processing stages, enabling monitoring and debugging of
        request flow through the system.

        Parameters
        ----------
        request_id : str
            Unique identifier for the request to update
        status : ResponseStatus
            New internal status reflecting current processing stage
        stage_details : Optional[Dict], default=None
            Additional metadata about current processing stage

        Returns
        -------
        bool
            True if status was successfully updated, False if request
            not found or update invalid

        Notes
        -----
        Status updates are for monitoring only and don't affect the
        final result. Only terminal statuses (COMPLETED, ERROR, TIMEOUT)
        trigger completion events.

        TradingContext
        --------------
        Status tracking enables operations teams to identify bottlenecks
        in order processing and optimize system performance.
        """
        with self._lock:
            pending_request = self._pending_requests.get(request_id)
            if not pending_request:
                logger.warning(
                    f"Status update for unknown request {request_id}"
                )
                return False

            # Don't update terminal statuses
            if pending_request.status.is_terminal():
                logger.debug(
                    f"Cannot update terminal status for request {request_id}"
                )
                return False

            # Update status
            old_status = pending_request.status
            pending_request.status = status

            # Update stage details
            if stage_details:
                pending_request.current_stage = stage_details.get(
                    "stage", pending_request.current_stage
                )
                # Add metrics if provided
                for key, value in stage_details.items():
                    if key.endswith("_ms") or key.endswith("_time"):
                        pending_request.add_processing_metric(key, value)

            logger.debug(
                f"Updated request {request_id} status: {old_status} -> {status}"
            )
            return True

    def get_request_status(self, request_id: str) -> Optional[PendingRequest]:
        """Retrieve current status and metadata for a request.

        Provides read-only access to request tracking information for
        monitoring, debugging, and administrative purposes.

        Parameters
        ----------
        request_id : str
            Unique identifier for the request to query

        Returns
        -------
        Optional[PendingRequest]
            Current request state if found, None otherwise

        Notes
        -----
        Returns a reference to the internal PendingRequest object.
        Callers should not modify the returned object.
        """
        with self._lock:
            return self._pending_requests.get(request_id)

    def _handle_expired_request(
        self, request_id: str, pending_request: PendingRequest
    ):
        """Handle an expired request during cleanup."""
        if pending_request.status != ResponseStatus.TIMEOUT:
            pending_request.status = ResponseStatus.TIMEOUT
            # Create and store timeout response
            self._completion_results[request_id] = (
                self._create_timeout_response(pending_request)
            )
            # Signal any waiting threads
            pending_request.completion_event.set()

    def _should_clean_completed_request(
        self, pending_request: PendingRequest, current_time: datetime
    ) -> bool:
        """Check if a completed request should be cleaned up."""
        if not pending_request.status.is_terminal():
            return False

        completion_age = current_time - pending_request.registered_at
        return (
            completion_age.total_seconds()
            > self.config.cleanup_interval_seconds
        )

    def cleanup_completed_requests(self) -> int:
        """Remove completed and expired requests from tracking.

        Performs maintenance cleanup to prevent memory leaks and
        maintain optimal performance by removing coordination state
        for requests that are no longer needed.

        Returns
        -------
        int
            Number of requests that were cleaned up

        Notes
        -----
        Cleanup removes:
        - Expired requests that timed out
        - Completed requests older than retention period
        - Cached responses no longer needed

        This method is thread-safe and can be called manually or
        will be called automatically by the background cleanup thread.
        """
        cleaned_count = 0
        current_time = datetime.now()

        with self._lock:
            # Find requests to clean up
            to_remove = []

            for request_id, pending_request in self._pending_requests.items():
                # Check if expired
                if pending_request.is_expired():
                    to_remove.append(request_id)
                    self._handle_expired_request(request_id, pending_request)
                    continue

                # Check if completed and old enough to clean
                if self._should_clean_completed_request(
                    pending_request, current_time
                ):
                    to_remove.append(request_id)

            # Remove identified requests and their results
            for request_id in to_remove:
                del self._pending_requests[request_id]
                # Also clean up any completion results
                if request_id in self._completion_results:
                    del self._completion_results[request_id]
                cleaned_count += 1

        if cleaned_count > 0:
            logger.info(
                f"Cleaned up {cleaned_count} completed/expired requests"
            )

        return cleaned_count

    def _create_timeout_response(
        self, pending_request: PendingRequest
    ) -> ResponseResult:
        """Create a timeout response for an expired request.

        Parameters
        ----------
        pending_request : PendingRequest
            The request that timed out

        Returns
        -------
        ResponseResult
            Timeout response ready for API return
        """
        processing_time_ms = (
            datetime.now() - pending_request.registered_at
        ).total_seconds() * 1000

        return ResponseResult(
            request_id=pending_request.request_id,
            success=False,
            api_response=ApiResponse(
                success=False,
                request_id=pending_request.request_id,
                order_id=None,
                data=None,
                error=ApiError(
                    code="PROCESSING_TIMEOUT",
                    message="Order processing exceeded time limit",
                    details={
                        "timeout_ms": int(
                            (
                                pending_request.timeout_at
                                - pending_request.registered_at
                            ).total_seconds()
                            * 1000
                        ),
                        "stage": pending_request.current_stage,
                        "team_id": pending_request.team_id,
                    },
                ),
            ),
            processing_time_ms=processing_time_ms,
            final_status=ResponseStatus.TIMEOUT,
        )

    def _start_cleanup_thread(self):
        """Start the background cleanup thread."""

        def cleanup_worker():
            """Background thread that periodically cleans up expired requests."""
            logger.info(
                f"Cleanup thread started, interval: {self.config.cleanup_interval_seconds}s"
            )

            while not self._shutdown:
                try:
                    # Wait for cleanup interval or shutdown signal
                    if self._cleanup_event.wait(
                        timeout=self.config.cleanup_interval_seconds
                    ):
                        # Event was set, check if we're shutting down
                        break

                    # Timeout occurred, perform cleanup
                    if not self._shutdown:
                        self.cleanup_completed_requests()

                except Exception as e:
                    logger.error(
                        f"Error in cleanup thread: {e}", exc_info=True
                    )

            logger.info("Cleanup thread stopped")

        self._cleanup_thread = threading.Thread(
            target=cleanup_worker,
            name="OrderResponseCoordinator-Cleanup",
            daemon=True,
        )
        self._cleanup_thread.start()

    def shutdown(self):
        """Shutdown the coordinator and cleanup resources.

        Stops accepting new requests and cleans up all resources.
        Should be called when the service is stopping.
        """
        logger.info("Shutting down OrderResponseCoordinator")

        with self._lock:
            self._shutdown = True

            # Signal all waiting threads with error responses
            for pending_request in self._pending_requests.values():
                if not pending_request.status.is_terminal():
                    pending_request.status = ResponseStatus.ERROR
                    # Create error response for shutdown
                    shutdown_result = ResponseResult(
                        request_id=pending_request.request_id,
                        success=False,
                        api_response=ApiResponse(
                            success=False,
                            request_id=pending_request.request_id,
                            error=ApiError(
                                code="SERVICE_SHUTDOWN",
                                message="Service shutting down",
                            ),
                        ),
                        processing_time_ms=(
                            datetime.now() - pending_request.registered_at
                        ).total_seconds()
                        * 1000,
                        final_status=ResponseStatus.ERROR,
                    )
                    self._completion_results[pending_request.request_id] = (
                        shutdown_result
                    )
                    pending_request.completion_event.set()

        # Signal cleanup thread to stop immediately
        self._cleanup_event.set()

        # Stop cleanup thread
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)  # Much shorter timeout now

        # Final cleanup
        with self._lock:
            self._pending_requests.clear()
            self._completion_results.clear()

        logger.info("OrderResponseCoordinator shutdown complete")
