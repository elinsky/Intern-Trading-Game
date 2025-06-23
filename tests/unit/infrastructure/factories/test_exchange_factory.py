"""Behavior tests for exchange factory functionality."""

from unittest.mock import Mock

from intern_trading_game.domain.exchange.book.matching_engine import (
    BatchMatchingEngine,
    ContinuousMatchingEngine,
)
from intern_trading_game.domain.exchange.types import PhaseState, PhaseType
from intern_trading_game.domain.exchange.venue import ExchangeVenue
from intern_trading_game.infrastructure.config.models import ExchangeConfig
from intern_trading_game.infrastructure.factories.exchange_factory import (
    ExchangeFactory,
)


class TestExchangeFactory:
    """Test exchange creation from configuration."""

    def _create_mock_phase_manager(self, execution_style: str):
        """Create a mock phase manager for testing.

        Parameters
        ----------
        execution_style : str
            Either "continuous" or "batch"

        Returns
        -------
        Mock
            A mock phase manager that returns consistent phase state
        """
        manager = Mock()
        phase_type = (
            PhaseType.CONTINUOUS
            if execution_style == "continuous"
            else PhaseType.OPENING_AUCTION
        )
        manager.get_current_phase_state.return_value = PhaseState(
            phase_type=phase_type,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style=execution_style,
        )
        return manager

    def test_create_continuous_exchange(self):
        """Test creating exchange with continuous matching engine.

        Given - Config specifying continuous matching mode
        When - Factory creates exchange from config
        Then - Exchange has continuous matching engine
        """
        # Given - Config for continuous mode
        config = ExchangeConfig(matching_mode="continuous")
        test_phase_manager = self._create_mock_phase_manager("continuous")

        # When - Create exchange with test phase manager
        exchange = ExchangeFactory.create_from_config(
            config, test_phase_manager
        )

        # Then - Should have continuous matching mode
        assert isinstance(exchange, ExchangeVenue)
        assert exchange.get_matching_mode() == "continuous"
        assert isinstance(exchange.matching_engine, ContinuousMatchingEngine)

    def test_create_batch_exchange(self):
        """Test creating exchange with batch matching engine.

        Given - Config specifying batch matching mode
        When - Factory creates exchange from config
        Then - Exchange has batch matching engine
        """
        # Given - Config for batch mode
        config = ExchangeConfig(matching_mode="batch")
        test_phase_manager = self._create_mock_phase_manager("batch")

        # When - Create exchange with test phase manager
        exchange = ExchangeFactory.create_from_config(
            config, test_phase_manager
        )

        # Then - Should have batch matching mode
        assert isinstance(exchange, ExchangeVenue)
        assert exchange.get_matching_mode() == "batch"
        assert isinstance(exchange.matching_engine, BatchMatchingEngine)

    def test_exchange_starts_empty(self):
        """Test that newly created exchange has no instruments.

        Given - Any valid config
        When - Factory creates exchange
        Then - Exchange has no instruments listed
        """
        # Given - Config (mode doesn't matter)
        config = ExchangeConfig(matching_mode="continuous")
        test_phase_manager = self._create_mock_phase_manager("continuous")

        # When - Create exchange with test phase manager
        exchange = ExchangeFactory.create_from_config(
            config, test_phase_manager
        )

        # Then - Should have no instruments
        assert len(exchange.get_all_instruments()) == 0
        assert len(exchange.instruments) == 0
        assert len(exchange.order_books) == 0

    def test_multiple_exchanges_are_independent(self):
        """Test that factory creates independent exchange instances.

        Given - Same config used twice
        When - Factory creates two exchanges
        Then - They are separate instances with separate state
        """
        # Given - Same config and test phase managers
        config = ExchangeConfig(matching_mode="continuous")
        test_phase_manager1 = self._create_mock_phase_manager("continuous")
        test_phase_manager2 = self._create_mock_phase_manager("continuous")

        # When - Create two exchanges with test phase managers
        exchange1 = ExchangeFactory.create_from_config(
            config, test_phase_manager1
        )
        exchange2 = ExchangeFactory.create_from_config(
            config, test_phase_manager2
        )

        # Then - Should be different instances
        assert exchange1 is not exchange2
        assert exchange1.matching_engine is not exchange2.matching_engine

        # Then - State should be independent
        from intern_trading_game.domain.exchange.models.instrument import (
            Instrument,
        )

        test_instrument = Instrument(
            symbol="TEST", strike=100.0, option_type="call", underlying="TEST"
        )
        exchange1.list_instrument(test_instrument)

        assert len(exchange1.instruments) == 1
        assert len(exchange2.instruments) == 0
