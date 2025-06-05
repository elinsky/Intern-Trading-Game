"""Order matching engine implementations for the Intern Trading Game.

This module implements the Strategy Pattern for order matching, supporting
both continuous (immediate) and batch matching modes. The design allows
the exchange to switch between different matching algorithms without
changing the core order submission logic.

Design Decisions:
-----------------

1. Batch matching includes fair randomization at the same price level to
   prevent timing advantages, crucial for a fair trading game where all
   participants should have equal opportunity.

2. We optimize for clarity and correctness over microsecond performance,
   as our game operates on 5-minute ticks with ~100s of orders, not millions
   of orders per second like HFT systems.

References:
-----------
The batch matching randomization approach is inspired by real exchange
mechanisms like NYSE's opening auction, where orders at the same price
are allocated fairly rather than strictly by time priority.
"""

import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from intern_trading_game.exchange.order import Order
from intern_trading_game.exchange.order_book import OrderBook
from intern_trading_game.exchange.order_result import OrderResult
from intern_trading_game.exchange.trade import Trade


class MatchingEngine(ABC):
    """Abstract base class defining the interface for order matching strategies.

    This interface ensures that all matching engines provide consistent
    methods for order submission and batch execution, allowing the
    ExchangeVenue to work with different matching algorithms transparently.

    The two key operations are:
    1. submit_order: Handle individual order submission
    2. execute_batch: Process any pending batch operations

    Notes
    -----
    The execute_batch method is called even in continuous mode (where it's
    a no-op) to maintain a consistent interface. This allows the GameLoop
    to call execute_batch at T+3:30 regardless of the matching mode.

    TradingContext
    --------------
    Market Assumptions
        - Orders are validated before reaching the matching engine
        - The engine is responsible only for the matching algorithm
        - Order books are maintained externally by the ExchangeVenue

    Trading Rules
        - Each engine must respect price priority
        - Time priority rules vary by engine type
        - Batch engines may randomize within price levels
    """

    @abstractmethod
    def submit_order(self, order: Order, order_book: OrderBook) -> OrderResult:
        """Process an order submission according to the matching strategy.

        Parameters
        ----------
        order : Order
            The order to be processed
        order_book : OrderBook
            The order book for the instrument being traded

        Returns
        -------
        OrderResult
            Result indicating order status and any immediate fills

        Notes
        -----
        In continuous mode, this method may generate immediate trades.
        In batch mode, orders are collected for later processing.
        """
        pass

    @abstractmethod
    def execute_batch(
        self, order_books: Dict[str, OrderBook]
    ) -> Dict[str, Dict[str, OrderResult]]:
        """Execute any pending batch operations.

        Parameters
        ----------
        order_books : Dict[str, OrderBook]
            All order books in the exchange, keyed by instrument ID

        Returns
        -------
        Dict[str, Dict[str, OrderResult]]
            Results organized by instrument ID, then order ID

        Notes
        -----
        For continuous matching engines, this returns an empty dict.
        For batch engines, this processes all pending orders.
        """
        pass

    @abstractmethod
    def get_mode(self) -> str:
        """Return the matching mode identifier.

        Returns
        -------
        str
            Either "continuous" or "batch"
        """
        pass


class ContinuousMatchingEngine(MatchingEngine):
    """Implements immediate order matching (traditional continuous trading).

    This engine processes each order as it arrives, attempting to match it
    against the opposite side of the order book immediately. This is the
    standard behavior for most electronic exchanges during regular trading
    hours.

    The engine maintains no internal state - each order is processed
    independently and immediately.

    Notes
    -----
    Continuous matching advantages:
    - Immediate price discovery
    - Real-time execution feedback
    - Simple implementation

    Continuous matching disadvantages:
    - Speed advantages matter (first-come, first-served)
    - Can lead to "winner takes all" scenarios
    - May discourage liquidity provision

    TradingContext
    --------------
    Market Assumptions
        - Orders execute immediately if matchable
        - No delay between submission and execution attempt
        - Market impact occurs order by order

    Trading Rules
        - Strict price-time priority
        - First submitted order at a price gets filled first
        - No randomization or batching
    """

    def submit_order(self, order: Order, order_book: OrderBook) -> OrderResult:
        """Process order immediately against the order book.

        The order is added to the order book, which handles matching
        internally. Any resulting trades are returned immediately.

        Parameters
        ----------
        order : Order
            The order to process
        order_book : OrderBook
            The relevant order book

        Returns
        -------
        OrderResult
            Status and any immediate fills

        Examples
        --------
        >>> engine = ContinuousMatchingEngine()
        >>> book = OrderBook("TEST")
        >>> order = Order(
        ...     instrument_id="TEST",
        ...     side="buy",
        ...     quantity=10,
        ...     price=100.0,
        ...     trader_id="trader1"
        ... )
        >>> result = engine.submit_order(order, book)
        >>> result.status
        'accepted'
        """
        # Delegate to the order book's existing matching logic
        # The order book handles price-time priority internally
        trades = order_book.add_order(order)

        # Determine status based on fill state
        if order.is_filled:
            status = "filled"
        elif trades:  # Partial fill
            status = "partially_filled"
        else:  # No fill, order resting in book
            status = "new"

        return OrderResult(
            order_id=order.order_id,
            status=status,
            fills=trades,
            remaining_quantity=order.remaining_quantity,
        )

    def execute_batch(
        self, order_books: Dict[str, OrderBook]
    ) -> Dict[str, Dict[str, OrderResult]]:
        """No-op for continuous matching - orders execute immediately.

        This method exists to maintain interface compatibility but
        performs no operations in continuous mode.

        Returns
        -------
        Dict[str, Dict[str, OrderResult]]
            Always returns empty dict
        """
        # Continuous matching has no batch phase
        # All orders were already matched in submit_order
        return {}

    def get_mode(self) -> str:
        """Return the matching mode identifier.

        Returns
        -------
        str
            Always returns "continuous"
        """
        return "continuous"


