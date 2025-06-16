"""Configuration loading utilities.

This module provides functionality to load and parse YAML configuration files,
with support for defaults and validation.
"""

from pathlib import Path
from typing import Dict, Optional

import yaml

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
