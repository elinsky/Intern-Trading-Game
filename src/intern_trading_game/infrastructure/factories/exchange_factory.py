"""Factory for creating configured exchange instances.

This module provides factory methods to create ExchangeVenue instances
with the appropriate matching engine based on configuration.
"""

from unittest.mock import Mock

from ...domain.exchange.book.matching_engine import (
    BatchMatchingEngine,
    ContinuousMatchingEngine,
    MatchingEngine,
)
from ...domain.exchange.phase.interfaces import PhaseManagerInterface
from ...domain.exchange.types import PhaseState, PhaseType
from ...domain.exchange.venue import ExchangeVenue
from ..config.models import ExchangeConfig


class ExchangeFactory:
    """Factory for creating configured exchange instances.

    This class provides static methods to create ExchangeVenue instances
    based on configuration objects, hiding the complexity of matching
    engine selection and initialization.
    """

    @staticmethod
    def create_from_config(config: ExchangeConfig) -> ExchangeVenue:
        """Create exchange based on configuration.

        Creates an ExchangeVenue with the appropriate matching engine
        based on the provided configuration.

        Parameters
        ----------
        config : ExchangeConfig
            Configuration specifying the exchange settings

        Returns
        -------
        ExchangeVenue
            Configured exchange instance ready for use

        Notes
        -----
        Currently supports two matching modes:
        - "continuous": Orders match immediately upon submission
        - "batch": Orders are collected and matched at intervals

        The factory prints the mode to stdout for operational visibility.
        """
        engine: MatchingEngine
        if config.matching_mode == "batch":
            engine = BatchMatchingEngine()
            print("Using batch matching engine")
        else:
            engine = ContinuousMatchingEngine()
            print("Using continuous matching engine")

        # Create a phase manager based on matching mode
        # In production, this would be created from configuration
        if config.matching_mode == "batch":
            phase_manager = ExchangeFactory._create_batch_phase_manager()
        else:
            phase_manager = ExchangeFactory._create_default_phase_manager()

        return ExchangeVenue(
            phase_manager=phase_manager, matching_engine=engine
        )

    @staticmethod
    def _create_default_phase_manager() -> PhaseManagerInterface:
        """Create a default phase manager for continuous trading.

        This is a temporary implementation that always returns
        continuous trading phase. In production, this would be
        replaced with ConfigDrivenPhaseManager based on schedule
        configuration.

        Returns
        -------
        PhaseManagerInterface
            A mock phase manager for continuous trading
        """
        manager = Mock(spec=PhaseManagerInterface)
        manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )
        manager.get_current_phase_type.return_value = PhaseType.CONTINUOUS
        return manager

    @staticmethod
    def _create_batch_phase_manager() -> PhaseManagerInterface:
        """Create a phase manager for batch mode testing.

        This creates a phase manager that simulates pre-open
        phase where orders are collected but not matched.

        Returns
        -------
        PhaseManagerInterface
            A mock phase manager for batch mode
        """
        manager = Mock(spec=PhaseManagerInterface)
        manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.PRE_OPEN,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="batch",
        )
        manager.get_current_phase_type.return_value = PhaseType.PRE_OPEN
        return manager
