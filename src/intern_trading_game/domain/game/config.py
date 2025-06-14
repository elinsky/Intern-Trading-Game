"""Game configuration for trading sessions.

This module defines configuration parameters that control game timing,
trading schedule, and session behavior.
"""

from dataclasses import dataclass, field
from datetime import time
from typing import List


@dataclass
class GameConfig:
    """Configuration parameters for a trading game session.

    Defines the operational parameters that control game timing,
    trading schedule, and session behavior in the continuous
    trading environment.

    Parameters
    ----------
    session_name : str
        Unique identifier for this game session
    trading_days : List[str], default=["Tuesday", "Thursday"]
        Days of week when trading occurs
    market_open : time, default=time(9, 30)
        Market opening time in CT (Central Time)
    market_close : time, default=time(15, 0)
        Market closing time in CT
    enable_volatility_events : bool, default=True
        Whether to generate volatility regime changes
    enable_news_events : bool, default=True
        Whether to generate market news events
    bot_timeout_seconds : float, default=10.0
        Maximum time allowed for bot response

    Notes
    -----
    Standard market hours (9:30 AM - 3:00 PM CT) provide 5.5 hours
    of regular trading time. The system operates continuously
    during market hours with real-time order matching.

    Bot timeout ensures system responsiveness - strategies that exceed
    the timeout may have orders rejected.

    TradingContext
    --------------
    Market Assumptions
        - Continuous trading during market hours
        - All strategies operate under same schedule
        - Market hours reflect equity market standards

    Trading Rules
        - No trading outside defined market hours
        - Real-time order matching when market is open
        - Bots must respond within timeout

    Examples
    --------
    >>> config = GameConfig(
    ...     session_name="training_session_1",
    ...     bot_timeout_seconds=5.0  # Faster for testing
    ... )
    >>> print(f"Session: {config.session_name}")
    Session: training_session_1
    """

    session_name: str
    trading_days: List[str] = field(
        default_factory=lambda: ["Tuesday", "Thursday"]
    )
    market_open: time = time(9, 30)
    market_close: time = time(15, 0)
    enable_volatility_events: bool = True
    enable_news_events: bool = True
    bot_timeout_seconds: float = 10.0
