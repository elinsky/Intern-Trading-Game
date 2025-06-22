"""Phase transition handler for the exchange.

This module implements the ExchangePhaseTransitionHandler that monitors
phase changes and executes appropriate actions like opening auctions
and order cancellations.
"""

from typing import Callable, Dict, Optional, Tuple

from intern_trading_game.domain.exchange.phase.protocols import (
    ExchangeOperations,
)
from intern_trading_game.domain.exchange.types import PhaseType


class ExchangePhaseTransitionHandler:
    """Handles phase transitions and executes appropriate exchange actions.

    This handler monitors changes in market phases and automatically
    executes required actions when specific transitions occur. It follows
    the principle of separation of concerns - the PhaseManager knows WHEN
    phases change, while this handler knows WHAT to do when they change.

    The handler executes actions during phase transitions:

    - PRE_OPEN -> OPENING_AUCTION: Executes opening auction during the auction window
    - CONTINUOUS -> CLOSED: Cancels all resting orders at market close

    Attributes
    ----------
    _exchange : ExchangeOperations
        The exchange operations interface for executing actions
    _last_phase : Optional[PhaseType]
        The last known phase, used to detect transitions
    _transition_actions : Dict[Tuple[PhaseType, PhaseType], Callable]
        Dispatch table mapping phase transitions to their actions

    Notes
    -----
    The handler is designed to be called periodically (e.g., every 100ms)
    from the exchange's matching thread. It detects phase changes by
    comparing the current phase with the last known phase.

    The opening auction executes during the OPENING_AUCTION phase rather
    than on transition to CONTINUOUS. This ensures:

    - The auction completes before continuous trading begins
    - No race conditions with incoming orders
    - Fair opening prices are established before market opens

    SOLID Compliance
    ----------------

    - Single Responsibility: Only handles phase transition actions
    - Open/Closed: New transitions can be added to dispatch table
    - Liskov Substitution: Works with any ExchangeOperations implementation
    - Interface Segregation: Depends only on minimal ExchangeOperations
    - Dependency Inversion: Depends on protocol, not concrete implementation

    Examples
    --------
    >>> # Create handler with exchange operations
    >>> exchange = ExchangeVenue(phase_manager)
    >>> handler = ExchangePhaseTransitionHandler(exchange)
    >>>
    >>> # Check for phase transitions periodically
    >>> current_phase = phase_manager.get_current_phase_state().phase_type
    >>> transition_occurred = handler.check_and_handle_transition(current_phase)
    >>>
    >>> # Direct transition handling (for testing)
    >>> handler.handle_transition(PhaseType.PRE_OPEN, PhaseType.OPENING_AUCTION)
    """

    def __init__(self, exchange_operations: ExchangeOperations) -> None:
        """Initialize the phase transition handler.

        Parameters
        ----------
        exchange_operations : ExchangeOperations
            The exchange operations interface for executing actions
        """
        self._exchange = exchange_operations
        self._last_phase: Optional[PhaseType] = None

        # Dispatch table for phase transitions
        # Maps (from_phase, to_phase) -> action method
        self._transition_actions: Dict[
            Tuple[PhaseType, PhaseType], Callable[[], None]
        ] = {
            (
                PhaseType.PRE_OPEN,
                PhaseType.OPENING_AUCTION,
            ): self._on_enter_auction,
            (PhaseType.CONTINUOUS, PhaseType.CLOSED): self._on_market_close,
        }

    def check_and_handle_transition(self, current_phase: PhaseType) -> bool:
        """Check for phase transition and execute action if needed.

        This is the main method called periodically to monitor phase
        changes. On first call, it records the initial phase. On
        subsequent calls, it detects transitions and executes any
        associated actions.

        Parameters
        ----------
        current_phase : PhaseType
            The current market phase

        Returns
        -------
        bool
            True if a phase transition occurred, False otherwise

        Notes
        -----
        The first call to this method will always return False as it
        needs to establish the initial phase state. Subsequent calls
        will detect transitions by comparing with the last known phase.

        Examples
        --------
        >>> # In the exchange's matching thread
        >>> while running:
        ...     current_phase = phase_manager.get_current_phase_state().phase_type
        ...     if handler.check_and_handle_transition(current_phase):
        ...         logger.info(f"Phase transition handled: {current_phase}")
        """
        # First call - just record the phase
        if self._last_phase is None:
            self._last_phase = current_phase
            return False

        # Check if phase changed
        if self._last_phase == current_phase:
            return False  # No transition

        # Phase transition detected
        from_phase = self._last_phase
        to_phase = current_phase
        self._last_phase = current_phase

        # Execute any action for this transition
        self.handle_transition(from_phase, to_phase)

        return True

    def handle_transition(
        self, from_phase: PhaseType, to_phase: PhaseType
    ) -> None:
        """Execute action for a specific phase transition.

        This method can be called directly to trigger transition actions,
        primarily useful for testing. It looks up the transition in the
        dispatch table and executes the associated action if found.

        Parameters
        ----------
        from_phase : PhaseType
            The phase transitioning from
        to_phase : PhaseType
            The phase transitioning to

        Notes
        -----
        This method is stateless regarding transitions - calling it
        multiple times with the same transition will execute the action
        multiple times. The exchange is responsible for ensuring
        idempotency if needed.

        Examples
        --------
        >>> # Direct invocation (mainly for testing)
        >>> handler.handle_transition(
        ...     PhaseType.PRE_OPEN,
        ...     PhaseType.OPENING_AUCTION
        ... )
        """
        transition = (from_phase, to_phase)
        action = self._transition_actions.get(transition)

        if action is not None:
            action()

    def reset(self) -> None:
        """Reset the handler's state.

        Clears the last known phase, causing the next call to
        check_and_handle_transition to behave like the first call.
        This is useful for testing or when reinitializing the system.

        Examples
        --------
        >>> # Reset for a fresh start
        >>> handler.reset()
        >>> # Next check will just record phase
        >>> handler.check_and_handle_transition(PhaseType.CLOSED)  # Returns False
        """
        self._last_phase = None

    def _on_enter_auction(self) -> None:
        """Execute opening auction when entering OPENING_AUCTION phase.

        This method is called when transitioning from PRE_OPEN to
        OPENING_AUCTION. It executes the batch matching of all orders
        collected during the pre-open period to establish fair opening
        prices.

        The auction executes during the OPENING_AUCTION phase (not on
        transition to CONTINUOUS) to ensure:
        - All pre-open orders are included
        - The order book is frozen during calculation
        - Opening prices are ready when continuous trading begins
        """
        self._exchange.execute_opening_auction()

    def _on_market_close(self) -> None:
        """Cancel all orders when market closes.

        This method is called when transitioning from CONTINUOUS to
        CLOSED. It ensures all resting orders are cancelled and don't
        carry over to the next trading day.
        """
        self._exchange.cancel_all_orders()
