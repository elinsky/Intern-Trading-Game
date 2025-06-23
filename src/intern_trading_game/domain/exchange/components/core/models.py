"""Core exchange domain models.

This module contains the fundamental domain objects for the exchange:
Order, Trade, Instrument, and OrderResult.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional


class OrderSide(str, Enum):
    """Enum representing the side of an order (buy or sell)."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Enum representing the type of order (limit or market)."""

    LIMIT = "limit"
    MARKET = "market"


@dataclass
class Instrument:
    r"""
    Represents a tradeable instrument in the exchange.

    This class models financial instruments that can be traded on the exchange.
    It supports various types of instruments including stocks, futures, and
    options. For options, additional fields like strike price, expiration date,
    and option type (call/put) are provided.

    The instrument serves as the fundamental unit of trading in the system and
    is referenced by orders, trades, and market data.

    Parameters
    ----------
    symbol : str
        The unique identifier for the instrument.
    strike : Optional[float], default=None
        The strike price for options. None for non-option instruments.
    expiry : Optional[str], default=None
        The expiration date for options in ISO format (YYYY-MM-DD).
        None for non-expiring instruments.
    option_type : Optional[str], default=None
        The type of option ('call' or 'put'). None for non-option instruments.
    underlying : Optional[str], default=None
        The underlying asset symbol for derivatives. None for non-derivative
        instruments.

    Attributes
    ----------
    symbol : str
        The unique identifier for the instrument.
    strike : Optional[float]
        The strike price for options. None for non-option instruments.
    expiry : Optional[str]
        The expiration date for options in ISO format (YYYY-MM-DD).
        None for non-expiring instruments.
    option_type : Optional[str]
        The type of option ('call' or 'put'). None for non-option instruments.
    underlying : Optional[str]
        The underlying asset symbol for derivatives. None for non-derivative
        instruments.

    Notes
    -----
    Financial instruments are the building blocks of any trading system. They
    represent the assets that can be bought and sold on the exchange.

    For options, the Black-Scholes model is commonly used for pricing:

    $$C = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)$$

    where:

    $$d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$$

    $$d_2 = d_1 - \sigma\sqrt{T}$$

    The instrument ID is derived from the symbol, which must be unique across
    the exchange. This simplifies instrument lookup and reference.

    TradingContext
    -------------
    This implementation assumes:
    - Instruments are uniquely identified by their symbol
    - Options require strike, expiry, and option_type
    - Expiry dates follow ISO format (YYYY-MM-DD)
    - Option types are limited to 'call' and 'put'
    - No support for complex derivatives like swaps or structured products
    - No handling of corporate actions (splits, dividends, etc.)
    - No support for different settlement types or delivery methods

    Examples
    --------
    Creating a stock instrument:

    >>> apple_stock = Instrument(symbol="AAPL", underlying="AAPL")
    >>> apple_stock.id
    'AAPL'
    >>> apple_stock.option_type is None
    True

    Creating an option instrument:

    >>> apple_call = Instrument(
    ...     symbol="AAPL_C_150_20230621",
    ...     underlying="AAPL",
    ...     strike=150.0,
    ...     expiry="2023-06-21",
    ...     option_type="call"
    ... )
    >>> apple_call.id
    'AAPL_C_150_20230621'
    >>> apple_call.option_type
    'call'
    """

    symbol: str
    strike: Optional[float] = None
    expiry: Optional[str] = None
    option_type: Optional[str] = None
    underlying: Optional[str] = None

    def __post_init__(self):
        """Validate the instrument attributes after initialization."""
        if self.option_type and self.option_type.lower() not in [
            "call",
            "put",
        ]:
            raise ValueError("Option type must be 'call' or 'put'")

        if self.expiry:
            try:
                # Validate expiry date format
                year, month, day = map(int, self.expiry.split("-"))
                date(year, month, day)
            except (ValueError, TypeError):
                raise ValueError("Expiry must be in ISO format (YYYY-MM-DD)")

    @property
    def id(self) -> str:
        """
        Get the unique identifier for this instrument.

        Returns
        -------
        str
            The instrument's symbol, which serves as its unique ID.
        """
        return self.symbol


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
    client_order_id : str, optional, default=None
        Client's reference ID for this order. Used by bots to track their
        orders across the system.

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
    client_order_id : Optional[str]
        Client's reference ID for tracking.
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
    client_order_id: Optional[str] = None
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

        # Validate price is in penny increments (for limit orders)
        if self.order_type == OrderType.LIMIT and self.price is not None:
            # Check if price has more than 2 decimal places
            if round(self.price, 2) != self.price:
                raise ValueError("Order price must be in penny increments")

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

    @property
    def filled_quantity(self) -> float:
        """
        Get the quantity that has been filled.

        Returns
        -------
        float
            The quantity that has been filled (original quantity minus remaining).
        """
        return self.quantity - self.remaining_quantity

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
    aggressor_side : str
        Which side initiated the trade ("buy" or "sell"). The aggressor
        is the taker who crossed the spread, while the other side is
        the maker who provided liquidity.
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
    aggressor_side : str
        Which side initiated the trade ("buy" or "sell").
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

    The aggressor_side field indicates which side initiated the trade:
    - If aggressor_side = "buy": Buyer was the taker (aggressor), seller was the maker
    - If aggressor_side = "sell": Seller was the taker (aggressor), buyer was the maker

    This distinction is crucial for fee calculations, as makers typically
    receive rebates while takers pay fees.

    Trade records are essential for:

    1. Market data dissemination
    2. Trade reporting and fee calculation
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
    Creating a trade where buyer was the aggressor (taker):

    >>> trade = Trade(
    ...     instrument_id="AAPL",
    ...     buyer_id="trader1",
    ...     seller_id="trader2",
    ...     price=150.0,
    ...     quantity=10,
    ...     buyer_order_id="order1",
    ...     seller_order_id="order2",
    ...     aggressor_side="buy"  # Buyer crossed the spread
    ... )
    >>> trade.value
    1500.0

    Converting a trade to a dictionary:

    >>> trade_dict = trade.to_dict()
    >>> trade_dict["instrument_id"]
    'AAPL'
    >>> trade_dict["aggressor_side"]
    'buy'
    """

    instrument_id: str
    buyer_id: str
    seller_id: str
    price: float
    quantity: float
    buyer_order_id: str
    seller_order_id: str
    aggressor_side: str  # "buy" or "sell"
    timestamp: datetime = field(default_factory=datetime.now)
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate the trade after creation."""
        if self.price <= 0:
            raise ValueError("Trade price must be positive")

        if self.quantity <= 0:
            raise ValueError("Trade quantity must be positive")

        if self.quantity != int(self.quantity):
            raise ValueError("Trade quantity must be a whole number")

        if self.aggressor_side not in ["buy", "sell"]:
            raise ValueError("Aggressor side must be 'buy' or 'sell'")

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
            "aggressor_side": self.aggressor_side,
            "timestamp": self.timestamp.isoformat(),
            "buyer_order_id": self.buyer_order_id,
            "seller_order_id": self.seller_order_id,
            "value": self.value,
        }


