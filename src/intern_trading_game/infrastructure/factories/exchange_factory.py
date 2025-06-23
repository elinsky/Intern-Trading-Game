"""Factory for creating configured exchange instances.

This module provides factory methods to create ExchangeVenue instances
with the appropriate matching engine based on configuration.
"""

from typing import Optional

from ...domain.exchange.book.matching_engine import (
    BatchMatchingEngine,
    ContinuousMatchingEngine,
)
from ...domain.exchange.phase.interfaces import PhaseManagerInterface
from ...domain.exchange.phase.manager import ConfigDrivenPhaseManager
from ...domain.exchange.venue import ExchangeVenue
from ..config.loader import ConfigLoader
from ..config.models import ExchangeConfig


class ExchangeFactory:
    """Factory for creating configured exchange instances.

    This class provides static methods to create ExchangeVenue instances
    based on configuration objects, hiding the complexity of matching
    engine selection and initialization.
    """

    @staticmethod
    def create_from_config(
        config: ExchangeConfig,
        test_phase_manager: Optional[PhaseManagerInterface] = None,
    ) -> ExchangeVenue:
        """Create exchange based on configuration.

        Creates an ExchangeVenue with explicit engine dependencies
        for better testability and dependency injection.

        Parameters
        ----------
        config : ExchangeConfig
            Configuration specifying the exchange settings
        test_phase_manager : Optional[PhaseManagerInterface]
            Optional phase manager for testing. If provided, uses this instead
            of ConfigDrivenPhaseManager. Intended for integration tests.

        Returns
        -------
        ExchangeVenue
            Configured exchange instance ready for use

        Notes
        -----
        Creates both continuous and batch engines explicitly and injects
        them into the ExchangeVenue along with either a ConfigDrivenPhaseManager
        (production) or test phase manager (testing). The exchange will
        automatically select the appropriate engine based on the current phase.
        """
        # Create both engines explicitly for dependency injection
        continuous_engine = ContinuousMatchingEngine()
        batch_engine = BatchMatchingEngine()

        # Create phase manager (test override or production)
        if test_phase_manager:
            # Use provided test phase manager for integration testing
            phase_manager = test_phase_manager
        else:
            # Production: create real phase manager using market configuration
            config_loader = ConfigLoader()
            market_phases_config = config_loader.get_market_phases_config()
            phase_manager = ConfigDrivenPhaseManager(market_phases_config)

        # Set primary engine based on config for backward compatibility
        primary_engine = (
            batch_engine
            if config.matching_mode == "batch"
            else continuous_engine
        )

        return ExchangeVenue(
            phase_manager=phase_manager,
            continuous_engine=continuous_engine,
            batch_engine=batch_engine,
            matching_engine=primary_engine,  # This makes tests pass
        )
