"""Interfaces for phase management.

This module defines the protocols and interfaces for phase management
components in the exchange domain.
"""

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from ..types import PhaseState, PhaseType


@runtime_checkable
class PhaseManagerInterface(Protocol):
    """Protocol for phase management operations.

    This interface defines the contract that any phase manager must
    implement. It provides methods to determine the current market
    phase based on time and configuration.

    The phase manager is responsible for:
    - Evaluating the current time against the market schedule
    - Determining which phase the market is in
    - Providing the complete phase state with operational rules

    Notes
    -----
    Implementations may use different strategies for phase evaluation:
    - Simple time-based checks against hardcoded schedule
    - Configuration-driven schedule with timezone support
    - External calendar integration for holidays
    - Real-time market status feeds

    The interface is designed to be minimal and focused on the
    essential operations needed by the exchange.

    Examples
    --------
    >>> # Using a phase manager (implementation-agnostic)
    >>> manager: PhaseManagerInterface = get_phase_manager()
    >>> current_phase = manager.get_current_phase_type()
    >>> if current_phase == PhaseType.CONTINUOUS:
    ...     print("Market is open for trading")
    >>>
    >>> # Get full state for exchange operations
    >>> state = manager.get_current_phase_state()
    >>> if state.is_matching_enabled:
    ...     process_order_matching()
    """

    def get_current_phase_type(
        self, current_time: Optional[datetime] = None
    ) -> PhaseType:
        """Determine current phase type based on time.

        Evaluates the provided time (or current time if not specified)
        against the market schedule to determine which phase is active.

        Parameters
        ----------
        current_time : Optional[datetime], default=None
            The time to evaluate. If None, uses current system time.

        Returns
        -------
        PhaseType
            The active market phase at the specified time

        Notes
        -----
        The time parameter supports:
        - Testing with specific times
        - Backtesting with historical dates
        - Preview of upcoming phase changes

        Implementations must handle:
        - Timezone conversions to market timezone
        - Weekend detection
        - Holiday calendars (if configured)

        Examples
        --------
        >>> # Check current phase
        >>> phase = manager.get_current_phase_type()
        >>>
        >>> # Check phase at specific time
        >>> future_time = datetime.now() + timedelta(hours=1)
        >>> future_phase = manager.get_current_phase_type(future_time)
        """
        ...

    def get_current_phase_state(self) -> PhaseState:
        """Get current phase state configuration.

        Returns the complete phase state including the phase type
        and all operational rules. This method always evaluates
        the current time and cannot be called with a custom time.

        Returns
        -------
        PhaseState
            Complete state information for the current phase

        Notes
        -----
        This method is typically called by the exchange to get
        its operational configuration. The returned state includes:
        - Which operations are allowed
        - How order matching should behave
        - Execution style for the phase

        For historical or future phase evaluation, use
        get_current_phase_type() with a specific time.

        Examples
        --------
        >>> state = manager.get_current_phase_state()
        >>> if not state.is_order_submission_allowed:
        ...     reject_order("MARKET_CLOSED")
        >>> elif state.is_matching_enabled:
        ...     match_order_immediately()
        >>> else:
        ...     queue_order_for_opening()
        """
        ...
