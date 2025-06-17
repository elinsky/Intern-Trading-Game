"""Data models for order response coordination.

This module defines the core data structures used by the OrderResponseService
to track request lifecycles, manage coordination state, and configure service
behavior. All models follow immutable design patterns where possible to
ensure thread safety in the multi-threaded exchange environment.

The models represent the business concepts involved in coordinating between
synchronous REST API responses and asynchronous order processing pipelines.

Examples
--------
>>> # Create a pending request
>>> request = PendingRequest(
...     request_id="req_123",
...     team_id="TEAM_001",
...     status=ResponseStatus.PENDING,
...     registered_at=datetime.now(),
...     timeout_at=datetime.now() + timedelta(seconds=5)
... )
>>>
>>> # Check if request has expired
>>> if request.is_expired():
...     print("Request timed out")
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class ResponseStatus(Enum):
    """Status enumeration for order response coordination lifecycle.

    This enumeration tracks the progression of an order request through
    the asynchronous processing pipeline, enabling proper coordination
    between the synchronous REST API and the multi-threaded exchange
    processing stages.

    The status progression typically follows:
    PENDING → VALIDATING → MATCHING → SETTLING → COMPLETED

    Error states (TIMEOUT, ERROR) can occur at any stage.

    Attributes
    ----------
    PENDING : str
        Request registered, awaiting processing
    VALIDATING : str
        Currently being processed by validator thread
    MATCHING : str
        Currently being processed by matching thread
    SETTLING : str
        Currently being processed by trade publisher thread
    COMPLETED : str
        Processing complete, final result available
    TIMEOUT : str
        Request expired without completion
    ERROR : str
        Pipeline error occurred during processing

    Notes
    -----
    Status transitions must follow business logic constraints:
    - Only PENDING requests can transition to VALIDATING
    - TIMEOUT and ERROR are terminal states
    - COMPLETED is the successful terminal state

    The status enables proper error handling and timeout management
    throughout the coordination process.

    TradingContext
    --------------
    In trading systems, request status is critical for:
    - API response timing and accuracy
    - Error reporting to trading algorithms
    - System performance monitoring and alerting
    - Regulatory audit trails for order processing

    Examples
    --------
    >>> # Check if request is still being processed
    >>> if status in [ResponseStatus.PENDING, ResponseStatus.VALIDATING]:
    ...     print("Request still in progress")
    >>>
    >>> # Check if request completed successfully
    >>> if status == ResponseStatus.COMPLETED:
    ...     return result.api_response
    """

    PENDING = "pending"
    VALIDATING = "validating"
    MATCHING = "matching"
    SETTLING = "settling"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal state.

        Returns
        -------
        bool
            True if status is COMPLETED, TIMEOUT, or ERROR
        """
        return self in {self.COMPLETED, self.TIMEOUT, self.ERROR}

    def is_active(self) -> bool:
        """Check if this status represents an active processing state.

        Returns
        -------
        bool
            True if status is PENDING, VALIDATING, MATCHING, or SETTLING
        """
        return self in {
            self.PENDING,
            self.VALIDATING,
            self.MATCHING,
            self.SETTLING,
        }


@dataclass
class CoordinationConfig:
    """Configuration settings for order response coordination service.

    This configuration class defines the behavioral parameters for the
    OrderResponseCoordinator service, including timeout values, resource
    limits, and operational settings. All settings have sensible defaults
    suitable for production trading environments.

    The configuration enables tuning of the coordination service based on
    system load characteristics, latency requirements, and resource
    constraints specific to different deployment environments.

    Attributes
    ----------
    default_timeout_seconds : float, default=5.0
        Maximum time to wait for order processing completion before
        returning 504 Gateway Timeout to API clients
    max_pending_requests : int, default=1000
        Maximum number of concurrent pending requests allowed before
        returning 503 Service Unavailable to new requests
    cleanup_interval_seconds : int, default=30
        How frequently to run background cleanup of expired requests
        and completed responses to prevent memory leaks
    enable_metrics : bool, default=True
        Whether to collect and expose performance metrics for monitoring
        and alerting on coordination service health
    enable_detailed_logging : bool, default=False
        Whether to log detailed coordination events for debugging.
        Warning: Can generate high log volume in production
    request_id_prefix : str, default="req"
        Prefix for generated request IDs to enable easy identification
        in logs and debugging tools

    Notes
    -----
    Configuration values should be tuned based on:
    - Expected order processing latency (timeout_seconds)
    - Peak concurrent load (max_pending_requests)
    - Memory usage patterns (cleanup_interval_seconds)
    - Monitoring infrastructure (enable_metrics)
    - Debugging requirements (enable_detailed_logging)

    Changes to configuration require service restart to take effect.

    TradingContext
    --------------
    Trading system configuration must balance:
    - **Responsiveness**: Short timeouts for fast feedback
    - **Reliability**: Sufficient timeouts for complex orders
    - **Capacity**: Adequate limits for peak trading periods
    - **Observability**: Metrics and logging for system health

    Typical production values:
    - High-frequency trading: 1-2 second timeouts
    - Institutional trading: 5-10 second timeouts
    - Retail trading: 10-30 second timeouts

    Examples
    --------
    >>> # Production configuration
    >>> config = CoordinationConfig(
    ...     default_timeout_seconds=3.0,
    ...     max_pending_requests=5000,
    ...     cleanup_interval_seconds=15,
    ...     enable_metrics=True,
    ...     enable_detailed_logging=False
    ... )
    >>>
    >>> # Development configuration
    >>> dev_config = CoordinationConfig(
    ...     default_timeout_seconds=10.0,
    ...     max_pending_requests=100,
    ...     enable_detailed_logging=True
    ... )
    """

    default_timeout_seconds: float = 5.0
    max_pending_requests: int = 1000
    cleanup_interval_seconds: int = 30
    enable_metrics: bool = True
    enable_detailed_logging: bool = False
    request_id_prefix: str = "req"


