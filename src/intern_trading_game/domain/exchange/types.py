"""Common types and enums for the exchange module.

This module contains shared types used across the exchange components
to avoid circular imports.
"""

from dataclasses import dataclass
from enum import Enum


class LiquidityType(str, Enum):
    """Liquidity type for trade execution.

    Indicates whether an order added or removed liquidity from the
    order book, which affects fee calculations and rebates.

    Attributes
    ----------
    MAKER : str
        Order added liquidity (posted to book and waited)
    TAKER : str
        Order removed liquidity (crossed the spread immediately)

    Notes
    -----
    Liquidity classification follows standard exchange conventions:
    - Maker orders provide liquidity by posting limit orders
    - Taker orders consume liquidity by crossing the spread
    - Market orders are always takers
    - Limit orders can be either, depending on price

    Fee structures typically favor makers with rebates and charge
    takers fees to incentivize liquidity provision.

    TradingContext
    --------------
    Market Assumptions
        - Maker rebates incentivize tight spreads
        - Taker fees fund the rebate pool
        - Classification happens at execution time

    Trading Rules
        - Market orders always pay taker fees
        - Limit orders at marketable prices are takers
        - Limit orders that post to book are makers

    Examples
    --------
    >>> # Limit order that posts to book
    >>> order = Order(side="buy", price=127.50, ...)  # Below ask
    >>> # This becomes a MAKER when it rests in book

    >>> # Market order that executes immediately
    >>> order = Order(order_type="market", ...)
    >>> # This is always a TAKER
    """

    MAKER = "maker"
    TAKER = "taker"


class PhaseType(str, Enum):
    """Market phase types for the trading system.

    These phases control when and how orders can be submitted and matched.

    Attributes
    ----------
    PRE_OPEN : str
        Market is preparing to open. Orders accepted but not matched.
    CONTINUOUS : str
        Normal trading hours. Orders accepted and matched immediately.
    CLOSED : str
        Market is closed. No orders accepted.

    Notes
    -----
    The exchange operates in one of these three phases at all times.
    Phase transitions are based on configured market hours and days.

    Each phase has specific rules for order handling:
    - PRE_OPEN: Accept orders, queue for opening
    - CONTINUOUS: Accept orders, match immediately
    - CLOSED: Reject all orders

    Examples
    --------
    >>> phase = PhaseType.CONTINUOUS
    >>> if phase == PhaseType.CLOSED:
    ...     print("Market is closed")
    ... else:
    ...     print(f"Market phase: {phase.value}")
    Market phase: continuous
    """

    PRE_OPEN = "pre_open"
    CONTINUOUS = "continuous"
    CLOSED = "closed"


@dataclass
class PhaseState:
    """Complete state information for a market phase.

    This dataclass combines the phase type with its operational rules,
    defining exactly what operations are allowed and how the exchange
    should behave.

    Attributes
    ----------
    phase_type : PhaseType
        The type of market phase
    is_order_submission_allowed : bool
        Whether new orders can be submitted
    is_order_cancellation_allowed : bool
        Whether existing orders can be cancelled
    is_matching_enabled : bool
        Whether order matching should occur
    execution_style : str
        How orders are executed ("none", "continuous", "batch")

    Notes
    -----
    PhaseState acts as the exchange's operational configuration,
    determining its behavior at any point in time. The state is
    typically derived from the current time and market schedule.

    The execution_style field supports future expansion:
    - "none": No execution (pre-open, closed)
    - "continuous": Immediate matching (normal trading)
    - "batch": Periodic auctions (future feature)

    Examples
    --------
    >>> # Pre-open state
    >>> state = PhaseState(
    ...     phase_type=PhaseType.PRE_OPEN,
    ...     is_order_submission_allowed=True,
    ...     is_order_cancellation_allowed=True,
    ...     is_matching_enabled=False,
    ...     execution_style="none"
    ... )
    >>> if state.is_order_submission_allowed and not state.is_matching_enabled:
    ...     print("Orders accepted but held for opening")
    Orders accepted but held for opening
    """

    phase_type: PhaseType
    is_order_submission_allowed: bool
    is_order_cancellation_allowed: bool
    is_matching_enabled: bool
    execution_style: str

    @classmethod
    def from_phase_type(cls, phase_type: PhaseType, config) -> "PhaseState":
        """Create PhaseState from phase type and configuration.

        Factory method that creates a PhaseState using the provided
        phase type and configuration settings.

        Parameters
        ----------
        phase_type : PhaseType
            The phase type to create state for
        config : PhaseStateConfig
            Configuration with the phase rules

        Returns
        -------
        PhaseState
            A new PhaseState instance with configured rules

        Notes
        -----
        This factory method allows the phase rules to be driven by
        configuration rather than hardcoded, supporting different
        market structures and testing scenarios.

        Examples
        --------
        >>> from intern_trading_game.infrastructure.config.models import PhaseStateConfig
        >>> config = PhaseStateConfig(
        ...     is_order_submission_allowed=True,
        ...     is_order_cancellation_allowed=True,
        ...     is_matching_enabled=True,
        ...     execution_style="continuous"
        ... )
        >>> state = PhaseState.from_phase_type(PhaseType.CONTINUOUS, config)
        >>> state.execution_style
        'continuous'
        """
        return cls(
            phase_type=phase_type,
            is_order_submission_allowed=config.is_order_submission_allowed,
            is_order_cancellation_allowed=config.is_order_cancellation_allowed,
            is_matching_enabled=config.is_matching_enabled,
            execution_style=config.execution_style,
        )
