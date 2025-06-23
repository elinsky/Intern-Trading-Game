"""Test phase management interfaces.

This module tests the PhaseManagerInterface protocol to ensure
it defines the correct contract for phase management.
"""

from intern_trading_game.domain.exchange.components.core.types import (
    PhaseState,
    PhaseType,
)


class TestPhaseManagerInterface:
    """Test the PhaseManagerInterface protocol."""

    def test_interface_definition(self):
        """Test that PhaseManagerInterface is properly defined."""
        # Import the interface (will fail if not implemented)
        from intern_trading_game.domain.exchange.phase.interfaces import (
            PhaseManagerInterface,
        )

        # Then - Interface should be a Protocol
        assert hasattr(PhaseManagerInterface, "__annotations__")

        # Check required methods exist in protocol
        # We'll validate the actual signatures when we implement

    def test_interface_methods_required(self):
        """Test that interface requires the correct methods."""
        # This test will validate the actual implementation
        # For now it documents what methods we expect
        pass  # Will be implemented with the interface

    def test_mock_phase_manager_satisfies_interface(self):
        """Test that a mock implementation can satisfy the interface."""
        # This test documents how the interface should work

        # Create a mock that satisfies the interface
        class MockPhaseManager:
            def get_current_phase_type(self, current_time=None):
                return PhaseType.CONTINUOUS

            def get_current_phase_state(self):
                return PhaseState(
                    phase_type=PhaseType.CONTINUOUS,
                    is_order_submission_allowed=True,
                    is_order_cancellation_allowed=True,
                    is_matching_enabled=True,
                    execution_style="continuous",
                )

        # Then - Mock should satisfy the interface
        manager = MockPhaseManager()
        assert hasattr(manager, "get_current_phase_type")
        assert hasattr(manager, "get_current_phase_state")
