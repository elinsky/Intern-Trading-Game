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


@dataclass
class PhaseScheduleConfig:
    """Configuration for a market phase schedule.

    Attributes
    ----------
    start_time : str
        Start time in 24-hour format (e.g., "08:00")
    end_time : str
        End time in 24-hour format (e.g., "09:30")
    weekdays : List[str]
        List of weekdays when this phase is active
        (e.g., ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    """

    start_time: str
    end_time: str
    weekdays: List[str]


@dataclass
class PhaseStateConfig:
    """Configuration for a market phase state.

    Attributes
    ----------
    is_order_submission_allowed : bool
        Whether new orders can be submitted in this phase
    is_order_cancellation_allowed : bool
        Whether existing orders can be cancelled in this phase
    is_matching_enabled : bool
        Whether order matching occurs in this phase
    execution_style : str
        How orders are executed ("none", "continuous", "batch")
    """

    is_order_submission_allowed: bool
    is_order_cancellation_allowed: bool
    is_matching_enabled: bool
    execution_style: str


@dataclass
class MarketPhasesConfig:
    """Configuration for market phases.

    Attributes
    ----------
    timezone : str
        Timezone for all phase times (e.g., "America/Chicago")
    schedule : Dict[str, PhaseScheduleConfig]
        Mapping of phase names to their schedules
    phase_states : Dict[str, PhaseStateConfig]
        Mapping of phase names to their state configurations
    """

    timezone: str
    schedule: Dict[str, PhaseScheduleConfig]
    phase_states: Dict[str, PhaseStateConfig]
