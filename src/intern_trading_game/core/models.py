"""Core data models for the Intern Trading Game.

This module defines the fundamental data structures used throughout
the game simulation, including market data distribution, game
configuration, and timing controls.
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Dict, List

from ..exchange.order_book import OrderBook


class TickPhase(Enum):
    """Enumeration of tick phases within a 5-minute trading cycle.

    Each tick follows a strict sequence of phases that control when
    different game activities occur. The tuple values represent
    (minutes, seconds) offset from tick start.

    Attributes
    ----------
    PRICE_PUBLICATION : tuple[int, int]
        T+0:00 - New underlying prices published
    ORDER_WINDOW_OPEN : tuple[int, int]
        T+0:30 - Trading strategies can submit orders
    ORDER_WINDOW_CLOSE : tuple[int, int]
        T+3:00 - No new orders accepted after this point
    BATCH_MATCHING : tuple[int, int]
        T+3:30 - Exchange processes all orders
    TICK_END : tuple[int, int]
        T+5:00 - Tick completes, prepare for next tick

    TradingContext
    --------------
    Market Assumptions
        - All participants receive price updates simultaneously
        - Order submission fairness via random queue position
        - No latency advantages between participants

    Trading Rules
        - Orders submitted outside window are rejected
        - Unfilled limit orders persist across ticks
        - Position limits checked at order submission
        - Bot response time limited to maintain game clock
    """

    PRICE_PUBLICATION = (0, 0)
    ORDER_WINDOW_OPEN = (0, 30)
    ORDER_WINDOW_CLOSE = (3, 0)
    BATCH_MATCHING = (3, 30)
    TICK_END = (5, 0)

    @property
    def total_seconds(self) -> int:
        """Convert phase timing to seconds from tick start."""
        minutes, seconds = self.value
        return minutes * 60 + seconds


@dataclass
class MarketData:
    """Public market information distributed to all strategies.

    Contains price and order book information that all participants
    receive simultaneously at the start of each tick. This ensures
    fair access to market information.

    Parameters
    ----------
    tick : int
        Current tick number (0-indexed)
    timestamp : datetime
        Real-world time of tick start
    spx_price : float
        S&P 500 index price for this tick
    spy_price : float
        SPDR S&P 500 ETF price for this tick
    order_book_snapshots : Dict[str, OrderBook]
        Current state of order books by instrument symbol

    Notes
    -----
    The SPX/SPY correlation is maintained at approximately 0.98 with
    tracking error modeled as:

    $SPY_t = \\frac{SPX_t}{10} + \\epsilon_t$

    where $\\epsilon_t \\sim N(0, \\sigma_{tracking}^2)$

    TradingContext
    --------------
    Market Assumptions
        - Prices reflect fair value at publication time
        - Order book snapshots are point-in-time accurate
        - All strategies receive identical market data

    Trading Rules
        - Market data published at T+0:00 each tick
        - Order books show 5 levels of depth
        - No hidden orders or reserve quantities

    Examples
    --------
    >>> data = MarketData(
    ...     tick=42,
    ...     timestamp=datetime(2024, 3, 21, 10, 30, 0),
    ...     spx_price=5234.50,
    ...     spy_price=523.15,
    ...     order_book_snapshots={}
    ... )
    >>> print(f"Tick {data.tick}: SPX={data.spx_price}")
    Tick 42: SPX=5234.5
    """

    tick: int
    timestamp: datetime
    spx_price: float
    spy_price: float
    order_book_snapshots: Dict[str, OrderBook]


@dataclass
class Signal:
    """Role-specific advance information for eligible strategies.

    Represents predictive signals distributed by the Event System
    to specific trading roles. Signal accuracy and timing vary by
    role type as configured in game parameters.

    Parameters
    ----------
    signal_type : str
        Type of signal ("volatility" or "tracking_error")
    tick_horizon : int
        Number of ticks in advance (1-5 for volatility)
    data : Dict[str, float]
        Signal-specific data payload
    accuracy : float
        Configured accuracy rate for this signal type

    Notes
    -----
    Volatility signals contain transition probabilities:
    - P(Low), P(Medium), P(High) summing to 1.0

    Tracking error signals contain:
    - Expected deviation magnitude and direction

    TradingContext
    --------------
    Market Assumptions
        - Signals represent probabilistic forecasts
        - Accuracy reflects long-run hit rate
        - No guarantee on individual predictions

    Trading Rules
        - Hedge funds receive volatility signals
        - Arbitrage desks receive tracking signals
        - Market makers receive no advance signals

    Examples
    --------
    >>> vol_signal = Signal(
    ...     signal_type="volatility",
    ...     tick_horizon=3,
    ...     data={"low": 0.2, "medium": 0.5, "high": 0.3},
    ...     accuracy=0.66
    ... )
    >>> print(f"Volatility forecast: {vol_signal.data}")
    Volatility forecast: {'low': 0.2, 'medium': 0.5, 'high': 0.3}
    """

    signal_type: str
    tick_horizon: int
    data: Dict[str, float]
    accuracy: float


@dataclass
class NewsEvent:
    """Market news event affecting prices or volatility.

    Represents significant market events generated by the Event
    System via Poisson process. Events may move prices, change
    volatility regimes, or be false signals.

    Parameters
    ----------
    event_id : str
        Unique identifier for this event
    event_type : str
        Category: "regime_shift", "price_jump", "false_signal"
    description : str
        Human-readable event description
    impact_magnitude : float
        Size of potential market impact
    tick_announced : int
        When event becomes public

    Notes
    -----
    Event generation follows Poisson process with configurable
    rate (typically λ=1 per 1-4 hours). Event type probabilities
    are configurable in game parameters.

    TradingContext
    --------------
    Market Assumptions
        - News reflects real market conditions
        - Impact varies with current volatility
        - Market digests news over multiple ticks

    Trading Rules
        - All players see news simultaneously
        - Some roles get advance warning via signals
        - News may or may not move markets

    Examples
    --------
    >>> event = NewsEvent(
    ...     event_id="NEWS-001",
    ...     event_type="regime_shift",
    ...     description="Fed announces rate decision",
    ...     impact_magnitude=0.02,
    ...     tick_announced=45
    ... )
    >>> print(f"Breaking: {event.description}")
    Breaking: Fed announces rate decision
    """

    event_id: str
    event_type: str
    description: str
    impact_magnitude: float
    tick_announced: int


@dataclass
class GameConfig:
    """Configuration parameters for a trading game session.

    Defines the operational parameters that control game timing,
    trading schedule, and session behavior. These settings ensure
    consistent gameplay across all participants.

    Parameters
    ----------
    session_name : str
        Unique identifier for this game session
    tick_duration_seconds : int, default=300
        Duration of each tick in seconds (5 minutes)
    trading_days : List[str], default=["Tuesday", "Thursday"]
        Days of week when trading occurs
    market_open : time, default=time(9, 30)
        Market opening time in CT (Central Time)
    market_close : time, default=time(15, 0)
        Market closing time in CT
    total_ticks : int, default=390
        Total ticks in a session (65 per day * 6 days)
    enable_volatility_events : bool, default=True
        Whether to generate volatility regime changes
    enable_news_events : bool, default=True
        Whether to generate market news events
    bot_timeout_seconds : float, default=10.0
        Maximum time allowed for bot response

    Attributes
    ----------
    ticks_per_hour : int
        Calculated as 3600 / tick_duration_seconds
    ticks_per_day : int
        Calculated based on market hours

    Notes
    -----
    Standard market hours (9:30 AM - 3:00 PM CT) provide 5.5 hours
    of trading time, which at 5-minute ticks yields:

    $\\text{ticks per day} = \\frac{5.5 \\times 60}{5} = 66$

    We use 65 ticks to account for opening/closing procedures.

    Bot timeout ensures game clock stability - strategies that exceed
    the timeout receive no orders for that tick.

    TradingContext
    --------------
    Market Assumptions
        - Consistent tick timing ensures fair play
        - All strategies operate under same schedule
        - Market hours reflect equity market standards

    Trading Rules
        - No trading outside defined market hours
        - Tick duration cannot be modified mid-session
        - Bots must respond within timeout or forfeit turn

    Examples
    --------
    >>> config = GameConfig(
    ...     session_name="training_session_1",
    ...     total_ticks=130,  # Two days only
    ...     bot_timeout_seconds=5.0  # Faster for testing
    ... )
    >>> print(f"Session: {config.session_name}")
    Session: training_session_1
    >>> print(f"Ticks per hour: {config.ticks_per_hour}")
    Ticks per hour: 12
    """

    session_name: str
    tick_duration_seconds: int = 300
    trading_days: List[str] = field(
        default_factory=lambda: ["Tuesday", "Thursday"]
    )
    market_open: time = time(9, 30)
    market_close: time = time(15, 0)
    total_ticks: int = 390
    enable_volatility_events: bool = True
    enable_news_events: bool = True
    bot_timeout_seconds: float = 10.0

    @property
    def ticks_per_hour(self) -> int:
        """Calculate ticks per hour based on duration."""
        return 3600 // self.tick_duration_seconds

    @property
    def ticks_per_day(self) -> int:
        """Calculate ticks per trading day."""
        # Market hours in seconds
        market_seconds = (
            self.market_close.hour * 3600
            + self.market_close.minute * 60
            - self.market_open.hour * 3600
            - self.market_open.minute * 60
        )
        return market_seconds // self.tick_duration_seconds
