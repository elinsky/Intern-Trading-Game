"""
Trade module for the Intern Trading Game.

This module defines the Trade class, which represents an executed trade.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Trade:
    r"""
    Represents an executed trade between two orders.

    A trade occurs when two orders are matched in the exchange. It records the
    details of the transaction, including the instrument, price, quantity, and
    the identities of the buyer and seller. Each trade has a unique identifier
    and a timestamp recording when it occurred.

    Parameters
    ----------
    instrument_id : str
        The ID of the instrument that was traded.
    buyer_id : str
        The ID of the trader who bought.
    seller_id : str
        The ID of the trader who sold.
    price : float
        The execution price of the trade. Must be positive.
    quantity : float
        The quantity that was traded. Must be positive.
    buyer_order_id : str
        The ID of the buy order that participated in this trade.
    seller_order_id : str
        The ID of the sell order that participated in this trade.
    timestamp : datetime, optional
        When the trade occurred. If not provided, the current time is used.
    trade_id : str, optional
        A unique identifier for this trade. If not provided, a UUID is generated.

    Attributes
    ----------
    instrument_id : str
        The ID of the instrument that was traded.
    buyer_id : str
        The ID of the trader who bought.
    seller_id : str
        The ID of the trader who sold.
    price : float
        The execution price of the trade.
    quantity : float
        The quantity that was traded.
    buyer_order_id : str
        The ID of the buy order.
    seller_order_id : str
        The ID of the sell order.
    timestamp : datetime
        When the trade occurred.
    trade_id : str
        A unique identifier for this trade.

    Notes
    -----
    Trades are the fundamental units of market activity. They represent the
    actual transfer of assets between market participants at an agreed price.

    The total value of a trade is calculated as:

    $$\text{Value} = \text{Price} \times \text{Quantity}$$

    Trades are created when orders are matched in the exchange. The matching
    process follows price-time priority, where orders with better prices are
    matched first, and for orders at the same price, earlier orders are
    matched first.

    Trade records are essential for:

    1. Market data dissemination
    2. Trade reporting to regulatory authorities
    3. Settlement and clearing processes
    4. Historical analysis and backtesting

    TradingContext
    -------------
    This implementation assumes:
    - Trades occur at a single price point (no average pricing)
    - Trades are between exactly two counterparties
    - No partial executions are tracked separately (each fill creates a new trade)
    - No fees or commissions are included in the trade record
    - No settlement or clearing information is included
    - No regulatory reporting information is included

    Examples
    --------
    Creating a trade:

    >>> trade = Trade(
    ...     instrument_id="AAPL",
    ...     buyer_id="trader1",
    ...     seller_id="trader2",
    ...     price=150.0,
    ...     quantity=10,
    ...     buyer_order_id="order1",
    ...     seller_order_id="order2"
    ... )
    >>> trade.value
    1500.0

    Converting a trade to a dictionary:

    >>> trade_dict = trade.to_dict()
    >>> trade_dict["instrument_id"]
    'AAPL'
    >>> trade_dict["price"]
    150.0
    """

    instrument_id: str
    buyer_id: str
    seller_id: str
    price: float
    quantity: float
    buyer_order_id: str
    seller_order_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate the trade after creation."""
        if self.price <= 0:
            raise ValueError("Trade price must be positive")

        if self.quantity <= 0:
            raise ValueError("Trade quantity must be positive")

    @property
    def value(self) -> float:
        """
        Calculate the total value of this trade.

        The value is calculated as the product of price and quantity, representing
        the total amount of money exchanged in this trade.

        Returns
        -------
        float
            The trade value (price * quantity).

        Notes
        -----
        This is a key metric for trade analysis and reporting. It represents the
        total economic value of the transaction.

        Examples
        --------
        >>> trade = Trade(
        ...     instrument_id="AAPL",
        ...     buyer_id="trader1",
        ...     seller_id="trader2",
        ...     price=150.0,
        ...     quantity=10,
        ...     buyer_order_id="order1",
        ...     seller_order_id="order2"
        ... )
        >>> trade.value
        1500.0
        """
        return self.price * self.quantity

    def to_dict(self) -> dict:
        """
        Convert the trade to a dictionary representation.

        Creates a dictionary containing all the trade details, suitable for
        serialization, storage, or transmission.

        Returns
        -------
        dict
            A dictionary containing the trade details, including:
            - trade_id: The unique identifier for this trade
            - instrument_id: The ID of the instrument that was traded
            - buyer_id: The ID of the trader who bought
            - seller_id: The ID of the trader who sold
            - price: The execution price of the trade
            - quantity: The quantity that was traded
            - timestamp: The ISO-formatted timestamp of when the trade occurred
            - buyer_order_id: The ID of the buy order
            - seller_order_id: The ID of the sell order
            - value: The total value of the trade (price * quantity)

        Notes
        -----
        This method is useful for:
        - Converting trade objects to JSON for API responses
        - Storing trade records in databases
        - Generating trade reports

        Examples
        --------
        >>> trade = Trade(
        ...     instrument_id="AAPL",
        ...     buyer_id="trader1",
        ...     seller_id="trader2",
        ...     price=150.0,
        ...     quantity=10,
        ...     buyer_order_id="order1",
        ...     seller_order_id="order2"
        ... )
        >>> trade_dict = trade.to_dict()
        >>> trade_dict["instrument_id"]
        'AAPL'
        >>> trade_dict["value"]
        1500.0
        """
        return {
            "trade_id": self.trade_id,
            "instrument_id": self.instrument_id,
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "price": self.price,
            "quantity": self.quantity,
            "timestamp": self.timestamp.isoformat(),
            "buyer_order_id": self.buyer_order_id,
            "seller_order_id": self.seller_order_id,
            "value": self.value,
        }
