"""Abstract interfaces for API service layer.

This module defines the abstract base classes that establish contracts
for extracting business logic from the monolithic thread functions in
main.py. Each interface represents a specific thread's business logic
while maintaining clear separation of concerns.

The interfaces are designed to:
- Extract pure business logic from infrastructure concerns
- Enable unit testing without threading complexity
- Support dependency injection for flexible implementations
- Reuse existing data types throughout the codebase

All interfaces follow SOLID principles, particularly:
- Interface Segregation: Each interface has a focused responsibility
- Dependency Inversion: Depend on abstractions, not concrete implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

from ..domain.exchange.core.order import Order
from ..domain.exchange.order_result import OrderResult
from ..infrastructure.api.models import OrderResponse, TeamInfo


class OrderValidationServiceInterface(ABC):
    """Abstract interface for order validation business logic.

    This service encapsulates the business logic currently embedded in
    the validator_thread (Thread 2), including order validation against
    constraints and cancellation request processing.

    The service is responsible for:
    - Building validation context with current positions and orders
    - Running constraint-based validation through OrderValidator
    - Processing cancellation requests with ownership verification
    - Returning structured results for thread infrastructure to handle

    Thread controllers use this service to separate business logic from
    queue management, threading, and response handling infrastructure.

    Notes
    -----
    This interface extracts logic from validator_thread() lines 144-261,
    preserving the exact validation behavior while enabling testability.

    The service maintains the existing two-phase validation:
    1. Constraint validation for new orders
    2. Ownership verification for cancellations

    TradingContext
    --------------
    Order validation enforces role-specific constraints including:
    - Position limits (e.g., market makers limited to ±50)
    - Order rate limits per tick
    - Instrument restrictions by role
    - Price range validations for limit orders

    Cancellation requests must verify ownership to prevent market
    manipulation attempts by unauthorized parties.

    Examples
    --------
    >>> # In thread controller (infrastructure)
    >>> validation_service = get_validation_service()
    >>> result = validation_service.validate_new_order(order, team)
    >>> if result.status == "accepted":
    ...     match_queue.put((order, team_info))
    >>> else:
    ...     # Send rejection via WebSocket
    ...     websocket_queue.put(create_rejection_message(result))
    """

    @abstractmethod
    def validate_new_order(self, order: Order, team: TeamInfo) -> OrderResult:
        """Validate a new order against all configured constraints.

        Performs comprehensive validation of an incoming order including
        position limits, order rates, instrument restrictions, and any
        role-specific constraints configured for the team.

        Parameters
        ----------
        order : Order
            The order to validate, containing instrument, side, quantity,
            and price information
        team : TeamInfo
            Team information including role and authentication details
            used to determine applicable constraints

        Returns
        -------
        OrderResult
            Result from exchange.order_result containing:
            - status: str ("accepted" or "rejected")
            - order_id: str identifying the order
            - error_code: Optional[str] for rejections
            - error_message: Optional[str] with constraint violation details

        Notes
        -----
        The method should:
        1. Retrieve current positions for the team
        2. Get order count for current tick
        3. Build ValidationContext with all required state
        4. Run validation through configured OrderValidator
        5. Return the unmodified ValidationResult

        The thread controller handles all infrastructure concerns like
        queue routing and WebSocket notifications based on the result.

        TradingContext
        --------------
        Validation includes role-specific business rules:
        - Market makers: ±50 position limit, all order types allowed
        - Hedge funds: Delta neutral constraints (future enhancement)
        - Arbitrage desks: SPX/SPY ratio constraints (future enhancement)

        The validation must complete quickly (<1ms) to maintain low
        latency order processing in the exchange pipeline.
        """
        pass

    @abstractmethod
    def validate_cancellation(
        self, order_id: str, team_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate and process an order cancellation request.

        Verifies that the requesting team owns the order before
        attempting cancellation at the exchange. This prevents
        unauthorized cancellation attempts.

        Parameters
        ----------
        order_id : str
            The exchange-assigned order ID to cancel
        team_id : str
            The ID of the team requesting cancellation, used for
            ownership verification

        Returns
        -------
        Tuple[bool, Optional[str]]
            A tuple containing:
            - success: bool indicating if cancellation succeeded
            - reason: Optional[str] with failure reason if applicable
              (e.g., "Order not found", "Unauthorized", "Already filled")

        Notes
        -----
        The method should:
        1. Verify the order exists and belongs to the requesting team
        2. Attempt cancellation at the exchange level
        3. Return success/failure with appropriate reason

        The thread controller uses this result to:
        - Create appropriate OrderResponse
        - Send WebSocket notifications (cancel_ack or cancel_reject)
        - Update any necessary state

        TradingContext
        --------------
        Cancellation requests are processed in FIFO order with all
        other order messages to ensure temporal fairness. A cancel
        submitted at T+1ms cannot jump ahead of a new order at T+0ms.

        In fast markets, cancellation may fail if the order has
        already been matched. This race condition is inherent to
        all exchanges and must be handled gracefully.
        """
        pass


