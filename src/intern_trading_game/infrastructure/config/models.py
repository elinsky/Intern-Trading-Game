"""Configuration data models.

This module defines the data structures for application configuration,
using dataclasses for type safety and clarity.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal


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


@dataclass
class ConstraintConfigData:
    """Configuration data for a single constraint.

    This represents constraint data as loaded from YAML before
    conversion to domain ConstraintConfig objects.

    Attributes
    ----------
    type : str
        The constraint type (e.g., "position_limit", "instrument_allowed")
    parameters : Dict[str, Any]
        Constraint-specific parameters
    error_code : str
        Error code to return when constraint is violated
    error_message : str
        Human-readable error message
    """

    type: str
    parameters: Dict[str, Any]
    error_code: str
    error_message: str


@dataclass
class RoleConfig:
    """Configuration for a trading role.

    Attributes
    ----------
    constraints : List[ConstraintConfigData]
        List of constraints that apply to this role
    """

    constraints: List[ConstraintConfigData]


@dataclass
class InstrumentConfigData:
    """Configuration data for an instrument.

    All fields are required since we only support options.

    Attributes
    ----------
    symbol : str
        Unique identifier for the instrument
    strike : float
        Strike price of the option
    option_type : str
        Type of option ("call" or "put")
    underlying : str
        Underlying asset symbol
    """

    symbol: str
    strike: float
    option_type: str
    underlying: str
