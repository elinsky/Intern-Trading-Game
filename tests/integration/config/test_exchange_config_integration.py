"""Integration tests for config-driven exchange creation."""

import tempfile
from pathlib import Path

import yaml

from intern_trading_game.infrastructure.config.loader import ConfigLoader
from intern_trading_game.infrastructure.factories.exchange_factory import (
    ExchangeFactory,
)
from tests.fixtures.market_data import (
    create_matched_orders,
    create_spx_option,
)


class TestExchangeConfigIntegration:
    """Test full integration of config-driven exchange."""

    def test_continuous_mode_end_to_end(self):
        """Test creating and using continuous exchange from config.

        Given - YAML config file with continuous mode
        When - System loads config and creates exchange
        Then - Exchange operates in continuous mode with immediate matching
        """
        # Given - Config file with continuous mode
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"exchange": {"matching_mode": "continuous"}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load config and create exchange
            loader = ConfigLoader(config_path)
            exchange_config = loader.get_exchange_config()
            exchange = ExchangeFactory.create_from_config(exchange_config)

            # List test instruments using fixture
            instrument = create_spx_option(strike=4500.0, option_type="call")
            exchange.list_instrument(instrument)

            # Then - Exchange should be in continuous mode
            assert exchange.get_matching_mode() == "continuous"

            # Then - Orders should match immediately
            # Create matched orders using fixture
            buy_order, sell_order = create_matched_orders(
                price=99.5,
                quantity=10,
                buyer_id="TRADER1",
                seller_id="TRADER2",
                instrument_id=instrument.symbol,
            )

            # Submit buy order first
            buy_result = exchange.submit_order(buy_order)
            assert buy_result.status == "new"  # Resting in book

            # Submit sell order - should match immediately
            sell_result = exchange.submit_order(sell_order)

            # Then - Should match immediately in continuous mode
            assert sell_result.status == "filled"
            assert len(sell_result.fills) == 1
            assert sell_result.fills[0].quantity == 10
            assert sell_result.fills[0].price == 99.5

        finally:
            config_path.unlink()

    def test_batch_mode_end_to_end(self):
        """Test creating and using batch exchange from config.

        Given - YAML config file with batch mode
        When - System loads config and creates exchange
        Then - Exchange operates in batch mode with delayed matching
        """
        # Given - Config file with batch mode
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"exchange": {"matching_mode": "batch"}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load config and create exchange
            loader = ConfigLoader(config_path)
            exchange_config = loader.get_exchange_config()
            exchange = ExchangeFactory.create_from_config(exchange_config)

            # List test instrument
            instrument = create_spx_option(strike=4500.0, option_type="put")
            exchange.list_instrument(instrument)

            # Then - Exchange should be in batch mode
            assert exchange.get_matching_mode() == "batch"

            # Then - Orders should NOT match immediately
            # Create matched orders
            buy_order, sell_order = create_matched_orders(
                price=100.0,
                quantity=50,
                buyer_id="MM1",
                seller_id="HF1",
                instrument_id=instrument.symbol,
            )

            # Submit both orders - should NOT match yet
            buy_result = exchange.submit_order(buy_order)
            assert buy_result.status == "pending_new"  # Batch mode status

            sell_result = exchange.submit_order(sell_order)
            assert sell_result.status == "pending_new"  # Also pending

            # When - Execute batch
            batch_results = exchange.execute_batch()

            # Then - Orders should match in batch
            assert instrument.symbol in batch_results
            assert len(batch_results[instrument.symbol]) == 2  # Both orders

            # Check that orders matched
            for order_id, result in batch_results[instrument.symbol].items():
                assert result.status == "filled"
                assert len(result.fills) == 1
                assert result.fills[0].quantity == 50
                assert result.fills[0].price == 100.0

        finally:
            config_path.unlink()

    def test_config_changes_exchange_behavior(self):
        """Test that different configs create different exchange behaviors.

        Given - Two different config files
        When - Exchanges are created from each
        Then - They exhibit different matching behaviors
        """
        # Given - Two config files
        continuous_config = {"exchange": {"matching_mode": "continuous"}}
        batch_config = {"exchange": {"matching_mode": "batch"}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f1:
            yaml.dump(continuous_config, f1)
            continuous_path = Path(f1.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f2:
            yaml.dump(batch_config, f2)
            batch_path = Path(f2.name)

        try:
            # When - Create two exchanges
            loader1 = ConfigLoader(continuous_path)
            exchange1 = ExchangeFactory.create_from_config(
                loader1.get_exchange_config()
            )

            loader2 = ConfigLoader(batch_path)
            exchange2 = ExchangeFactory.create_from_config(
                loader2.get_exchange_config()
            )

            # Then - They should have different modes
            assert exchange1.get_matching_mode() == "continuous"
            assert exchange2.get_matching_mode() == "batch"

            # Then - They should behave differently
            # Use same instrument on both
            instrument = create_spx_option()
            exchange1.list_instrument(instrument)
            exchange2.list_instrument(instrument)

            # Create matched orders
            buy_order, sell_order = create_matched_orders(
                price=102.5, quantity=1, instrument_id=instrument.symbol
            )

            # Submit only buy order to both exchanges
            result1 = exchange1.submit_order(buy_order)
            result2 = exchange2.submit_order(buy_order)

            # Different statuses based on mode
            assert result1.status == "new"  # Continuous - in book
            assert result2.status == "pending_new"  # Batch - pending

        finally:
            continuous_path.unlink()
            batch_path.unlink()

    def test_multiple_matched_orders_batch_mode(self):
        """Test batch mode with multiple matching orders.

        Given - Batch exchange with multiple crossing orders
        When - Batch is executed
        Then - All matching orders are processed fairly
        """
        # Given - Config for batch mode
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump({"exchange": {"matching_mode": "batch"}}, f)
            config_path = Path(f.name)

        try:
            # Create batch exchange
            loader = ConfigLoader(config_path)
            exchange = ExchangeFactory.create_from_config(
                loader.get_exchange_config()
            )

            # List instrument
            instrument = create_spx_option()
            exchange.list_instrument(instrument)

            # Submit multiple matched order pairs at same price
            order_pairs = []
            for i in range(3):
                buy, sell = create_matched_orders(
                    price=100.0,  # Same price for all orders
                    quantity=10,
                    buyer_id=f"BUYER_{i}",
                    seller_id=f"SELLER_{i}",
                    instrument_id=instrument.symbol,
                )
                order_pairs.append((buy, sell))

                # Submit to batch
                buy_result = exchange.submit_order(buy)
                sell_result = exchange.submit_order(sell)
                assert buy_result.status == "pending_new"
                assert sell_result.status == "pending_new"

            # When - Execute batch
            results = exchange.execute_batch()

            # Then - All orders should match
            assert len(results[instrument.symbol]) == 6  # 3 buy + 3 sell

            filled_count = 0
            for order_id, result in results[instrument.symbol].items():
                if result.status == "filled":
                    filled_count += 1
                    assert len(result.fills) == 1
                    assert result.fills[0].quantity == 10
                    assert result.fills[0].price == 100.0

            # All orders should fill since they're at same price
            assert filled_count == 6

        finally:
            config_path.unlink()
