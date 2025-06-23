"""Unit tests specifically for midpoint selection in batch auction pricing strategy.

These tests verify the critical behavior where multiple prices achieve
the same maximum volume, and the MaximumVolumePricingStrategy must select the midpoint.
This is a key fairness feature of the Maximum Volume algorithm.
"""

from intern_trading_game.domain.exchange.book.batch_auction_strategies import (
    MaximumVolumePricingStrategy,
)
from intern_trading_game.domain.exchange.components.core.models import Order


class TestMidpointSelectionScenarios:
    """Test midpoint selection when multiple prices maximize volume."""

    def setup_method(self):
        """Set up test fixtures."""
        # Just create the strategy directly - no need for exchange
        self.strategy = MaximumVolumePricingStrategy()

        # We'll use a simple instrument ID for all tests
        self.instrument_id = "TEST_INSTRUMENT"

    # fmt: off
    def test_two_prices_maximize_volume_chooses_midpoint(self):
        """Test midpoint selection with two prices maximizing volume.

        Given - An auction where exactly two prices allow maximum volume
        This is the simplest case of the midpoint rule

        When - The auction has this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [100]            |  100  | 101.00 |  100  | [100]            | 100     | 200      | 100       | Cross ✓ |
        | [100]            |  100  | 100.00 |  100  | [100]            | 200     | 100      | 100       | Cross ✓ |

        Then - Clearing price should be (100 + 101) / 2 = 100.50
        100 shares trade at the midpoint price
        """
        # Create orders at two price levels
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=100,
                price=101.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER2",
                side="buy",
                quantity=100,
                price=100.00,
            ),
        ]

        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=100,
                price=101.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER2",
                side="sell",
                quantity=100,
                price=100.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 100.50  # Midpoint of 100-101
        assert result.max_volume == 100  # 100 shares can trade at both prices
        assert result.algorithm == "maximum_volume"
        assert result.price_range == (100.00, 101.00)  # Both prices allow 100 shares
    # fmt: on

    # fmt: off
    def test_three_prices_maximize_volume_chooses_middle(self):
        """Test midpoint selection with three prices maximizing volume.

        Given - Three different prices all allow the same maximum volume

        When - The auction has this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [100]            |  100  | 130.00 |       |                  | 100     | 300      | 100       |         |
        | [100]            |  100  | 129.00 |       |                  | 200     | 300      | 200       |         |
        | [100]            |  100  | 128.00 |       |                  | 300     | 300      | 300       | Cross ✓ |
        |                  |       | 127.00 |       |                  | 300     | 300      | 300       | Cross ✓ |
        |                  |       | 126.00 |  100  | [100]            | 300     | 300      | 300       | Cross ✓ |
        |                  |       | 125.00 |  100  | [100]            | 300     | 200      | 200       |         |
        |                  |       | 124.00 |  100  | [100]            | 300     | 100      | 100       |         |

        Then - Prices 126, 127, 128 all allow 300 shares
        Clearing price = (126 + 128) / 2 = 127
        """
        # Create buy orders
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=100,
                price=130.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER2",
                side="buy",
                quantity=100,
                price=129.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER3",
                side="buy",
                quantity=100,
                price=128.00,
            ),
        ]

        # Create sell orders
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=100,
                price=126.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER2",
                side="sell",
                quantity=100,
                price=125.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER3",
                side="sell",
                quantity=100,
                price=124.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 127.00  # Midpoint of 126-128
        assert result.max_volume == 300  # 300 shares can trade at 126, 127, 128
        assert result.algorithm == "maximum_volume"
        assert result.price_range == (126.00, 128.00)  # Three prices allow 300 shares
    # fmt: on

    # fmt: off
    def test_many_prices_maximize_volume_chooses_midpoint(self):
        """Test midpoint with many prices achieving max volume.

        Given - A wide range of prices all allow the same volume

        When - The auction has an order book where prices 100-105 all allow 50 shares

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [50]             |   50  | 105.00 |       |                  | 50      | 50       | 50        | Cross ✓ |
        | [0]              |    0  | 104.00 |       |                  | 50      | 50       | 50        | Cross ✓ |
        | [0]              |    0  | 103.00 |       |                  | 50      | 50       | 50        | Cross ✓ |
        | [0]              |    0  | 102.00 |       |                  | 50      | 50       | 50        | Cross ✓ |
        | [0]              |    0  | 101.00 |       |                  | 50      | 50       | 50        | Cross ✓ |
        | [0]              |    0  | 100.00 |   50  | [50]             | 50      | 50       | 50        | Cross ✓ |

        Then - Clearing price = (100 + 105) / 2 = 102.50
        """
        # Create a scenario where buyer will pay up to 105, seller will accept down to 100
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=50,
                price=105.00,
            )
        ]

        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=50,
                price=100.00,
            )
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 102.50  # Midpoint of 100-105
        assert result.max_volume == 50  # 50 shares can trade at all prices 100-105
        assert result.algorithm == "maximum_volume"
        assert result.price_range == (100.00, 105.00)  # Wide range allows 50 shares
    # fmt: on

    # fmt: off
    def test_midpoint_calculation_with_fractional_prices(self):
        """Test midpoint calculation handles decimal prices correctly.

        Given - Prices with decimals that result in a fractional midpoint

        When - Two prices maximize volume: $127.25 and $128.75

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [100]            |  100  | 128.75 |  100  | [100]            | 100     | 200      | 100       | Cross ✓ |
        | [100]            |  100  | 127.25 |  100  | [100]            | 200     | 100      | 100       | Cross ✓ |

        Then - Midpoint should be exactly 128.00
        Tests that (127.25 + 128.75) / 2 = 128.00 is calculated correctly
        """
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=100,
                price=128.75,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER2",
                side="buy",
                quantity=100,
                price=127.25,
            ),
        ]

        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=100,
                price=128.75,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER2",
                side="sell",
                quantity=100,
                price=127.25,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 128.00  # Midpoint of 127.25-128.75
        assert result.max_volume == 100  # 100 shares can trade at both prices
        assert result.algorithm == "maximum_volume"
        assert result.price_range == (127.25, 128.75)  # Both prices allow 100 shares

        # Also verify it's not a floating point approximation
        assert abs(result.clearing_price - 128.00) < 0.0001
    # fmt: on

    # fmt: off
    def test_midpoint_with_true_fractional_result(self):
        """Test midpoint when result is not a round number.

        Given - Prices that result in a non-round midpoint

        When - Two prices maximize volume: $100.25 and $101.00

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [50]             |   50  | 101.00 |   50  | [50]             | 50      | 100      | 50        | Cross ✓ |
        | [50]             |   50  | 100.25 |   50  | [50]             | 100     | 50       | 50        | Cross ✓ |

        Then - Midpoint = (100.25 + 101.00) / 2 = 100.625
        Tests true fractional midpoint calculation
        """
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=50,
                price=101.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER2",
                side="buy",
                quantity=50,
                price=100.25,
            ),
        ]

        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=50,
                price=101.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER2",
                side="sell",
                quantity=50,
                price=100.25,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        expected_price = 100.625
        assert result.clearing_price == expected_price  # Midpoint of 100.25-101.00
        assert result.max_volume == 50  # 50 shares can trade at both prices
        assert result.algorithm == "maximum_volume"
        assert result.price_range == (100.25, 101.00)  # Both prices allow 50 shares

        # Verify precision
        assert abs(result.clearing_price - expected_price) < 0.0001
    # fmt: on
