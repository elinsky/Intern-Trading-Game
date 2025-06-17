"""Configuration loading utilities.

This module provides functionality to load and parse YAML configuration files,
with support for defaults and validation.
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ...domain.exchange.models.instrument import Instrument
from ...domain.exchange.response.models import CoordinationConfig
from ...domain.exchange.validation.order_validator import (
    ConstraintConfig,
    ConstraintType,
)
from ...domain.positions.models import FeeSchedule
from .models import ExchangeConfig


class ConfigLoader:
    """Loads and manages application configuration from YAML files.

    This class provides a centralized way to load configuration from YAML files,
    with caching to avoid repeated file I/O.

    Parameters
    ----------
    config_path : Optional[Path]
        Path to the configuration file. If None, defaults to "config/default.yaml"

    Attributes
    ----------
    config_path : Path
        The path to the configuration file
    _config_data : Optional[Dict]
        Cached configuration data
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the config loader with a path."""
        self.config_path = config_path or Path("config/default.yaml")
        self._config_data: Optional[Dict] = None

    def load(self) -> Dict:
        """Load raw configuration data from YAML file.

        Loads the YAML file and caches the result. Subsequent calls
        return the cached data.

        Returns
        -------
        Dict
            The parsed YAML configuration as a dictionary

        Raises
        ------
        FileNotFoundError
            If the configuration file doesn't exist
        yaml.YAMLError
            If the YAML file is malformed
        """
        if self._config_data is None:
            if not self.config_path.exists():
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_path}"
                )

            with open(self.config_path) as f:
                try:
                    self._config_data = yaml.safe_load(f) or {}
                except yaml.YAMLError as e:
                    raise yaml.YAMLError(
                        f"Failed to parse config file {self.config_path}: {e}"
                    )

        return self._config_data

    def get_exchange_config(self) -> ExchangeConfig:
        """Get exchange-specific configuration.

        Extracts the exchange section from the configuration and returns
        it as a typed ExchangeConfig object.

        Returns
        -------
        ExchangeConfig
            The exchange configuration with defaults applied
        """
        data = self.load()
        exchange_data = data.get("exchange", {})

        # Create config with explicit field extraction for clarity
        return ExchangeConfig(
            matching_mode=exchange_data.get("matching_mode", "continuous")
        )

    def get_role_constraints(self, role: str) -> List[ConstraintConfig]:
        """Get constraints for a specific role.

        Loads the constraints defined for the given role and converts them
        to ConstraintConfig objects that can be used by the validator.

        Parameters
        ----------
        role : str
            The role name (e.g., "market_maker", "hedge_fund")

        Returns
        -------
        List[ConstraintConfig]
            List of constraint configurations for the role, or empty list
            if role not found or has no constraints

        Raises
        ------
        ValueError
            If constraint type is invalid
        KeyError
            If required constraint fields are missing
        """
        data = self.load()
        roles_data = data.get("roles", {})

        # If role doesn't exist, return empty list
        if role not in roles_data:
            return []

        role_data = roles_data[role]
        constraints_data = role_data.get("constraints", [])

        constraints = []
        for constraint_data in constraints_data:
            # Validate constraint type
            constraint_type_str = constraint_data["type"]
            try:
                constraint_type = ConstraintType(constraint_type_str)
            except ValueError:
                valid_types = [ct.value for ct in ConstraintType]
                raise ValueError(
                    f"Invalid constraint type: {constraint_type_str}. "
                    f"Valid types are: {valid_types}"
                )

            # Create ConstraintConfig object
            constraint = ConstraintConfig(
                constraint_type=constraint_type,
                parameters=constraint_data["parameters"],
                error_code=constraint_data["error_code"],
                error_message=constraint_data["error_message"],
            )
            constraints.append(constraint)

        return constraints

    def get_instruments(self) -> List[Instrument]:
        """Get instrument definitions from configuration.

        Loads the instruments section and creates Instrument objects.
        All fields (symbol, strike, option_type, underlying) are required.

        Returns
        -------
        List[Instrument]
            List of configured instruments, or empty list if none defined

        Raises
        ------
        KeyError
            If required instrument fields are missing
        ValueError
            If option_type is invalid
        """
        data = self.load()
        instruments_data = data.get("instruments", [])

        instruments = []
        for inst_data in instruments_data:
            # All fields are required - will raise KeyError if missing
            instrument = Instrument(
                symbol=inst_data["symbol"],
                strike=inst_data["strike"],
                option_type=inst_data["option_type"],
                underlying=inst_data["underlying"],
            )
            instruments.append(instrument)

        return instruments

    def get_fee_schedules(self) -> Dict[str, FeeSchedule]:
        """Get fee schedules for all roles from configuration.

        Parses the roles section of the configuration to extract
        fee schedules for each role. Validates that both maker_rebate
        and taker_fee are present for each role with a fees section.

        Returns
        -------
        Dict[str, FeeSchedule]
            Mapping from role name to FeeSchedule object

        Raises
        ------
        ValueError
            If a role has incomplete fee configuration (missing
            maker_rebate or taker_fee)

        Notes
        -----
        Roles without a fees section are skipped entirely.
        Only roles with complete fee configuration are included.

        The fee structure is critical for P&L calculation, so
        incomplete configurations are treated as errors.

        Examples
        --------
        >>> loader = ConfigLoader()
        >>> fee_schedules = loader.get_fee_schedules()
        >>> print(fee_schedules["market_maker"].maker_rebate)
        0.02
        """
        data = self.load()
        roles_data = data.get("roles", {})
        fee_schedules = {}

        for role_name, role_data in roles_data.items():
            fees_data = role_data.get("fees", {})

            # Roles must have fees section
            if not fees_data:
                raise ValueError(
                    f"Missing fees section for role: {role_name}. "
                    "All trading roles must have fee configuration."
                )

            # Validate required fields
            if "maker_rebate" not in fees_data:
                raise ValueError(
                    f"Missing required fee 'maker_rebate' for role: {role_name}"
                )
            if "taker_fee" not in fees_data:
                raise ValueError(
                    f"Missing required fee 'taker_fee' for role: {role_name}"
                )

            # Create fee schedule
            fee_schedules[role_name] = FeeSchedule(
                maker_rebate=fees_data["maker_rebate"],
                taker_fee=fees_data["taker_fee"],
            )

        return fee_schedules

    def get_response_coordinator_config(self) -> CoordinationConfig:
        """Get response coordinator configuration.

        Extracts the response coordinator section from the configuration
        and validates that all required fields are present. This method
        enforces explicit configuration to prevent accidental use of
        defaults in production.

        Returns
        -------
        CoordinationConfig
            The response coordination configuration

        Raises
        ------
        ValueError
            If the response_coordinator section is missing or incomplete

        Notes
        -----
        The response coordinator manages the synchronization between
        REST API requests and asynchronous order processing. Configuration
        parameters affect system performance and resource usage:

        - timeout_seconds: Maximum time API clients wait for responses
        - max_pending_requests: Memory limit and overload protection
        - cleanup_interval: Balance between memory usage and CPU overhead
        - enable_metrics: Performance tracking vs overhead tradeoff

        All configuration values must be explicitly set to ensure
        intentional configuration for production deployments.

        Examples
        --------
        >>> loader = ConfigLoader()
        >>> coord_config = loader.get_response_coordinator_config()
        >>> print(coord_config.default_timeout_seconds)
        5.0
        """
        data = self.load()

        # Require response_coordinator section
        if "response_coordinator" not in data:
            raise ValueError(
                "Missing required 'response_coordinator' section in configuration. "
                "All response coordination parameters must be explicitly configured."
            )

        coord_data = data["response_coordinator"]

        # Validate all required fields are present
        required_fields = [
            "default_timeout_seconds",
            "max_pending_requests",
            "cleanup_interval_seconds",
            "enable_metrics",
            "enable_detailed_logging",
            "request_id_prefix",
        ]

        missing_fields = [
            field for field in required_fields if field not in coord_data
        ]
        if missing_fields:
            raise ValueError(
                f"Missing required response_coordinator fields: {missing_fields}. "
                "All configuration parameters must be explicitly set."
            )

        # Validate field values
        timeout = coord_data["default_timeout_seconds"]
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError(
                f"Invalid default_timeout_seconds: {timeout}. "
                "Must be a positive number."
            )

        max_requests = coord_data["max_pending_requests"]
        if not isinstance(max_requests, int) or max_requests <= 0:
            raise ValueError(
                f"Invalid max_pending_requests: {max_requests}. "
                "Must be a positive integer."
            )

        cleanup_interval = coord_data["cleanup_interval_seconds"]
        if (
            not isinstance(cleanup_interval, (int, float))
            or cleanup_interval <= 0
        ):
            raise ValueError(
                f"Invalid cleanup_interval_seconds: {cleanup_interval}. "
                "Must be a positive number."
            )

        # Create config with validated values
        return CoordinationConfig(
            default_timeout_seconds=timeout,
            max_pending_requests=max_requests,
            cleanup_interval_seconds=int(cleanup_interval),
            enable_metrics=bool(coord_data["enable_metrics"]),
            enable_detailed_logging=bool(
                coord_data["enable_detailed_logging"]
            ),
            request_id_prefix=str(coord_data["request_id_prefix"]),
        )
