"""Phase manager implementation.

This module provides a configuration-driven phase manager that determines
market phases based on time and schedule configuration.
"""

from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from ..components.core.types import PhaseState, PhaseType


class ConfigDrivenPhaseManager:
    """Configuration-driven implementation of phase management.

    This phase manager uses configuration to determine market phases
    based on schedules and rules. It supports timezone-aware operations
    and configurable trading days.

    Attributes
    ----------
    config : MarketPhasesConfig
        The market phases configuration
    market_tz : ZoneInfo
        The market timezone for schedule evaluation

    Notes
    -----
    The manager evaluates phases based on:
    1. Current time converted to market timezone
    2. Day of week checking against configured weekdays
    3. Time of day checking against phase schedules
    4. Default to CLOSED if no active phase found

    The implementation assumes:
    - Phase schedules don't overlap
    - All times are evaluated in market timezone
    - Naive datetimes are treated as market timezone

    Examples
    --------
    >>> from intern_trading_game.infrastructure.config.models import MarketPhasesConfig
    >>> config = load_market_phases_config()
    >>> manager = ConfigDrivenPhaseManager(config)
    >>> current_phase = manager.get_current_phase_type()
    >>> print(f"Market is {current_phase.value}")
    Market is continuous
    """

    def __init__(self, config):
        """Initialize phase manager with configuration.

        Parameters
        ----------
        config : MarketPhasesConfig
            The market phases configuration containing timezone,
            schedules, and phase state definitions
        """
        self.config = config
        self.market_tz = ZoneInfo(config.timezone)

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
        The method follows this logic:
        1. Convert time to market timezone
        2. Check if it's a configured trading day
        3. Check time against each phase schedule
        4. Return CLOSED if no phase matches

        Naive datetimes are assumed to be in market timezone.

        Examples
        --------
        >>> # Check current phase
        >>> phase = manager.get_current_phase_type()
        >>>
        >>> # Check phase at specific time
        >>> from datetime import datetime
        >>> future_time = datetime(2024, 1, 8, 10, 0)
        >>> future_phase = manager.get_current_phase_type(future_time)
        """
        # Get current time if not provided
        if current_time is None:
            current_time = datetime.now(tz=self.market_tz)

        # Convert to market timezone if needed
        if current_time.tzinfo is None:
            # Naive datetime - assume market timezone
            market_time = current_time.replace(tzinfo=self.market_tz)
        else:
            # Convert to market timezone
            market_time = current_time.astimezone(self.market_tz)

        # Get day of week name
        weekday_name = market_time.strftime("%A")

        # Check each phase schedule
        for phase_name, schedule in self.config.schedule.items():
            # Check if today is a trading day for this phase
            if weekday_name not in schedule.weekdays:
                continue

            # Parse schedule times
            start_time = time.fromisoformat(schedule.start_time)
            end_time = time.fromisoformat(schedule.end_time)

            # Check if current time is within schedule
            current_time_only = market_time.time()
            if start_time <= current_time_only < end_time:
                # Map phase name to PhaseType enum
                return PhaseType(phase_name)

        # Default to CLOSED if no phase matches
        return PhaseType.CLOSED

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
        This method:
        1. Determines current phase type using current time
        2. Looks up phase state configuration
        3. Creates PhaseState with operational rules

        Examples
        --------
        >>> state = manager.get_current_phase_state()
        >>> if not state.is_order_submission_allowed:
        ...     print("Market is closed for orders")
        >>> elif state.is_matching_enabled:
        ...     print("Orders will be matched immediately")
        """
        # Get current phase type
        phase_type = self.get_current_phase_type()

        # Get configuration for this phase
        phase_config = self.config.phase_states[phase_type.value]

        # Create phase state from configuration
        return PhaseState.from_phase_type(phase_type, phase_config)