@dataclass
class PendingRequest:
    """Represents a request awaiting completion in the coordination system.

    This class encapsulates all the state and metadata required to track
    an individual order request as it progresses through the asynchronous
    processing pipeline. It provides thread-safe coordination between the
    API thread waiting for a response and the pipeline threads processing
    the order.

    The PendingRequest maintains the synchronization primitive (Event) and
    timing information needed to implement proper timeout behavior and
    resource cleanup in the coordination service.

    Attributes
    ----------
    request_id : str
        Unique identifier for this coordination request, used to correlate
        API calls with pipeline processing results
    team_id : str
        ID of the trading team that submitted the request, used for
        authorization and audit trails
    status : ResponseStatus
        Current processing status, updated as request progresses through
        pipeline stages
    completion_event : threading.Event
        Thread synchronization primitive used to signal when processing
        is complete and result is available
    registered_at : datetime
        Timestamp when request was first registered, used for timeout
        calculations and performance metrics
    timeout_at : datetime
        Absolute timestamp when request should be considered expired,
        calculated from registered_at + timeout_seconds
    order_id : Optional[str], default=None
        Exchange-assigned order ID, set after order creation in validator
        thread. None until order is actually created
    current_stage : str, default="registration"
        Human-readable description of current processing stage for
        debugging and monitoring purposes
    error_details : Optional[str], default=None
        Detailed error information if processing fails, used to generate
        appropriate API error responses
    processing_metrics : Dict, default=empty
        Performance metrics collected during processing, including timing
        information for each pipeline stage

    Notes
    -----
    PendingRequest instances are created by the coordination service and
    should not be directly instantiated by client code. The completion_event
    is managed internally and should not be manipulated externally.

    Thread safety is ensured through proper use of the completion_event
    and atomic updates to status fields. Multiple threads may read from
    the same PendingRequest safely.

    TradingContext
    --------------
    In trading systems, pending requests represent:
    - **Active Orders**: Orders currently being processed
    - **API Contracts**: Promises to deliver responses to clients
    - **Audit Points**: Trackable events for regulatory compliance
    - **Performance Metrics**: Data for system optimization

    Request lifecycle typically spans 10-500ms depending on:
    - Order complexity and validation requirements
    - Market conditions and liquidity availability
    - System load and processing capacity

    Examples
    --------
    >>> # Check if request has expired
    >>> request = PendingRequest(...)
    >>> if request.is_expired():
    ...     print(f"Request {request.request_id} timed out")
    >>>
    >>> # Update processing stage
    >>> request.current_stage = "validation"
    >>> request.status = ResponseStatus.VALIDATING
    >>>
    >>> # Wait for completion with timeout
    >>> if request.completion_event.wait(timeout=1.0):
    ...     print("Request completed")
    ... else:
    ...     print("Still waiting...")
    """

    request_id: str
    team_id: str
    status: ResponseStatus
    completion_event: threading.Event
    registered_at: datetime
    timeout_at: datetime
    order_id: Optional[str] = None
    current_stage: str = "registration"
    error_details: Optional[str] = None
    processing_metrics: Dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if this request has exceeded its timeout.

        Returns
        -------
        bool
            True if current time is past the timeout_at timestamp

        Notes
        -----
        This method uses the system clock to determine expiration.
        Clock skew or system time changes could affect accuracy.
        """
        return datetime.now() >= self.timeout_at

    def add_processing_metric(self, stage: str, duration_ms: float) -> None:
        """Add a processing time metric for a pipeline stage.

        Parameters
        ----------
        stage : str
            Name of the processing stage (e.g., "validation", "matching")
        duration_ms : float
            Processing time in milliseconds for this stage

        Notes
        -----
        Metrics are stored in the processing_metrics dictionary for
        later analysis and reporting. This method is thread-safe.
        """
        self.processing_metrics[stage] = duration_ms

    def get_total_processing_time_ms(self) -> float:
        """Calculate total processing time from registration to now.

        Returns
        -------
        float
            Total elapsed time in milliseconds since request registration
        """
        elapsed = datetime.now() - self.registered_at
        return elapsed.total_seconds() * 1000