class OrderMatchingServiceInterface(ABC):
    """Abstract interface for order matching business logic.

    This service encapsulates the business logic currently embedded in
    the matching_thread (Thread 3), including exchange interaction and
    error handling for order submission.

    The service is responsible for:
    - Submitting validated orders to the exchange
    - Handling exchange responses and errors
    - Creating standardized error responses
    - Returning results for thread infrastructure to process

    Thread controllers use this service to separate exchange interaction
    from queue management and WebSocket notification infrastructure.

    Notes
    -----
    This interface extracts logic from matching_thread() lines 267-321,
    preserving the exact exchange interaction patterns.

    The service maintains separation between successful submissions
    (which may still result in rejections) and exception cases.

    TradingContext
    --------------
    The matching engine uses continuous matching with price-time priority.
    Orders are processed immediately upon receipt, with no batching delay.

    Exchange interactions must be extremely fast (<5 microseconds) to
    maintain overall system latency targets for high-frequency trading.

    Examples
    --------
    >>> # In thread controller (infrastructure)
    >>> matching_service = get_matching_service()
    >>> try:
    ...     result = matching_service.submit_order_to_exchange(order)
    ...     if result.status in ["new", "partially_filled", "filled"]:
    ...         websocket_queue.put(create_ack_message(result))
    ...     trade_queue.put((result, order, team_info))
    ... except Exception as e:
    ...     error_result = matching_service.handle_exchange_error(e, order)
    ...     # Handle error response
    """

    @abstractmethod
    def submit_order_to_exchange(self, order: Order) -> OrderResult:
        """Submit a validated order to the exchange for matching.

        Wraps the exchange venue's order submission with appropriate
        error handling and result standardization.

        Parameters
        ----------
        order : Order
            The validated order to submit to the exchange

        Returns
        -------
        OrderResult
            Result from exchange.order_result containing:
            - order_id: str identifying the order
            - status: str ("new", "partially_filled", "filled", "rejected")
            - fills: List[Trade] of any immediate executions
            - remaining_quantity: float of unfilled quantity
            - error_code: Optional[str] for rejections
            - error_message: Optional[str] for rejections

        Notes
        -----
        The method should:
        1. Call exchange.submit_order(order)
        2. Return the OrderResult unchanged
        3. Let exceptions propagate for handle_exchange_error

        The thread controller uses the status to determine:
        - Whether to send order acknowledgment via WebSocket
        - How to process any resulting trades
        - Whether error handling is needed

        TradingContext
        --------------
        Orders may receive immediate fills if they cross the spread.
        Market orders always fill immediately if liquidity exists.
        Limit orders may rest in the book if no match is available.

        The exchange maintains strict price-time priority for all
        resting orders in the limit order book.
        """
        pass

    @abstractmethod
    def handle_exchange_error(
        self, error: Exception, order: Order
    ) -> OrderResult:
        """Handle exceptions from exchange interactions.

        Creates a standardized error response when the exchange
        raises an exception during order processing.

        Parameters
        ----------
        error : Exception
            The exception raised by the exchange
        order : Order
            The order that caused the exception

        Returns
        -------
        OrderResult
            An error OrderResult with:
            - order_id: The order's ID
            - status: "error" or "rejected"
            - error_code: Standardized error code
            - error_message: Human-readable error description

        Notes
        -----
        The method should:
        1. Log the exception for debugging
        2. Determine appropriate error code based on exception type
        3. Create user-friendly error message
        4. Return OrderResult with error details

        Common exceptions include:
        - ValueError: Invalid order parameters
        - KeyError: Unknown instrument
        - RuntimeError: Exchange internal errors

        TradingContext
        --------------
        Exchange errors are rare but must be handled gracefully to
        prevent thread termination. Common causes include:
        - Invalid instrument IDs
        - System overload conditions
        - Internal consistency violations

        Error responses allow trading algorithms to handle failures
        appropriately, such as retrying or alerting operators.
        """
        pass


