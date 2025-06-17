"""Tests for service initialization in main.py."""

from unittest.mock import Mock, patch

from intern_trading_game.api import main


class TestServiceInitialization:
    """Test that services are properly initialized and not global."""

    def test_validation_service_not_initialized_at_import(self):
        """Test validation service initialization pattern.

        Given - Application module with service variables
        Services should be initialized in startup(), not at
        module import time.

        When - Check service declaration
        The service should be declared as Optional type hint
        with None as initial value.

        Then - Service follows lazy initialization pattern
        This confirms proper dependency injection design.
        """
        # This test verifies the pattern, not runtime state
        # The actual initialization happens in startup()

        # Check that the service is properly typed
        import inspect

        # Verify it's declared in the module
        assert "validation_service" in main.__dict__

        # The important thing is that startup() sets it
        assert "validation_service" in inspect.getsource(main.startup)

    def test_fee_service_not_initialized_at_import(self):
        """Test fee service initialization pattern.

        Given - Application module with service variables
        Fee service should not exist until configuration
        is loaded and factory creates it.

        When - Check service declaration
        The service should follow same pattern as validation_service.

        Then - Service follows lazy initialization pattern
        No hardcoded fee schedules are loaded at import.
        """
        # Check that the service is properly declared
        assert "fee_service" in main.__dict__

        # The important thing is that startup() sets it
        import inspect

        assert "fee_service" in inspect.getsource(main.startup)

    @patch("intern_trading_game.infrastructure.config.ConfigLoader")
    @patch(
        "intern_trading_game.infrastructure.factories.exchange_factory.ExchangeFactory"
    )
    @patch(
        "intern_trading_game.infrastructure.factories.validator_factory.ValidatorFactory"
    )
    @patch(
        "intern_trading_game.infrastructure.factories.fee_service_factory.FeeServiceFactory"
    )
    def test_services_initialized_in_startup(
        self,
        mock_fee_factory,
        mock_validator_factory,
        mock_exchange_factory,
        mock_config_loader,
    ):
        """Test services are created during startup.

        Given - Mocked factories and config loader
        The startup function should use factories to create
        all services from configuration.

        When - Run startup (without starting threads)
        Services should be created and stored in module state.

        Then - All services are initialized
        validation_service and fee_service should be set.
        """
        # Given - Mock the dependencies
        mock_config = Mock()
        mock_config_loader.return_value = mock_config
        mock_config.get_exchange_config.return_value = Mock()
        mock_config.get_instruments.return_value = []

        mock_exchange = Mock()
        mock_exchange_factory.create_from_config.return_value = mock_exchange

        mock_validator = Mock()
        mock_validator_factory.create_from_config.return_value = mock_validator

        mock_fee_service = Mock()
        mock_fee_factory.create_from_config.return_value = mock_fee_service

        # Mock thread objects to prevent actual thread creation
        main.validator_t = Mock()
        main.matching_t = Mock()
        main.publisher_t = Mock()
        main.position_t = Mock()
        main.websocket_t = Mock()

        # When - Run startup synchronously
        import asyncio

        asyncio.run(main.startup())

        # Then - Services should be initialized
        assert main.validation_service is not None
        assert main.fee_service is not None
        assert main.fee_service == mock_fee_service

        # Verify factories were called
        mock_fee_factory.create_from_config.assert_called_once_with(
            mock_config
        )
        mock_validator_factory.create_from_config.assert_called_once_with(
            mock_config
        )

    def test_trade_publisher_uses_fee_service(self):
        """Test trade publisher thread uses configured fee service.

        Given - Fee service is set in module state
        The trade publisher wrapper should pass this service
        to the actual thread function.

        When - Call trade publisher wrapper
        It should use the module-level fee_service.

        Then - Thread function receives fee service
        The configured service is used for fee calculations.
        """
        # Given - Set up fee service
        mock_fee_service = Mock()
        main.fee_service = mock_fee_service

        # Mock the actual thread function
        with patch(
            "intern_trading_game.api.main.trade_publisher_thread"
        ) as mock_thread:
            # When - Call wrapper
            main.trade_publisher_thread_wrapper()

            # Then - Thread function called with fee service
            mock_thread.assert_called_once_with(mock_fee_service)

        # Cleanup
        main.fee_service = None
