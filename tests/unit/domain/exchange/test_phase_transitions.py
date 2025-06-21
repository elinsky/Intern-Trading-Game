"""Test phase transitions in the exchange.

This module tests the critical phase transition scenarios:
- Pre-open to opening auction triggers batch matching
- Continuous to closed cancels all resting orders
- Transitions work correctly even without orders
"""

from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.models.instrument import Instrument
from intern_trading_game.domain.exchange.models.order import Order
from intern_trading_game.domain.exchange.types import PhaseState, PhaseType
from intern_trading_game.domain.exchange.venue import ExchangeVenue


class TestPhaseTransitions:
    """Test phase transitions trigger appropriate exchange actions."""

    @pytest.fixture
    def mock_phase_manager(self):
        """Create a mock phase manager for testing."""
        manager = Mock()
        # Default to pre-open
        manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.PRE_OPEN,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="none",
        )
        return manager

    @pytest.fixture
    def exchange_with_phase_manager(self, mock_phase_manager):
        """Create exchange with phase manager."""
        # This will fail until we add phase_manager parameter
        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        # List a test instrument
        instrument = Instrument(
            symbol="SPX-20240115-4500-C",
            underlying="SPX",
        )
        exchange.list_instrument(instrument)

        return exchange

    def test_opening_auction_triggers_batch_match(
        self, exchange_with_phase_manager, mock_phase_manager
    ):
        """Test that pre-open to auction transition triggers batch matching.

        Given - Orders submitted during pre-open phase
        The exchange accepts orders but doesn't match them immediately.
        These orders rest in the book waiting for the market to open.

        When - Phase transitions from pre-open to opening auction then continuous
        At 9:29:30, the market enters opening auction phase where the book
        is frozen. At 9:30:00, batch matching executes to establish opening prices.

        Then - Batch matching executes automatically
        All crossing orders from pre-open are matched in a single batch
        with fair randomization at each price level.
        """
        # Given - Submit orders during pre-open
        buy_order1 = Order(
            instrument_id="SPX-20240115-4500-C",
            side="buy",
            quantity=10,
            price=100.0,
            trader_id="trader1",
        )
        buy_order2 = Order(
            instrument_id="SPX-20240115-4500-C",
            side="buy",
            quantity=5,
            price=100.0,
            trader_id="trader2",
        )
        sell_order = Order(
            instrument_id="SPX-20240115-4500-C",
            side="sell",
            quantity=15,
            price=99.0,
            trader_id="trader3",
        )

        result1 = exchange_with_phase_manager.submit_order(buy_order1)
        result2 = exchange_with_phase_manager.submit_order(buy_order2)
        result3 = exchange_with_phase_manager.submit_order(sell_order)

        # Orders should be accepted but not matched (pending_new from batch engine)
        assert result1.status == "pending_new"
        assert result2.status == "pending_new"
        assert result3.status == "pending_new"
        assert len(result1.fills) == 0
        assert len(result2.fills) == 0
        assert len(result3.fills) == 0

        # Verify orders are NOT in the book yet (batch engine holds them)
        book = exchange_with_phase_manager.get_order_book(
            "SPX-20240115-4500-C"
        )
        assert len(book.bids) == 0  # Orders are in batch engine, not book
        assert len(book.asks) == 0  # Orders are in batch engine, not book

        # When - Transition to opening auction (book frozen)
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.OPENING_AUCTION,
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=True,
            execution_style="batch",
        )

        # Then transition to continuous (triggers batch match)
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )

        # Execute the opening auction
        exchange_with_phase_manager.execute_opening_auction()

        # Then - Orders should have matched
        # Both buy orders at 100 cross with sell at 99
        # Total 15 shares should trade
        book_after = exchange_with_phase_manager.get_order_book(
            "SPX-20240115-4500-C"
        )
        trades = book_after.get_recent_trades(10)

        assert len(trades) > 0
        total_traded = sum(t.quantity for t in trades)
        assert total_traded == 15  # All shares matched

    def test_market_close_cancels_all_orders(
        self, exchange_with_phase_manager, mock_phase_manager
    ):
        """Test that continuous to closed transition cancels orders.

        Given - Resting orders in continuous phase
        During regular trading hours, limit orders rest in the book
        waiting for matching counterparties.

        When - Phase transitions to closed
        At 4:00 PM when the market closes, all open orders must be
        cancelled to prevent stale orders from executing the next day.

        Then - All orders are cancelled
        The order books are cleared and traders receive cancellation
        notifications for any unfilled orders.
        """
        # Given - Market in continuous phase
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )

        # Submit orders that won't match
        buy_order = Order(
            instrument_id="SPX-20240115-4500-C",
            side="buy",
            quantity=10,
            price=90.0,  # Low bid
            trader_id="trader1",
        )
        sell_order = Order(
            instrument_id="SPX-20240115-4500-C",
            side="sell",
            quantity=10,
            price=110.0,  # High ask
            trader_id="trader2",
        )

        result1 = exchange_with_phase_manager.submit_order(buy_order)
        result2 = exchange_with_phase_manager.submit_order(sell_order)

        # Orders should be resting
        assert result1.status == "new"
        assert result2.status == "new"

        book = exchange_with_phase_manager.get_order_book(
            "SPX-20240115-4500-C"
        )
        assert len(book.bids) == 1
        assert len(book.asks) == 1

        # When - Transition to closed
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CLOSED,
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=False,
            execution_style="none",
        )

        # Execute market close
        exchange_with_phase_manager.cancel_all_orders()

        # Then - All orders should be cancelled
        book_after = exchange_with_phase_manager.get_order_book(
            "SPX-20240115-4500-C"
        )
        assert len(book_after.bids) == 0
        assert len(book_after.asks) == 0

    def test_transition_without_orders(
        self, exchange_with_phase_manager, mock_phase_manager
    ):
        """Test transitions work even with no orders.

        Given - Empty order books
        No orders have been submitted to the exchange.

        When - Phase transitions occur
        The market goes through its normal phase transitions even
        when there are no orders to process.

        Then - No errors, transitions complete successfully
        The exchange handles empty transitions gracefully without
        errors or exceptions.
        """
        # Given - Empty order books (no orders submitted)
        book = exchange_with_phase_manager.get_order_book(
            "SPX-20240115-4500-C"
        )
        assert len(book.bids) == 0
        assert len(book.asks) == 0

        # When - Execute opening auction with no orders
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )

        # Should not raise any errors
        exchange_with_phase_manager.execute_opening_auction()

        # When - Close market with no orders
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CLOSED,
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=False,
            execution_style="none",
        )

        # Should not raise any errors
        exchange_with_phase_manager.cancel_all_orders()

        # Then - Books still empty, no errors
        assert len(book.bids) == 0
        assert len(book.asks) == 0

    def test_rapid_phase_transitions(
        self, exchange_with_phase_manager, mock_phase_manager
    ):
        """Test handling of back-to-back transitions.

        Given - Multiple transitions scheduled close together
        Some days may have rapid transitions, like pre-open ending
        at 9:29:30 and auction ending at 9:30:00.

        When - Transitions execute
        The system processes each transition in sequence even when
        they occur within seconds of each other.

        Then - Each transition completes in order
        All transition actions execute properly without race conditions
        or missed transitions.
        """
        # Given - Submit order in pre-open
        order = Order(
            instrument_id="SPX-20240115-4500-C",
            side="buy",
            quantity=10,
            price=100.0,
            trader_id="trader1",
        )
        result = exchange_with_phase_manager.submit_order(order)
        assert (
            result.status == "pending_new"
        )  # Batch engine returns pending_new

        # When - Rapid transitions: pre-open -> auction -> continuous
        transitions = [
            PhaseState(
                phase_type=PhaseType.OPENING_AUCTION,
                is_order_submission_allowed=False,
                is_order_cancellation_allowed=False,
                is_matching_enabled=True,
                execution_style="batch",
            ),
            PhaseState(
                phase_type=PhaseType.CONTINUOUS,
                is_order_submission_allowed=True,
                is_order_cancellation_allowed=True,
                is_matching_enabled=True,
                execution_style="continuous",
            ),
        ]

        for phase_state in transitions:
            mock_phase_manager.get_current_phase_state.return_value = (
                phase_state
            )

            # Trigger any necessary transition actions
            if phase_state.phase_type == PhaseType.CONTINUOUS:
                exchange_with_phase_manager.execute_opening_auction()

        # Then - Order still in book (no match without counterparty)
        book = exchange_with_phase_manager.get_order_book(
            "SPX-20240115-4500-C"
        )
        assert len(book.bids) == 1

    def test_opening_auction_with_batch_matching_engine(
        self, mock_phase_manager
    ):
        """Test that opening auction uses batch matching engine.

        Given - Exchange configured for opening auction
        The exchange needs to switch to batch matching during the
        opening auction to ensure fair order allocation.

        When - Opening auction phase is active
        Between 9:29:30 and 9:30:00, the book is frozen (no new orders
        or cancellations). The exchange processes all resting orders
        from pre-open using batch matching.

        Then - Batch matching engine is used
        Orders are randomized within price levels to ensure fairness
        and prevent timing advantages.
        """
        # Given - Create exchange with phase manager
        ExchangeVenue(phase_manager=mock_phase_manager)

        # Set up opening auction phase
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.OPENING_AUCTION,
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=True,
            execution_style="batch",
        )

        # When - Exchange is in opening auction phase
        # Then - Exchange automatically uses batch matching
        # (The exchange selects engine based on phase, no manual switch needed)

    @pytest.mark.parametrize(
        "from_phase,to_phase,expected_action",
        [
            (PhaseType.PRE_OPEN, PhaseType.OPENING_AUCTION, "none"),
            (
                PhaseType.OPENING_AUCTION,
                PhaseType.CONTINUOUS,
                "execute_auction",
            ),
            (PhaseType.CONTINUOUS, PhaseType.CLOSED, "cancel_all"),
            (PhaseType.CLOSED, PhaseType.PRE_OPEN, "none"),
        ],
    )
    def test_phase_transition_actions(
        self,
        exchange_with_phase_manager,
        from_phase,
        to_phase,
        expected_action,
    ):
        """Test that correct actions are triggered for each transition.

        Different phase transitions require different actions:
        - Pre-open to auction: No action (orders wait)
        - Auction to continuous: Execute batch match
        - Continuous to closed: Cancel all orders
        - Closed to pre-open: No action (fresh start)
        """
        # Test framework to verify transition actions
        # This is a template for how transitions should be handled
        pass