# Helper functions for batch matching
def _create_trade(
    buy_order: Order, sell_order: Order, quantity: float
) -> Trade:
    """Create a trade between two orders at the sell price."""
    # Price should never be None for orders that are matching
    assert (
        sell_order.price is not None
    ), "Sell order price cannot be None in trade"
    return Trade(
        instrument_id=buy_order.instrument_id,
        buyer_order_id=buy_order.order_id,
        seller_order_id=sell_order.order_id,
        buyer_id=buy_order.trader_id,
        seller_id=sell_order.trader_id,
        price=sell_order.price,  # Match at passive (sell) side
        quantity=quantity,
    )


def _sort_orders(orders: List[Order], descending: bool) -> List[Order]:
    """Sort orders by price with randomization at same level."""
    # Filter out market orders (price=None) - they should be handled separately
    # For batch matching, we only sort limit orders
    return sorted(
        orders,
        key=lambda o: (
            -o.price if descending and o.price is not None else (o.price or 0),
            random.random(),  # nosec B311 - Not cryptographic use
        ),
    )


@dataclass
class BatchContext:
    """Context for batch matching pipeline - manages state through processing steps.

    This class uses a clean pipeline pattern where each method transforms
    the internal state, making the business logic clear and testable.

    Attributes
    ----------
    pending_orders : Dict[str, List[Order]]
        Orders to be processed, keyed by instrument
    order_books : Dict[str, OrderBook]
        Available order books for matching
    results : Dict[str, Dict[str, OrderResult]]
        Results being built, using defaultdict for simplicity
    """

    pending_orders: Dict[str, List[Order]]
    order_books: Dict[str, OrderBook]
    results: Dict[str, Dict[str, OrderResult]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    def _get_or_create_result(
        self, instrument_id: str, order: Order
    ) -> OrderResult:
        """Get existing result or create new one."""
        if order.order_id not in self.results[instrument_id]:
            self.results[instrument_id][order.order_id] = OrderResult(
                order_id=order.order_id,
                status="new",
                fills=[],
                remaining_quantity=order.remaining_quantity,
            )
        return self.results[instrument_id][order.order_id]

    def _record_trade(
        self, trade: Trade, buy_order: Order, sell_order: Order
    ) -> None:
        """Record a trade in both order results."""
        instrument_id = trade.instrument_id

        # Update order states - reduce remaining quantity
        buy_order.remaining_quantity -= trade.quantity
        sell_order.remaining_quantity -= trade.quantity

        # Record in results
        self._get_or_create_result(instrument_id, buy_order).fills.append(
            trade
        )
        self._get_or_create_result(instrument_id, sell_order).fills.append(
            trade
        )

    def match_batch_orders(self) -> None:
        """Match orders within each instrument's batch."""
        for instrument_id, orders in self.pending_orders.items():
            if instrument_id not in self.order_books:
                continue

            # Separate and sort orders
            buy_orders = _sort_orders(
                [o for o in orders if o.side == "buy"], descending=True
            )
            sell_orders = _sort_orders(
                [o for o in orders if o.side == "sell"], descending=False
            )

            # Match crossing orders
            buy_idx = sell_idx = 0

            while buy_idx < len(buy_orders) and sell_idx < len(sell_orders):
                buy_order = buy_orders[buy_idx]
                sell_order = sell_orders[sell_idx]

                # Both orders must have prices for limit order matching
                if (
                    buy_order.price is not None
                    and sell_order.price is not None
                    and buy_order.price >= sell_order.price
                ):
                    # Orders cross - create trade
                    match_qty = min(
                        buy_order.remaining_quantity,
                        sell_order.remaining_quantity,
                    )
                    trade = _create_trade(buy_order, sell_order, match_qty)
                    self._record_trade(trade, buy_order, sell_order)

                    # Advance filled orders
                    if buy_order.is_filled:
                        buy_idx += 1
                    if sell_order.is_filled:
                        sell_idx += 1
                else:
                    # No more crosses
                    break

            # Add remaining orders to book
            remaining = buy_orders[buy_idx:] + sell_orders[sell_idx:]
            self._add_orders_to_book(instrument_id, remaining)

    def _add_orders_to_book(
        self, instrument_id: str, orders: List[Order]
    ) -> None:
        """Add unmatched orders to the order book."""
        order_book = self.order_books[instrument_id]

        for order in orders:
            trades = order_book.add_order(order)
            result = self._get_or_create_result(instrument_id, order)
            result.fills.extend(trades)

    def finalize_results(self) -> None:
        """Set final status for all orders based on fill state."""
        for instrument_id, orders in self.pending_orders.items():
            for order in orders:
                result = self._get_or_create_result(instrument_id, order)
                result.remaining_quantity = order.remaining_quantity

                # Determine final status
                if order.is_filled:
                    result.status = "filled"
                elif result.fills:
                    result.status = "partially_filled"
                else:
                    result.status = "new"


class BatchMatchingEngine(MatchingEngine):
    r"""Implements batch order matching with fair randomization.

    This engine collects orders during a submission window and processes
    them all simultaneously at a designated time. Orders at the same price
    level are randomized to ensure fairness, preventing timing advantages.

    This approach is inspired by opening/closing auctions on major exchanges
    and is ideal for game environments where fairness is paramount.

    Parameters
    ----------
    None

    Attributes
    ----------
    pending_orders : Dict[str, List[Order]]
        Orders awaiting batch execution, organized by instrument ID.
        Structure: {instrument_id: [order1, order2, ...]}

        We organize by instrument for efficiency during batch processing,
        avoiding the need to filter orders repeatedly.

    Notes
    -----
    Batch matching advantages:
    - No speed advantages - fair for all participants
    - Encourages liquidity provision
    - Natural fit for discrete time games

    Batch matching disadvantages:
    - Delayed execution feedback
    - No real-time price discovery during batch window
    - More complex implementation

    Mathematical Fairness Guarantees
    --------------------------------
    For orders at the same price level:

    $$P(\text{Order A fills before Order B}) = \frac{1}{2}$$

    For n orders at the same price competing for limited liquidity:

    $$P(\text{Order i in position j}) = \frac{1}{n}$$

    This ensures uniform distribution of execution priority within each
    price level, eliminating timing advantages.

    Implementation notes:
    - We use a single-pass sort with random keys for efficiency,
      avoiding the group-then-shuffle approach from the low-latency article
    - Orders are organized by instrument to optimize batch processing
    - State is cleared after each batch to prevent order accumulation

    TradingContext
    --------------
    Market Assumptions
        - All orders in a batch see the same initial market state
        - No information leakage between orders in the batch
        - Randomization ensures fairness at each price level

    Trading Rules
        - Price priority is strictly maintained
        - Time priority is replaced by random priority within price
        - All orders must be submitted before batch execution

    Examples
    --------
    >>> engine = BatchMatchingEngine()
    >>> book = OrderBook("SPX_CALL_5000")
    >>>
    >>> # Orders are collected, not matched immediately
    >>> order1 = Order(instrument_id="SPX_CALL_5000", side="buy",
    ...                quantity=10, price=25.50, trader_id="MM1")
    >>> result1 = engine.submit_order(order1, book)
    >>> result1.status
    'pending'
    >>>
    >>> # Multiple orders can be submitted
    >>> order2 = Order(instrument_id="SPX_CALL_5000", side="buy",
    ...                quantity=5, price=25.50, trader_id="HF1")
    >>> result2 = engine.submit_order(order2, book)
    >>>
    >>> # Batch execution processes all orders fairly
    >>> results = engine.execute_batch({"SPX_CALL_5000": book})
    >>> # Orders at the same price (25.50) were randomized
    """

    def __init__(self):
        """Initialize the batch matching engine with empty order collection."""
        # Design decision: Use Dict[str, List[Order]] instead of simple List[Order]
        # This pre-organizes orders by instrument, making batch execution more
        # efficient as we don't need to filter orders for each instrument
        self.pending_orders: Dict[str, List[Order]] = {}

    def submit_order(self, order: Order, order_book: OrderBook) -> OrderResult:
        """Collect order for batch processing without immediate matching.

        Orders are stored in pending_orders organized by instrument ID.
        No matching occurs until execute_batch is called.

        Parameters
        ----------
        order : Order
            The order to queue for batch processing
        order_book : OrderBook
            Not used in submit phase, but maintained for interface compatibility

        Returns
        -------
        OrderResult
            Always returns status="pending" with no fills

        Notes
        -----
        The order book parameter is not used during submission but is
        required for interface compatibility. Actual order book interaction
        occurs during execute_batch.
        """
        instrument_id = order.instrument_id

        # Initialize list for new instruments
        if instrument_id not in self.pending_orders:
            self.pending_orders[instrument_id] = []

        # Collect the order for later processing
        self.pending_orders[instrument_id].append(order)

        # Return pending_new status - no immediate execution
        return OrderResult(
            order_id=order.order_id,
            status="pending_new",
            fills=[],  # No fills yet
            remaining_quantity=order.quantity,  # Nothing filled yet
        )

    def execute_batch(
        self, order_books: Dict[str, OrderBook]
    ) -> Dict[str, Dict[str, OrderResult]]:
        """Execute all pending orders using a clear pipeline pattern.

        The batch matching process follows these steps:
        1. Create context with pending orders and order books
        2. Match crossing orders within the batch
        3. Add remaining orders to order books
        4. Finalize order statuses
        5. Clear pending orders

        Parameters
        ----------
        order_books : Dict[str, OrderBook]
            All available order books, keyed by instrument ID

        Returns
        -------
        Dict[str, Dict[str, OrderResult]]
            Nested dict: {instrument_id: {order_id: OrderResult}}

        Notes
        -----
        The pipeline pattern makes the business logic clear:
        - Each step has a single responsibility
        - State flows through the context object
        - Easy to test and debug each step

        After execution, pending_orders is cleared to prevent orders
        from being processed multiple times.
        """
        # Create context with current state
        ctx = BatchContext(
            pending_orders=self.pending_orders.copy(),  # Copy to avoid mutations
            order_books=order_books,
        )

        # Execute pipeline steps
        ctx.match_batch_orders()
        ctx.finalize_results()

        # Clear pending orders
        self.pending_orders.clear()

        # Convert defaultdict to regular dict for return
        return dict(ctx.results)

    def get_mode(self) -> str:
        """Return the matching mode identifier.

        Returns
        -------
        str
            Always returns "batch"
        """
        return "batch"

    def get_pending_count(self, instrument_id: str) -> int:
        """Get count of pending orders for an instrument (useful for testing).

        This helper method allows tests to verify that orders are being
        collected properly before batch execution.

        Parameters
        ----------
        instrument_id : str
            The instrument to check

        Returns
        -------
        int
            Number of pending orders for the instrument

        Notes
        -----
        This method is primarily for testing and monitoring. Production
        code should not rely on checking pending counts.
        """
        return len(self.pending_orders.get(instrument_id, []))

    def _randomize_same_price_orders(
        self, orders: List[Order], descending: bool
    ) -> List[Order]:
        """Sort orders by price with randomization at same price level.

        This method implements fair randomization by using a random value
        as a tiebreaker in the sort key. This approach is more efficient
        than grouping orders by price and shuffling each group separately.

        Parameters
        ----------
        orders : List[Order]
            Orders to sort and randomize
        descending : bool
            True for buy orders (high to low), False for sell orders (low to high)

        Returns
        -------
        List[Order]
            Orders sorted by price with randomization within price levels

        Notes
        -----
        The random.random() call in the sort key ensures that orders at
        the same price level are randomly ordered. This is more efficient
        than the group-and-shuffle approach because:

        1. Single pass: O(n log n) instead of O(n log n) + O(n)
        2. No intermediate data structures
        3. Maintains price priority strictly

        Mathematical guarantee: For orders A and B at the same price,
        P(A before B) = P(B before A) = 0.5

        Examples
        --------
        >>> orders = [
        ...     Order(price=100, ...),  # These three orders
        ...     Order(price=100, ...),  # will be randomly
        ...     Order(price=100, ...),  # ordered
        ...     Order(price=99, ...),   # This will be last (buy side)
        ... ]
        >>> sorted_orders = engine._randomize_same_price_orders(orders, descending=True)
        >>> # All price=100 orders come before price=99, but their relative order is random
        """
        return sorted(
            orders,
            key=lambda o: (
                -o.price
                if descending and o.price is not None
                else (o.price or 0),  # Price priority
                random.random(),  # nosec B311 - Random tiebreaker for same price
            ),
        )
