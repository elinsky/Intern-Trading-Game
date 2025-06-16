"""Behavior tests for configuration loading functionality."""

import tempfile
from pathlib import Path

import pytest
import yaml

from intern_trading_game.infrastructure.config.loader import ConfigLoader
from intern_trading_game.infrastructure.config.models import ExchangeConfig


class TestConfigLoader:
    """Test configuration loading behavior."""

    def test_load_default_config(self):
        """Test loading configuration with default values.

        Given - A YAML config file with exchange settings
        When - Config loader reads the file
        Then - Exchange config object has correct matching mode
        """
        # Given - Create a temporary config file with continuous mode
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"exchange": {"matching_mode": "continuous"}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load the configuration
            loader = ConfigLoader(config_path)
            exchange_config = loader.get_exchange_config()

            # Then - Config should have continuous matching mode
            assert exchange_config.matching_mode == "continuous"
            assert isinstance(exchange_config, ExchangeConfig)
        finally:
            config_path.unlink()

    def test_load_batch_mode_config(self):
        """Test loading configuration with batch matching mode.

        Given - A YAML config specifying batch matching mode
        When - Config loader reads the file
        Then - Exchange config reflects batch mode
        """
        # Given - Create config with batch mode
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"exchange": {"matching_mode": "batch"}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load the configuration
            loader = ConfigLoader(config_path)
            exchange_config = loader.get_exchange_config()

            # Then - Config should have batch matching mode
            assert exchange_config.matching_mode == "batch"
        finally:
            config_path.unlink()

    def test_missing_exchange_section_uses_defaults(self):
        """Test that missing exchange section falls back to defaults.

        Given - A YAML config file without exchange section
        When - Config loader tries to get exchange config
        Then - Default continuous mode is used
        """
        # Given - Config file with no exchange section
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"other_section": {"some_value": 123}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load exchange configuration
            loader = ConfigLoader(config_path)
            exchange_config = loader.get_exchange_config()

            # Then - Should use default continuous mode
            assert exchange_config.matching_mode == "continuous"
        finally:
            config_path.unlink()

    def test_empty_config_file_uses_defaults(self):
        """Test that empty config file doesn't break loading.

        Given - An empty YAML config file
        When - Config loader reads the file
        Then - Default values are used without errors
        """
        # Given - Empty config file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("")  # Empty file
            config_path = Path(f.name)

        try:
            # When - Load configuration
            loader = ConfigLoader(config_path)
            exchange_config = loader.get_exchange_config()

            # Then - Should work with defaults
            assert exchange_config.matching_mode == "continuous"
        finally:
            config_path.unlink()

    def test_config_file_not_found_error(self):
        """Test proper error when config file doesn't exist.

        Given - A path to non-existent config file
        When - Config loader tries to load it
        Then - FileNotFoundError is raised with helpful message
        """
        # Given - Non-existent file path
        bad_path = Path("/tmp/does_not_exist_12345.yaml")
        loader = ConfigLoader(bad_path)

        # When/Then - Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load()

        assert "Configuration file not found" in str(exc_info.value)
        assert str(bad_path) in str(exc_info.value)

    def test_malformed_yaml_error(self):
        """Test proper error handling for invalid YAML.

        Given - A config file with invalid YAML syntax
        When - Config loader tries to parse it
        Then - YAMLError is raised with helpful message
        """
        # Given - Invalid YAML file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid yaml: [unclosed bracket")
            config_path = Path(f.name)

        try:
            # When/Then - Should raise YAMLError
            loader = ConfigLoader(config_path)
            with pytest.raises(yaml.YAMLError) as exc_info:
                loader.load()

            assert "Failed to parse config file" in str(exc_info.value)
        finally:
            config_path.unlink()

    def test_config_caching(self):
        """Test that config is loaded only once and cached.

        Given - A config file that will be modified after first load
        When - Config is loaded multiple times
        Then - The first loaded values are returned (cached)
        """
        # Given - Initial config file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"exchange": {"matching_mode": "continuous"}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load config first time
            loader = ConfigLoader(config_path)
            first_config = loader.get_exchange_config()
            assert first_config.matching_mode == "continuous"

            # When - Modify file and load again
            with open(config_path, "w") as f:
                new_data = {"exchange": {"matching_mode": "batch"}}
                yaml.dump(new_data, f)

            second_config = loader.get_exchange_config()

            # Then - Should still return cached continuous mode
            assert second_config.matching_mode == "continuous"
        finally:
            config_path.unlink()
