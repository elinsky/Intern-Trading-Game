"""
Exchange Venue module for the Intern Trading Game.

This module defines the ExchangeVenue class, which is the main entry point for
the exchange.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from intern_trading_game.exchange.order import Order
from intern_trading_game.exchange.order_book import OrderBook
from intern_trading_game.exchange.trade import Trade
from intern_trading_game.instruments.instrument import Instrument


@dataclass
class OrderResult:
    """
    Represents the result of submitting an order.

    Attributes:
        order_id (str): The ID of the submitted order.
        status (str): The status of the order ('accepted' or 'filled').
        fills (List[Trade]): Any trades that were generated.
        remaining_quantity (float): The unfilled quantity of the order.
    """

    order_id: str
    status: str
    fills: List[Trade] = field(default_factory=list)
    remaining_quantity: float = 0


class ExchangeVenue:
    """
    The main exchange venue that handles order submission and matching.

    This class represents a trading venue where financial instruments can be
    listed and traded. It maintains separate order books for each instrument,
    handles order submission, matching, and cancellation, and provides market
    data such as order book depth and trade history.

    The exchange implements a standard price-time priority matching algorithm,
    where orders are matched based on price first (best prices get priority)
    and then by time (earlier orders at the same price get priority).

    Parameters
    ----------
    None

    Attributes
    ----------
    order_books : Dict[str, OrderBook]
        Map of instrument IDs to their order books.
    instruments : Dict[str, Instrument]
        Map of instrument IDs to their instrument objects.
    all_order_ids : Set[str]
        Set of all order IDs across all books.

    Notes
    -----
    The exchange venue is the central component of a trading system, responsible
    for maintaining fair and orderly markets. It implements the core matching
    logic that pairs buyers with sellers according to well-defined rules.

    The matching algorithm follows price-time priority:

    $$\text{Priority} = (\text{Price}, \text{Time})$$

    For buy orders, higher prices have higher priority.
    For sell orders, lower prices have higher priority.
    For orders at the same price, earlier orders have higher priority.

    TradingContext
    -------------
    This implementation assumes:
    - A central limit order book model
    - Continuous trading (no auctions or opening/closing procedures)
    - No circuit breakers or trading halts
    - No fees or commissions
    - No position limits or risk checks
    - No support for hidden orders, iceberg orders, or other advanced order types
    - All orders can be partially filled
    - No cross-instrument strategies or basket orders

    Examples
    --------
    Creating an exchange and listing an instrument:

    >>> exchange = ExchangeVenue()
    >>> apple_stock = Instrument(symbol="AAPL", underlying="AAPL")
    >>> exchange.list_instrument(apple_stock)

    Submitting orders and checking the market:

    >>> buy_order = Order(
    ...     instrument_id="AAPL",
    ...     side="buy",
    ...     quantity=10,
    ...     price=150.0,
    ...     trader_id="trader1"
    ... )
    >>> result = exchange.submit_order(buy_order)
    >>> result.status
    'accepted'
    >>> market = exchange.get_market_summary("AAPL")
    >>> market["best_bid"]
    {'price': 150.0, 'quantity': 10.0}
    """

    def __init__(self):
        """Initialize the exchange venue."""
        # Map of instrument IDs to their order books
        self.order_books: Dict[str, OrderBook] = {}

        # Map of instrument IDs to their instrument objects
        self.instruments: Dict[str, Instrument] = {}

        # Set of all order IDs across all books
        self.all_order_ids: Set[str] = set()

    def list_instrument(self, instrument: Instrument) -> None:
        """
        Register an instrument with the exchange.

        Args:
            instrument (Instrument): The instrument to register.

        Raises:
            ValueError: If an instrument with the same ID already exists.
        """
        instrument_id = instrument.id

        if instrument_id in self.instruments:
            raise ValueError(
                f"Instrument with ID {instrument_id} already exists"
            )

        self.instruments[instrument_id] = instrument
        self.order_books[instrument_id] = OrderBook(instrument_id)

    def submit_order(self, order: Order) -> OrderResult:
        """
        Submit an order to the exchange.

        Args:
            order (Order): The order to submit.

        Returns:
            OrderResult: The result of the order submission.

        Raises:
            ValueError: If the instrument doesn't exist or the order ID is
                already in use.
        """
        # Validate the order
        if order.instrument_id not in self.order_books:
            raise ValueError(f"Instrument {order.instrument_id} not found")

        if order.order_id in self.all_order_ids:
            raise ValueError(f"Order ID {order.order_id} already exists")

        # Add the order ID to our set
        self.all_order_ids.add(order.order_id)

        # Get the order book for this instrument
        order_book = self.order_books[order.instrument_id]

        # Add the order to the book and get any trades
        trades = order_book.add_order(order)

        # Determine the status
        status = "filled" if order.is_filled else "accepted"

        # Create and return the result
        return OrderResult(
            order_id=order.order_id,
            status=status,
            fills=trades,
            remaining_quantity=order.remaining_quantity,
        )

    def cancel_order(self, order_id: str, trader_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id (str): The ID of the order to cancel.
            trader_id (str): The ID of the trader who owns the order.

        Returns:
            bool: True if the order was cancelled, False otherwise.

        Raises:
            ValueError: If the trader doesn't own the order.
        """
        # Check if the order exists
        if order_id not in self.all_order_ids:
            return False

        # Find the order book that contains this order
        for book in self.order_books.values():
            order = book.get_order(order_id)
            if order:
                # Check if the trader owns the order
                if order.trader_id != trader_id:
                    raise ValueError(
                        f"Trader {trader_id} does not own order {order_id}"
                    )

                # Cancel the order
                cancelled = book.cancel_order(order_id)
                if cancelled:
                    self.all_order_ids.remove(order_id)
                    return True

                return False

        return False

    def get_order_book(self, instrument_id: str) -> Optional[OrderBook]:
        """
        Get the order book for an instrument.

        Args:
            instrument_id (str): The ID of the instrument.

        Returns:
            Optional[OrderBook]: The order book, or None if the instrument
                doesn't exist.
        """
        return self.order_books.get(instrument_id)

    def get_trade_history(
        self, instrument_id: str, limit: int = 10
    ) -> List[Trade]:
        """
        Get the trade history for an instrument.

        Args:
            instrument_id (str): The ID of the instrument.
            limit (int): The maximum number of trades to return.

        Returns:
            List[Trade]: The most recent trades, newest first.

        Raises:
            ValueError: If the instrument doesn't exist.
        """
        if instrument_id not in self.order_books:
            raise ValueError(f"Instrument {instrument_id} not found")

        return self.order_books[instrument_id].get_recent_trades(limit)

    def get_market_summary(self, instrument_id: str) -> Dict[str, object]:
        """
        Get a summary of the current market state for an instrument.

        Args:
            instrument_id (str): The ID of the instrument.

        Returns:
            Dict: A dictionary containing the best bid/ask and recent trades.

        Raises:
            ValueError: If the instrument doesn't exist.
        """
        if instrument_id not in self.order_books:
            raise ValueError(f"Instrument {instrument_id} not found")

        book = self.order_books[instrument_id]

        return {
            "instrument_id": instrument_id,
            "best_bid": book.best_bid(),
            "best_ask": book.best_ask(),
            "last_trades": book.get_recent_trades(5),
            "depth": book.depth_snapshot(),
        }

    def get_all_instruments(self) -> List[Instrument]:
        """
        Get all instruments listed on the exchange.

        Returns:
            List[Instrument]: All registered instruments.
        """
        return list(self.instruments.values())