@dataclass
class OrderResult:
    """Represents the result of submitting an order.

    This class encapsulates all information about what happened when an order
    was submitted to the exchange, including its status, any trades that were
    generated, and the remaining unfilled quantity.

    Attributes
    ----------
    order_id : str
        The ID of the submitted order.
    status : str
        The status of the order. Possible values:
        - 'pending_new': Order is queued for batch matching (batch mode only)
        - 'new': Order acknowledged and resting in the order book
        - 'partially_filled': Order partially executed, remainder in book
        - 'filled': Order was completely filled
        - 'rejected': Order was rejected (future use for validation failures)
        - 'cancelled': Order was cancelled (future use)
    fills : List[Trade]
        Any trades that were generated. Empty for pending orders.
    remaining_quantity : float
        The unfilled quantity of the order. Equal to original quantity
        for pending orders, 0 for fully filled orders.
    error_code : Optional[str]
        Error code if order was rejected (None otherwise).
    error_message : Optional[str]
        Human-readable error message if order was rejected.

    Notes
    -----
    In continuous mode, orders will have status 'new', 'partially_filled',
    or 'filled' immediately upon submission. In batch mode, orders start
    as 'pending_new' and transition to 'new', 'partially_filled', or 'filled'
    after batch execution.

    The status progression follows standard FIX protocol conventions where
    possible, adapted for our game's requirements.
    """

    order_id: str
    status: str
    fills: List[Trade] = field(default_factory=list)
    remaining_quantity: float = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None


__all__ = [
    "Instrument",
    "Order",
    "OrderSide",
    "OrderType",
    "Trade",
    "OrderResult",
]
