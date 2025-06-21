"""Test phase manager implementation.

This module tests the ConfigDrivenPhaseManager that determines
market phases based on configuration and current time.
"""

from datetime import datetime, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from intern_trading_game.domain.exchange.phase.interfaces import (
    PhaseManagerInterface,
)
from intern_trading_game.domain.exchange.types import PhaseType
from intern_trading_game.infrastructure.config.models import (
    MarketPhasesConfig,
    PhaseScheduleConfig,
    PhaseStateConfig,
)


class TestConfigDrivenPhaseManager:
    """Test the configuration-driven phase manager implementation."""

    @pytest.fixture
    def default_phase_config(self) -> MarketPhasesConfig:
        """Create default market phases configuration."""
        return MarketPhasesConfig(
            timezone="America/Chicago",
            schedule={
                "pre_open": PhaseScheduleConfig(
                    start_time="08:00",
                    end_time="09:30",
                    weekdays=[
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                    ],
                ),
                "continuous": PhaseScheduleConfig(
                    start_time="09:30",
                    end_time="16:00",
                    weekdays=[
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                    ],
                ),
            },
            phase_states={
                "closed": PhaseStateConfig(
                    is_order_submission_allowed=False,
                    is_order_cancellation_allowed=False,
                    is_matching_enabled=False,
                    execution_style="none",
                ),
                "pre_open": PhaseStateConfig(
                    is_order_submission_allowed=True,
                    is_order_cancellation_allowed=True,
                    is_matching_enabled=False,
                    execution_style="none",
                ),
                "continuous": PhaseStateConfig(
                    is_order_submission_allowed=True,
                    is_order_cancellation_allowed=True,
                    is_matching_enabled=True,
                    execution_style="continuous",
                ),
            },
        )

    def test_phase_manager_creation(self, default_phase_config):
        """Test creating a phase manager with configuration."""
        # When - Creating phase manager with config
        # This will fail until we implement ConfigDrivenPhaseManager
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)

        # Then - Manager should implement the interface
        assert isinstance(manager, PhaseManagerInterface)

    def test_closed_phase_on_weekend(self, default_phase_config):
        """Test that market is closed on weekends."""
        # Given - A Saturday in Chicago time
        # January 6, 2024 is a Saturday
        saturday = datetime(
            2024, 1, 6, 12, 0, 0, tzinfo=ZoneInfo("America/Chicago")
        )

        # When - Checking phase on weekend
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)
        phase_type = manager.get_current_phase_type(saturday)

        # Then - Market should be closed
        assert phase_type == PhaseType.CLOSED

    def test_closed_phase_outside_hours(self, default_phase_config):
        """Test that market is closed outside trading hours."""
        # Given - A weekday but outside trading hours
        # Monday at 7:00 AM Chicago time (before pre-open)
        early_monday = datetime(
            2024, 1, 8, 7, 0, 0, tzinfo=ZoneInfo("America/Chicago")
        )

        # When - Checking phase before market hours
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)
        phase_type = manager.get_current_phase_type(early_monday)

        # Then - Market should be closed
        assert phase_type == PhaseType.CLOSED

    def test_pre_open_phase(self, default_phase_config):
        """Test pre-open phase detection."""
        # Given - A weekday during pre-open hours
        # Monday at 8:30 AM Chicago time
        pre_open_time = datetime(
            2024, 1, 8, 8, 30, 0, tzinfo=ZoneInfo("America/Chicago")
        )

        # When - Checking phase during pre-open
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)
        phase_type = manager.get_current_phase_type(pre_open_time)

        # Then - Market should be in pre-open
        assert phase_type == PhaseType.PRE_OPEN

    def test_continuous_phase(self, default_phase_config):
        """Test continuous trading phase detection."""
        # Given - A weekday during regular trading hours
        # Monday at 10:00 AM Chicago time
        trading_time = datetime(
            2024, 1, 8, 10, 0, 0, tzinfo=ZoneInfo("America/Chicago")
        )

        # When - Checking phase during trading hours
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)
        phase_type = manager.get_current_phase_type(trading_time)

        # Then - Market should be in continuous trading
        assert phase_type == PhaseType.CONTINUOUS

    def test_phase_boundaries(self, default_phase_config):
        """Test phase detection at exact boundaries."""
        # Given - Exact boundary times
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)

        # Test pre-open start (8:00 AM)
        pre_open_start = datetime(
            2024, 1, 8, 8, 0, 0, tzinfo=ZoneInfo("America/Chicago")
        )
        assert (
            manager.get_current_phase_type(pre_open_start)
            == PhaseType.PRE_OPEN
        )

        # Test continuous start (9:30 AM)
        continuous_start = datetime(
            2024, 1, 8, 9, 30, 0, tzinfo=ZoneInfo("America/Chicago")
        )
        assert (
            manager.get_current_phase_type(continuous_start)
            == PhaseType.CONTINUOUS
        )

        # Test market close (4:00 PM)
        market_close = datetime(
            2024, 1, 8, 16, 0, 0, tzinfo=ZoneInfo("America/Chicago")
        )
        assert manager.get_current_phase_type(market_close) == PhaseType.CLOSED

    def test_timezone_conversion(self, default_phase_config):
        """Test that timezone conversion works correctly."""
        # Given - Times in different timezones
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)

        # 10 AM Chicago = 11 AM Eastern = 4 PM UTC (during standard time)
        utc_time = datetime(2024, 1, 8, 16, 0, 0, tzinfo=timezone.utc)
        eastern_time = datetime(
            2024, 1, 8, 11, 0, 0, tzinfo=ZoneInfo("America/New_York")
        )
        chicago_time = datetime(
            2024, 1, 8, 10, 0, 0, tzinfo=ZoneInfo("America/Chicago")
        )

        # When - Checking phase from different timezones
        utc_phase = manager.get_current_phase_type(utc_time)
        eastern_phase = manager.get_current_phase_type(eastern_time)
        chicago_phase = manager.get_current_phase_type(chicago_time)

        # Then - All should detect continuous trading
        assert utc_phase == PhaseType.CONTINUOUS
        assert eastern_phase == PhaseType.CONTINUOUS
        assert chicago_phase == PhaseType.CONTINUOUS

    def test_get_current_phase_state(self, default_phase_config):
        """Test getting complete phase state."""
        # Given - A time during continuous trading
        trading_time = datetime(
            2024, 1, 8, 10, 0, 0, tzinfo=ZoneInfo("America/Chicago")
        )

        # When - Getting current phase state
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)

        # Mock datetime.now() to return our test time
        import intern_trading_game.domain.exchange.phase.manager as manager_module

        original_datetime = manager_module.datetime
        mock_datetime = Mock(wraps=original_datetime)
        mock_datetime.now.return_value = trading_time
        manager_module.datetime = mock_datetime

        try:
            state = manager.get_current_phase_state()

            # Then - State should match continuous trading config
            assert state.phase_type == PhaseType.CONTINUOUS
            assert state.is_order_submission_allowed is True
            assert state.is_order_cancellation_allowed is True
            assert state.is_matching_enabled is True
            assert state.execution_style == "continuous"
        finally:
            # Restore original datetime
            manager_module.datetime = original_datetime

    def test_naive_datetime_handling(self, default_phase_config):
        """Test that naive datetimes use market timezone."""
        # Given - A naive datetime during trading hours
        naive_time = datetime(2024, 1, 8, 10, 0, 0)  # No timezone

        # When - Checking phase with naive datetime
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)
        phase_type = manager.get_current_phase_type(naive_time)

        # Then - Should interpret as market timezone (Chicago)
        # and detect continuous trading
        assert phase_type == PhaseType.CONTINUOUS

    def test_weekday_validation(self, default_phase_config):
        """Test that only configured weekdays have trading phases."""
        # Given - Different days of the week at trading time
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)

        # Test each day at 10 AM Chicago time
        days = [
            (datetime(2024, 1, 8, 10, 0), "Monday", PhaseType.CONTINUOUS),
            (datetime(2024, 1, 9, 10, 0), "Tuesday", PhaseType.CONTINUOUS),
            (datetime(2024, 1, 10, 10, 0), "Wednesday", PhaseType.CONTINUOUS),
            (datetime(2024, 1, 11, 10, 0), "Thursday", PhaseType.CONTINUOUS),
            (datetime(2024, 1, 12, 10, 0), "Friday", PhaseType.CONTINUOUS),
            (datetime(2024, 1, 13, 10, 0), "Saturday", PhaseType.CLOSED),
            (datetime(2024, 1, 14, 10, 0), "Sunday", PhaseType.CLOSED),
        ]

        for dt, day_name, expected_phase in days:
            # Add timezone
            dt_with_tz = dt.replace(tzinfo=ZoneInfo("America/Chicago"))
            phase = manager.get_current_phase_type(dt_with_tz)
            assert (
                phase == expected_phase
            ), f"{day_name} at 10 AM should be {expected_phase}"

    @pytest.mark.parametrize(
        "hour,minute,expected_phase",
        [
            (7, 59, PhaseType.CLOSED),  # Before pre-open
            (8, 0, PhaseType.PRE_OPEN),  # Pre-open start
            (9, 29, PhaseType.PRE_OPEN),  # End of pre-open
            (9, 30, PhaseType.CONTINUOUS),  # Continuous start
            (15, 59, PhaseType.CONTINUOUS),  # End of continuous
            (16, 0, PhaseType.CLOSED),  # Market close
            (20, 0, PhaseType.CLOSED),  # Evening
        ],
    )
    def test_phase_throughout_day(
        self, default_phase_config, hour, minute, expected_phase
    ):
        """Test phase detection throughout a trading day."""
        # Given - Various times during a weekday
        test_time = datetime(
            2024, 1, 8, hour, minute, 0, tzinfo=ZoneInfo("America/Chicago")
        )

        # When - Checking phase
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )

        manager = ConfigDrivenPhaseManager(default_phase_config)
        phase_type = manager.get_current_phase_type(test_time)

        # Then - Phase should match expected
        assert phase_type == expected_phase