class TradeProcessingServiceInterface(ABC):
    """Abstract interface for trade processing business logic.

    This service encapsulates the business logic currently embedded in
    the trade_publisher_thread (Thread 4), including fee calculation,
    position updates, and execution report generation.

    The service is responsible for:
    - Processing trade executions from the matching engine
    - Calculating fees based on role and liquidity type
    - Updating position tracking
    - Creating complete OrderResponse for API clients

    Thread controllers use this service to separate trade processing
    from queue management and WebSocket broadcasting infrastructure.

    Notes
    -----
    This interface extracts logic from trade_publisher_thread() lines
    323-427, consolidating the complex trade processing workflow.

    The service coordinates multiple concerns internally while
    presenting a simple interface to the thread controller.

    TradingContext
    --------------
    Trade processing involves several business rules:
    - Market makers receive rebates for providing liquidity
    - All participants pay fees for removing liquidity
    - Positions must be updated atomically for risk management
    - Average prices use volume-weighted calculations

    Processing must complete quickly to maintain real-time position
    updates and P&L calculations for trading algorithms.

    Examples
    --------
    >>> # In thread controller (infrastructure)
    >>> trade_service = get_trade_processing_service()
    >>> response = trade_service.process_trade_result(result, order, team)
    >>>
    >>> # Update response tracking
    >>> order_responses[order.order_id] = response
    >>>
    >>> # Extract data for WebSocket notifications
    >>> if response.filled_quantity > 0:
    ...     for fill in result.fills:
    ...         websocket_queue.put(create_execution_report(fill, response))
    """

    @abstractmethod
    def process_trade_result(
        self, result: OrderResult, order: Order, team: TeamInfo
    ) -> OrderResponse:
        """Process trade execution result into complete order response.

        Coordinates all aspects of trade processing including fee
        calculation, position updates, and response generation.

        Parameters
        ----------
        result : OrderResult
            The result from the matching engine containing order status
            and any fill information
        order : Order
            The original order that was matched
        team : TeamInfo
            Team information including role for fee calculation

        Returns
        -------
        OrderResponse
            Complete response from api.models containing:
            - order_id: str
            - status: str matching the OrderResult status
            - timestamp: datetime of processing
            - filled_quantity: int total quantity filled
            - average_price: Optional[float] volume-weighted average
            - fees: float total fees (negative for rebates)
            - liquidity_type: Optional[str] "maker", "taker", or "mixed"

        Notes
        -----
        The method should internally:
        1. Calculate fees for each fill based on aggressor side
        2. Update position tracking atomically
        3. Calculate volume-weighted average price
        4. Determine overall liquidity type
        5. Create complete OrderResponse

        Fee calculation rules:
        - Market makers: -$0.02/contract rebate as maker
        - All roles: $0.05/contract fee as taker

        Position updates:
        - Buy orders increase position
        - Sell orders decrease position
        - Updates must be thread-safe

        TradingContext
        --------------
        Trade processing determines profit/loss for each participant:
        - Makers earn rebates for providing liquidity
        - Takers pay fees for immediate execution
        - Position tracking enables risk management

        The liquidity_type field helps algorithms optimize their
        order placement strategies to minimize costs or maximize
        rebates based on their role.
        """
        pass


