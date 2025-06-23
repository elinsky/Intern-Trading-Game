"""Unit tests for MaximumVolumePricingStrategy.

These tests verify the Maximum Volume (MV) algorithm correctly finds
the price that maximizes trading volume, with special focus on the
midpoint selection rule when multiple prices achieve maximum volume.
"""

from intern_trading_game.domain.exchange.book.batch_auction_strategies import (
    MaximumVolumePricingStrategy,
)
from intern_trading_game.domain.exchange.components.core.models import Order


class TestMaximumVolumePricingStrategy:
    """Test the MaximumVolumePricingStrategy implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Just create the strategy directly - no need for exchange
        self.strategy = MaximumVolumePricingStrategy()

        # We'll use a simple instrument ID for all tests
        self.instrument_id = "TEST_INSTRUMENT"

    # fmt: off
    def test_single_large_buyer_many_small_sellers(self):
        """Test price discovery with asymmetric order sizes.

        Given - One institutional buyer wants a large position
        Multiple retail sellers offer small amounts at various prices

        When - The auction executes with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details       | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|---------------------|---------|----------|-----------|---------|
        | [500]            |  500  | 130.00 |   20  | [20]                | 500     | 165      | 165       | Cross ✓ |
        |                  |       | 129.00 |   25  | [25]                | 500     | 145      | 145       |         |
        |                  |       | 128.00 |   30  | [30]                | 500     | 120      | 120       |         |
        |                  |       | 127.00 |   40  | [40]                | 500     | 90       | 90        |         |
        |                  |       | 126.00 |   50  | [50]                | 500     | 50       | 50        |         |

        Then - The large buyer gets partial fill at best available price
        Price should be $130.00 (only price that maximizes volume)
        All sellers at or below clearing price get filled
        """
        # Create one large buy order
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="INST_BUYER",
                side="buy",
                quantity=500,
                price=130.00,
            )
        ]

        # Create many small sell orders
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id=f"RETAIL{i}",
                side="sell",
                quantity=qty,
                price=price,
            )
            for i, (qty, price) in enumerate([
                (20, 130.00),
                (25, 129.00),
                (30, 128.00),
                (40, 127.00),
                (50, 126.00),
            ])
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 130.00  # Only price that maximizes volume
        assert result.max_volume == 165  # All sellers can trade
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_many_small_buyers_single_large_seller(self):
        """Test price discovery with many buyers vs one seller.

        Given - Multiple retail buyers want small amounts
        One institutional seller offers a large block

        When - The auction executes with this order book:

        | Order Details       |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |---------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [50]                |   50  | 128.00 |       |                  | 50      | 500      | 50        |         |
        | [40]                |   40  | 127.00 |       |                  | 90      | 500      | 90        |         |
        | [30]                |   30  | 126.00 |       |                  | 120     | 500      | 120       |         |
        | [25]                |   25  | 125.00 |       |                  | 145     | 500      | 145       |         |
        | [20]                |   20  | 124.00 |  500  | [500]            | 165     | 500      | 165       | Cross ✓ |

        Then - All buyers get filled at lowest price
        Price should be $124.00 (maximizes volume at 165 shares)
        Large seller gets partial fill
        """
        # Create many small buy orders
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id=f"RETAIL{i}",
                side="buy",
                quantity=qty,
                price=price,
            )
            for i, (qty, price) in enumerate([
                (50, 128.00),
                (40, 127.00),
                (30, 126.00),
                (25, 125.00),
                (20, 124.00),
            ])
        ]

        # Create one large sell order
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="INST_SELLER",
                side="sell",
                quantity=500,
                price=124.00,
            )
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 124.00  # Only price that maximizes volume
        assert result.max_volume == 165  # All buyers can trade
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_multiple_prices_maximize_volume_chooses_midpoint(self):
        """Test the critical midpoint selection rule.

        Given - An auction where multiple prices result in the same maximum volume
        This tests the key midpoint selection rule from the MV algorithm

        When - The auction has this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [30]             |   30  | 102.00 |       |                  | 30      | 60       | 30        |         |
        | [20]             |   20  | 101.00 |       |                  | 50      | 60       | 50        |         |
        | [10]             |   10  | 100.00 |       |                  | 60      | 60       | 60        | Cross ✓ |
        |                  |       | 99.00  |   20  | [20]             | 60      | 60       | 60        | Cross ✓ |
        |                  |       | 98.00  |   20  | [20]             | 60      | 40       | 40        |         |
        |                  |       | 97.00  |   20  | [20]             | 60      | 20       | 20        |         |

        Then - The clearing price should be the midpoint
        Prices 99 and 100 both allow 60 shares to trade
        Clearing price should be (99 + 100) / 2 = 99.50
        """
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id=f"BUYER{i}",
                side="buy",
                quantity=qty,
                price=price,
            )
            for i, (qty, price) in enumerate([
                (30, 102.00),
                (20, 101.00),
                (10, 100.00),
            ])
        ]

        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id=f"SELLER{i}",
                side="sell",
                quantity=qty,
                price=price,
            )
            for i, (qty, price) in enumerate([
                (20, 99.00),
                (20, 98.00),
                (20, 97.00),
            ])
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 99.50  # Midpoint of 99 and 100
        assert result.max_volume == 60  # Maximum possible volume
        assert result.algorithm == "maximum_volume"
        assert result.price_range == (99.00, 100.00)  # Both prices allow 60 shares
    # fmt: on

    # fmt: off
    def test_staggered_price_levels_maximize_volume(self):
        """Test volume maximization with staggered price levels.

        Given - Orders at many different price points
        Creating a complex supply/demand interaction

        When - The auction executes with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [100]            |  100  | 105.00 |       |                  | 100     | 250      | 100       |         |
        | [75]             |   75  | 104.00 |       |                  | 175     | 250      | 175       |         |
        | [50]             |   50  | 103.00 |       |                  | 225     | 250      | 225       |         |
        | [25]             |   25  | 102.00 |   50  | [50]             | 250     | 250      | 250       | Cross ✓ |
        |                  |       | 101.00 |   75  | [75]             | 250     | 200      | 200       |         |
        |                  |       | 100.00 |  125  | [125]            | 250     | 125      | 125       |         |

        Then - Algorithm finds price that allows maximum shares to trade
        Should trade 250 shares at $102.00
        """
        # Create staggered buy orders
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id=f"BUYER{i}",
                side="buy",
                quantity=qty,
                price=price,
            )
            for i, (qty, price) in enumerate([
                (100, 105.00),
                (75, 104.00),
                (50, 103.00),
                (25, 102.00),
            ])
        ]

        # Create staggered sell orders
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id=f"SELLER{i}",
                side="sell",
                quantity=qty,
                price=price,
            )
            for i, (qty, price) in enumerate([
                (50, 102.00),
                (75, 101.00),
                (125, 100.00),
            ])
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 102.00  # Price that maximizes volume
        assert result.max_volume == 250  # Maximum possible volume
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_auction_avoids_manipulation(self):
        """Test that extreme orders can't manipulate the auction price.

        Given - Normal market with reasonable orders
        Plus one extreme order trying to manipulate

        When - Someone places an extreme buy order at $200
        But the rest of the market is trading around $100

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [1]              |    1  | 200.00 |       |                  | 1       | 100      | 1         |         |
        | [50]             |   50  | 101.00 |       |                  | 51      | 100      | 51        |         |
        | [50]             |   50  | 100.00 |   50  | [50]             | 101     | 100      | 100       | Cross ✓ |
        |                  |       | 99.00  |   50  | [50]             | 101     | 50       | 50        |         |

        Then - The extreme order doesn't affect the clearing price
        Market clears at $100.00 where real liquidity exists
        """
        # Normal market buy orders plus extreme order
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MANIPULATOR",
                side="buy",
                quantity=1,
                price=200.00,
            ),
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
                price=100.00,
            ),
        ]

        # Normal market sell orders
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=50,
                price=100.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER2",
                side="sell",
                quantity=50,
                price=99.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 100.00  # Where maximum volume trades
        assert result.max_volume == 100  # Not affected by extreme order
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_excess_demand_at_clearing_price(self):
        """Test when demand exceeds supply at the clearing price.

        Given - Multiple traders competing for limited supply
        All willing to pay the same price

        When - 5 traders each want 50 shares at $100
        But only 150 shares available

        | Order Details         |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |-----------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [50,50,50,50,50]      |  250  | 100.00 |  150  | [150]            | 250     | 150      | 150       | Cross ✓ |

        Then - Strategy identifies clearing price and max volume
        Note: The actual allocation is handled by the matching engine, not the strategy
        """
        # Create 5 identical buy orders
        buy_orders = []
        for i in range(5):
            order = Order(
                instrument_id=self.instrument_id,
                trader_id=f"BUYER{i+1}",
                side="buy",
                quantity=50,
                price=100.00,
            )
            buy_orders.append(order)

        # Create limited sell supply
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=150,
                price=100.00,
            )
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 100.00  # Only crossing price
        assert result.max_volume == 150  # Limited by supply
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price
    # fmt: on
