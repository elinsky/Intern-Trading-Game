"""Test market phases configuration loading.

This module tests the ConfigLoader's ability to load and validate
market phases configuration from YAML files.
"""

from typing import Any, Dict

import pytest
import yaml

from intern_trading_game.infrastructure.config.loader import ConfigLoader
from intern_trading_game.infrastructure.config.models import (
    MarketPhasesConfig,
)


@pytest.fixture
def valid_market_phases_config() -> Dict[str, Any]:
    """Create a valid market phases configuration."""
    return {
        "market_phases": {
            "timezone": "America/Chicago",
            "schedule": {
                "pre_open": {
                    "start_time": "08:00",
                    "end_time": "09:30",
                    "weekdays": [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                    ],
                },
                "continuous": {
                    "start_time": "09:30",
                    "end_time": "16:00",
                    "weekdays": [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                    ],
                },
            },
            "phase_states": {
                "closed": {
                    "is_order_submission_allowed": False,
                    "is_order_cancellation_allowed": False,
                    "is_matching_enabled": False,
                    "execution_style": "none",
                },
                "pre_open": {
                    "is_order_submission_allowed": True,
                    "is_order_cancellation_allowed": True,
                    "is_matching_enabled": False,
                    "execution_style": "none",
                },
                "continuous": {
                    "is_order_submission_allowed": True,
                    "is_order_cancellation_allowed": True,
                    "is_matching_enabled": True,
                    "execution_style": "continuous",
                },
            },
        }
    }


