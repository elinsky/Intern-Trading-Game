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
from .phase.transition_handler import ExchangePhaseTransitionHandler
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

    Responsibilities
    ---------------

    - Maintain order books for all listed instruments
    - Route orders to appropriate matching engines based on phase
    - Enforce phase-based trading rules (via PhaseManager)
    - Execute opening auctions and market close procedures
    - Provide market data snapshots

    NOT Responsible For
    -------------------

    - Determining market phases (delegated to PhaseManager)
    - Order validation beyond basic checks (delegated to validators)
    - Position tracking (handled by PositionService)
    - Fee calculations (handled by separate fee services)

    SOLID Compliance
    ---------------

    - Single Responsibility: Currently violates SRP by handling both order
      management AND phase transition actions. Future refactoring will extract
      phase transition logic to ExchangePhaseTransitionHandler.
    - Open/Closed: Uses MatchingEngine protocol for extensibility
    - Liskov Substitution: Accepts any PhaseManagerInterface implementation
    - Interface Segregation: Implements focused ExchangeServiceProtocol
    - Dependency Inversion: Depends on abstractions (PhaseManagerInterface,
      MatchingEngine) not concrete implementations

    Parameters
    ----------
    phase_manager : PhaseManagerInterface
        The phase manager that determines market phases and rules.
        Exchange depends on this abstraction, not concrete implementation.
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
    phase_manager : PhaseManagerInterface
        Determines current market phase and operational rules.
    _continuous_engine : ContinuousMatchingEngine
        Engine for immediate order matching during continuous trading.
    _batch_engine : BatchMatchingEngine
        Engine for batch matching during auctions.

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
    - Phase-aware matching (continuous vs batch based on market phase)
    - No circuit breakers or trading halts
    - No fees or commissions at exchange level
    - No position limits or risk checks at exchange level
    - No support for hidden orders, iceberg orders, or other advanced order types
    - All orders can be partially filled
    - No cross-instrument strategies or basket orders

    The exchange automatically selects the appropriate matching engine based
    on the current market phase, supporting both continuous trading and
    auction-based matching.

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
        continuous_engine: Optional[ContinuousMatchingEngine] = None,
        batch_engine: Optional[BatchMatchingEngine] = None,
        matching_engine: Optional[MatchingEngine] = None,
    ):
        """Initialize the exchange venue.

        Parameters
        ----------
        phase_manager : PhaseManagerInterface
            The phase manager that determines market phases and rules
        continuous_engine : ContinuousMatchingEngine, optional
            The engine for continuous trading. If not provided, creates default.
        batch_engine : BatchMatchingEngine, optional
            The engine for batch trading. If not provided, creates default.
        matching_engine : MatchingEngine, optional
            Deprecated: Use continuous_engine and batch_engine instead.
            Maintained for backward compatibility.

        Notes
        -----
        Preferred usage is to provide both continuous_engine and batch_engine
        for explicit dependency injection and better testability:

        >>> exchange = ExchangeVenue(
        ...     phase_manager=manager,
        ...     continuous_engine=ContinuousMatchingEngine(),
        ...     batch_engine=BatchMatchingEngine()
        ... )

        The exchange automatically selects the appropriate engine based on
        the current market phase as determined by the phase manager.
        """
        # Map of instrument IDs to their order books
        self.order_books: Dict[str, OrderBook] = {}

        # Map of instrument IDs to their instrument objects
        self.instruments: Dict[str, Instrument] = {}

        # Set of all order IDs across all books
        self.all_order_ids: Set[str] = set()

        # Phase manager is required for phase-aware operations
        self.phase_manager = phase_manager

        # Initialize engines - use injected engines or create defaults
        self._continuous_engine = (
            continuous_engine or ContinuousMatchingEngine()
        )
        self._batch_engine = batch_engine or BatchMatchingEngine()

        # For backward compatibility, still support old matching_engine param
        self.matching_engine = matching_engine or self._continuous_engine

        # Cache current phase state to avoid repeated lookups
        self._current_phase_state = (
            self.phase_manager.get_current_phase_state()
        )

        # Initialize phase transition handler to automatically execute
        # actions during phase transitions (e.g., opening auction, close)
        self._transition_handler = ExchangePhaseTransitionHandler(
            self, self.phase_manager
        )

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
        if not self._current_phase_state.is_order_submission_allowed:
            return OrderResult(
                order_id=order.order_id,
                status="rejected",
                fills=[],
                remaining_quantity=order.quantity,
                error_message=f"Order submission not allowed during {self._current_phase_state.phase_type.value} phase",
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
        if self._should_use_batch_engine():
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
        if not self._current_phase_state.is_order_cancellation_allowed:
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
        # Only batch engine has meaningful execute_batch
        if self._current_phase_state.execution_style == "batch":
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

    def check_phase_transitions(self) -> None:
        """Check for phase transitions and execute actions if needed.

        This method should be called periodically (e.g., every 100ms) to
        monitor for phase changes and execute appropriate actions like
        opening auctions or market close procedures.

        The method:
        1. Gets the current phase from the phase manager
        2. Updates the cached phase state for use by other methods
        3. Delegates to the transition handler to execute actions

        Notes
        -----
        This is designed to be called from the matching thread's main loop.
        It's safe to call frequently as it only takes action when phases
        actually change.

        Examples
        --------
        >>> # In the matching thread's run loop
        >>> while self.running:
        ...     # Check for phase transitions periodically
        ...     self.exchange.check_phase_transitions()
        ...     # Continue with normal order processing
        ...     self._process_orders()
        """
        # Get current phase from phase manager and update cached state
        new_phase_state = self.phase_manager.get_current_phase_state()
        self._current_phase_state = new_phase_state

        # Let the handler check and execute any needed actions
        self._transition_handler.check_and_handle_transition(
            new_phase_state.phase_type
        )

    def _should_use_batch_engine(self) -> bool:
        """Determine if the batch matching engine should be used.

        Returns
        -------
        bool
            True if batch engine should be used based on current phase state

        Notes
        -----
        Batch engine is used during:
        - Pre-open phase: Orders collected but not matched
        - Opening auction: Orders matched in batch at market open
        - Any phase where matching is disabled

        Continuous engine is used during:
        - Continuous trading: Orders matched immediately
        """
        return (
            self._current_phase_state.execution_style == "batch"
            or not self._current_phase_state.is_matching_enabled
        )
