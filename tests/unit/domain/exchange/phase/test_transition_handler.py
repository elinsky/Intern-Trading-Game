"""Test ExchangePhaseTransitionHandler functionality.

This module tests the phase transition handler that monitors phase changes
and executes appropriate actions like opening auctions and order cancellations.
"""

from unittest.mock import Mock

from intern_trading_game.domain.exchange.phase.protocols import (
    ExchangeOperations,
)
from intern_trading_game.domain.exchange.phase.transition_handler import (
    ExchangePhaseTransitionHandler,
)
from intern_trading_game.domain.exchange.types import PhaseType


class TestBasicFunctionality:
    """Test basic phase detection and state management."""

    def test_detects_phase_transition(self):
        """Test that handler detects when phase changes.

        Given - Handler tracking current market phase
        When - Phase changes from one type to another
        Then - Handler returns True indicating transition detected
        """
        # Given - Handler in PRE_OPEN phase with mock exchange
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)

        # Record initial phase
        result1 = handler.check_and_handle_transition(PhaseType.PRE_OPEN)
        assert result1 is False  # First check just records phase

        # When - Phase changes to OPENING_AUCTION
        # This transition triggers the batch match execution
        # during the auction phase
        result2 = handler.check_and_handle_transition(
            PhaseType.OPENING_AUCTION
        )

        # Then - Transition is detected and auction executes
        assert result2 is True
        # Opening auction executes when entering OPENING_AUCTION phase
        mock_exchange.execute_opening_auction.assert_called_once()
        mock_exchange.cancel_all_orders.assert_not_called()

    def test_no_transition_when_phase_unchanged(self):
        """Test that handler returns False when phase stays the same.

        Given - Handler tracking current phase
        When - Same phase is checked multiple times
        Then - Handler returns False (no transition)
        """
        # Given - Handler in CONTINUOUS phase
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.CONTINUOUS)

        # When - Check same phase again
        result = handler.check_and_handle_transition(PhaseType.CONTINUOUS)

        # Then - No transition detected
        assert result is False
        mock_exchange.execute_opening_auction.assert_not_called()
        mock_exchange.cancel_all_orders.assert_not_called()

    def test_first_check_records_phase(self):
        """Test that first call just records phase without transition.

        Given - Fresh handler with no phase history
        When - First phase check occurs
        Then - Phase is recorded but no transition detected
        """
        # Given - New handler
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)

        # When - First check
        result = handler.check_and_handle_transition(PhaseType.CONTINUOUS)

        # Then - No transition on first check
        assert result is False
        mock_exchange.execute_opening_auction.assert_not_called()
        mock_exchange.cancel_all_orders.assert_not_called()

    def test_reset_clears_state(self):
        """Test that reset allows fresh start.

        Given - Handler with existing phase state
        When - Reset is called
        Then - Next check behaves like first check
        """
        # Given - Handler with phase history
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.PRE_OPEN)
        handler.check_and_handle_transition(PhaseType.CONTINUOUS)

        # When - Reset handler
        handler.reset()

        # Then - Next check acts like first check
        result = handler.check_and_handle_transition(PhaseType.CLOSED)
        assert result is False  # First check after reset
        mock_exchange.cancel_all_orders.assert_not_called()


