"""Tests for response coordinator configuration loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from intern_trading_game.domain.exchange.response.models import (
    CoordinationConfig,
)
from intern_trading_game.infrastructure.config.loader import ConfigLoader


class TestResponseCoordinatorConfig:
    """Test loading response coordinator configuration."""

    def test_load_default_coordinator_config(self):
        """Test loading response coordinator configuration from default file.

        Given - Default configuration file exists with coordinator section
        When - Loading response coordinator config
        Then - Config loaded with correct values
        """
        # Given - Config loader with default path
        loader = ConfigLoader()

        # When - Load response coordinator config
        config = loader.get_response_coordinator_config()

        # Then - Config loaded correctly from file
        assert isinstance(config, CoordinationConfig)
        assert config.default_timeout_seconds == 5.0
        assert config.max_pending_requests == 1000
        assert config.cleanup_interval_seconds == 30
        assert config.enable_metrics is True
        assert config.enable_detailed_logging is False
        assert config.request_id_prefix == "req"

    def test_custom_coordinator_config(self):
        """Test loading custom response coordinator configuration.

        Given - Custom config file with coordinator settings
        When - Loading response coordinator config
        Then - Custom values override defaults
        """
        # Given - Custom config file
        custom_config = {
            "response_coordinator": {
                "default_timeout_seconds": 3.0,
                "max_pending_requests": 5000,
                "cleanup_interval_seconds": 15,
                "enable_metrics": False,
                "enable_detailed_logging": True,
                "request_id_prefix": "ord_req",
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(custom_config, f)
            config_path = Path(f.name)

        try:
            # When - Load custom config
            loader = ConfigLoader(config_path)
            config = loader.get_response_coordinator_config()

            # Then - Custom values loaded
            assert config.default_timeout_seconds == 3.0
            assert config.max_pending_requests == 5000
            assert config.cleanup_interval_seconds == 15
            assert config.enable_metrics is False
            assert config.enable_detailed_logging is True
            assert config.request_id_prefix == "ord_req"

        finally:
            config_path.unlink()

    def test_missing_coordinator_config_raises_error(self):
        """Test that missing coordinator config section raises error.

        Given - Config file without response_coordinator section
        When - Loading response coordinator config
        Then - ValueError is raised
        """
        # Given - Config without coordinator section
        minimal_config = {"exchange": {"matching_mode": "continuous"}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(minimal_config, f)
            config_path = Path(f.name)

        try:
            # When/Then - Load config raises ValueError
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_response_coordinator_config()

            assert "Missing required 'response_coordinator' section" in str(
                exc_info.value
            )

        finally:
            config_path.unlink()

    def test_partial_coordinator_config_raises_error(self):
        """Test that partial coordinator config raises error.

        Given - Config with only some coordinator settings
        When - Loading response coordinator config
        Then - ValueError is raised listing missing fields
        """
        # Given - Partial config missing required fields
        partial_config = {
            "response_coordinator": {
                "default_timeout_seconds": 10.0,
                "enable_metrics": False,
                # Other required fields missing
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(partial_config, f)
            config_path = Path(f.name)

        try:
            # When/Then - Load config raises ValueError
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_response_coordinator_config()

            error_msg = str(exc_info.value)
            assert "Missing required response_coordinator fields" in error_msg
            # Should list the missing fields
            assert "max_pending_requests" in error_msg
            assert "cleanup_interval_seconds" in error_msg
            assert "enable_detailed_logging" in error_msg
            assert "request_id_prefix" in error_msg

        finally:
            config_path.unlink()

    def test_coordinator_config_validation_ranges(self):
        """Test that coordinator config values are sensible.

        Given - Loaded coordinator configuration
        When - Checking configuration values
        Then - Values are within reasonable ranges
        """
        # Given - Default config
        loader = ConfigLoader()
        config = loader.get_response_coordinator_config()

        # Then - Values are reasonable
        assert (
            0.1 <= config.default_timeout_seconds <= 60.0
        ), "Timeout should be reasonable"
        assert (
            10 <= config.max_pending_requests <= 100000
        ), "Request limit should be reasonable"
        assert (
            1 <= config.cleanup_interval_seconds <= 300
        ), "Cleanup interval should be reasonable"
        assert isinstance(config.enable_metrics, bool)
        assert isinstance(config.enable_detailed_logging, bool)
        assert (
            len(config.request_id_prefix) > 0
        ), "Request ID prefix should not be empty"

    def test_invalid_timeout_seconds_raises_error(self):
        """Test that invalid timeout value raises error.

        Given - Config with invalid timeout value
        When - Loading response coordinator config
        Then - ValueError is raised
        """
        # Test negative timeout
        invalid_config = {
            "response_coordinator": {
                "default_timeout_seconds": -1.0,
                "max_pending_requests": 1000,
                "cleanup_interval_seconds": 30,
                "enable_metrics": True,
                "enable_detailed_logging": False,
                "request_id_prefix": "req",
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_response_coordinator_config()

            assert "Invalid default_timeout_seconds" in str(exc_info.value)
            assert "Must be a positive number" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_invalid_max_pending_requests_raises_error(self):
        """Test that invalid max_pending_requests value raises error.

        Given - Config with invalid max_pending_requests
        When - Loading response coordinator config
        Then - ValueError is raised
        """
        # Test with float instead of int
        invalid_config = {
            "response_coordinator": {
                "default_timeout_seconds": 5.0,
                "max_pending_requests": 1000.5,  # Should be int
                "cleanup_interval_seconds": 30,
                "enable_metrics": True,
                "enable_detailed_logging": False,
                "request_id_prefix": "req",
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_response_coordinator_config()

            assert "Invalid max_pending_requests" in str(exc_info.value)
            assert "Must be a positive integer" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_zero_cleanup_interval_raises_error(self):
        """Test that zero cleanup interval raises error.

        Given - Config with zero cleanup interval
        When - Loading response coordinator config
        Then - ValueError is raised
        """
        invalid_config = {
            "response_coordinator": {
                "default_timeout_seconds": 5.0,
                "max_pending_requests": 1000,
                "cleanup_interval_seconds": 0,  # Invalid
                "enable_metrics": True,
                "enable_detailed_logging": False,
                "request_id_prefix": "req",
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_response_coordinator_config()

            assert "Invalid cleanup_interval_seconds" in str(exc_info.value)
            assert "Must be a positive number" in str(exc_info.value)

        finally:
            config_path.unlink()
