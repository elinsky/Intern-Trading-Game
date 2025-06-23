"""WebSocket message types and builders following FIX protocol conventions.

This module defines all WebSocket message types, enums, and builder functions
for the Intern Trading Game. Message types follow FIX protocol naming
conventions for consistency with industry standards.

The module provides:
- Standardized message type enums
- Type-safe message builder functions
- Consistent field naming across all messages

Notes
-----
FIX protocol conventions used:
- new_order_ack: Successful order acknowledgment
- new_order_reject: Order rejection
- execution_report: Trade execution or order status
- cancel_ack: Cancel acknowledgment
- cancel_reject: Cancel rejection

All timestamps use ISO 8601 format for consistency and timezone awareness.
Sequence numbers are managed by the WebSocketManager, not this module.

TradingContext
--------------
In production FIX implementations, these messages would be binary-encoded
with strict field ordering and checksums. For this educational game, we
use JSON for debuggability while maintaining FIX naming conventions.

Examples
--------
>>> msg = build_new_order_ack(
...     order_id="ORD-123",
...     client_order_id="CLIENT-1",
...     instrument_id="SPX_4500_CALL",
...     side="buy",
...     quantity=10,
...     order_type="limit",
...     price=128.50
... )
>>> msg["order_id"]
'ORD-123'
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from ...domain.exchange.components.core.types import LiquidityType


class MessageType(str, Enum):
    """WebSocket message types following FIX protocol conventions.

    These message types represent different kinds of updates sent to
    connected clients via WebSocket.

    Attributes
    ----------
    NEW_ORDER_ACK : str
        Order accepted by the exchange
    NEW_ORDER_REJECT : str
        Order rejected by validation or exchange
    EXECUTION_REPORT : str
        Trade execution or order status update
    CANCEL_ACK : str
        Order cancellation confirmed
    CANCEL_REJECT : str
        Order cancellation rejected
    QUOTE_ACK : str
        Quote accepted (market makers only)
    QUOTE_REJECT : str
        Quote rejected (market makers only)
    POSITION_SNAPSHOT : str
        Current position state (custom for this system)
    MARKET_DATA : str
        Market quotes and prices
    SIGNAL : str
        Role-specific trading signal
    EVENT : str
        Market news or announcement
    CONNECTION_STATUS : str
        Connection lifecycle events
    """

    NEW_ORDER_ACK = "new_order_ack"
    NEW_ORDER_REJECT = "new_order_reject"
    EXECUTION_REPORT = "execution_report"
    CANCEL_ACK = "cancel_ack"
    CANCEL_REJECT = "cancel_reject"
    QUOTE_ACK = "quote_ack"
    QUOTE_REJECT = "quote_reject"
    POSITION_SNAPSHOT = "position_snapshot"
    MARKET_DATA = "market_data"
    SIGNAL = "signal"
    EVENT = "event"
    CONNECTION_STATUS = "connection_status"


def build_new_order_ack(
    order_id: str,
    client_order_id: Optional[str],
    instrument_id: str,
    side: str,
    quantity: int,
    order_type: str,
    price: Optional[float],
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build new order acknowledgment message.

    Constructs a message confirming that an order has been accepted
    by the exchange and entered into the order book (for limit orders)
    or is ready for immediate execution (for market orders).

    Parameters
    ----------
    order_id : str
        Exchange-assigned order identifier
    client_order_id : Optional[str]
        Client's order reference
    instrument_id : str
        Instrument being traded
    side : str
        Order side ("buy" or "sell")
    quantity : int
        Order quantity
    order_type : str
        Type of order ("limit" or "market")
    price : Optional[float]
        Limit price (None for market orders)
    timestamp : Optional[datetime]
        Message timestamp (defaults to now)

    Returns
    -------
    dict
        Formatted message ready for WebSocket transmission

    Notes
    -----
    This message indicates the order passed all validations and is
    now active in the exchange. For limit orders, it's resting in
    the book. For market orders, it's ready for immediate matching.
    """
    data = {
        "order_id": order_id,
        "instrument_id": instrument_id,
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "status": "new",  # Matches OrderResult status values
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }

    if client_order_id:
        data["client_order_id"] = client_order_id

    if price is not None:
        data["price"] = price

    return data