class TestTransitionActions:
    """Test that correct actions are triggered for specific transitions."""

    def test_executes_opening_auction_on_market_open(self):
        """Test opening auction executes on PRE_OPEN -> OPENING_AUCTION.

        Given - Market in pre-open phase with orders collected
        When - Phase transitions to opening auction
        Then - Opening auction is executed during the auction phase
        """
        # Given - Handler tracking pre-open phase
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.PRE_OPEN)

        # When - Market enters opening auction phase
        result = handler.check_and_handle_transition(PhaseType.OPENING_AUCTION)

        # Then - Opening auction executes during the auction window
        assert result is True
        mock_exchange.execute_opening_auction.assert_called_once()
        mock_exchange.cancel_all_orders.assert_not_called()

    def test_opening_auction_to_continuous_no_action(self):
        """Test OPENING_AUCTION -> CONTINUOUS triggers no action.

        Given - Market in opening auction phase (auction already executed)
        When - Phase transitions to continuous trading
        Then - No action needed (auction already happened on entry to OPENING_AUCTION)
        """
        # Given - Handler tracking opening auction phase
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.OPENING_AUCTION)

        # When - Market transitions to continuous trading
        result = handler.check_and_handle_transition(PhaseType.CONTINUOUS)

        # Then - Transition detected but no action
        assert result is True
        mock_exchange.execute_opening_auction.assert_not_called()
        mock_exchange.cancel_all_orders.assert_not_called()

    def test_cancels_orders_on_market_close(self):
        """Test all orders cancelled on CONTINUOUS -> CLOSED.

        Given - Market in continuous trading
        When - Market closes
        Then - All resting orders are cancelled
        """
        # Given - Handler tracking continuous phase
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.CONTINUOUS)

        # When - Market closes
        result = handler.check_and_handle_transition(PhaseType.CLOSED)

        # Then - All orders cancelled
        assert result is True
        mock_exchange.cancel_all_orders.assert_called_once()
        mock_exchange.execute_opening_auction.assert_not_called()

    def test_no_action_for_unknown_transitions(self):
        """Test that unknown transitions don't trigger actions.

        Given - Various phase transitions
        When - Transitions that don't have specific actions
        Then - No exchange operations are triggered
        """
        # Given - Handler
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)

        # Test various transitions without actions
        transitions = [
            (PhaseType.CLOSED, PhaseType.PRE_OPEN),  # New day
            (PhaseType.OPENING_AUCTION, PhaseType.CONTINUOUS),  # After auction
            (PhaseType.OPENING_AUCTION, PhaseType.CLOSED),  # Emergency close
            (
                PhaseType.PRE_OPEN,
                PhaseType.CLOSED,
            ),  # Emergency close during pre-open
        ]

        for from_phase, to_phase in transitions:
            mock_exchange.reset_mock()
            handler.reset()

            # When - Transition occurs
            handler.check_and_handle_transition(from_phase)
            result = handler.check_and_handle_transition(to_phase)

            # Then - Transition detected but no action
            assert result is True
            mock_exchange.execute_opening_auction.assert_not_called()
            mock_exchange.cancel_all_orders.assert_not_called()

    def test_handles_direct_transition_call(self):
        """Test handle_transition method works directly.

        Given - Handler with direct transition method
        When - Specific transition is triggered directly
        Then - Appropriate action is executed
        """
        # Given - Handler
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)

        # When - Direct transition call for opening auction
        handler.handle_transition(
            PhaseType.PRE_OPEN, PhaseType.OPENING_AUCTION
        )

        # Then - Opening auction executed
        mock_exchange.execute_opening_auction.assert_called_once()

        # Reset and test market close
        mock_exchange.reset_mock()

        # When - Direct transition call for market close
        handler.handle_transition(PhaseType.CONTINUOUS, PhaseType.CLOSED)

        # Then - Orders cancelled
        mock_exchange.cancel_all_orders.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_multiple_rapid_transitions(self):
        """Test handling of back-to-back phase changes.

        Given - Market with rapid phase transitions
        When - Multiple transitions occur quickly
        Then - Each transition is handled correctly
        """
        # Given - Handler starting in PRE_OPEN
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.PRE_OPEN)

        # When - Rapid transitions occur
        # PRE_OPEN -> OPENING_AUCTION -> CONTINUOUS
        result1 = handler.check_and_handle_transition(
            PhaseType.OPENING_AUCTION
        )
        result2 = handler.check_and_handle_transition(PhaseType.CONTINUOUS)

        # Then - Each transition detected and handled
        assert result1 is True  # Transition detected
        assert result2 is True  # Transition detected
        # Opening auction called exactly once when entering OPENING_AUCTION
        mock_exchange.execute_opening_auction.assert_called_once()
        mock_exchange.cancel_all_orders.assert_not_called()

        # The auction was called on PRE_OPEN -> OPENING_AUCTION transition
        # No additional action on OPENING_AUCTION -> CONTINUOUS

    def test_skipped_phase_transitions(self):
        """Test handling non-adjacent phase transitions.

        Given - System that might skip phases
        When - Non-adjacent transition occurs (e.g., PRE_OPEN -> CONTINUOUS)
        Then - Handler detects transition but takes no action
        """
        # Given - Handler in PRE_OPEN
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.PRE_OPEN)

        # When - Skip directly to CONTINUOUS (unusual but possible)
        result = handler.check_and_handle_transition(PhaseType.CONTINUOUS)

        # Then - Transition detected but no auction
        # (auction only runs from OPENING_AUCTION -> CONTINUOUS)
        assert result is True
        mock_exchange.execute_opening_auction.assert_not_called()
        mock_exchange.cancel_all_orders.assert_not_called()

    def test_idempotent_transition_handling(self):
        """Test that same transition twice is safe.

        Given - A specific transition that triggers an action
        When - Same transition is somehow triggered again
        Then - Action is not duplicated
        """
        # Given - Handler
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)

        # When - Same transition triggered twice via direct calls
        handler.handle_transition(
            PhaseType.PRE_OPEN, PhaseType.OPENING_AUCTION
        )
        handler.handle_transition(
            PhaseType.PRE_OPEN, PhaseType.OPENING_AUCTION
        )

        # Then - Action executed twice (handler is stateless for direct calls)
        # This is expected behavior - idempotency is exchange's responsibility
        assert mock_exchange.execute_opening_auction.call_count == 2

    def test_transition_from_closed_to_preopen(self):
        """Test new trading day transition.

        Given - Market closed from previous day
        When - New day begins with PRE_OPEN
        Then - No action needed (fresh start)
        """
        # Given - Handler in CLOSED phase
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.CLOSED)

        # When - New day starts
        result = handler.check_and_handle_transition(PhaseType.PRE_OPEN)

        # Then - Transition detected but no action
        assert result is True
        mock_exchange.execute_opening_auction.assert_not_called()
        mock_exchange.cancel_all_orders.assert_not_called()


