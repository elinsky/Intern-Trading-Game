"""Exchange service API protocol definitions.

This module defines the protocol (interface) for exchange services,
establishing a contract for order submission, cancellation, and
order book access as required by the REST API.

The protocol maps to the 5 core REST operations:
1. Submit Order (POST /orders)
2. Cancel Order (DELETE /orders/{id})
3. Get Open Orders (GET /orders)
4. Get Positions (handled by PositionService)
5. Register Team (handled by GameService)

Notes
-----
Using Python's Protocol from typing rather than ABC to allow
structural subtyping - any class implementing these methods
will satisfy the protocol without explicit inheritance.
"""

from typing import Dict, Optional, Protocol

from .book.order_book import OrderBook
from .models.order import Order
from .order_result import OrderResult
from .types import PhaseState


class ExchangeServiceProtocol(Protocol):
    """Protocol defining the exchange service interface for REST operations.

    This protocol establishes the contract for exchange operations that
    support the REST API endpoints. It focuses on the core operations
    needed by trading bots.

    WebSocket events are handled separately through event publishing,
    not through this protocol.
    """

    def submit_order(self, order: Order) -> OrderResult:
        """Submit an order to the exchange.

        Parameters
        ----------
        order : Order
            The order to submit

        Returns
        -------
        OrderResult
            Result containing order status and any fills

        Notes
        -----
        Maps to POST /orders endpoint.
        The order should already be validated before submission.
        This method handles the matching process and returns the
        result, which could be:
        - new: Order accepted and resting in book
        - filled: Order completely filled
        - partially_filled: Order partially filled
        - rejected: Order rejected by exchange rules
        """
        ...

    def cancel_order(self, order_id: str, trader_id: str) -> bool:
        """Cancel an existing order.

        Parameters
        ----------
        order_id : str
            The unique order identifier
        trader_id : str
            The trader requesting cancellation (for ownership check)

        Returns
        -------
        bool
            True if order was cancelled, False if not found or unauthorized

        Notes
        -----
        Maps to DELETE /orders/{id} endpoint.
        Only the order owner can cancel their order.
        """
        ...

    def get_order_book(self, instrument_id: str) -> Optional[OrderBook]:
        """Get the order book for an instrument.

        Parameters
        ----------
        instrument_id : str
            The instrument to query

        Returns
        -------
        Optional[OrderBook]
            The order book, or None if instrument doesn't exist

        Notes
        -----
        Used by GET /orders endpoint to extract resting orders.
        The OrderBook contains all resting orders which can be
        filtered by trader_id for the REST response.
        """
        ...

    @property
    def order_books(self) -> Dict[str, OrderBook]:
        """Get all order books.

        Returns
        -------
        Dict[str, OrderBook]
            Mapping of instrument_id to OrderBook

        Notes
        -----
        Property access for compatibility with existing implementation.
        Used by GET /orders to iterate all instruments.
        """
        ...

    def get_current_phase_state(self) -> PhaseState:
        """Get the current market phase state.

        Returns the complete phase state configuration including
        the current phase type and all operational rules.

        Returns
        -------
        PhaseState
            Current market phase state with operational rules

        Notes
        -----
        This method is used by the REST API and other components
        to determine what operations are currently allowed.
        The phase state affects:
        - Order submission permissions
        - Order cancellation permissions
        - Order matching behavior
        - Execution style (continuous vs batch)
        """
        ...


class ExchangeEventType:
    """Enumeration of exchange WebSocket event types.

    These events are published by the exchange service for
    real-time updates to connected clients.

    Notes
    -----
    These map to the existing WebSocket message types:
    - NEW_ORDER_ACK: Order accepted by exchange
    - NEW_ORDER_REJECT: Order rejected
    - EXECUTION_REPORT: Trade execution details
    - CANCEL_ACK: Cancellation confirmed
    - CANCEL_REJECT: Cancellation rejected
    """

    NEW_ORDER_ACK = "new_order_ack"
    NEW_ORDER_REJECT = "new_order_reject"
    EXECUTION_REPORT = "execution_report"
    CANCEL_ACK = "cancel_ack"
    CANCEL_REJECT = "cancel_reject"