def build_new_order_reject(
    order_id: str,
    client_order_id: Optional[str],
    reason: str,
    error_code: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build new order rejection message.

    Constructs a message indicating that an order was rejected
    during validation or submission to the exchange.

    Parameters
    ----------
    order_id : str
        Exchange-assigned order identifier
    client_order_id : Optional[str]
        Client's order reference
    reason : str
        Human-readable rejection reason
    error_code : Optional[str]
        Machine-readable error code
    timestamp : Optional[datetime]
        Message timestamp (defaults to now)

    Returns
    -------
    dict
        Formatted rejection message

    Notes
    -----
    Common rejection reasons include:
    - Position limit exceeded
    - Invalid price or quantity
    - Insufficient buying power
    - Market closed
    - Unknown instrument
    """
    data = {
        "order_id": order_id,
        "status": "rejected",  # Matches OrderResult status values
        "reason": reason,
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }

    if client_order_id:
        data["client_order_id"] = client_order_id

    if error_code:
        data["error_code"] = error_code

    return data


def build_execution_report(
    order_id: str,
    client_order_id: Optional[str],
    trade_id: str,
    instrument_id: str,
    side: str,
    executed_quantity: int,
    executed_price: float,
    remaining_quantity: int,
    order_status: str,  # Uses string status from OrderResult
    liquidity_type: LiquidityType,
    fees: float,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build execution report for trades and order updates.

    Constructs a comprehensive execution report message that includes
    trade details, fees, and updated order status. This is the primary
    message type for communicating fills to clients.

    Parameters
    ----------
    order_id : str
        Exchange-assigned order identifier
    client_order_id : Optional[str]
        Client's order reference
    trade_id : str
        Unique trade identifier
    instrument_id : str
        Instrument that was traded
    side : str
        Order side ("buy" or "sell")
    executed_quantity : int
        Quantity filled in this execution
    executed_price : float
        Price at which the trade occurred
    remaining_quantity : int
        Quantity still open on the order
    order_status : str
        Updated order status ('filled', 'partially_filled', etc.)
    liquidity_type : LiquidityType
        Whether this was maker or taker liquidity
    fees : float
        Fees charged for this execution
    timestamp : Optional[datetime]
        Execution timestamp (defaults to now)

    Returns
    -------
    dict
        Formatted execution report message

    Notes
    -----
    The execution report is the most important message for bots as it:
    - Confirms actual trades with prices and quantities
    - Provides fee information for P&L calculation
    - Updates order status (partial fill vs complete fill)
    - Indicates liquidity type for rebate calculations

    For partial fills, multiple execution reports will be sent for
    the same order_id as each fill occurs.
    """
    data = {
        "order_id": order_id,
        "trade_id": trade_id,
        "instrument_id": instrument_id,
        "side": side,
        "executed_quantity": executed_quantity,
        "executed_price": executed_price,
        "remaining_quantity": remaining_quantity,
        "order_status": order_status,  # Already a string
        "liquidity_type": liquidity_type.value,
        "fees": fees,
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }

    if client_order_id:
        data["client_order_id"] = client_order_id

    return data


def build_cancel_ack(
    order_id: str,
    client_order_id: Optional[str],
    cancelled_quantity: int,
    reason: str = "user_requested",
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build order cancellation acknowledgment.

    Constructs a message confirming successful order cancellation.

    Parameters
    ----------
    order_id : str
        Exchange-assigned order identifier
    client_order_id : Optional[str]
        Client's order reference
    cancelled_quantity : int
        Quantity that was cancelled
    reason : str
        Cancellation reason (default: "user_requested")
    timestamp : Optional[datetime]
        Cancellation timestamp (defaults to now)

    Returns
    -------
    dict
        Formatted cancellation acknowledgment

    Notes
    -----
    Cancellation reasons may include:
    - user_requested: Client initiated cancellation
    - tick_end: Automatic cancellation at tick boundary
    - session_end: Trading session closed
    """
    data = {
        "order_id": order_id,
        "status": "cancelled",  # Matches OrderResult status values
        "cancelled_quantity": cancelled_quantity,
        "reason": reason,
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }

    if client_order_id:
        data["client_order_id"] = client_order_id

    return data


def build_cancel_reject(
    order_id: str,
    client_order_id: Optional[str],
    reason: str,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build order cancellation rejection.

    Constructs a message indicating that a cancellation request failed.

    Parameters
    ----------
    order_id : str
        Exchange-assigned order identifier
    client_order_id : Optional[str]
        Client's order reference
    reason : str
        Why the cancellation was rejected
    timestamp : Optional[datetime]
        Rejection timestamp (defaults to now)

    Returns
    -------
    dict
        Formatted cancellation rejection

    Notes
    -----
    Common rejection reasons:
    - Order not found
    - Order already filled
    - Order already cancelled
    - Not order owner
    """
    data = {
        "order_id": order_id,
        "status": "cancel_rejected",  # Consistent with cancel_ack having "cancelled"
        "reason": reason,
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }

    if client_order_id:
        data["client_order_id"] = client_order_id

    return data


def build_quote_ack(
    instrument_id: str,
    bid_price: float,
    ask_price: float,
    size: int,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build quote acknowledgment for market makers.

    Confirms that a two-sided quote has been accepted.

    Parameters
    ----------
    instrument_id : str
        Instrument being quoted
    bid_price : float
        Bid price level
    ask_price : float
        Ask price level
    size : int
        Size available at both bid and ask
    timestamp : Optional[datetime]
        Quote acceptance time

    Returns
    -------
    dict
        Formatted quote acknowledgment
    """
    return {
        "instrument_id": instrument_id,
        "bid_price": bid_price,
        "ask_price": ask_price,
        "size": size,
        "status": "active",
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }


def build_quote_reject(
    instrument_id: str,
    reason: str,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build quote rejection for market makers.

    Indicates why a quote was not accepted.

    Parameters
    ----------
    instrument_id : str
        Instrument quote was for
    reason : str
        Why the quote was rejected
    timestamp : Optional[datetime]
        Rejection time

    Returns
    -------
    dict
        Formatted quote rejection
    """
    return {
        "instrument_id": instrument_id,
        "reason": reason,
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }


def build_position_snapshot(
    positions: dict, timestamp: Optional[datetime] = None
) -> dict:
    """Build position snapshot message.

    Constructs a message containing current position state, typically
    sent when a client first connects.

    Parameters
    ----------
    positions : dict
        Dictionary mapping instrument_id to position quantity
    timestamp : Optional[datetime]
        Snapshot timestamp (defaults to now)

    Returns
    -------
    dict
        Formatted position snapshot
    """
    return {
        "positions": positions,
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }


def build_market_data(
    instrument_id: str,
    bid: Optional[float],
    ask: Optional[float],
    last: Optional[float],
    bid_size: Optional[int] = None,
    ask_size: Optional[int] = None,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build market data update message.

    Constructs a message containing current market prices and sizes
    for a specific instrument.

    Parameters
    ----------
    instrument_id : str
        Instrument with updated market data
    bid : Optional[float]
        Best bid price (None if no bids)
    ask : Optional[float]
        Best ask price (None if no asks)
    last : Optional[float]
        Last traded price (None if no trades)
    bid_size : Optional[int]
        Size available at best bid
    ask_size : Optional[int]
        Size available at best ask
    timestamp : Optional[datetime]
        Market data timestamp (defaults to now)

    Returns
    -------
    dict
        Formatted market data message
    """
    data: dict = {
        "instrument_id": instrument_id,
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }

    if bid is not None:
        data["bid"] = bid
    if ask is not None:
        data["ask"] = ask
    if last is not None:
        data["last"] = last
    if bid_size is not None:
        data["bid_size"] = bid_size
    if ask_size is not None:
        data["ask_size"] = ask_size

    return data


def build_connection_status(
    status: str,
    message: str,
    timestamp: Optional[datetime] = None,
) -> dict:
    """Build connection status message.

    Used for connection lifecycle events like authentication
    and readiness notifications.

    Parameters
    ----------
    status : str
        Connection status ("connected", "authenticated", "ready")
    message : str
        Human-readable status message
    timestamp : Optional[datetime]
        Status change time

    Returns
    -------
    dict
        Formatted connection status message
    """
    return {
        "status": status,
        "message": message,
        "timestamp": (timestamp or datetime.now()).isoformat(),
    }
