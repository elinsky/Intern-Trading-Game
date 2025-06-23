"""Test phase types and state models.

This module tests the PhaseType enum and PhaseState dataclass that form
the foundation of the phase-based trading system.
"""

from intern_trading_game.domain.exchange.components.core.types import (
    PhaseState,
    PhaseType,
)
from intern_trading_game.infrastructure.config.models import PhaseStateConfig


class TestPhaseType:
    """Test the PhaseType enum."""

    def test_phase_type_values(self):
        """Test that PhaseType has the correct values."""
        # Then - PhaseType should have exactly four values
        assert len(PhaseType) == 4
        assert PhaseType.PRE_OPEN.value == "pre_open"
        assert PhaseType.OPENING_AUCTION.value == "opening_auction"
        assert PhaseType.CONTINUOUS.value == "continuous"
        assert PhaseType.CLOSED.value == "closed"

    def test_phase_type_is_string_enum(self):
        """Test that PhaseType values are strings."""
        # Then - All values should be strings
        for phase in PhaseType:
            assert isinstance(phase.value, str)
            # str() of a StrEnum returns the full enum name
            assert str(phase) == f"PhaseType.{phase.name}"


class TestPhaseState:
    """Test the PhaseState dataclass."""

    def test_phase_state_creation(self):
        """Test creating a PhaseState instance."""
        # When - Creating a phase state
        state = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )

        # Then - All attributes should be set correctly
        assert state.phase_type == PhaseType.CONTINUOUS
        assert state.is_order_submission_allowed is True
        assert state.is_order_cancellation_allowed is True
        assert state.is_matching_enabled is True
        assert state.execution_style == "continuous"

    def test_phase_state_from_closed_phase_type(self):
        """Test creating PhaseState for CLOSED phase."""
        # Given - Config for closed phase
        config = PhaseStateConfig(
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=False,
            execution_style="none",
        )

        # When - Creating state from phase type
        state = PhaseState.from_phase_type(PhaseType.CLOSED, config)

        # Then - State should reflect closed market
        assert state.phase_type == PhaseType.CLOSED
        assert state.is_order_submission_allowed is False
        assert state.is_order_cancellation_allowed is False
        assert state.is_matching_enabled is False
        assert state.execution_style == "none"

    def test_phase_state_from_pre_open_phase_type(self):
        """Test creating PhaseState for PRE_OPEN phase."""
        # Given - Config for pre-open phase
        config = PhaseStateConfig(
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="none",
        )

        # When - Creating state from phase type
        state = PhaseState.from_phase_type(PhaseType.PRE_OPEN, config)

        # Then - State should allow orders but no matching
        assert state.phase_type == PhaseType.PRE_OPEN
        assert state.is_order_submission_allowed is True
        assert state.is_order_cancellation_allowed is True
        assert state.is_matching_enabled is False
        assert state.execution_style == "none"

    def test_phase_state_from_continuous_phase_type(self):
        """Test creating PhaseState for CONTINUOUS phase."""
        # Given - Config for continuous phase
        config = PhaseStateConfig(
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )

        # When - Creating state from phase type
        state = PhaseState.from_phase_type(PhaseType.CONTINUOUS, config)

        # Then - State should allow everything
        assert state.phase_type == PhaseType.CONTINUOUS
        assert state.is_order_submission_allowed is True
        assert state.is_order_cancellation_allowed is True
        assert state.is_matching_enabled is True
        assert state.execution_style == "continuous"

    def test_phase_state_with_custom_config(self):
        """Test that PhaseState respects custom configuration."""
        # Given - Custom config with unusual settings
        config = PhaseStateConfig(
            is_order_submission_allowed=False,  # No new orders
            is_order_cancellation_allowed=True,  # But can cancel
            is_matching_enabled=True,  # And matching continues
            execution_style="batch",  # With batch execution
        )

        # When - Creating state with custom config
        state = PhaseState.from_phase_type(PhaseType.CONTINUOUS, config)

        # Then - State should use the custom config values
        assert state.phase_type == PhaseType.CONTINUOUS
        assert state.is_order_submission_allowed is False
        assert state.is_order_cancellation_allowed is True
        assert state.is_matching_enabled is True
        assert state.execution_style == "batch"

    def test_phase_state_equality(self):
        """Test PhaseState equality comparison."""
        # Given - Two identical phase states
        config = PhaseStateConfig(True, True, True, "continuous")
        state1 = PhaseState.from_phase_type(PhaseType.CONTINUOUS, config)
        state2 = PhaseState.from_phase_type(PhaseType.CONTINUOUS, config)

        # Then - They should be equal
        assert state1 == state2

        # Given - Different phase states
        state3 = PhaseState.from_phase_type(
            PhaseType.PRE_OPEN, PhaseStateConfig(True, True, False, "none")
        )

        # Then - They should not be equal
        assert state1 != state3