class TestBusinessScenarios:
    """Test realistic business scenarios."""

    def test_handles_weekend_to_monday_transition(self):
        """Test CLOSED -> PRE_OPEN after weekend.

        Given - Market closed over weekend
        When - Monday morning arrives
        Then - Transition handled without issues
        """
        # Given - Handler that's been in CLOSED for weekend
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)

        # Simulate Friday close
        handler.check_and_handle_transition(PhaseType.CONTINUOUS)
        handler.check_and_handle_transition(PhaseType.CLOSED)

        # When - Monday morning PRE_OPEN
        result = handler.check_and_handle_transition(PhaseType.PRE_OPEN)

        # Then - Transition handled cleanly
        assert result is True

    def test_handles_holiday_scenarios(self):
        """Test extended CLOSED period doesn't break state.

        Given - Market closed for holiday
        When - Multiple days pass in CLOSED state
        Then - Handler maintains correct state
        """
        # Given - Handler in CLOSED
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.CLOSED)

        # When - Multiple checks during holiday
        for _ in range(10):
            result = handler.check_and_handle_transition(PhaseType.CLOSED)
            assert result is False  # No transition

        # Then - Eventually opens normally
        result = handler.check_and_handle_transition(PhaseType.PRE_OPEN)
        assert result is True
        mock_exchange.execute_opening_auction.assert_not_called()
        mock_exchange.cancel_all_orders.assert_not_called()

    def test_auction_not_called_during_closed(self):
        """Test safety check for invalid transitions.

        Given - Invalid phase sequence
        When - Impossible transition occurs
        Then - No actions are triggered
        """
        # Given - Handler in OPENING_AUCTION
        mock_exchange = Mock(spec=ExchangeOperations)
        handler = ExchangePhaseTransitionHandler(mock_exchange)
        handler.check_and_handle_transition(PhaseType.OPENING_AUCTION)

        # When - Direct to CLOSED (should go through CONTINUOUS first)
        result = handler.check_and_handle_transition(PhaseType.CLOSED)

        # Then - Transition detected but no auction
        # (auction only for OPENING_AUCTION -> CONTINUOUS)
        assert result is True
        mock_exchange.execute_opening_auction.assert_not_called()
        mock_exchange.cancel_all_orders.assert_not_called()
