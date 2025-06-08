"""Order matching service implementation.

This module provides the concrete implementation of order matching
business logic for the trading system, handling exchange interactions
and error processing.
"""

import logging

from ..domain.exchange.order import Order
from ..domain.exchange.order_result import OrderResult
from ..domain.exchange.venue import ExchangeVenue
from .interfaces import OrderMatchingServiceInterface

logger = logging.getLogger(__name__)


class OrderMatchingService(OrderMatchingServiceInterface):
    """Service for processing order submission to the exchange.

    This service encapsulates the business logic for submitting orders
    to the exchange and handling the results. It provides a clean
    separation between the exchange interaction logic and the thread
    infrastructure concerns like queue management and WebSocket messaging.

    The service is responsible for:
    - Submitting orders to the exchange venue
    - Handling successful submissions (new, filled, partially filled)
    - Converting exchange exceptions to standardized error responses
    - Logging for debugging and monitoring

    Parameters
    ----------
    exchange : ExchangeVenue
        The exchange venue instance for order submission

    Attributes
    ----------
    exchange : ExchangeVenue
        The exchange venue used for order matching

    Notes
    -----
    This service extracts logic from matching_thread() lines 306-342,
    preserving the exact behavior while improving testability and
    maintainability.

    The service does not handle:
    - WebSocket notifications (infrastructure concern)
    - Queue management (thread responsibility)
    - Response delivery (thread responsibility)

    TradingContext
    --------------
    The exchange uses continuous matching with price-time priority:
    - Orders are matched immediately upon receipt
    - Best price gets priority
    - For equal prices, earlier orders match first
    - Market orders execute immediately if liquidity exists
    - Limit orders may rest in the book waiting for match

    Orders may receive immediate fills if they cross the spread,
    which is why the result includes a fills list even for new orders.

    Examples
    --------
    >>> # Initialize service
    >>> matching_service = OrderMatchingService(exchange)
    >>>
    >>> # Submit an order
    >>> order = Order(
    ...     instrument_id="SPX_4500_CALL",
    ...     side="buy",
    ...     quantity=10,
    ...     price=125.50,
    ...     trader_id="TEAM001"
    ... )
    >>> result = matching_service.submit_order_to_exchange(order)
    >>>
    >>> # Check result
    >>> if result.status == "filled":
    ...     print(f"Order filled with {len(result.fills)} trades")
    >>> elif result.status == "new":
    ...     print("Order resting in book")
    """

    def __init__(self, exchange: ExchangeVenue):
        """Initialize the order matching service.

        Parameters
        ----------
        exchange : ExchangeVenue
            The exchange venue for order submission
        """
        self.exchange = exchange

    def submit_order_to_exchange(self, order: Order) -> OrderResult:
        """Submit a validated order to the exchange for matching.

        Wraps the exchange venue's order submission with logging
        and lets any exceptions propagate for proper error handling.

        Parameters
        ----------
        order : Order
            The validated order to submit to the exchange

        Returns
        -------
        OrderResult
            Result from exchange containing:
            - order_id: str identifying the order
            - status: str ("new", "partially_filled", "filled", "rejected")
            - fills: List[Trade] of any immediate executions
            - remaining_quantity: float of unfilled quantity
            - error_code: Optional[str] for rejections
            - error_message: Optional[str] for rejections

        Raises
        ------
        ValueError
            If order parameters are invalid
        KeyError
            If instrument is not listed on exchange
        RuntimeError
            For exchange internal errors

        Notes
        -----
        The method directly calls the exchange and returns its result
        unchanged. This preserves the exact matching engine behavior
        while adding observability through logging.

        Successful submission doesn't guarantee the order is resting -
        it may have been immediately filled or rejected by the engine.

        TradingContext
        --------------
        Common scenarios and their results:
        - Market buy crossing ask: status="filled" with trades
        - Limit buy below bid: status="new", no fills
        - Limit sell at bid: status="filled" as maker
        - Order exceeding book: status="partially_filled"
        - Invalid price: Exception raised

        Examples
        --------
        >>> # Submit a limit order that crosses the spread
        >>> order = Order(
        ...     instrument_id="SPX_4500_CALL",
        ...     side="buy",
        ...     quantity=10,
        ...     price=126.00,  # Above current ask of 125.50
        ...     trader_id="TEAM001"
        ... )
        >>> result = service.submit_order_to_exchange(order)
        >>> assert result.status == "filled"
        >>> assert len(result.fills) > 0
        """
        logger.debug(
            f"Submitting order {order.order_id} to exchange: "
            f"{order.side} {order.quantity} {order.instrument_id} "
            f"@ {order.price if order.price else 'MARKET'}"
        )

        # Submit to exchange - let exceptions propagate
        result = self.exchange.submit_order(order)

        logger.info(
            f"Order {order.order_id} result: status={result.status}, "
            f"fills={len(result.fills)}, remaining={result.remaining_quantity}"
        )

        return result

    def handle_exchange_error(
        self, error: Exception, order: Order
    ) -> OrderResult:
        """Handle exceptions from exchange interactions.

        Creates a standardized error response when the exchange
        raises an exception during order processing. Maps different
        exception types to appropriate error codes and user-friendly
        messages.

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
            - status: "error"
            - error_code: Standardized error code
            - error_message: Human-readable error description

        Notes
        -----
        This method standardizes error handling across the system,
        ensuring consistent error responses regardless of the underlying
        exception type.

        Common error mappings:
        - ValueError → "INVALID_ORDER"
        - KeyError → "UNKNOWN_INSTRUMENT"
        - RuntimeError → "EXCHANGE_ERROR"
        - Others → "INTERNAL_ERROR"

        TradingContext
        --------------
        In production exchanges, errors are categorized by FIX protocol:
        - Session level: Connection/auth issues
        - Application level: Business rule violations
        - Market level: Instrument suspensions

        This simplified model focuses on order-level errors that
        traders need to handle in their algorithms.

        Examples
        --------
        >>> # Handle an invalid instrument error
        >>> try:
        ...     result = service.submit_order_to_exchange(order)
        ... except KeyError as e:
        ...     error_result = service.handle_exchange_error(e, order)
        ...     assert error_result.status == "error"
        ...     assert error_result.error_code == "UNKNOWN_INSTRUMENT"
        """
        # Log the full exception for debugging
        logger.error(
            f"Exchange error for order {order.order_id}: "
            f"{type(error).__name__}: {str(error)}"
        )

        # Map exception types to error codes
        if isinstance(error, ValueError):
            error_code = "INVALID_ORDER"
            error_message = f"Invalid order parameters: {str(error)}"
        elif isinstance(error, KeyError):
            error_code = "UNKNOWN_INSTRUMENT"
            error_message = f"Instrument not found: {order.instrument_id}"
        elif isinstance(error, RuntimeError):
            error_code = "EXCHANGE_ERROR"
            error_message = f"Exchange error: {str(error)}"
        else:
            error_code = "INTERNAL_ERROR"
            error_message = f"Unexpected error: {str(error)}"

        # Create error response
        return OrderResult(
            order_id=order.order_id,
            status="error",
            fills=[],
            remaining_quantity=order.quantity,
            error_code=error_code,
            error_message=error_message,
        )
