"""Trading signals for role-specific strategies.

This module defines the Signal data structure used to distribute
predictive information to eligible trading roles.
"""

from dataclasses import dataclass
from typing import Dict


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
    horizon_minutes : int
        Number of minutes in advance (5-25 for volatility)
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
    ...     horizon_minutes=15,
    ...     data={"low": 0.2, "medium": 0.5, "high": 0.3},
    ...     accuracy=0.66
    ... )
    >>> print(f"Volatility forecast: {vol_signal.data}")
    Volatility forecast: {'low': 0.2, 'medium': 0.5, 'high': 0.3}
    """

    signal_type: str
    horizon_minutes: int
    data: Dict[str, float]
    accuracy: float
