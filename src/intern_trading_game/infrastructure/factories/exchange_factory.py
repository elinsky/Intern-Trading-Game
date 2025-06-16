"""Factory for creating configured exchange instances.

This module provides factory methods to create ExchangeVenue instances
with the appropriate matching engine based on configuration.
"""

from ...domain.exchange.book.matching_engine import (
    BatchMatchingEngine,
    ContinuousMatchingEngine,
    MatchingEngine,
)
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

        return ExchangeVenue(engine)
