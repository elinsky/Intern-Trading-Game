"""Behavior tests for exchange factory functionality."""

from unittest.mock import Mock, patch

from intern_trading_game.domain.exchange.book.matching_engine import (
    ContinuousMatchingEngine,
)
from intern_trading_game.domain.exchange.types import PhaseState, PhaseType
from intern_trading_game.domain.exchange.venue import ExchangeVenue
from intern_trading_game.infrastructure.config.models import ExchangeConfig
from intern_trading_game.infrastructure.factories.exchange_factory import (
    ExchangeVenueFactory,
)


class TestExchangeVenueFactory:
    """Test exchange creation from configuration."""

    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ConfigDrivenPhaseManager"
    )
    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ConfigLoader"
    )
    def test_create_continuous_exchange(
        self, mock_config_loader, mock_phase_manager_class
    ):
        """Test creating exchange with continuous matching engine.

        Given - Config specifying continuous matching mode
        When - Factory creates exchange from config
        Then - Exchange has continuous matching engine
        """
        # Given - Config and mock phase manager
        config = ExchangeConfig()

        # Set up mock phase manager to return continuous phase
        mock_phase_manager = Mock()
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )
        mock_phase_manager_class.return_value = mock_phase_manager

        # When - Create exchange
        exchange = ExchangeVenueFactory.create_from_config(config)

        # Then - Should have continuous matching mode
        assert isinstance(exchange, ExchangeVenue)
        assert exchange.get_matching_mode() == "continuous"
        # Exchange has both engines available
        assert isinstance(
            exchange._continuous_engine, ContinuousMatchingEngine
        )

    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ConfigDrivenPhaseManager"
    )
    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ConfigLoader"
    )
    def test_create_batch_exchange(
        self, mock_config_loader, mock_phase_manager_class
    ):
        """Test creating exchange with batch matching engine.

        Given - Config specifying batch matching mode
        When - Factory creates exchange from config
        Then - Exchange has batch matching engine
        """
        # Given - Config and mock phase manager
        config = ExchangeConfig()

        # Set up mock phase manager to return batch phase
        mock_phase_manager = Mock()
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.OPENING_AUCTION,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="batch",
        )
        mock_phase_manager_class.return_value = mock_phase_manager

        # When - Create exchange
        exchange = ExchangeVenueFactory.create_from_config(config)

        # Then - Should have batch matching mode from phase
        assert isinstance(exchange, ExchangeVenue)
        assert exchange.get_matching_mode() == "batch"
        # Exchange has both engines available
        assert hasattr(exchange, "_continuous_engine")
        assert hasattr(exchange, "_batch_engine")

    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ConfigDrivenPhaseManager"
    )
    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ConfigLoader"
    )
    def test_exchange_starts_empty(
        self, mock_config_loader, mock_phase_manager_class
    ):
        """Test that newly created exchange has no instruments.

        Given - Any valid config
        When - Factory creates exchange
        Then - Exchange has no instruments listed
        """
        # Given - Config and mock phase manager
        config = ExchangeConfig()

        # Set up mock phase manager
        mock_phase_manager = Mock()
        mock_phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )
        mock_phase_manager_class.return_value = mock_phase_manager

        # When - Create exchange
        exchange = ExchangeVenueFactory.create_from_config(config)

        # Then - Should have no instruments
        assert len(exchange.get_all_instruments()) == 0
        assert len(exchange.instruments) == 0
        assert len(exchange.order_books) == 0

    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ConfigDrivenPhaseManager"
    )
    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ConfigLoader"
    )
    def test_multiple_exchanges_are_independent(
        self, mock_config_loader, mock_phase_manager_class
    ):
        """Test that factory creates independent exchange instances.

        Given - Same config used twice
        When - Factory creates two exchanges
        Then - They are separate instances with separate state
        """
        # Given - Same config and set up mock phase manager
        config = ExchangeConfig()

        # Set up mock phase manager factory to return new instances
        def create_mock_phase_manager():
            mock = Mock()
            mock.get_current_phase_state.return_value = PhaseState(
                phase_type=PhaseType.CONTINUOUS,
                is_order_submission_allowed=True,
                is_order_cancellation_allowed=True,
                is_matching_enabled=True,
                execution_style="continuous",
            )
            return mock

        mock_phase_manager_class.side_effect = [
            create_mock_phase_manager(),
            create_mock_phase_manager(),
        ]

        # When - Create two exchanges
        exchange1 = ExchangeVenueFactory.create_from_config(config)
        exchange2 = ExchangeVenueFactory.create_from_config(config)

        # Then - Should be different instances
        assert exchange1 is not exchange2
        assert exchange1._continuous_engine is not exchange2._continuous_engine

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
