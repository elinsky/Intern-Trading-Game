"""Unit tests for PositionManagementService."""

import threading
from unittest.mock import MagicMock

import pytest

from intern_trading_game.services.position_management import (
    PositionManagementService,
)


class TestPositionManagementService:
    """Test suite for PositionManagementService."""

    @pytest.fixture
    def positions_dict(self):
        """Create a test positions dictionary."""
        return {}

    @pytest.fixture
    def positions_lock(self):
        """Create a test lock."""
        return threading.RLock()

    @pytest.fixture
    def service(self, positions_dict, positions_lock):
        """Create a PositionManagementService instance."""
        return PositionManagementService(positions_dict, positions_lock)

    def test_service_initialization(
        self, service, positions_dict, positions_lock
    ):
        """Test service initializes with shared state."""
        assert service.positions is positions_dict
        assert service.lock is positions_lock

    def test_update_position_new_team(self, service, positions_dict):
        """Test updating position for new team.

        Given - Team with no existing positions
        When - Position update occurs
        Then - Team and instrument initialized, position set
        """
        service.update_position("TEAM001", "SPX-CALL-4500", 10)

        assert "TEAM001" in positions_dict
        assert "SPX-CALL-4500" in positions_dict["TEAM001"]
        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == 10

    def test_update_position_existing_team_new_instrument(
        self, service, positions_dict
    ):
        """Test adding new instrument position for existing team.

        Given - Team with positions in other instruments
        When - Position update for new instrument
        Then - New instrument added without affecting others
        """
        # Setup existing position
        positions_dict["TEAM001"] = {"SPX-PUT-4500": -5}

        # Update with new instrument
        service.update_position("TEAM001", "SPX-CALL-4500", 10)

        assert positions_dict["TEAM001"]["SPX-PUT-4500"] == -5  # Unchanged
        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == 10  # New

    def test_update_position_cumulative(self, service, positions_dict):
        """Test position updates are cumulative.

        Given - Existing position
        When - Multiple updates occur
        Then - Position reflects net change
        """
        # Initial buy
        service.update_position("TEAM001", "SPX-CALL-4500", 10)
        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == 10

        # Additional buy
        service.update_position("TEAM001", "SPX-CALL-4500", 5)
        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == 15

        # Sell (negative delta)
        service.update_position("TEAM001", "SPX-CALL-4500", -7)
        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == 8

    def test_update_position_to_zero(self, service, positions_dict):
        """Test position can be reduced to zero."""
        service.update_position("TEAM001", "SPX-CALL-4500", 10)
        service.update_position("TEAM001", "SPX-CALL-4500", -10)

        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == 0

    def test_update_position_negative(self, service, positions_dict):
        """Test short positions (negative quantities)."""
        service.update_position("TEAM001", "SPX-CALL-4500", -20)
        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == -20

    def test_get_positions_empty_team(self, service):
        """Test getting positions for team with no positions."""
        positions = service.get_positions("TEAM001")
        assert positions == {}

    def test_get_positions_returns_copy(self, service, positions_dict):
        """Test get_positions returns a copy, not reference.

        Given - Team with positions
        When - Positions retrieved and modified
        Then - Original positions unchanged
        """
        positions_dict["TEAM001"] = {"SPX-CALL-4500": 10}

        # Get positions and modify the returned dict
        positions = service.get_positions("TEAM001")
        positions["SPX-CALL-4500"] = 999
        positions["NEW-INSTRUMENT"] = 100

        # Original should be unchanged
        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == 10
        assert "NEW-INSTRUMENT" not in positions_dict["TEAM001"]

    def test_get_positions_multiple_instruments(self, service, positions_dict):
        """Test getting positions with multiple instruments."""
        positions_dict["TEAM001"] = {
            "SPX-CALL-4500": 10,
            "SPX-PUT-4500": -5,
            "SPY-CALL-450": 20,
        }

        positions = service.get_positions("TEAM001")
        assert len(positions) == 3
        assert positions["SPX-CALL-4500"] == 10
        assert positions["SPX-PUT-4500"] == -5
        assert positions["SPY-CALL-450"] == 20

    def test_get_position_for_instrument_exists(self, service, positions_dict):
        """Test getting specific instrument position."""
        positions_dict["TEAM001"] = {"SPX-CALL-4500": 15}

        position = service.get_position_for_instrument(
            "TEAM001", "SPX-CALL-4500"
        )
        assert position == 15

    def test_get_position_for_instrument_not_exists(self, service):
        """Test getting position for non-existent instrument returns 0."""
        position = service.get_position_for_instrument(
            "TEAM001", "SPX-CALL-4500"
        )
        assert position == 0

    def test_get_position_for_instrument_team_not_exists(self, service):
        """Test getting position for non-existent team returns 0."""
        position = service.get_position_for_instrument(
            "UNKNOWN", "SPX-CALL-4500"
        )
        assert position == 0

    def test_initialize_team_new(self, service, positions_dict):
        """Test initializing new team."""
        service.initialize_team("TEAM001")

        assert "TEAM001" in positions_dict
        assert positions_dict["TEAM001"] == {}

    def test_initialize_team_idempotent(self, service, positions_dict):
        """Test initialize_team is idempotent.

        Given - Team already exists with positions
        When - Initialize called again
        Then - Existing positions preserved
        """
        positions_dict["TEAM001"] = {"SPX-CALL-4500": 10}

        service.initialize_team("TEAM001")

        # Should not overwrite existing positions
        assert positions_dict["TEAM001"]["SPX-CALL-4500"] == 10

    def test_get_total_absolute_position_empty(self, service):
        """Test total absolute position for team with no positions."""
        total = service.get_total_absolute_position("TEAM001")
        assert total == 0

    def test_get_total_absolute_position_single(self, service, positions_dict):
        """Test total absolute position with single instrument."""
        positions_dict["TEAM001"] = {"SPX-CALL-4500": 30}

        total = service.get_total_absolute_position("TEAM001")
        assert total == 30

    def test_get_total_absolute_position_mixed(self, service, positions_dict):
        """Test total absolute position with mixed long/short.

        Given - Team with long and short positions
        When - Total calculated
        Then - Sum of absolute values returned
        """
        positions_dict["TEAM001"] = {
            "SPX-CALL-4500": 30,  # Long
            "SPX-PUT-4500": -20,  # Short
            "SPY-CALL-450": 10,  # Long
        }

        total = service.get_total_absolute_position("TEAM001")
        assert total == 60  # |30| + |-20| + |10|

    def test_thread_safety_mock(self, positions_dict):
        """Test that lock is properly used for thread safety."""
        mock_lock = MagicMock()
        service = PositionManagementService(positions_dict, mock_lock)

        # Test update_position acquires lock
        service.update_position("TEAM001", "SPX-CALL-4500", 10)
        mock_lock.__enter__.assert_called()
        mock_lock.__exit__.assert_called()

        # Reset mock
        mock_lock.reset_mock()

        # Test get_positions acquires lock
        service.get_positions("TEAM001")
        mock_lock.__enter__.assert_called()
        mock_lock.__exit__.assert_called()

    @pytest.mark.parametrize(
        "initial_pos,delta,expected",
        [
            (0, 10, 10),  # New long position
            (10, 5, 15),  # Increase long
            (10, -5, 5),  # Decrease long
            (10, -10, 0),  # Close position
            (10, -15, -5),  # Flip to short
            (-10, 5, -5),  # Cover partial short
            (-10, -5, -15),  # Increase short
            (-10, 10, 0),  # Cover full short
        ],
    )
    def test_position_update_scenarios(
        self, service, positions_dict, initial_pos, delta, expected
    ):
        """Test various position update scenarios."""
        if initial_pos != 0:
            positions_dict["TEAM001"] = {"INSTRUMENT": initial_pos}

        service.update_position("TEAM001", "INSTRUMENT", delta)

        final_pos = positions_dict["TEAM001"]["INSTRUMENT"]
        assert final_pos == expected