class WebSocketMessagingServiceInterface(ABC):
    """Abstract interface for WebSocket messaging business logic.

    This service encapsulates the business logic currently embedded in
    the websocket_async_loop (Thread 8), including message routing and
    formatting for real-time client notifications.

    The service is responsible for:
    - Routing messages to appropriate WebSocket broadcast methods
    - Checking connection status before sending
    - Formatting standardized message types
    - Providing fire-and-forget async messaging

    Thread controllers use this service to separate message routing
    logic from async/await infrastructure and queue management.

    Notes
    -----
    This interface extracts logic from websocket_async_loop() lines
    486-531, focusing on the business logic of message routing.

    The service uses fire-and-forget pattern as WebSocket delivery
    is best-effort and non-blocking for trading operations.

    TradingContext
    --------------
    WebSocket messages provide real-time updates to trading algorithms:
    - Order acknowledgments confirm exchange acceptance
    - Execution reports detail individual trades
    - Rejection messages explain validation failures
    - Position snapshots show current holdings

    Message delivery must not block trading operations. Disconnected
    clients miss messages but can request position snapshots upon
    reconnection.

    Examples
    --------
    >>> # In thread controller (infrastructure)
    >>> messaging_service = get_messaging_service()
    >>>
    >>> # Route message from queue
    >>> msg_type, team_id, data = websocket_queue.get()
    >>> await messaging_service.route_message(msg_type, team_id, data)
    >>>
    >>> # Format standardized message
    >>> ack_data = messaging_service.format_order_ack(order, "new")
    >>> await messaging_service.route_message("new_order_ack", team_id, ack_data)
    """

    @abstractmethod
    async def route_message(
        self, msg_type: str, team_id: str, data: Dict
    ) -> None:
        """Route a message to the appropriate WebSocket broadcast method.

        Checks connection status and routes messages based on type
        to the correct WebSocket manager method.

        Parameters
        ----------
        msg_type : str
            The type of message to route. Valid values:
            - "new_order_ack": Order accepted by exchange
            - "new_order_reject": Order validation failed
            - "execution_report": Trade executed
            - "position_snapshot": Current positions
            - "order_cancel_ack": Cancellation confirmed
            - "order_cancel_reject": Cancellation failed
        team_id : str
            The team ID to send the message to
        data : Dict
            The message data to send, format depends on msg_type

        Returns
        -------
        None
            Fire-and-forget pattern, no return value

        Notes
        -----
        The method should:
        1. Check if team is connected via WebSocket
        2. Route to appropriate broadcast method based on msg_type
        3. Return immediately without waiting for delivery
        4. Silently skip if team not connected

        Message routing:
        - new_order_ack -> broadcast_new_order_ack()
        - new_order_reject -> broadcast_new_order_reject()
        - execution_report -> broadcast_trade_execution()
        - position_snapshot -> send_position_snapshot()
        - order_cancel_ack -> broadcast_cancel_ack()
        - order_cancel_reject -> broadcast_cancel_reject()

        TradingContext
        --------------
        Messages are delivered in order per team but may interleave
        between teams. Algorithms must handle out-of-order delivery
        gracefully.

        Critical messages like execution reports should be processed
        idempotently as network issues may cause duplicates.
        """
        pass

    @abstractmethod
    def format_order_ack(self, order: Order, status: str) -> Dict:
        """Format standardized order acknowledgment message.

        Creates consistent message format for order acknowledgments
        sent when orders are accepted by the exchange.

        Parameters
        ----------
        order : Order
            The order that was acknowledged
        status : str
            The order status from exchange (typically "new")

        Returns
        -------
        Dict
            Formatted message containing:
            - order_id: str
            - client_order_id: Optional[str]
            - instrument_id: str
            - side: str ("buy" or "sell")
            - quantity: int
            - price: Optional[float]
            - status: str

        Notes
        -----
        This method extracts the inline formatting currently done
        in the matching thread when creating acknowledgment messages.

        The format should match the WebSocket API specification
        for new_order_ack messages.

        TradingContext
        --------------
        Order acknowledgments confirm that the exchange has accepted
        an order for processing. For limit orders, this means the
        order is resting in the book. For market orders, this
        precedes immediate execution reports.

        Algorithms use acknowledgments to track order state and
        manage their order inventory.
        """
        pass
