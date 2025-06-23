"""Test exchange integration with phase management.

This module tests how the exchange service integrates with the phase
manager to enforce trading rules based on market phases.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.components.core.models import Order
from intern_trading_game.domain.exchange.components.core.types import (
    PhaseState,
    PhaseType,
)


class TestExchangePhaseIntegration:
    """Test exchange behavior under different market phases."""

    @pytest.fixture
    def mock_phase_manager(self):
        """Create a mock phase manager for testing."""
        manager = Mock()
        # Default to continuous trading
        manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )
        return manager

    @pytest.fixture
    def sample_order(self) -> Order:
        """Create a sample order for testing."""
        return Order(
            instrument_id="SPX-20240115-4500-C",
            side="buy",
            quantity=10,
            price=100.0,
            trader_id="trader1",
            order_type="limit",
        )

    @pytest.mark.skip(
        reason="ExchangeVenue doesn't support phase_manager parameter yet"
    )
    def test_exchange_accepts_phase_manager_in_constructor(self):
        """Test that exchange can be created with a phase manager."""
        # Given - A phase manager
        from intern_trading_game.domain.exchange.phase.manager import (
            ConfigDrivenPhaseManager,
        )
        from intern_trading_game.infrastructure.config.models import (
            MarketPhasesConfig,
        )

        config = MarketPhasesConfig(
            timezone="America/Chicago", schedule={}, phase_states={}
        )
        phase_manager = ConfigDrivenPhaseManager(config)

        # When - Creating exchange with phase manager
        # This will fail until we add phase_manager parameter
        from intern_trading_game.domain.exchange.venue import ExchangeVenue

        exchange = ExchangeVenue(phase_manager=phase_manager)

        # Then - Exchange should have phase manager
        assert exchange.phase_manager is phase_manager

    @pytest.mark.skip(reason="ExchangeVenue doesn't check phase state yet")
    def test_order_rejected_when_market_closed(
        self, mock_phase_manager, sample_order
    ):
        """Test that orders are rejected during CLOSED phase."""
        # Given - Market is closed
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CLOSED,
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=False,
            execution_style="none",
        )

        # When - Submitting order during closed phase
        from intern_trading_game.domain.exchange.venue import ExchangeVenue

        exchange = ExchangeVenue(phase_manager=mock_phase_manager)
        result = exchange.submit_order(sample_order)

        # Then - Order should be rejected with appropriate reason
        assert result.status == "rejected"
        assert result.error_message is not None
        assert "market closed" in result.error_message.lower()

    @pytest.mark.skip(
        reason="ExchangeVenue doesn't check phase state for matching yet"
    )
    def test_order_accepted_but_not_matched_during_pre_open(
        self, mock_phase_manager, sample_order
    ):
        """Test pre-open behavior: accept orders but don't match."""
        # Given - Market is in pre-open
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.PRE_OPEN,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="none",
        )

        # When - Submitting order during pre-open
        from intern_trading_game.domain.exchange.venue import ExchangeVenue

        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        # First list the instrument
        from intern_trading_game.domain.models import OptionInstrument

        instrument = OptionInstrument(
            id=sample_order.instrument_id,
            symbol="SPX",
            expiration=datetime(2024, 1, 15),
            strike=4500.0,
            option_type="call",
        )
        exchange.list_instrument(instrument)

        result = exchange.submit_order(sample_order)

        # Then - Order should be accepted but remain in book
        assert result.status == "new"
        assert result.order_id is not None
        assert len(result.fills) == 0  # No fills during pre-open

        # And - Order should be in the book
        order_book = exchange.get_order_book(sample_order.instrument_id)
        assert len(order_book.bids) == 1

    @pytest.mark.skip(reason="ExchangeVenue doesn't check phase state yet")
    def test_order_matched_during_continuous_trading(
        self, mock_phase_manager, sample_order
    ):
        """Test that orders are matched during continuous phase."""
        # Given - Market is in continuous trading
        # (default state from fixture)

        # When - Submitting matching buy and sell orders
        from intern_trading_game.domain.exchange.venue import ExchangeVenue

        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        # List the instrument first
        from intern_trading_game.domain.models import OptionInstrument

        instrument = OptionInstrument(
            id=sample_order.instrument_id,
            symbol="SPX",
            expiration=datetime(2024, 1, 15),
            strike=4500.0,
            option_type="call",
        )
        exchange.list_instrument(instrument)

        # Submit buy order
        _buy_result = exchange.submit_order(sample_order)  # For documentation

        # Submit matching sell order
        sell_order = Order(
            instrument_id="SPX-20240115-4500-C",
            side="sell",
            quantity=10,
            price=100.0,
            trader_id="trader2",
            order_type="limit",
        )
        sell_result = exchange.submit_order(sell_order)

        # Then - Orders should match
        assert sell_result.status == "filled"
        assert len(sell_result.fills) == 1
        assert sell_result.fills[0].quantity == 10
        assert sell_result.fills[0].price == 100.0

    @pytest.mark.skip(
        reason="ExchangeVenue doesn't check phase state for cancellations yet"
    )
    def test_cancellation_rejected_when_not_allowed(
        self, mock_phase_manager, sample_order
    ):
        """Test that cancellations are rejected when phase disallows."""
        # Given - Market phase that doesn't allow cancellations
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CLOSED,
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=False,
            execution_style="none",
        )

        # When - Trying to cancel an order
        from intern_trading_game.domain.exchange.venue import ExchangeVenue

        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        # Try to cancel (even though no order exists)
        success = exchange.cancel_order("some-order-id", "trader1")

        # Then - Cancellation should fail
        assert success is False

    @pytest.mark.skip(
        reason="ExchangeVenue doesn't implement get_current_phase_state yet"
    )
    def test_exchange_get_current_phase_state(self, mock_phase_manager):
        """Test that exchange exposes current phase state."""
        # Given - Exchange with phase manager
        from intern_trading_game.domain.exchange.venue import ExchangeVenue

        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        # When - Getting current phase state
        phase_state = exchange.get_current_phase_state()

        # Then - Should return phase manager's state
        assert phase_state.phase_type == PhaseType.CONTINUOUS
        assert phase_state.is_matching_enabled is True
        mock_phase_manager.get_current_phase_state.assert_called_once()

    @pytest.mark.skip(reason="ExchangeVenue doesn't check phase state yet")
    def test_phase_transition_during_operation(
        self, mock_phase_manager, sample_order
    ):
        """Test exchange behavior when phase changes during operation."""
        # Given - Exchange starting in pre-open
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.PRE_OPEN,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="none",
        )

        from intern_trading_game.domain.exchange.venue import ExchangeVenue

        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        # List instrument
        from intern_trading_game.domain.models import OptionInstrument

        instrument = OptionInstrument(
            id=sample_order.instrument_id,
            symbol="SPX",
            expiration=datetime(2024, 1, 15),
            strike=4500.0,
            option_type="call",
        )
        exchange.list_instrument(instrument)

        # Submit order during pre-open
        result = exchange.submit_order(sample_order)
        assert result.status == "new"

        # When - Phase transitions to continuous
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )

        # And - Matching order arrives
        sell_order = Order(
            instrument_id="SPX-20240115-4500-C",
            side="sell",
            quantity=10,
            price=100.0,
            trader_id="trader2",
            order_type="limit",
        )
        sell_result = exchange.submit_order(sell_order)

        # Then - Orders should now match
        assert sell_result.status == "filled"

    @pytest.mark.parametrize(
        "phase_type,expected_behavior",
        [
            (
                PhaseType.CLOSED,
                {
                    "submit_allowed": False,
                    "cancel_allowed": False,
                    "matching_enabled": False,
                },
            ),
            (
                PhaseType.PRE_OPEN,
                {
                    "submit_allowed": True,
                    "cancel_allowed": True,
                    "matching_enabled": False,
                },
            ),
            (
                PhaseType.CONTINUOUS,
                {
                    "submit_allowed": True,
                    "cancel_allowed": True,
                    "matching_enabled": True,
                },
            ),
        ],
    )
    @pytest.mark.skip(reason="ExchangeVenue doesn't enforce phase rules yet")
    def test_phase_rules_enforcement(
        self, mock_phase_manager, sample_order, phase_type, expected_behavior
    ):
        """Test that exchange enforces phase-specific rules."""
        # Given - Specific phase configuration
        phase_states = {
            PhaseType.CLOSED: PhaseState(
                phase_type=PhaseType.CLOSED,
                is_order_submission_allowed=False,
                is_order_cancellation_allowed=False,
                is_matching_enabled=False,
                execution_style="none",
            ),
            PhaseType.PRE_OPEN: PhaseState(
                phase_type=PhaseType.PRE_OPEN,
                is_order_submission_allowed=True,
                is_order_cancellation_allowed=True,
                is_matching_enabled=False,
                execution_style="none",
            ),
            PhaseType.CONTINUOUS: PhaseState(
                phase_type=PhaseType.CONTINUOUS,
                is_order_submission_allowed=True,
                is_order_cancellation_allowed=True,
                is_matching_enabled=True,
                execution_style="continuous",
            ),
        }

        mock_phase_manager.get_current_phase_state.return_value = phase_states[
            phase_type
        ]

        # When - Testing exchange operations
        from intern_trading_game.domain.exchange.venue import ExchangeVenue

        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        # List instrument if needed
        if expected_behavior["submit_allowed"]:
            from intern_trading_game.domain.models import OptionInstrument

            instrument = OptionInstrument(
                id=sample_order.instrument_id,
                symbol="SPX",
                expiration=datetime(2024, 1, 15),
                strike=4500.0,
                option_type="call",
            )
            exchange.list_instrument(instrument)

        # Test order submission
        result = exchange.submit_order(sample_order)
        if expected_behavior["submit_allowed"]:
            assert result.status in ["new", "filled"]
        else:
            assert result.status == "rejected"

        # Test if matching would occur (for continuous phase with two orders)
        if (
            expected_behavior["submit_allowed"]
            and expected_behavior["matching_enabled"]
        ):
            sell_order = Order(
                instrument_id="SPX-20240115-4500-C",
                side="sell",
                quantity=10,
                price=100.0,
                trader_id="trader2",
                order_type="limit",
            )
            sell_result = exchange.submit_order(sell_order)
            assert sell_result.status == "filled"
