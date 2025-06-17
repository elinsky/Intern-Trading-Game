"""Integration tests for fee configuration loading."""

import tempfile
from pathlib import Path

import yaml

from intern_trading_game.infrastructure.config.loader import ConfigLoader
from intern_trading_game.infrastructure.factories.fee_service_factory import (
    FeeServiceFactory,
)


class TestFeeConfigIntegration:
    """Test fee configuration and service creation integration."""

    def test_load_fees_from_default_config(self):
        """Test loading fees from default configuration file.

        Given - Default configuration with market maker fees
        The default config should have basic fee structure
        for development and testing.

        When - Load fees using standard flow
        ConfigLoader reads default.yaml and factory creates
        fee service from the configuration.

        Then - Fee service calculates correctly
        Market maker fees should match the default config
        values for maker rebates and taker fees.
        """
        # Given/When - Load from default config
        loader = ConfigLoader()
        fee_service = FeeServiceFactory.create_from_config(loader)

        # Then - Market maker fees work correctly
        # Maker gets rebate
        maker_fee = fee_service.calculate_fee(100, "market_maker", "maker")
        assert maker_fee == 2.0  # 100 * 0.02

        # Taker pays fee
        taker_fee = fee_service.calculate_fee(100, "market_maker", "taker")
        assert taker_fee == -1.0  # 100 * -0.01

    def test_multi_role_fee_calculation(self):
        """Test fee calculations across multiple roles.

        Given - Config with multiple trading roles
        Each role has different fee tiers based on their
        market function and sophistication level.

        When - Create fee service and calculate fees
        The service should handle all roles correctly
        with their specific fee schedules.

        Then - Each role has correct fee calculations
        Market makers get best rates, retail pays most,
        and institutional traders are in between.
        """
        # Given - Multi-role configuration
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
            # When - Create service
            loader = ConfigLoader(config_path)
            fee_service = FeeServiceFactory.create_from_config(loader)

            # Then - Calculate fees for a 50-contract trade
            quantity = 50

            # Market maker: Best rates
            assert (
                fee_service.calculate_fee(quantity, "market_maker", "maker")
                == 1.0
            )  # Rebate
            assert (
                fee_service.calculate_fee(quantity, "market_maker", "taker")
                == -0.5
            )  # Small fee

            # Hedge fund: Medium rates
            assert (
                fee_service.calculate_fee(quantity, "hedge_fund", "maker")
                == 0.5
            )  # Smaller rebate
            assert (
                fee_service.calculate_fee(quantity, "hedge_fund", "taker")
                == -1.0
            )  # Higher fee

            # Retail: Worst rates
            assert (
                fee_service.calculate_fee(quantity, "retail", "maker") == -0.5
            )  # Pay as maker
            assert (
                fee_service.calculate_fee(quantity, "retail", "taker") == -1.5
            )  # Highest fee

        finally:
            config_path.unlink()

    def test_fee_service_liquidity_determination(self):
        """Test fee service determines liquidity type correctly.

        Given - Trade with known aggressor side
        In continuous markets, one side initiates the trade
        (aggressor/taker) while the other provides liquidity.

        When - Determine liquidity type for each side
        The service uses aggressor side to classify each
        participant as maker or taker.

        Then - Correct fee tier applied
        Aggressor pays taker fee, passive side gets maker rate.
        """
        # Given - Config with test role
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "test_trader": {
                        "fees": {"maker_rebate": 0.015, "taker_fee": -0.025}
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create service
            loader = ConfigLoader(config_path)
            fee_service = FeeServiceFactory.create_from_config(loader)

            # Then - Test liquidity determination
            # Buy order aggressed (lifted the offer)
            assert (
                fee_service.determine_liquidity_type("buy", "buy") == "taker"
            )
            assert (
                fee_service.determine_liquidity_type("buy", "sell") == "maker"
            )

            # Sell order aggressed (hit the bid)
            assert (
                fee_service.determine_liquidity_type("sell", "sell") == "taker"
            )
            assert (
                fee_service.determine_liquidity_type("sell", "buy") == "maker"
            )

            # Calculate fees based on liquidity type
            # Aggressive buy pays taker fee
            liq_type = fee_service.determine_liquidity_type("buy", "buy")
            fee = fee_service.calculate_fee(100, "test_trader", liq_type)
            assert fee == -2.5  # 100 * -0.025

            # Passive sell gets maker rebate
            liq_type = fee_service.determine_liquidity_type("buy", "sell")
            fee = fee_service.calculate_fee(100, "test_trader", liq_type)
            assert fee == 1.5  # 100 * 0.015

        finally:
            config_path.unlink()

    def test_invalid_role_fee_calculation_fails(self):
        """Test fee calculation for unknown role fails appropriately.

        Given - Fee service with limited roles configured
        Not all possible roles may be configured in a
        given deployment.

        When - Calculate fees for unknown role
        The service should detect the unknown role and
        provide clear error messaging.

        Then - Raises KeyError with helpful message
        Error identifies the unknown role and lists
        available configured roles.
        """
        # Given - Config with one role
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
            # When - Create service
            loader = ConfigLoader(config_path)
            fee_service = FeeServiceFactory.create_from_config(loader)

            # Then - Unknown role raises error
            try:
                fee_service.calculate_fee(100, "unknown_role", "maker")
                assert False, "Should have raised KeyError"
            except KeyError as e:
                assert "Unknown role: unknown_role" in str(e)
                assert "Available roles: ['market_maker']" in str(e)

        finally:
            config_path.unlink()
