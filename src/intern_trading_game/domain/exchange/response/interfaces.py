"""Abstract interfaces for order response coordination.

This module defines the contracts and protocols for the order response
coordination system. These interfaces enable dependency injection, testing
with mocks, and clear separation between coordination logic and implementation
details.

The interfaces follow the Dependency Inversion Principle by defining
abstractions that the coordination service depends on, rather than concrete
implementations. This enables flexible testing and future extensibility.

Examples
--------
>>> # Using the interface for dependency injection
>>> def create_api_endpoint(coordinator: OrderResponseCoordinatorInterface):
...     @router.post("/orders")
...     async def submit_order(request: OrderRequest):
...         registration = coordinator.register_request("TEAM_001")
...         # Submit to pipeline...
...         result = await coordinator.wait_for_completion(registration.request_id)
...         return result.to_api_response()
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from ....infrastructure.api.models import ApiResponse
from .models import PendingRequest, ResponseStatus


@dataclass
class ResponseRegistration:
    """Registration result for a new coordination request.

    This immutable data structure represents the successful registration
    of a new order request in the coordination system. It contains the
    unique identifiers and metadata needed to track the request through
    the processing pipeline.

    The registration serves as a handle for API threads to reference
    their specific request during coordination operations like status
    checks and completion waiting.

    Attributes
    ----------
    request_id : str
        Unique identifier for this coordination request, used to correlate
        pipeline notifications with waiting API threads
    team_id : str
        ID of the trading team that submitted the request, used for
        authorization and audit trails
    timeout_at : datetime
        Absolute timestamp when request will be considered expired,
        enabling proper timeout handling and resource cleanup
    status : ResponseStatus
        Initial status of the request, typically PENDING when first
        registered with the coordination service

    Notes
    -----
    ResponseRegistration instances are immutable and should not be
    modified after creation. They serve as proof of successful
    registration and contain all metadata needed for coordination.

    The request_id must be unique across all concurrent requests to
    prevent coordination conflicts. The coordination service generates
    these IDs using a prefix plus timestamp plus random component.

    TradingContext
    --------------
    In trading systems, registration represents:
    - **Request Receipt**: Confirmation that order was accepted for processing
    - **Timeout Contract**: SLA for maximum processing time
    - **Audit Trail**: Trackable event for regulatory compliance
    - **Resource Allocation**: Claim on system processing capacity

    Examples
    --------
    >>> # Register a new request
    >>> registration = coordinator.register_request("TEAM_001", timeout_seconds=5.0)
    >>> print(f"Request {registration.request_id} registered")
    >>>
    >>> # Check if registration has expired
    >>> if datetime.now() >= registration.timeout_at:
    ...     print("Request expired")
    """

    request_id: str
    team_id: str
    timeout_at: datetime
    status: ResponseStatus


@dataclass
class ResponseResult:
    """Final result of order response coordination.

    This immutable data structure contains the complete result of
    processing an order request through the coordination system. It
    aggregates all information needed to generate the final API response
    that will be returned to the waiting client.

    The result encapsulates both successful and failed outcomes,
    providing a unified interface for API threads to handle any
    coordination outcome without needing to understand the internal
    coordination mechanisms.

    Attributes
    ----------
    request_id : str
        Unique identifier for the coordinated request, matching the
        ID from the original ResponseRegistration
    success : bool
        Whether the coordination completed successfully with a valid
        order result, or failed with an error condition
    api_response : ApiResponse
        Complete API response ready to be returned to the client,
        formatted according to the standard ApiResponse structure
    processing_time_ms : float
        Total time spent in coordination from registration to completion,
        useful for performance monitoring and SLA tracking
    final_status : ResponseStatus
        Final internal status when coordination completed, useful for
        debugging and monitoring coordination patterns
    order_id : Optional[str]
        Exchange-assigned order ID if order was successfully created,
        None for validation failures or system errors

    Notes
    -----
    ResponseResult instances are immutable and represent the final
    outcome of coordination. They contain everything needed to:
    - Return appropriate HTTP response to API client
    - Record metrics and audit information
    - Clean up coordination state

    The api_response field is pre-formatted and ready for direct
    return to the client, eliminating the need for API endpoints
    to understand coordination internals.

    TradingContext
    --------------
    In trading systems, coordination results represent:
    - **Order Outcome**: Final status of order processing
    - **Performance Data**: Timing information for optimization
    - **Audit Evidence**: Complete record of processing outcome
    - **Client Communication**: Formatted response for trading algorithms

    Examples
    --------
    >>> # Wait for coordination to complete
    >>> result = await coordinator.wait_for_completion("req_123")
    >>>
    >>> # Return API response
    >>> return JSONResponse(
    ...     status_code=200 if result.success else 400,
    ...     content=result.api_response.dict()
    ... )
    >>>
    >>> # Record performance metrics
    >>> metrics.record_processing_time(result.processing_time_ms)
    """

    request_id: str
    success: bool
    api_response: ApiResponse
    processing_time_ms: float
    final_status: ResponseStatus
    order_id: Optional[str] = None


class OrderResponseCoordinatorInterface(ABC):
    """Abstract interface for order response coordination service.

    This interface defines the contract for coordinating synchronous API
    responses with asynchronous order processing pipelines. It provides
    the methods needed to register requests, track their progress, and
    deliver final results to waiting API threads.

    The interface abstracts the complex multi-threaded coordination
    mechanisms behind simple, testable methods that can be easily
    mocked and dependency-injected throughout the application.

    Implementations of this interface must provide thread-safe operation
    suitable for high-concurrency trading environments with multiple
    API threads and pipeline threads operating simultaneously.

    Notes
    -----
    This interface follows the Interface Segregation Principle by
    providing only the methods needed for coordination, without
    exposing internal implementation details like threading primitives
    or state management mechanisms.

    All methods must be thread-safe and suitable for concurrent access
    from multiple threads. Implementations should use appropriate
    synchronization mechanisms internally.

    TradingContext
    --------------
    In trading systems, the coordinator serves as:
    - **Response Bridge**: Connecting sync APIs with async processing
    - **SLA Enforcer**: Ensuring timely responses to trading algorithms
    - **Resource Manager**: Preventing memory leaks from abandoned requests
    - **Performance Monitor**: Tracking coordination efficiency

    The interface enables clean separation between API concerns and
    coordination concerns, supporting both unit testing and integration
    testing strategies.

    Examples
    --------
    >>> # Dependency injection in API endpoint
    >>> @router.post("/orders")
    >>> async def submit_order(
    ...     request: OrderRequest,
    ...     coordinator: OrderResponseCoordinatorInterface = Depends(get_coordinator)
    ... ):
    ...     registration = coordinator.register_request(team.team_id)
    ...     # Submit to pipeline...
    ...     result = await coordinator.wait_for_completion(registration.request_id)
    ...     return JSONResponse(content=result.api_response.dict())
    >>>
    >>> # Unit testing with mock
    >>> @pytest.fixture
    >>> def mock_coordinator():
    ...     coordinator = Mock(spec=OrderResponseCoordinatorInterface)
    ...     coordinator.register_request.return_value = ResponseRegistration(...)
    ...     return coordinator
    """

    @abstractmethod
    def register_request(
        self, team_id: str, timeout_seconds: Optional[float] = None
    ) -> ResponseRegistration:
        """Register a new request for coordination tracking.

        Creates a new coordination entry for an incoming order request,
        allocating the necessary tracking resources and generating a
        unique identifier for pipeline correlation.

        This method must be called by API threads before submitting
        orders to the processing pipeline to ensure proper response
        coordination and timeout handling.

        Parameters
        ----------
        team_id : str
            ID of the trading team submitting the request, used for
            authorization checks and audit trail generation
        timeout_seconds : Optional[float], default=None
            Maximum time to wait for processing completion before
            returning timeout error. If None, uses service default

        Returns
        -------
        ResponseRegistration
            Registration handle containing request_id and metadata
            needed for subsequent coordination operations

        Raises
        ------
        CoordinationError
            If registration fails due to resource limits or invalid
            parameters. Common causes include:
            - Too many pending requests (service overloaded)
            - Invalid team_id or timeout value
            - Service shutdown in progress

        Notes
        -----
        This method allocates coordination resources including:
        - Unique request identifier generation
        - Threading event creation for completion signaling
        - Timeout calculation and tracking
        - Memory allocation for request metadata

        The method must be thread-safe and should complete quickly
        (typically <1ms) to avoid blocking API request processing.

        TradingContext
        --------------
        Registration represents the beginning of the order lifecycle:
        - **Resource Allocation**: Claim on coordination capacity
        - **SLA Establishment**: Timeout contract with client
        - **Audit Initiation**: Start of request tracking
        - **Pipeline Preparation**: Setup for async processing

        Failed registration typically indicates system overload and
        should result in 503 Service Unavailable responses.

        Examples
        --------
        >>> # Basic registration
        >>> registration = coordinator.register_request("TEAM_001")
        >>> print(f"Registered as {registration.request_id}")
        >>>
        >>> # Registration with custom timeout
        >>> registration = coordinator.register_request(
        ...     team_id="TEAM_HFT",
        ...     timeout_seconds=2.0  # High-frequency trading needs fast response
        ... )
        >>>
        >>> # Handle registration failure
        >>> try:
        ...     registration = coordinator.register_request("TEAM_001")
        ... except CoordinationError as e:
        ...     return JSONResponse(503, {"error": "Service overloaded"})
        """
        pass

    @abstractmethod
    def wait_for_completion(
        self, request_id: str, timeout_seconds: Optional[float] = None
    ) -> ResponseResult:
        """Wait for request processing to complete and return final result.

        Blocks the calling thread until the specified request completes
        processing through the pipeline, returning the final result that
        should be sent to the API client.

        This method implements the core coordination mechanism that bridges
        synchronous API expectations with asynchronous pipeline processing.

        Parameters
        ----------
        request_id : str
            Unique identifier for the request to wait for, obtained from
            the ResponseRegistration returned by register_request()
        timeout_seconds : Optional[float], default=None
            Maximum time to wait for completion. If None, uses the timeout
            specified during registration or service default

        Returns
        -------
        ResponseResult
            Complete result containing formatted API response and metadata
            ready for return to the client

        Raises
        ------
        CoordinationError
            If waiting fails due to invalid request_id or coordination
            system errors. This indicates a programming error rather
            than normal business logic failures
        TimeoutError
            If processing exceeds the specified timeout. Note that
            normal timeout handling creates ResponseResult with error
            rather than raising exceptions

        Notes
        -----
        This method implements the core blocking behavior that allows
        REST API endpoints to provide synchronous responses for
        asynchronous processing.

        The method must be async-compatible and should not block the
        event loop for non-async callers. Implementation should use
        appropriate async synchronization primitives.

        Timeout handling creates appropriate HTTP error responses:
        - 504 Gateway Timeout for processing delays
        - 500 Internal Server Error for system failures
        - 400 Bad Request for validation failures

        TradingContext
        --------------
        Completion waiting represents the critical path for:
        - **API Response Timing**: Delivering timely feedback to traders
        - **SLA Compliance**: Meeting response time commitments
        - **Error Communication**: Providing clear failure information
        - **Performance Measurement**: Tracking end-to-end latency

        This method determines the perceived performance and reliability
        of the entire trading system from the client perspective.

        Examples
        --------
        >>> # Basic completion waiting
        >>> result = await coordinator.wait_for_completion("req_123")
        >>> return JSONResponse(content=result.api_response.dict())
        >>>
        >>> # Custom timeout for high-frequency trading
        >>> try:
        ...     result = await coordinator.wait_for_completion(
        ...         request_id="req_hft_456",
        ...         timeout_seconds=1.0
        ...     )
        ... except TimeoutError:
        ...     return JSONResponse(504, {"error": "Processing timeout"})
        >>>
        >>> # Handle coordination errors
        >>> try:
        ...     result = await coordinator.wait_for_completion("invalid_id")
        ... except CoordinationError:
        ...     return JSONResponse(500, {"error": "Internal coordination error"})
        """
        pass

    @abstractmethod
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

        This method implements the signaling mechanism that unblocks
        waiting API threads and delivers final results.

        Parameters
        ----------
        request_id : str
            Unique identifier for the completed request, matching the
            ID from the original registration
        api_response : ApiResponse
            Complete API response formatted for return to client,
            including success/failure status and all result data
        order_id : Optional[str], default=None
            Exchange-assigned order ID if order was successfully created,
            used for correlation and audit purposes

        Returns
        -------
        bool
            True if notification was successfully processed, False if
            request was not found (already completed, expired, or invalid)

        Notes
        -----
        This method must be thread-safe and callable from any pipeline
        thread. It should complete quickly to avoid blocking pipeline
        processing.

        The method handles:
        - Request validation and lookup
        - Result storage for retrieval by waiting threads
        - Thread signaling to unblock API threads
        - State transition to terminal status

        Multiple notifications for the same request_id are ignored
        (idempotent operation) to handle race conditions in pipeline
        processing.

        TradingContext
        --------------
        Completion notification represents:
        - **Pipeline Completion**: End of order processing workflow
        - **Result Delivery**: Final outcome communication
        - **Resource Release**: Signal for cleanup operations
        - **Audit Completion**: Final entry in request lifecycle

        This method determines how quickly API clients receive responses
        and must be optimized for low latency.

        Examples
        --------
        >>> # Successful order completion
        >>> success = coordinator.notify_completion(
        ...     request_id="req_123",
        ...     api_response=ApiResponse(
        ...         success=True,
        ...         order_id="ORD_456",
        ...         data={"status": "filled", "quantity": 100}
        ...     ),
        ...     order_id="ORD_456"
        ... )
        >>>
        >>> # Validation failure completion
        >>> coordinator.notify_completion(
        ...     request_id="req_124",
        ...     api_response=ApiResponse(
        ...         success=False,
        ...         error=ApiError(
        ...             code="POSITION_LIMIT_EXCEEDED",
        ...             message="Order exceeds position limit"
        ...         )
        ...     )
        ... )
        """
        pass

    @abstractmethod
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

        This method supports observability and debugging by tracking
        detailed request progression, but does not affect the final
        client response.

        Parameters
        ----------
        request_id : str
            Unique identifier for the request to update
        status : ResponseStatus
            New internal status reflecting current processing stage
        stage_details : Optional[Dict], default=None
            Additional metadata about current processing stage,
            such as timing information or interim results

        Returns
        -------
        bool
            True if status was successfully updated, False if request
            was not found or update was invalid

        Notes
        -----
        This method enables detailed tracking of request progression
        for monitoring, alerting, and debugging purposes. Status
        updates are used for:
        - Performance monitoring dashboards
        - Bottleneck identification
        - Error root cause analysis
        - Capacity planning

        Status transitions must follow business logic rules:
        - Forward progression through pipeline stages
        - No transitions from terminal states
        - Appropriate error state transitions

        TradingContext
        --------------
        Status updates enable:
        - **Performance Monitoring**: Track stage-specific latencies
        - **Bottleneck Detection**: Identify slow processing stages
        - **Error Analysis**: Understand where failures occur
        - **Capacity Planning**: Monitor queue depths and utilization

        Examples
        --------
        >>> # Update to validation stage
        >>> coordinator.update_status("req_123", ResponseStatus.VALIDATING)
        >>>
        >>> # Update with stage details
        >>> coordinator.update_status(
        ...     request_id="req_124",
        ...     status=ResponseStatus.MATCHING,
        ...     stage_details={"partial_fills": 2, "remaining_quantity": 50}
        ... )
        """
        pass

    @abstractmethod
    def get_request_status(self, request_id: str) -> Optional[PendingRequest]:
        """Retrieve current status and metadata for a request.

        Provides read-only access to request tracking information for
        monitoring, debugging, and administrative purposes.

        This method supports operational visibility into coordination
        state without affecting request processing.

        Parameters
        ----------
        request_id : str
            Unique identifier for the request to query

        Returns
        -------
        Optional[PendingRequest]
            Current request state if found, None if request does not
            exist, has been cleaned up, or was never registered

        Notes
        -----
        This method is primarily for monitoring and debugging purposes.
        Normal API operation should not require status queries.

        The returned PendingRequest contains:
        - Current processing status
        - Timing information
        - Associated metadata
        - Processing metrics

        TradingContext
        --------------
        Status queries support:
        - **Operations Monitoring**: Real-time system visibility
        - **Debugging Support**: Investigation of stuck requests
        - **Performance Analysis**: Understanding processing patterns
        - **Administrative Tools**: System health assessment

        Examples
        --------
        >>> # Check request status
        >>> pending = coordinator.get_request_status("req_123")
        >>> if pending:
        ...     print(f"Status: {pending.status}, Stage: {pending.current_stage}")
        >>>
        >>> # Monitor processing time
        >>> if pending and pending.get_total_processing_time_ms() > 1000:
        ...     alert_slow_processing(pending.request_id)
        """
        pass

    @abstractmethod
    def cleanup_completed_requests(self) -> int:
        """Remove completed and expired requests from tracking.

        Performs maintenance cleanup to prevent memory leaks and
        maintain optimal performance by removing coordination state
        for requests that are no longer needed.

        This method is typically called by background maintenance
        threads on a regular schedule.

        Returns
        -------
        int
            Number of requests that were cleaned up

        Notes
        -----
        Cleanup removes:
        - Completed requests older than retention period
        - Expired requests that timed out
        - Orphaned requests from crashed threads

        The method preserves:
        - Active requests still being processed
        - Recently completed requests for metric collection
        - Requests within configured retention window

        Cleanup is essential for:
        - Preventing memory leaks in long-running processes
        - Maintaining lookup performance
        - Managing resource utilization

        TradingContext
        --------------
        Regular cleanup ensures:
        - **System Stability**: Prevents memory exhaustion
        - **Performance Maintenance**: Keeps lookups fast
        - **Resource Efficiency**: Manages coordination overhead
        - **Operational Health**: Supports continuous operation

        Examples
        --------
        >>> # Manual cleanup trigger
        >>> cleaned = coordinator.cleanup_completed_requests()
        >>> print(f"Cleaned up {cleaned} completed requests")
        >>>
        >>> # Background cleanup loop
        >>> while True:
        ...     await asyncio.sleep(30)  # Every 30 seconds
        ...     coordinator.cleanup_completed_requests()
        """
        pass
