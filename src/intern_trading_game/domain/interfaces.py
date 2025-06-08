"""Core interfaces for the Intern Trading Game.

This module defines the abstract base classes that establish
contracts for trading strategies and other pluggable components.
These interfaces ensure clean separation between the game engine
and participant implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .exchange.order import Order
from .exchange.order_result import OrderResult
from .models import MarketData, NewsEvent, Signal, TickPhase


@dataclass
class StrategyAction:
    """Container for all actions a strategy wants to take in a tick.

    Strategies return this object to specify all their trading
    intentions including new orders, quotes, and cancellations.

    Parameters
    ----------
    orders : List[Order]
        New limit/market orders to submit
    quotes : Dict[str, tuple[float, float, int]]
        Two-sided quotes by instrument (bid, ask, size)
    cancel_order_ids : List[str]
        Specific order IDs to cancel
    cancel_all : bool
        Cancel all open orders if True

    Notes
    -----
    All actions are processed atomically at the appropriate
    tick phase. Cancellations are processed before new orders.

    Examples
    --------
    >>> # Submit new orders and update quotes
    >>> action = StrategyAction(
    ...     orders=[Order(...)],
    ...     quotes={"SPX_CALL_5200": (25.50, 25.70, 10)},
    ...     cancel_order_ids=["ORD-123"],
    ...     cancel_all=False
    ... )
    """

    orders: List[Order] = field(default_factory=list)
    quotes: Dict[str, tuple[float, float, int]] = field(default_factory=dict)
    cancel_order_ids: List[str] = field(default_factory=list)
    cancel_all: bool = False


class TradingContext(ABC):
    """Abstract interface for accessing game state and services.

    Provides strategies with read-only access to their positions,
    trade history, and other relevant game state. This ensures
    strategies can make informed decisions while maintaining
    proper encapsulation.

    Notes
    -----
    All methods return copies or immutable views to prevent
    strategies from modifying game state directly.

    Portfolio valuation is intentionally excluded - strategies
    must implement their own option pricing models.
    """

    @abstractmethod
    def get_position(self, instrument: str) -> int:
        """Get current position in an instrument.

        Parameters
        ----------
        instrument : str
            Symbol of the instrument to query

        Returns
        -------
        int
            Current position (positive=long, negative=short)
        """
        pass

    @abstractmethod
    def get_all_positions(self) -> Dict[str, int]:
        """Get all current positions across instruments.

        Returns
        -------
        Dict[str, int]
            Map of instrument symbol to position size
        """
        pass

    @abstractmethod
    def get_open_orders(self) -> List[Order]:
        """Get list of currently open orders.

        Returns
        -------
        List[Order]
            Orders that are resting in the book
        """
        pass

    @abstractmethod
    def get_last_trades(self, n: int = 10) -> List[Dict]:
        """Get recent trades executed by this strategy.

        Parameters
        ----------
        n : int, default=10
            Number of recent trades to return

        Returns
        -------
        List[Dict]
            Recent trades with price, quantity, and timestamp
        """
        pass


class TradingStrategy(ABC):
    """Abstract interface for trading strategy implementations.

    All trading bots must implement this interface to participate
    in the game. The game loop calls these methods at appropriate
    times during each tick cycle, ensuring fair and synchronized
    trading opportunities for all participants.

    Strategies receive a TradingContext object that provides
    access to their current state and positions.

    Notes
    -----
    Strategies operate under strict timing constraints. The
    make_trading_decision method must return within the configured
    bot_timeout_seconds or the strategy forfeits that tick.

    TradingContext
    --------------
    Market Assumptions
        - All strategies receive identical market data
        - Order submission window is T+0:30 to T+3:00
        - Strategies cannot observe other participants' orders

    Trading Rules
        - Must respect role-specific position limits
        - Must use allowed order types for assigned role
        - Orders submitted outside window are rejected

    Examples
    --------
    >>> class SimpleStrategy(TradingStrategy):
    ...     def __init__(self):
    ...         self.pending_signals = []
    ...
    ...     def get_name(self) -> str:
    ...         return "SimpleBot"
    ...
    ...     def make_trading_decision(
    ...         self,
    ...         market_data: MarketData,
    ...         context: TradingContext
    ...     ) -> StrategyAction:
    ...         # Check current position
    ...         spx_pos = context.get_position("SPX")
    ...
    ...         # Simple logic: buy if flat and price drops
    ...         if spx_pos == 0 and market_data.spx_price < 5000:
    ...             return StrategyAction(
    ...                 orders=[Order(...)]  # Buy order
    ...             )
    ...         return StrategyAction()  # No action
    ...
    ...     def on_signal(self, signal: Signal) -> None:
    ...         # Store signal for future use
    ...         self.pending_signals.append(signal)
    ...
    ...     def on_news(self, event: NewsEvent) -> None:
    ...         pass  # Ignore news
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return strategy name for identification and logging.

        Returns
        -------
        str
            Unique name identifying this strategy instance

        Notes
        -----
        Names should be descriptive and unique within a game
        session. They appear in trade logs and leaderboards.
        """
        pass

    @abstractmethod
    def make_trading_decision(
        self, market_data: MarketData, context: TradingContext
    ) -> StrategyAction:
        """Decide all trading actions for this tick.

        Called at T+0:30 each tick with fresh market data and
        access to current positions. The strategy must analyze
        conditions and return all desired trading actions.

        Parameters
        ----------
        market_data : MarketData
            Current tick's prices and order book snapshots
        context : TradingContext
            Interface to query positions and portfolio state

        Returns
        -------
        StrategyAction
            Container with all orders, quotes, and cancellations

        Notes
        -----
        This method has a strict timeout. Strategies that exceed
        bot_timeout_seconds receive no orders for the tick.

        Action validation occurs after return - invalid actions
        are rejected with appropriate error messages.

        Processing order:

        1. Cancel orders (specific IDs or all)
        2. Submit new orders
        3. Post/update quotes

        TradingContext
        --------------
        Market Assumptions
            - Prices in data are firm and tradeable
            - Order books show current resting orders
            - No information about other strategies' intentions

        Trading Rules
            - Orders must be for valid instruments
            - Quantities must respect position limits
            - Order types must be allowed for role
            - Quotes only allowed for market makers
        """
        pass

    def on_signal(self, signal: Signal) -> None:
        """Receive role-specific advance market signals.

        Called when the Event System distributes signals to
        eligible strategies. Default implementation ignores
        signals - override if your role receives them.

        Signals are advance information that strategies typically
        store and act upon in future trading decisions, not
        immediately.

        Parameters
        ----------
        signal : Signal
            Advance information (volatility or tracking error)

        Notes
        -----
        Only specific roles receive signals:
        - Hedge Funds: volatility regime forecasts (1-5 ticks)
        - Arbitrage Desks: tracking error predictions
        - Market Makers: no signals

        Signal accuracy is configurable but typically:
        - Volatility signals: 66% accurate
        - Tracking signals: 80% accurate

        Why no return value? Signals are information to process
        and store, not immediate action triggers. Trading decisions
        based on signals happen later in make_trading_decision()
        when you can combine the signal with current market state.

        TradingContext
        --------------
        Market Assumptions
            - Signals are probabilistic, not guarantees
            - Accuracy measured over long run
            - Timing varies (1-5 ticks advance for volatility)

        Trading Rules
            - Cannot share signals with other players
            - Must not rely solely on signals
            - Should blend with market analysis

        Examples
        --------
        >>> def on_signal(self, signal: Signal) -> None:
        ...     if signal.signal_type == "volatility":
        ...         # Store for future trading decisions
        ...         self.vol_forecasts[signal.tick_horizon] = signal
        """
        pass

    def on_news(self, event: NewsEvent) -> None:
        """React to market news announcements.

        Called when the Event System publishes news that may
        affect market conditions. All strategies receive news
        simultaneously at the announcement time.

        Like signals, news is information to process, not an
        immediate action trigger. Trading based on news happens
        in make_trading_decision().

        Parameters
        ----------
        event : NewsEvent
            Market news that may impact prices/volatility

        Notes
        -----
        News events are generated via Poisson process and may:
        - Trigger volatility regime changes
        - Cause immediate price jumps
        - Be false signals with no impact

        Some strategies may have received advance warning via
        signals, but the news itself is public information.

        TradingContext
        --------------
        Market Assumptions
            - News reflects realistic market events
            - Impact depends on current market state
            - Markets may take time to fully react

        Trading Rules
            - All players see news simultaneously
            - Cannot trade on news before announcement
            - Should consider news in context
        """
        pass


@dataclass
class ValidationContext:
    """Context information needed for order validation.

    Contains all the state and metadata required to validate an order
    against the configured constraints. This allows validators to make
    decisions based on current positions, order rates, and other factors.

    Parameters
    ----------
    order : Order
        The order being validated
    trader_id : str
        ID of the trader submitting the order
    trader_role : str
        Role of the trader (determines which constraints apply)
    tick_phase : TickPhase
        Current phase of the trading tick
    current_positions : Dict[str, int]
        Current positions by instrument_id (positive=long, negative=short)
    orders_this_tick : int
        Number of orders already submitted by this trader in current tick
    metadata : Dict[str, Any]
        Additional context that may be needed by custom constraints

    Notes
    -----
    This context object is passed to all constraint validators, allowing
    them to make decisions based on the full trading state without
    needing direct access to services.

    The positions dictionary only includes instruments with non-zero
    positions to minimize memory usage.
    """

    order: Order
    trader_id: str
    trader_role: str
    tick_phase: "TickPhase"
    current_positions: Dict[str, int] = field(default_factory=dict)
    orders_this_tick: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderValidator(ABC):
    """Abstract interface for order validation.

    The OrderValidator is responsible for checking all orders against
    configurable constraints before they reach the exchange. It enforces
    trading rules without any hardcoded role-specific logic.

    All validation rules are expressed as generic constraints that can
    be configured differently per role through configuration files.

    Notes
    -----
    The validator is designed to be role-agnostic. It understands
    constraint types (position limits, order sizes) but has no
    knowledge of specific roles (market maker, hedge fund).

    Validation follows a fail-fast approach where the first constraint
    violation immediately rejects the order with a specific error.

    TradingContext
    --------------
    Market Assumptions
        - Orders must be validated before exchange submission
        - Validation rules can vary by role but use same constraint types
        - Position limits are enforced pre-trade

    Trading Rules
        - Trading window constraints apply to all roles
        - Each role may have different position and order limits
        - Validation errors provide clear feedback
    """

    @abstractmethod
    def validate_order(self, context: ValidationContext) -> "OrderResult":
        """Validate an order against all configured constraints.

        Parameters
        ----------
        context : ValidationContext
            Context containing the order and all state needed for validation

        Returns
        -------
        OrderResult
            Result indicating acceptance or rejection with details

        Notes
        -----
        Validation is performed sequentially with early exit on first
        failure. The order of constraint checking may affect performance
        but not correctness.

        The context contains all necessary information including:
        - The order to validate
        - Current trader positions
        - Orders submitted this tick
        - Current tick phase
        - Trader role for loading constraints
        """
        pass
