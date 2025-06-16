"""Configuration loading utilities.

This module provides functionality to load and parse YAML configuration files,
with support for defaults and validation.
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ...domain.exchange.models.instrument import Instrument
from ...domain.exchange.validation.order_validator import (
    ConstraintConfig,
    ConstraintType,
)
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
