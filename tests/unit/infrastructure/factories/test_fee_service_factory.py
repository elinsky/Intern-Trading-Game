"""Tests for fee service factory functionality."""

import tempfile
from pathlib import Path

import pytest
import yaml

from intern_trading_game.domain.positions import TradingFeeService
from intern_trading_game.infrastructure.config.loader import ConfigLoader
from intern_trading_game.infrastructure.factories.fee_service_factory import (
    FeeServiceFactory,
)


class TestFeeServiceFactory:
    """Test creating fee services from configuration."""

    def test_create_fee_service_with_single_role(self):
        """Test creating fee service with one role configured.

        Given - Config with single market maker role
        During development, we might start with just one
        role configured to test fee calculation logic.

        When - Factory creates fee service from config
        The factory should load fee schedules and create
        a properly configured TradingFeeService instance.

        Then - Service has market maker fees loaded
        The service can calculate fees for market maker
        trades using the configured rebate structure.
        """
        # Given - Config with market maker fees
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "fees": {
                            "maker_rebate": 0.02,
                            "taker_fee": -0.01,
                        }
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create fee service via factory
            loader = ConfigLoader(config_path)
            fee_service = FeeServiceFactory.create_from_config(loader)

            # Then - Service is properly configured
            assert isinstance(fee_service, TradingFeeService)

            # Then - Can calculate market maker fees
            maker_fee = fee_service.calculate_fee(100, "market_maker", "maker")
            assert maker_fee == 2.0  # 100 * 0.02 rebate

            taker_fee = fee_service.calculate_fee(100, "market_maker", "taker")
            assert taker_fee == -1.0  # 100 * -0.01 fee

        finally:
            config_path.unlink()

    def test_create_fee_service_with_all_roles(self):
        """Test creating fee service with complete role configuration.

        Given - Full game config with all trading roles
        Production system needs fee schedules for all roles
        to properly calculate P&L for different participants.

        When - Factory creates service from complete config
        All role fee schedules should be loaded and available
        for fee calculations during trade processing.

        Then - Service can calculate fees for any role
        The service handles fee calculations correctly for
        market makers, hedge funds, arbitrage, and retail.
        """
        # Given - Complete role configuration
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "fees": {"maker_rebate": 0.02, "taker_fee": -0.01}
                    },
                    "hedge_fund": {
                        "fees": {"maker_rebate": 0.01, "taker_fee": -0.02}
                    },
                    "arbitrage_desk": {
                        "fees": {"maker_rebate": 0.01, "taker_fee": -0.02}
                    },
                    "retail": {
                        "fees": {"maker_rebate": -0.01, "taker_fee": -0.03}
                    },
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create fee service
            loader = ConfigLoader(config_path)
            fee_service = FeeServiceFactory.create_from_config(loader)

            # Then - All roles can calculate fees
            # Market maker gets rebates
            mm_maker = fee_service.calculate_fee(50, "market_maker", "maker")
            assert mm_maker == 1.0  # 50 * 0.02

            # Hedge fund gets smaller rebates
            hf_maker = fee_service.calculate_fee(50, "hedge_fund", "maker")
            assert hf_maker == 0.5  # 50 * 0.01

            # Retail pays fees even as maker
            retail_maker = fee_service.calculate_fee(50, "retail", "maker")
            assert retail_maker == -0.5  # 50 * -0.01

            # Retail pays highest taker fees
            retail_taker = fee_service.calculate_fee(50, "retail", "taker")
            assert retail_taker == -1.5  # 50 * -0.03

        finally:
            config_path.unlink()

    def test_factory_creates_new_instances(self):
        """Test that factory creates independent service instances.

        Given - Same configuration used multiple times
        Factory pattern should create new instances to
        avoid shared state between different components.

        When - Factory creates multiple services
        Each call should return a new TradingFeeService
        instance with its own internal state.

        Then - Services are independent instances
        Multiple services can exist without interfering
        with each other's fee calculations.
        """
        # Given - A configuration
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "fees": {"maker_rebate": 0.02, "taker_fee": -0.01}
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create two services
            loader = ConfigLoader(config_path)
            service1 = FeeServiceFactory.create_from_config(loader)
            service2 = FeeServiceFactory.create_from_config(loader)

            # Then - Services are different instances
            assert service1 is not service2

            # But both work correctly
            fee1 = service1.calculate_fee(100, "market_maker", "maker")
            fee2 = service2.calculate_fee(100, "market_maker", "maker")
            assert fee1 == fee2 == 2.0

        finally:
            config_path.unlink()

    def test_empty_config_creates_empty_service(self):
        """Test factory handles empty configuration gracefully.

        Given - Config file with no roles section
        System should start even without fee configuration
        for development and testing scenarios.

        When - Factory creates service from empty config
        Service should be created but with no fee schedules
        loaded, allowing system to function.

        Then - Service created but has no roles
        Attempting to calculate fees for unknown roles
        should raise appropriate errors.
        """
        # Given - Empty config
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"exchange": {"matching_mode": "continuous"}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create service
            loader = ConfigLoader(config_path)
            fee_service = FeeServiceFactory.create_from_config(loader)

            # Then - Service created but empty
            assert isinstance(fee_service, TradingFeeService)

            # Calculating fees for unknown role raises error
            with pytest.raises(KeyError) as exc_info:
                fee_service.calculate_fee(100, "unknown_role", "maker")

            assert "Unknown role: unknown_role" in str(exc_info.value)

        finally:
            config_path.unlink()

    @pytest.mark.parametrize(
        "quantity,role,liquidity_type,expected",
        [
            (100, "market_maker", "maker", 2.0),  # MM rebate
            (100, "market_maker", "taker", -1.0),  # MM fee
            (50, "hedge_fund", "maker", 0.5),  # HF smaller rebate
            (50, "hedge_fund", "taker", -1.0),  # HF taker fee
            (25, "retail", "maker", -0.25),  # Retail pays as maker
            (25, "retail", "taker", -0.75),  # Retail highest fee
        ],
    )
    def test_fee_calculations_match_game_mechanics(
        self, quantity, role, liquidity_type, expected
    ):
        """Test fee calculations align with game design.

        Given - Game mechanics for role-based fees
        Each role has specific fee tiers that affect
        their profitability and trading strategies.

        When - Calculate fees for various scenarios
        The fee service should apply the correct rates
        based on role and liquidity provision.

        Then - Fees match expected game mechanics
        Market makers are incentivized with rebates,
        while retail traders face highest costs.
        """
        # Given - Config with game fee structure
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "fees": {"maker_rebate": 0.02, "taker_fee": -0.01}
                    },
                    "hedge_fund": {
                        "fees": {"maker_rebate": 0.01, "taker_fee": -0.02}
                    },
                    "retail": {
                        "fees": {"maker_rebate": -0.01, "taker_fee": -0.03}
                    },
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create service and calculate fee
            loader = ConfigLoader(config_path)
            fee_service = FeeServiceFactory.create_from_config(loader)
            actual_fee = fee_service.calculate_fee(
                quantity, role, liquidity_type
            )

            # Then - Fee matches expected calculation
            assert actual_fee == expected

        finally:
            config_path.unlink()

    def test_factory_prints_loaded_roles(self, capsys):
        """Test factory provides visibility into loaded configuration.

        Given - Config with multiple roles
        Operators need visibility into what was loaded
        for debugging and operational monitoring.

        When - Factory creates service
        It should print information about loaded roles
        to provide operational transparency.

        Then - Output shows loaded roles
        Console output confirms which roles were configured
        with fee schedules.
        """
        # Given - Config with roles
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "fees": {"maker_rebate": 0.02, "taker_fee": -0.01}
                    },
                    "hedge_fund": {
                        "fees": {"maker_rebate": 0.01, "taker_fee": -0.02}
                    },
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create service
            loader = ConfigLoader(config_path)
            _ = FeeServiceFactory.create_from_config(loader)

            # Then - Output shows loaded roles
            captured = capsys.readouterr()
            assert "Loaded fee schedules for 2 roles" in captured.out
            assert "market_maker" in captured.out
            assert "hedge_fund" in captured.out

        finally:
            config_path.unlink()