class TestMarketPhasesConfigLoading:
    """Test loading market phases configuration."""

    def test_load_valid_market_phases_config(
        self, tmp_path, valid_market_phases_config
    ):
        """Test loading a valid market phases configuration."""
        # Given - Valid config file with market phases
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_market_phases_config, f)

        loader = ConfigLoader(config_file)

        # When - Loading market phases config
        config = loader.get_market_phases_config()

        # Then - Config should be loaded correctly
        assert isinstance(config, MarketPhasesConfig)
        assert config.timezone == "America/Chicago"

        # Check schedule
        assert len(config.schedule) == 2
        assert "pre_open" in config.schedule
        assert "continuous" in config.schedule

        pre_open_schedule = config.schedule["pre_open"]
        assert pre_open_schedule.start_time == "08:00"
        assert pre_open_schedule.end_time == "09:30"
        assert pre_open_schedule.weekdays == [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
        ]

        # Check phase states
        assert len(config.phase_states) == 3
        assert "closed" in config.phase_states
        assert "pre_open" in config.phase_states
        assert "continuous" in config.phase_states

        closed_state = config.phase_states["closed"]
        assert closed_state.is_order_submission_allowed is False
        assert closed_state.is_order_cancellation_allowed is False
        assert closed_state.is_matching_enabled is False
        assert closed_state.execution_style == "none"

        continuous_state = config.phase_states["continuous"]
        assert continuous_state.is_order_submission_allowed is True
        assert continuous_state.is_order_cancellation_allowed is True
        assert continuous_state.is_matching_enabled is True
        assert continuous_state.execution_style == "continuous"

    def test_missing_market_phases_section(self, tmp_path):
        """Test error when market_phases section is missing."""
        # Given - Config without market_phases section
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"other_config": {}}, f)

        loader = ConfigLoader(config_file)

        # When/Then - Should raise ValueError
        with pytest.raises(
            ValueError, match="Missing required 'market_phases' section"
        ):
            loader.get_market_phases_config()

    def test_missing_timezone(self, tmp_path, valid_market_phases_config):
        """Test error when timezone is missing."""
        # Given - Config without timezone
        config_data = valid_market_phases_config.copy()
        del config_data["market_phases"]["timezone"]

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When/Then - Should raise ValueError
        with pytest.raises(ValueError, match="Missing required 'timezone'"):
            loader.get_market_phases_config()

    def test_missing_schedule(self, tmp_path, valid_market_phases_config):
        """Test error when schedule is missing."""
        # Given - Config without schedule
        config_data = valid_market_phases_config.copy()
        del config_data["market_phases"]["schedule"]

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When/Then - Should raise ValueError
        with pytest.raises(ValueError, match="Missing required 'schedule'"):
            loader.get_market_phases_config()

    def test_missing_phase_states(self, tmp_path, valid_market_phases_config):
        """Test error when phase_states is missing."""
        # Given - Config without phase_states
        config_data = valid_market_phases_config.copy()
        del config_data["market_phases"]["phase_states"]

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When/Then - Should raise ValueError
        with pytest.raises(
            ValueError, match="Missing required 'phase_states'"
        ):
            loader.get_market_phases_config()

    def test_incomplete_schedule_config(
        self, tmp_path, valid_market_phases_config
    ):
        """Test error when schedule is missing required fields."""
        # Given - Schedule missing end_time
        config_data = valid_market_phases_config.copy()
        del config_data["market_phases"]["schedule"]["pre_open"]["end_time"]

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When/Then - Should raise ValueError
        with pytest.raises(
            ValueError, match="Missing required fields.*end_time.*pre_open"
        ):
            loader.get_market_phases_config()

    def test_incomplete_phase_state_config(
        self, tmp_path, valid_market_phases_config
    ):
        """Test error when phase state is missing required fields."""
        # Given - Phase state missing is_matching_enabled
        config_data = valid_market_phases_config.copy()
        del config_data["market_phases"]["phase_states"]["continuous"][
            "is_matching_enabled"
        ]

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When/Then - Should raise ValueError
        with pytest.raises(
            ValueError,
            match="Missing required fields.*is_matching_enabled.*continuous",
        ):
            loader.get_market_phases_config()

    def test_empty_weekdays_list(self, tmp_path, valid_market_phases_config):
        """Test that empty weekdays list is allowed."""
        # Given - Schedule with empty weekdays (e.g., for special phases)
        config_data = valid_market_phases_config.copy()
        config_data["market_phases"]["schedule"]["pre_open"]["weekdays"] = []

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When - Loading config
        config = loader.get_market_phases_config()

        # Then - Should load successfully with empty weekdays
        assert config.schedule["pre_open"].weekdays == []

    def test_invalid_phase_name_in_schedule(self, tmp_path):
        """Test that invalid phase names in schedule are rejected."""
        # Given - Config with invalid phase name in schedule
        config_data = {
            "market_phases": {
                "timezone": "America/Chicago",
                "schedule": {
                    "early_morning": {  # Invalid phase name
                        "start_time": "04:00",
                        "end_time": "09:30",
                        "weekdays": ["Monday", "Friday"],
                    }
                },
                "phase_states": {
                    "closed": {
                        "is_order_submission_allowed": False,
                        "is_order_cancellation_allowed": False,
                        "is_matching_enabled": False,
                        "execution_style": "none",
                    }
                },
            }
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When/Then - Should raise ValueError
        with pytest.raises(
            ValueError,
            match="Invalid phase name.*early_morning.*Valid phase names are.*closed.*continuous.*pre_open",
        ):
            loader.get_market_phases_config()

    def test_invalid_phase_name_in_states(self, tmp_path):
        """Test that invalid phase names in phase_states are rejected."""
        # Given - Config with invalid phase name in states
        config_data = {
            "market_phases": {
                "timezone": "America/Chicago",
                "schedule": {
                    "pre_open": {
                        "start_time": "08:00",
                        "end_time": "09:30",
                        "weekdays": ["Monday"],
                    }
                },
                "phase_states": {
                    "after_hours": {  # Invalid phase name
                        "is_order_submission_allowed": False,
                        "is_order_cancellation_allowed": False,
                        "is_matching_enabled": False,
                        "execution_style": "none",
                    }
                },
            }
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When/Then - Should raise ValueError
        with pytest.raises(
            ValueError,
            match="Invalid phase name.*after_hours.*Valid phase names are.*closed.*continuous.*pre_open",
        ):
            loader.get_market_phases_config()

    def test_boolean_coercion(self, tmp_path, valid_market_phases_config):
        """Test that boolean fields are properly coerced."""
        # Given - Config with numeric booleans (YAML converts 0/1 to False/True)
        config_data = valid_market_phases_config.copy()
        config_data["market_phases"]["phase_states"]["closed"][
            "is_order_submission_allowed"
        ] = 0
        config_data["market_phases"]["phase_states"]["closed"][
            "is_matching_enabled"
        ] = 0
        config_data["market_phases"]["phase_states"]["continuous"][
            "is_order_submission_allowed"
        ] = 1
        config_data["market_phases"]["phase_states"]["continuous"][
            "is_matching_enabled"
        ] = 1

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        # When - Loading config
        config = loader.get_market_phases_config()

        # Then - Values should be coerced to boolean
        assert (
            config.phase_states["closed"].is_order_submission_allowed is False
        )
        assert config.phase_states["closed"].is_matching_enabled is False
        assert (
            config.phase_states["continuous"].is_order_submission_allowed
            is True
        )
        assert config.phase_states["continuous"].is_matching_enabled is True
