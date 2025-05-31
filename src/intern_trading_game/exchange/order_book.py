"""
OrderBook module for the Intern Trading Game.

This module defines the OrderBook class, which maintains the order book for a
single instrument.
"""

import bisect
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from intern_trading_game.exchange.order import Order
from intern_trading_game.exchange.trade import Trade


@dataclass
class PriceLevel:
    """
    Represents a price level in the order book.

    A price level is a collection of orders at the same price point in the order
    book. Orders at the same price level are prioritized by time (first in, first
    out). The price level tracks the total quantity of all orders at this price,
    which is used for market depth calculations.

    Parameters
    ----------
    price : float
        The price level. This is the price at which all orders in this level
        will execute.
    orders : deque, optional
        Queue of orders at this price level, sorted by time priority (first in,
        first out). If not provided, an empty queue is created.
    total_quantity : float, optional, default=0
        Total quantity of all orders at this level. This is automatically
        calculated when orders are added or removed.

    Attributes
    ----------
    price : float
        The price level.
    orders : deque
        Queue of orders at this price level (time priority).
    total_quantity : float
        Total quantity of all orders at this level.

    Notes
    -----
    Price levels are a key concept in order book management. They allow for
    efficient organization of orders by price, which is essential for
    implementing price-time priority matching algorithms.

    The total quantity at a price level is an important metric for market
    participants, as it indicates the liquidity available at that price.

    In a limit order book, price levels are typically organized in two separate
    lists:
    1. Bid price levels (buy orders) - sorted in descending order (highest first)
    2. Ask price levels (sell orders) - sorted in ascending order (lowest first)

    This organization allows for efficient matching of incoming orders against
    the best available prices.

    TradingContext
    -------------
    This implementation assumes:
    - Price-time priority (orders at the same price are executed in time order)
    - No hidden or iceberg orders (all order quantity is visible)
    - No pro-rata matching (where orders at the same price are matched
      proportionally to their size)
    - No minimum quantity requirements for order matching

    Examples
    --------
    Creating a price level and adding orders:

    >>> from collections import deque
    >>> from intern_trading_game.exchange.order import Order
    >>> level = PriceLevel(price=150.0)
    >>> buy_order = Order(
    ...     instrument_id="AAPL",
    ...     side="buy",
    ...     quantity=10,
    ...     price=150.0,
    ...     trader_id="trader1"
    ... )
    >>> level.add_order(buy_order)
    >>> level.total_quantity
    10.0
    >>> second_order = Order(
    ...     instrument_id="AAPL",
    ...     side="buy",
    ...     quantity=5,
    ...     price=150.0,
    ...     trader_id="trader2"
    ... )
    >>> level.add_order(second_order)
    >>> level.total_quantity
    15.0
    """

    price: float
    orders: deque = field(default_factory=deque)
    total_quantity: float = 0

    def add_order(self, order: Order) -> None:
        """
        Add an order to this price level.

        Parameters
        ----------
        order : Order
            The order to add to this price level. The order's price should match
            the price level's price.

        Notes
        -----
        This method updates the total quantity of the price level by adding
        the remaining quantity of the order.
        """
        self.orders.append(order)
        self.total_quantity += order.remaining_quantity

    def remove_order(self, order_id: str) -> Optional[Order]:
        """
        Remove an order from this price level by its ID.

        Parameters
        ----------
        order_id : str
            The ID of the order to remove.

        Returns
        -------
        Optional[Order]
            The removed order, or None if not found.

        Notes
        -----
        This method updates the total quantity of the price level by subtracting
        the remaining quantity of the removed order.
        """
        for i, order in enumerate(self.orders):
            if order.order_id == order_id:
                removed_order = self.orders[i]
                self.total_quantity -= removed_order.remaining_quantity
                del self.orders[i]
                return removed_order
        return None

    def update_quantity(self, order_id: str, new_quantity: float) -> None:
        """
        Update the quantity of an order at this price level.

        Parameters
        ----------
        order_id : str
            The ID of the order to update.
        new_quantity : float
            The new remaining quantity for the order.

        Notes
        -----
        This method updates the total quantity of the price level to reflect
        the change in the order's quantity.
        """
        for order in self.orders:
            if order.order_id == order_id:
                old_quantity = order.remaining_quantity
                order.remaining_quantity = new_quantity
                self.total_quantity = (
                    self.total_quantity - old_quantity + new_quantity
                )
                break

    def is_empty(self) -> bool:
        """
        Check if this price level has no orders.

        Returns
        -------
        bool
            True if there are no orders at this price level, False otherwise.

        Notes
        -----
        Empty price levels are typically removed from the order book to
        maintain efficiency.
        """
        return len(self.orders) == 0


