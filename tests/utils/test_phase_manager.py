"""Test utilities for phase management.

This module provides test-specific phase managers that enable predictable
behavior during integration testing, separate from production phase logic.
"""

from intern_trading_game.domain.exchange.phase.interfaces import (
    PhaseManagerInterface,
)
from intern_trading_game.domain.exchange.types import PhaseState, PhaseType


class IntegrationTestPhaseManager(PhaseManagerInterface):
    """Phase manager for testing that always allows trading operations.

    This test utility provides a predictable phase manager that always
    returns CONTINUOUS phase, allowing integration tests to run outside
    of actual market hours without being blocked by CLOSED phase.

    Notes
    -----
    This is intended only for integration testing. Production code should
    use ConfigDrivenPhaseManager for realistic market behavior.

    Examples
    --------
    >>> # In integration test fixtures
    >>> test_manager = TestPhaseManager()
    >>> exchange = ExchangeFactory.create_from_config(
    ...     config, test_phase_manager=test_manager
    ... )
    >>> # Exchange will accept orders anytime during tests
    """

    def get_current_phase_state(self) -> PhaseState:
        """Get current phase state (always CONTINUOUS for testing).

        Returns
        -------
        PhaseState
            A phase state that allows all trading operations
        """
        return PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )

    def get_current_phase_type(self) -> PhaseType:
        """Get current phase type (always CONTINUOUS for testing).

        Returns
        -------
        PhaseType
            Always PhaseType.CONTINUOUS
        """
        return PhaseType.CONTINUOUS
