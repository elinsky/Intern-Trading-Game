"""Configuration data models.

This module defines the data structures for application configuration,
using dataclasses for type safety and clarity.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ExchangeConfig:
    """Exchange configuration.

    Attributes
    ----------
    matching_mode : Literal["continuous", "batch"]
        The order matching mode for the exchange.
        - "continuous": Orders match immediately upon submission
        - "batch": Orders collected and matched at intervals
    """

    matching_mode: Literal["continuous", "batch"] = "continuous"