class OrderBook:
    """
    Maintains the order book for a single instrument.

    The order book keeps track of all open orders for an instrument,
    matches incoming orders against existing orders, and generates trades.
    It implements a price-time priority matching algorithm, where orders
    are matched first by price (highest bid, lowest ask) and then by time
    (first in, first out).

    Parameters
    ----------
    instrument_id : str
        The ID of the instrument this order book is for.

    Attributes
    ----------
    instrument_id : str
        The ID of the instrument this order book is for.
    bids : List[PriceLevel]
        Price levels for buy orders, sorted by price in descending order.
    asks : List[PriceLevel]
        Price levels for sell orders, sorted by price in ascending order.
    order_price_map : Dict[str, float]
        Maps order IDs to their price levels for quick lookup.
    order_ids : Set[str]
        Set of order IDs in this book.
    trades : deque
        Recent trades, limited to the last 100.

    Notes
    -----
    The order book maintains two separate lists of price levels: one for bids
    (buy orders) and one for asks (sell orders). Each price level contains
    a queue of orders at that price, sorted by time priority.

    The matching algorithm follows these steps:
    1. Determine the opposite side of the book to match against
    2. Check if the incoming order's price is acceptable
    3. Match against the best price level until filled or no more matches
    4. Add any remaining quantity to the book (for limit orders)

    TradingContext
    --------------
    This order book implementation assumes:
    - Continuous trading (no auctions or circuit breakers)
    - No self-trade prevention
    - No iceberg or hidden orders
    - No minimum tick size enforcement
    - No position limits or risk checks

    Examples
    --------
    >>> book = OrderBook("AAPL")
    >>> buy_order = Order(instrument_id="AAPL", side="buy", quantity=10, price=150.0, trader_id="trader1")
    >>> trades = book.add_order(buy_order)
    >>> sell_order = Order(instrument_id="AAPL", side="sell", quantity=5, price=150.0, trader_id="trader2")
    >>> trades = book.add_order(sell_order)
    >>> print(len(trades))
    1
    >>> print(trades[0].quantity)
    5
    """

    def __init__(self, instrument_id: str):
        """
        Initialize an order book for an instrument.

        Parameters
        ----------
        instrument_id : str
            The ID of the instrument this order book is for.

        Notes
        -----
        This constructor initializes empty bid and ask sides of the book,
        as well as data structures for tracking orders and trades.
        """
        self.instrument_id = instrument_id

        # Price levels sorted by price
        # (ascending for asks, descending for bids)
        # Highest bid first, lowest ask first
        self.bids: List[PriceLevel] = []  # Highest bid first
        self.asks: List[PriceLevel] = []  # Lowest ask first

        # Maps order IDs to their price levels for quick lookup
        self.order_price_map: Dict[str, float] = {}

        # Set of order IDs in this book
        self.order_ids: Set[str] = set()

        # Recent trades
        self.trades: deque = deque(maxlen=100)

    def add_order(self, order: Order) -> List[Trade]:
        """
        Add an order to the book and attempt to match it.

        This is the main entry point for adding orders to the order book.
        The method first validates the order, then attempts to match it against
        existing orders on the opposite side of the book. If the order is not
        fully filled and it's a limit order, the remaining quantity is added
        to the book.

        Parameters
        ----------
        order : Order
            The order to add to the book. Must have the same instrument_id as
            the order book and a unique order_id.

        Returns
        -------
        List[Trade]
            A list of trades that were generated from matching the order.
            Empty list if no matches were found.

        Raises
        ------
        ValueError
            If the order's instrument_id doesn't match the book's instrument_id
            or if the order_id already exists in the book.

        Notes
        -----
        The order matching process follows price-time priority:
        1. For buy orders, match against asks in ascending price order
        2. For sell orders, match against bids in descending price order
        3. At each price level, match against orders in time priority (FIFO)

        Market orders are always matched immediately at the best available price,
        while limit orders are only matched if the price is acceptable.

        TradingContext
        --------------
        This method assumes:
        - Orders are validated before submission
        - No position limits or risk checks
        - No fees or commissions
        - Continuous trading (no auction periods)

        Examples
        --------
        >>> book = OrderBook("AAPL")
        >>> # Add a limit sell order
        >>> sell_order = Order(
        ...     instrument_id="AAPL",
        ...     side="sell",
        ...     quantity=10,
        ...     price=150.0,
        ...     trader_id="trader1"
        ... )
        >>> trades = book.add_order(sell_order)
        >>> print(len(trades))
        0
        >>> # Add a matching buy order
        >>> buy_order = Order(
        ...     instrument_id="AAPL",
        ...     side="buy",
        ...     quantity=5,
        ...     price=150.0,
        ...     trader_id="trader2"
        ... )
        >>> trades = book.add_order(buy_order)
        >>> print(len(trades))
        1
        >>> print(trades[0].quantity)
        5
        """
        # Validate order
        if order.instrument_id != self.instrument_id:
            raise ValueError(
                f"Order instrument {order.instrument_id} does not match "
                f"book instrument {self.instrument_id}"
            )

        if order.order_id in self.order_ids:
            raise ValueError(
                f"Order ID {order.order_id} already exists in the book"
            )

        # Try to match the order first
        trades = self._match_order(order)

        # If the order wasn't fully filled, add the remainder to the book
        if not order.is_filled and order.is_limit_order:
            self._insert_order(order)

        return trades

    def cancel_order(self, order_id: str) -> Optional[Order]:
        """
        Cancel and remove an order from the book.

        Parameters
        ----------
        order_id : str
            The ID of the order to cancel.

        Returns
        -------
        Optional[Order]
            The cancelled order, or None if not found.

        Notes
        -----
        This method removes the order from the book and updates all relevant
        data structures. If the price level becomes empty after removing the
        order, the price level is also removed.

        Examples
        --------
        >>> book = OrderBook("AAPL")
        >>> order = Order(
        ...     instrument_id="AAPL",
        ...     side="buy",
        ...     quantity=10,
        ...     price=150.0,
        ...     trader_id="trader1"
        ... )
        >>> book.add_order(order)
        []
        >>> cancelled = book.cancel_order(order.order_id)
        >>> cancelled.order_id == order.order_id
        True
        """
        if order_id not in self.order_price_map:
            return None

        price = self.order_price_map[order_id]
        order_list = self.bids if self._is_bid_price(price) else self.asks

        # Find the price level
        for level in order_list:
            if level.price == price:
                order = level.remove_order(order_id)
                if order:
                    del self.order_price_map[order_id]
                    self.order_ids.remove(order_id)

                    # Remove empty price levels
                    if level.is_empty():
                        order_list.remove(level)

                    return order
                break

        return None

    def _match_order(self, order: Order) -> List[Trade]:
        """
        Try to match an order against the opposite side of the book.

        This method implements the core matching algorithm using price-time priority.
        It attempts to match the incoming order against existing orders on the
        opposite side of the book, generating trades for any matches found.

        Parameters
        ----------
        order : Order
            The order to match against the book.

        Returns
        -------
        List[Trade]
            A list of trades that were generated from the matching process.
            Empty list if no matches were found.

        Notes
        -----
        The matching algorithm follows these steps:
        1. Determine which side of the book to match against (asks for buy orders,
           bids for sell orders)
        2. For limit orders, check if the price is acceptable
           (buy price >= ask price or sell price <= bid price)
        3. Match against orders at the best price level until either:
           - The incoming order is fully filled
           - The price is no longer acceptable
           - There are no more orders on the opposite side
        4. For each match, create a trade and update the quantities of both orders

        TradingContext
        --------------
        The matching process assumes:
        - Price-time priority (better prices first, then earlier orders)
        - No minimum match size
        - No self-trade prevention
        - Continuous trading (no auction periods)
        - Trades execute at the price of the resting order

        Examples
        --------
        >>> book = OrderBook("AAPL")
        >>> # Add a resting sell order
        >>> sell_order = Order(instrument_id="AAPL", side="sell", quantity=10,
        ...                    price=150.0, trader_id="trader1")
        >>> book._insert_order(sell_order)
        >>> # Match a buy order against it
        >>> buy_order = Order(instrument_id="AAPL", side="buy", quantity=5,
        ...                   price=150.0, trader_id="trader2")
        >>> trades = book._match_order(buy_order)
        >>> print(len(trades))
        1
        >>> print(trades[0].quantity)
        5
        >>> print(trades[0].price)
        150.0
        """
        trades = []

        # Determine which side of the book to match against
        opposite_side = self.asks if order.is_buy else self.bids

        # Keep matching until the order is filled or no more matches are
        # possible
        while not order.is_filled and opposite_side:
            best_price_level = opposite_side[0]

            # For limit orders, check if the price is acceptable
            if order.is_limit_order and order.price is not None:
                if (order.is_buy and best_price_level.price > order.price) or (
                    order.is_sell and best_price_level.price < order.price
                ):
                    break  # No more acceptable prices

            # Get the first order at this price level
            matching_order = best_price_level.orders[0]

            # Determine the fill quantity
            fill_qty = min(
                order.remaining_quantity, matching_order.remaining_quantity
            )

            # Create a trade
            if order.is_buy:
                trade = Trade(
                    instrument_id=self.instrument_id,
                    buyer_id=order.trader_id,
                    seller_id=matching_order.trader_id,
                    price=best_price_level.price,
                    quantity=fill_qty,
                    buyer_order_id=order.order_id,
                    seller_order_id=matching_order.order_id,
                )
            else:
                trade = Trade(
                    instrument_id=self.instrument_id,
                    buyer_id=matching_order.trader_id,
                    seller_id=order.trader_id,
                    price=best_price_level.price,
                    quantity=fill_qty,
                    buyer_order_id=matching_order.order_id,
                    seller_order_id=order.order_id,
                )

            trades.append(trade)
            self.trades.append(trade)

            # Update the orders
            order.fill(fill_qty)
            matching_order.fill(fill_qty)

            # Update the quantity in the price level for the matching order
            best_price_level.total_quantity -= fill_qty

            # If the matching order is filled, remove it
            if matching_order.is_filled:
                best_price_level.remove_order(matching_order.order_id)
                self.order_ids.remove(matching_order.order_id)
                del self.order_price_map[matching_order.order_id]

                # If the price level is empty, remove it
                if best_price_level.is_empty():
                    opposite_side.pop(0)

        return trades

    def _insert_order(self, order: Order) -> None:
        """
        Insert a limit order into the book.

        Parameters
        ----------
        order : Order
            The limit order to insert. Must be a limit order with a valid price.

        Notes
        -----
        This method inserts the order into the appropriate side of the book
        (bids or asks) at the correct price level. If a price level for the
        order's price doesn't exist, a new one is created.

        The price levels are maintained in sorted order:
        - Bids: descending order (highest price first)
        - Asks: ascending order (lowest price first)

        This sorting ensures that the best prices are always at the front
        of each list, which is essential for efficient matching.
        """
        assert (
            order.is_limit_order
        ), "Only limit orders can be inserted into the book"
        # The above line is exactly 79 characters, so it's fine
        assert order.price is not None, "Limit orders must have a price"

        # Determine which side of the book to insert into
        order_list = self.bids if order.is_buy else self.asks

        # Find the correct position to insert the order
        price_level = None
        for level in order_list:
            if level.price == order.price:
                price_level = level
                break

        # If no price level exists for this price, create one
        if price_level is None:
            price_level = PriceLevel(price=order.price)

            # Insert the price level in the correct position to maintain
            # sorting
            if order.is_buy:
                # Bids are sorted in descending order (highest first)
                insert_pos = bisect.bisect_left(
                    [-level.price for level in self.bids], -order.price
                )
                self.bids.insert(insert_pos, price_level)
            else:
                # Asks are sorted in ascending order (lowest first)
                insert_pos = bisect.bisect_left(
                    [level.price for level in self.asks], order.price
                )
                self.asks.insert(insert_pos, price_level)

        # Add the order to the price level
        price_level.add_order(order)

        # Update our maps
        self.order_price_map[order.order_id] = order.price
        self.order_ids.add(order.order_id)

    def _is_bid_price(self, price: float) -> bool:
        """
        Check if a price is in the bid side of the book.

        Parameters
        ----------
        price : float
            The price to check.

        Returns
        -------
        bool
            True if the price is in the bid side, False otherwise.

        Notes
        -----
        This method is used to determine which side of the book (bids or asks)
        an order is on, given its price. This is useful for operations like
        cancelling orders where we need to know which list to search.
        """
        return any(level.price == price for level in self.bids)

    def best_bid(self) -> Optional[Tuple[float, float]]:
        """
        Get the best (highest) bid price and quantity.

        Returns
        -------
        Optional[Tuple[float, float]]
            A tuple containing (price, quantity) of the best bid, or None if
            there are no bids in the book.

        Notes
        -----
        The best bid is the highest price at which someone is willing to buy.
        This is always the first price level in the bids list, since it's
        sorted in descending order.

        Examples
        --------
        >>> book = OrderBook("AAPL")
        >>> book.best_bid()
        None
        >>> order = Order(
        ...     instrument_id="AAPL",
        ...     side="buy",
        ...     quantity=10,
        ...     price=150.0,
        ...     trader_id="trader1"
        ... )
        >>> book.add_order(order)
        []
        >>> book.best_bid()
        (150.0, 10.0)
        """
        if not self.bids:
            return None
        level = self.bids[0]
        return (level.price, level.total_quantity)

    def best_ask(self) -> Optional[Tuple[float, float]]:
        """
        Get the best (lowest) ask price and quantity.

        Returns
        -------
        Optional[Tuple[float, float]]
            A tuple containing (price, quantity) of the best ask, or None if
            there are no asks in the book.

        Notes
        -----
        The best ask is the lowest price at which someone is willing to sell.
        This is always the first price level in the asks list, since it's
        sorted in ascending order.

        Examples
        --------
        >>> book = OrderBook("AAPL")
        >>> book.best_ask()
        None
        >>> order = Order(
        ...     instrument_id="AAPL",
        ...     side="sell",
        ...     quantity=10,
        ...     price=150.0,
        ...     trader_id="trader1"
        ... )
        >>> book.add_order(order)
        []
        >>> book.best_ask()
        (150.0, 10.0)
        """
        if not self.asks:
            return None
        level = self.asks[0]
        return (level.price, level.total_quantity)

    def depth_snapshot(
        self, levels: int = 5
    ) -> Dict[str, List[Tuple[float, float]]]:
        """
        Get a snapshot of the order book depth.

        Parameters
        ----------
        levels : int, default=5
            The number of price levels to include in the snapshot.

        Returns
        -------
        Dict[str, List[Tuple[float, float]]]
            A dictionary with 'bids' and 'asks' keys, each with a list of
            (price, quantity) tuples representing the order book depth.

        Notes
        -----
        This method provides a view of the current state of the order book,
        showing the available liquidity at different price levels. This is
        useful for market data display and analysis.

        The depth snapshot is often used to create a "market depth" or "level 2"
        view of the market, showing the available liquidity at different price
        points.

        Examples
        --------
        >>> book = OrderBook("AAPL")
        >>> buy_order = Order(
        ...     instrument_id="AAPL",
        ...     side="buy",
        ...     quantity=10,
        ...     price=150.0,
        ...     trader_id="trader1"
        ... )
        >>> book.add_order(buy_order)
        []
        >>> sell_order = Order(
        ...     instrument_id="AAPL",
        ...     side="sell",
        ...     quantity=5,
        ...     price=151.0,
        ...     trader_id="trader2"
        ... )
        >>> book.add_order(sell_order)
        []
        >>> depth = book.depth_snapshot()
        >>> depth["bids"]
        [(150.0, 10.0)]
        >>> depth["asks"]
        [(151.0, 5.0)]
        """
        bids = []
        for level in self.bids[:levels]:
            bids.append((level.price, level.total_quantity))
        asks = []
        for level in self.asks[:levels]:
            asks.append((level.price, level.total_quantity))

        result = {"bids": bids, "asks": asks}
        return result

    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get an order from the book by its ID.

        Parameters
        ----------
        order_id : str
            The ID of the order to get.

        Returns
        -------
        Optional[Order]
            The order with the specified ID, or None if not found.

        Notes
        -----
        This method searches for an order in the book by its ID. It uses the
        order_price_map to quickly determine which side of the book to search
        and at which price level.

        Examples
        --------
        >>> book = OrderBook("AAPL")
        >>> order = Order(
        ...     instrument_id="AAPL",
        ...     side="buy",
        ...     quantity=10,
        ...     price=150.0,
        ...     trader_id="trader1"
        ... )
        >>> book.add_order(order)
        []
        >>> retrieved = book.get_order(order.order_id)
        >>> retrieved.order_id == order.order_id
        True
        """
        if order_id not in self.order_price_map:
            return None

        price = self.order_price_map[order_id]
        order_list = self.bids if self._is_bid_price(price) else self.asks

        for level in order_list:
            if level.price == price:
                for order in level.orders:
                    if order.order_id == order_id:
                        return order

        return None

    def get_recent_trades(self, limit: int = 10) -> List[Trade]:
        """
        Get the most recent trades.

        Parameters
        ----------
        limit : int, default=10
            The maximum number of trades to return.

        Returns
        -------
        List[Trade]
            The most recent trades, newest first, up to the specified limit.

        Notes
        -----
        This method returns the most recent trades that occurred in this order
        book. The trades are returned in reverse chronological order (newest
        first).

        The order book maintains a circular buffer of the last 100 trades,
        so requesting more than 100 trades will still return at most 100.

        Examples
        --------
        >>> book = OrderBook("AAPL")
        >>> buy_order = Order(
        ...     instrument_id="AAPL",
        ...     side="buy",
        ...     quantity=10,
        ...     price=150.0,
        ...     trader_id="trader1"
        ... )
        >>> book.add_order(buy_order)
        []
        >>> sell_order = Order(
        ...     instrument_id="AAPL",
        ...     side="sell",
        ...     quantity=5,
        ...     price=150.0,
        ...     trader_id="trader2"
        ... )
        >>> trades = book.add_order(sell_order)
        >>> len(trades)
        1
        >>> recent = book.get_recent_trades()
        >>> len(recent)
        1
        >>> recent[0].quantity
        5.0
        """
        return list(self.trades)[-limit:]
