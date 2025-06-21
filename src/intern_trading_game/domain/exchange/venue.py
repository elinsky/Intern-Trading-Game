"""
Exchange Venue module for the Intern Trading Game.

This module defines the ExchangeVenue class, which is the main entry point for
the exchange.
"""

from typing import Dict, List, Optional, Set

from .book.matching_engine import (
    BatchMatchingEngine,
    ContinuousMatchingEngine,
    MatchingEngine,
)
from .book.order_book import OrderBook
from .models.instrument import Instrument
from .models.order import Order
from .models.trade import Trade
from .order_result import OrderResult
from .phase.interfaces import PhaseManagerInterface
from .types import PhaseState


class ExchangeVenue:
    r"""
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
    matching_engine : MatchingEngine, optional
        The matching engine to use for order processing. If not provided,
        defaults to ContinuousMatchingEngine for immediate order matching.

    Attributes
    ----------
    order_books : Dict[str, OrderBook]
        Map of instrument IDs to their order books.
    instruments : Dict[str, Instrument]
        Map of instrument IDs to their instrument objects.
    all_order_ids : Set[str]
        Set of all order IDs across all books.
    matching_engine : MatchingEngine
        The engine responsible for order matching logic.

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
    - Configurable matching mode (continuous or batch)
    - No circuit breakers or trading halts
    - No fees or commissions
    - No position limits or risk checks
    - No support for hidden orders, iceberg orders, or other advanced order types
    - All orders can be partially filled
    - No cross-instrument strategies or basket orders

    The matching engine can be switched between continuous and batch modes
    to support different trading scenarios. Batch mode is particularly useful
    for fair order processing in game environments.

    Examples
    --------
    Creating an exchange with continuous matching (default):

    >>> exchange = ExchangeVenue()
    >>> apple_stock = Instrument(symbol="AAPL", underlying="AAPL")
    >>> exchange.list_instrument(apple_stock)

    Using batch matching for fair order processing:

    >>> from .matching_engine import BatchMatchingEngine
    >>> batch_exchange = ExchangeVenue(matching_engine=BatchMatchingEngine())
    >>>
    >>> # Orders are collected during submission
    >>> order1 = Order(instrument_id="AAPL", side="buy", quantity=10,
    ...                price=150.0, trader_id="trader1")
    >>> result1 = batch_exchange.submit_order(order1)
    >>> result1.status
    'pending'
    >>>
    >>> # Execute batch to process all orders
    >>> batch_results = batch_exchange.execute_batch()
    >>> batch_results["AAPL"][order1.order_id].status
    'accepted'
    """

    def __init__(
        self,
        phase_manager: PhaseManagerInterface,
        matching_engine: Optional[MatchingEngine] = None,
    ):
        """Initialize the exchange venue.

        Parameters
        ----------
        phase_manager : PhaseManagerInterface
            The phase manager that determines market phases and rules
        matching_engine : MatchingEngine, optional
            The matching engine to use. Defaults to ContinuousMatchingEngine
            if not provided.

        Notes
        -----
        The choice of matching engine determines how orders are processed:
        - ContinuousMatchingEngine: Orders match immediately upon submission
        - BatchMatchingEngine: Orders are collected and matched in batches

        The phase manager is required to enforce phase-based trading rules
        and ensure orders are only accepted/matched during appropriate phases.
        """
        # Map of instrument IDs to their order books
        self.order_books: Dict[str, OrderBook] = {}

        # Map of instrument IDs to their instrument objects
        self.instruments: Dict[str, Instrument] = {}

        # Set of all order IDs across all books
        self.all_order_ids: Set[str] = set()

        # Phase manager is required for phase-aware operations
        self.phase_manager = phase_manager

        # Initialize matching engine - default to continuous if not specified
        # This maintains backward compatibility while allowing batch mode
        self.matching_engine = matching_engine or ContinuousMatchingEngine()

        # Initialize all engine types for phase-aware operation
        self._continuous_engine = ContinuousMatchingEngine()
        self._batch_engine = BatchMatchingEngine()

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

        Notes
        -----
        This method first checks the current phase state to ensure orders
        can be submitted. It then delegates the actual matching logic to
        the configured matching engine. In continuous mode, orders may match
        immediately. In batch mode, orders are collected for later processing.
        """
        # Check phase state
        phase_state = self.phase_manager.get_current_phase_state()
        if not phase_state.is_order_submission_allowed:
            return OrderResult(
                order_id=order.order_id,
                status="rejected",
                fills=[],
                remaining_quantity=order.quantity,
                error_message=f"Order submission not allowed during {phase_state.phase_type.value} phase",
            )

        # Validate the order
        if order.instrument_id not in self.order_books:
            raise ValueError(f"Instrument {order.instrument_id} not found")

        if order.order_id in self.all_order_ids:
            raise ValueError(f"Order ID {order.order_id} already exists")

        # Add the order ID to our set
        self.all_order_ids.add(order.order_id)

        # Get the order book for this instrument
        order_book = self.order_books[order.instrument_id]

        # Select engine based on phase state
        engine: MatchingEngine
        if (
            phase_state.execution_style == "batch"
            or not phase_state.is_matching_enabled
        ):
            # Pre-open and opening auction: use batch engine
            # During pre-open, orders are collected but not matched
            # During opening auction, execute_batch processes them
            engine = self._batch_engine
        else:
            # Continuous: use continuous engine
            engine = self._continuous_engine

        # Delegate to the selected engine
        result = engine.submit_order(order, order_book)

        # For batch mode, the order might be pending without fills
        # For continuous mode, the order might have immediate fills
        return result

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
        # Check phase state
        phase_state = self.phase_manager.get_current_phase_state()
        if not phase_state.is_order_cancellation_allowed:
            return False

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

    def execute_batch(self) -> Dict[str, Dict[str, OrderResult]]:
        """Execute batch matching for all instruments.

        This method triggers the matching engine to process any pending
        orders that have been collected. In continuous mode, this is a no-op
        since orders are matched immediately. In batch mode, this processes
        all pending orders with fair randomization.

        Returns
        -------
        Dict[str, Dict[str, OrderResult]]
            Results organized by instrument ID, then order ID.
            Empty dict for continuous mode.

        Notes
        -----
        This method should be called at designated times in the trading
        cycle (e.g., T+3:30 in the game loop). The exact behavior depends
        on the configured matching engine.

        For batch mode:
        - All pending orders are processed simultaneously
        - Orders at the same price are randomized fairly
        - Results include the final status of each order

        Examples
        --------
        >>> # In batch mode
        >>> exchange = ExchangeVenue(BatchMatchingEngine())
        >>> # ... submit multiple orders ...
        >>> results = exchange.execute_batch()
        >>> for instrument_id, instrument_results in results.items():
        ...     for order_id, result in instrument_results.items():
        ...         print(f"Order {order_id}: {result.status}")
        """
        # Get current phase to determine which engine to use
        phase_state = self.phase_manager.get_current_phase_state()

        # Only batch engine has meaningful execute_batch
        if phase_state.execution_style == "batch":
            return self._batch_engine.execute_batch(self.order_books)
        else:
            # Other engines return empty dict
            return {}

    def get_matching_mode(self) -> str:
        """Get the current matching mode of the exchange.

        Returns
        -------
        str
            Either "continuous" or "batch"

        Notes
        -----
        This is useful for strategies or systems that need to adapt their
        behavior based on the matching mode. For example, a strategy might
        submit orders differently if it knows they won't match immediately.

        Examples
        --------
        >>> exchange = ExchangeVenue()
        >>> exchange.get_matching_mode()
        'continuous'
        >>>
        >>> batch_exchange = ExchangeVenue(BatchMatchingEngine())
        >>> batch_exchange.get_matching_mode()
        'batch'
        """
        return self.matching_engine.get_mode()

    def get_current_phase_state(self) -> PhaseState:
        """Get the current market phase state.

        Returns
        -------
        PhaseState
            The current phase state including phase type and operational rules

        Notes
        -----
        This delegates to the phase manager to get the current phase state.
        The phase state determines what operations are allowed at any given time.

        Examples
        --------
        >>> state = exchange.get_current_phase_state()
        >>> if state.is_order_submission_allowed:
        ...     # Submit orders
        >>> if state.phase_type == PhaseType.CLOSED:
        ...     print("Market is closed")
        """
        return self.phase_manager.get_current_phase_state()

    def set_matching_engine(self, matching_engine: MatchingEngine) -> None:
        """Set the matching engine for the exchange.

        This method allows switching between different matching engines,
        typically used for phase transitions (e.g., switching to batch
        mode for opening auction).

        Parameters
        ----------
        matching_engine : MatchingEngine
            The new matching engine to use

        Notes
        -----
        This is primarily used by the PhaseTransitionExecutor to switch
        between continuous and batch matching modes based on market phase.
        """
        self.matching_engine = matching_engine

    def execute_opening_auction(self) -> None:
        """Execute the opening auction batch match.

        This method is called when transitioning from OPENING_AUCTION
        to CONTINUOUS phase. It processes all orders collected during
        pre-open using batch matching to establish fair opening prices.

        Notes
        -----
        This method assumes the exchange is currently using a batch
        matching engine. It executes the batch for all instruments
        and processes the results.

        The opening auction ensures:
        - All crossing orders from pre-open are matched
        - Orders at the same price are randomized fairly
        - Opening prices are established for all traded instruments
        """
        # Execute batch matching for all instruments
        # Use batch engine directly since we're now in continuous phase
        results = self._batch_engine.execute_batch(self.order_books)

        # Log summary of opening auction results
        total_trades = 0
        for instrument_id, instrument_results in results.items():
            trades_for_instrument = sum(
                len(result.fills) for result in instrument_results.values()
            )
            if trades_for_instrument > 0:
                total_trades += trades_for_instrument
                # Could emit opening price events here in the future

        # Log auction completion
        # In a real system, this might publish market data events

    def cancel_all_orders(self) -> None:
        """Cancel all resting orders across all instruments.

        This method is called when the market closes to ensure all
        open orders are cancelled and don't carry over to the next
        trading day.

        Notes
        -----
        This iterates through all order books and cancels every resting
        order. In a real system, this would also notify traders of the
        cancellations.
        """
        cancelled_count = 0

        for instrument_id, order_book in self.order_books.items():
            # Get all order IDs from the book
            all_orders: List[Order] = []

            # Collect all buy orders
            for price_level in order_book.bids:
                all_orders.extend(price_level.orders)

            # Collect all sell orders
            for price_level in order_book.asks:
                all_orders.extend(price_level.orders)

            # Cancel each order
            for order in all_orders:
                if order_book.cancel_order(order.order_id):
                    self.all_order_ids.discard(order.order_id)
                    cancelled_count += 1

        # Log cancellation summary
        # In a real system, this might publish end-of-day events
