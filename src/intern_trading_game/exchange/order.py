"""
Order module for the Intern Trading Game.

This module defines the Order class, which represents a trading order.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    """Enum representing the side of an order (buy or sell)."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Enum representing the type of order (limit or market)."""

    LIMIT = "limit"
    MARKET = "market"


@dataclass
class Order:
    """
    Represents a trading order in the exchange.

    An order is a request to buy or sell a financial instrument. It contains
    information about the instrument, quantity, price (for limit orders), and
    the trader who submitted it. Orders can be either market orders (executed
    immediately at the best available price) or limit orders (executed only at
    a specified price or better).

    Parameters
    ----------
    instrument_id : str
        The ID of the instrument being traded.
    side : OrderSide or str
        Whether this is a buy or sell order. Can be provided as an OrderSide
        enum value or a string ('buy' or 'sell').
    quantity : float
        The quantity to be traded. Must be positive.
    trader_id : str
        The ID of the trader submitting the order.
    price : float, optional, default=None
        The limit price. If None, the order is treated as a market order.
        Must be positive for limit orders.
    order_id : str, optional
        A unique identifier for this order. If not provided, a UUID is generated.
    timestamp : datetime, optional
        When the order was created. If not provided, the current time is used.
    order_type : OrderType, optional, default=OrderType.LIMIT
        The type of order (limit or market). This is automatically set based on
        the price parameter, but can be explicitly provided.

    Attributes
    ----------
    instrument_id : str
        The ID of the instrument being traded.
    side : OrderSide
        Whether this is a buy or sell order.
    quantity : float
        The quantity to be traded.
    price : Optional[float]
        The limit price (None for market orders).
    trader_id : str
        The ID of the trader submitting the order.
    order_id : str
        A unique identifier for this order.
    timestamp : datetime
        When the order was created.
    order_type : OrderType
        The type of order (limit or market).
    remaining_quantity : float
        The unfilled quantity of the order.

    Notes
    -----
    Orders are the fundamental building blocks of a trading system. They
    represent the intention of a trader to execute a transaction in the market.

    The order lifecycle typically follows these stages:
    1. Creation - Order is created with initial parameters
    2. Validation - Order is checked for validity (positive quantity, etc.)
    3. Submission - Order is submitted to the exchange
    4. Matching - Order is matched against other orders
    5. Execution - Trades are created when orders match
    6. Settlement - The final stage where assets are exchanged

    The price-time priority rule is commonly used for order matching:

    $$\text{Priority} = (\text{Price}, \text{Time})$$

    Where better prices have higher priority, and for equal prices, earlier
    orders have higher priority.

    TradingContext
    -------------
    This implementation assumes:
    - Orders can be either market or limit orders
    - Market orders execute immediately at the best available price
    - Limit orders execute only at the specified price or better
    - Orders can be partially filled
    - Order quantities must be positive
    - Limit orders must have a positive price
    - No support for stop orders, iceberg orders, or other advanced order types
    - No position limits or risk checks

    Examples
    --------
    Creating a limit buy order:

    >>> buy_order = Order(
    ...     instrument_id="AAPL",
    ...     side="buy",
    ...     quantity=10,
    ...     price=150.0,
    ...     trader_id="trader1"
    ... )
    >>> buy_order.is_buy
    True
    >>> buy_order.is_limit_order
    True

    Creating a market sell order:

    >>> sell_order = Order(
    ...     instrument_id="AAPL",
    ...     side="sell",
    ...     quantity=5,
    ...     price=None,
    ...     trader_id="trader2"
    ... )
    >>> sell_order.is_market_order
    True
    >>> sell_order.remaining_quantity
    5.0
    """

    instrument_id: str
    side: OrderSide
    quantity: float
    trader_id: str
    price: Optional[float] = None
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    order_type: OrderType = OrderType.LIMIT
    remaining_quantity: float = field(init=False)

    def __post_init__(self):
        """Validate and initialize the order after creation."""
        # Convert string side to enum if needed
        if isinstance(self.side, str):
            self.side = OrderSide(self.side.lower())

        # Determine order type based on price
        if self.price is None:
            self.order_type = OrderType.MARKET
        else:
            self.order_type = OrderType.LIMIT

        # Validate price for limit orders
        if self.order_type == OrderType.LIMIT and (
            self.price is None or self.price <= 0
        ):
            raise ValueError("Limit orders must have a positive price")

        # Validate quantity
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")

        # Initialize remaining quantity
        self.remaining_quantity = self.quantity

    @property
    def is_buy(self) -> bool:
        """
        Check if this is a buy order.

        Returns
        -------
        bool
            True if this is a buy order, False otherwise.
        """
        return self.side == OrderSide.BUY

    @property
    def is_sell(self) -> bool:
        """
        Check if this is a sell order.

        Returns
        -------
        bool
            True if this is a sell order, False otherwise.
        """
        return self.side == OrderSide.SELL

    @property
    def is_market_order(self) -> bool:
        """
        Check if this is a market order.

        Returns
        -------
        bool
            True if this is a market order, False otherwise.
        """
        return self.order_type == OrderType.MARKET

    @property
    def is_limit_order(self) -> bool:
        """
        Check if this is a limit order.

        Returns
        -------
        bool
            True if this is a limit order, False otherwise.
        """
        return self.order_type == OrderType.LIMIT

    @property
    def is_filled(self) -> bool:
        """
        Check if this order is completely filled.

        Returns
        -------
        bool
            True if the order is filled, False otherwise.
        """
        return self.remaining_quantity == 0

    def fill(self, quantity: float) -> None:
        """
        Mark a quantity of this order as filled.

        Parameters
        ----------
        quantity : float
            The quantity that was filled. Must be positive and not exceed
            the remaining quantity.

        Raises
        ------
        ValueError
            If the quantity is invalid or exceeds the remaining quantity.
        """
        if quantity <= 0:
            raise ValueError("Fill quantity must be positive")

        if quantity > self.remaining_quantity:
            raise ValueError(
                f"Fill quantity {quantity} exceeds remaining quantity "
                f"{self.remaining_quantity}"
            )

        self.remaining_quantity -= quantity
