"""Position management service for thread-safe position tracking.

This module provides centralized position management with proper
thread synchronization for the multi-threaded trading system.
"""

import threading
from typing import Dict


class PositionManagementService:
    """Service for managing trading positions with thread safety.

    This service provides thread-safe position tracking and updates,
    ensuring data consistency across multiple threads in the trading
    system. It owns and encapsulates all position state internally
    with proper locking mechanisms.

    The service maintains positions as a nested dictionary structure
    where positions[team_id][instrument_id] = position_quantity.

    Attributes
    ----------
    _positions : Dict[str, Dict[str, int]]
        Internal positions dictionary (team_id -> instrument -> quantity)
    _lock : threading.RLock
        Internal lock for thread-safe access

    Notes
    -----
    This service owns position state internally, following the same
    pattern as OrderValidationService with rate limiting. All operations
    acquire the lock to ensure consistency when multiple threads read
    or update positions.

    The service uses an RLock (reentrant lock) which allows the same
    thread to acquire the lock multiple times, preventing deadlocks
    in nested function calls.

    TradingContext
    --------------
    Position tracking is critical for risk management and compliance:
    - Enforces position limits before order submission
    - Updates positions atomically after trade execution
    - Provides consistent view for P&L calculations
    - Supports real-time risk monitoring

    The thread-safe design ensures position integrity even under
    high-frequency trading scenarios with concurrent operations.

    Examples
    --------
    >>> # Initialize service (state managed internally)
    >>> position_service = PositionManagementService()
    >>>
    >>> # Update position after a trade
    >>> position_service.update_position("TEAM001", "SPX-CALL-4500", 10)
    >>>
    >>> # Get current positions for risk check
    >>> team_positions = position_service.get_positions("TEAM001")
    >>> print(team_positions)  # {"SPX-CALL-4500": 10}
    """

    def __init__(self):
        """Initialize the position management service.

        Creates internal state for position tracking with thread-safe
        access. No external dependencies required.
        """
        self._positions: Dict[str, Dict[str, int]] = {}
        self._lock = threading.RLock()

    def update_position(
        self, team_id: str, instrument_id: str, delta: int
    ) -> None:
        """Update a team's position in an instrument.

        Atomically updates the position by adding the delta to the
        current position. Initializes the position to zero if it
        doesn't exist.

        Parameters
        ----------
        team_id : str
            The team identifier
        instrument_id : str
            The instrument identifier
        delta : int
            Change in position (positive for buy, negative for sell)

        Notes
        -----
        The update is atomic - no other thread can read or modify
        positions while this operation is in progress.

        Position initialization is handled automatically:
        - If team has no positions, creates team entry
        - If instrument position doesn't exist, starts at 0

        TradingContext
        --------------
        Position updates must be atomic to prevent:
        - Race conditions between validation and execution
        - Inconsistent position states during batch processing
        - Double-counting in multi-fill scenarios

        Examples
        --------
        >>> # Buy 10 contracts
        >>> position_service.update_position("TEAM001", "SPX-CALL", 10)
        >>>
        >>> # Sell 5 contracts
        >>> position_service.update_position("TEAM001", "SPX-CALL", -5)
        >>>
        >>> # Net position is now 5
        """
        with self._lock:
            # Initialize team positions if needed
            if team_id not in self._positions:
                self._positions[team_id] = {}

            # Initialize instrument position if needed
            if instrument_id not in self._positions[team_id]:
                self._positions[team_id][instrument_id] = 0

            # Update position
            self._positions[team_id][instrument_id] += delta

    def get_positions(self, team_id: str) -> Dict[str, int]:
        """Get all positions for a team.

        Returns a copy of the team's positions to prevent external
        modification of the internal state.

        Parameters
        ----------
        team_id : str
            The team identifier

        Returns
        -------
        Dict[str, int]
            Copy of positions by instrument (empty dict if no positions)

        Notes
        -----
        Returns a copy to ensure thread safety - callers cannot
        modify the internal positions dictionary directly.

        TradingContext
        --------------
        Position snapshots are used for:
        - Pre-trade validation checks
        - Real-time P&L calculations
        - Risk monitoring dashboards
        - End-of-day reconciliation

        Examples
        --------
        >>> positions = position_service.get_positions("TEAM001")
        >>> total_risk = sum(abs(pos) for pos in positions.values())
        """
        with self._lock:
            return self._positions.get(team_id, {}).copy()

    def get_position_for_instrument(
        self, team_id: str, instrument_id: str
    ) -> int:
        """Get position for a specific instrument.

        Returns the current position quantity for a team in a
        specific instrument.

        Parameters
        ----------
        team_id : str
            The team identifier
        instrument_id : str
            The instrument identifier

        Returns
        -------
        int
            Current position (0 if no position exists)

        Notes
        -----
        Returns 0 for non-existent positions rather than raising
        an error, following the convention that no position equals
        zero position.

        TradingContext
        --------------
        Single instrument queries are common for:
        - Order validation (checking position limits)
        - Calculating available trading capacity
        - Hedging calculations
        - Position-specific risk metrics

        Examples
        --------
        >>> pos = position_service.get_position_for_instrument(
        ...     "TEAM001", "SPX-CALL-4500"
        ... )
        >>> remaining_capacity = position_limit - abs(pos)
        """
        with self._lock:
            if team_id in self._positions:
                return self._positions[team_id].get(instrument_id, 0)
            return 0

    def initialize_team(self, team_id: str) -> None:
        """Initialize position tracking for a new team.

        Creates an empty position dictionary for a team if it
        doesn't already exist.

        Parameters
        ----------
        team_id : str
            The team identifier to initialize

        Notes
        -----
        This method is idempotent - calling it multiple times
        for the same team has no effect after the first call.

        TradingContext
        --------------
        Called during team registration to ensure position
        tracking is ready before the team starts trading.

        Examples
        --------
        >>> # During team registration
        >>> position_service.initialize_team("TEAM001")
        """
        with self._lock:
            if team_id not in self._positions:
                self._positions[team_id] = {}

    def get_total_absolute_position(self, team_id: str) -> int:
        """Calculate total absolute position across all instruments.

        Sums the absolute values of all positions for portfolio-level
        risk calculations.

        Parameters
        ----------
        team_id : str
            The team identifier

        Returns
        -------
        int
            Sum of absolute position values

        Notes
        -----
        Used for portfolio-level position limit checks where the
        total risk across all instruments is constrained.

        TradingContext
        --------------
        Portfolio-level constraints ensure teams don't concentrate
        too much risk, even if individual positions are within limits.

        This metric is used for:
        - Portfolio position limit validation
        - Margin calculations
        - Risk-based capital requirements

        Examples
        --------
        >>> # Team with mixed long/short positions
        >>> # SPX-CALL: +30, SPX-PUT: -20, SPY-CALL: +10
        >>> total = position_service.get_total_absolute_position("TEAM001")
        >>> assert total == 60  # |30| + |-20| + |10|
        """
        with self._lock:
            team_positions = self._positions.get(team_id, {})
            return sum(abs(pos) for pos in team_positions.values())
