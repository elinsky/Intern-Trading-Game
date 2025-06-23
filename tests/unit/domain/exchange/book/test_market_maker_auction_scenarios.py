"""Unit tests for market maker scenarios in batch auction pricing strategy.

These tests verify how the MaximumVolumePricingStrategy handles market maker scenarios,
including liquidity provision, competition between market makers, and
interaction with directional flow.
"""

from intern_trading_game.domain.exchange.book.batch_auction_strategies import (
    MaximumVolumePricingStrategy,
)
from intern_trading_game.domain.exchange.components.core.models import Order


class TestMarketMakerAuctionScenarios:
    """Test how market makers interact with auction mechanisms."""

    def setup_method(self):
        """Set up test fixtures."""
        # Just create the strategy directly - no need for exchange
        self.strategy = MaximumVolumePricingStrategy()

        # We'll use a simple instrument ID for all tests
        self.instrument_id = "TEST_INSTRUMENT"

    # fmt: off
    def test_market_maker_provides_liquidity_both_sides(self):
        """Test market maker providing two-sided liquidity helps price discovery.

        Given - Market makers quote both sides around fair value
        Creating a liquid market for other participants

        When - Multiple MMs quote with overlapping spreads:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [MM1:50]         |   50  | 100.50 |   25  | [MM2:25]         | 50      | 150      | 50        |         |
        | [MM2:75]         |   75  | 100.25 |   50  | [MM1:50]         | 125     | 125      | 125       | Cross ✓ |
        | [MM3:50]         |   50  | 100.00 |   75  | [MM3:75]         | 175     | 75       | 75        |         |

        Then - Auction discovers fair price where MM spreads overlap
        Maximum liquidity at the crossing point
        MMs on both sides get fills
        """
        # MM1 quotes 100.25 bid / 100.50 ask
        # MM2 quotes 100.25 bid / 100.50 ask (same spread)
        # MM3 quotes 100.00 bid / 100.00 ask (crossing at 100.00)
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="buy",
                quantity=50,
                price=100.50,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="buy",
                quantity=75,
                price=100.25,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM3",
                side="buy",
                quantity=50,
                price=100.00,
            ),
        ]

        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="sell",
                quantity=50,
                price=100.25,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="sell",
                quantity=25,
                price=100.50,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM3",
                side="sell",
                quantity=75,
                price=100.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 100.25  # Maximum volume at 100.25
        assert result.max_volume == 125  # 125 shares can trade at 100.25
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_multiple_market_makers_compete(self):
        """Test competition between market makers improves spreads.

        Given - Multiple market makers competing for order flow
        Each trying to capture spread while managing inventory

        When - MMs post increasingly aggressive quotes:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [MM1:100]        |  100  | 101.00 |       |                  | 100     | 300      | 100       |         |
        | [MM2:150]        |  150  | 100.75 |  100  | [MM3:100]        | 250     | 300      | 250       | Cross ✓ |
        | [MM3:200]        |  200  | 100.50 |  150  | [MM2:150]        | 450     | 200      | 200       |         |
        |                  |       | 100.25 |   50  | [MM1:50]         | 450     | 50       | 50        |         |

        Then - Competition drives spreads tighter
        More aggressive MMs capture more volume
        """
        # Create buy orders from three market makers
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="buy",
                quantity=100,
                price=101.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="buy",
                quantity=150,
                price=100.75,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM3",
                side="buy",
                quantity=200,
                price=100.50,
            ),
        ]

        # Create sell orders from three market makers
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="sell",
                quantity=50,
                price=100.25,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="sell",
                quantity=150,
                price=100.50,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM3",
                side="sell",
                quantity=100,
                price=100.75,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 100.75  # Maximum volume at 100.75
        assert result.max_volume == 250  # 250 shares can trade at 100.75
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_market_maker_vs_directional_flow(self):
        """Test how market makers handle one-sided flow.

        Given - Market makers providing liquidity
        Sudden directional flow from hedge funds

        When - Large buy interest hits the market:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [HF1:200,HF2:150]|  350  | 102.00 |       |                  | 350     | 175      | 175       | Cross ✓ |
        | [MM1:50]         |   50  | 101.00 |   25  | [MM1:25]         | 400     | 175      | 175       | Cross ✓ |
        |                  |       | 100.50 |   50  | [MM2:50]         | 400     | 150      | 150       |         |
        |                  |       | 100.00 |  100  | [MM3:100]        | 400     | 100      | 100       |         |

        Then - Market makers absorb the flow
        Price moves in direction of flow
        MMs provide liquidity but at higher prices
        """
        # Directional buyers (hedge funds) and one MM buyer
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="HF1",
                side="buy",
                quantity=200,
                price=102.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="HF2",
                side="buy",
                quantity=150,
                price=102.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="buy",
                quantity=50,
                price=101.00,
            ),
        ]

        # Market maker sell orders
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="sell",
                quantity=25,
                price=101.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="sell",
                quantity=50,
                price=100.50,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM3",
                side="sell",
                quantity=100,
                price=100.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        # With strong buy pressure, maximum volume trades at high prices
        # At 101.00: buy=400, sell=175, so 175 shares trade
        # At 102.00: buy=350, sell=175, so 175 shares trade
        # Both prices allow 175 shares, so midpoint = 101.50
        assert result.clearing_price == 101.50  # Midpoint of 101-102
        assert result.max_volume == 175  # Limited by sell side
        assert result.algorithm == "maximum_volume"
        assert result.price_range == (101.00, 102.00)  # Both prices allow 175 shares
    # fmt: on

    # fmt: off
    def test_auction_rewards_aggressive_market_making(self):
        """Test that aggressive pricing gets rewarded with fills.

        Given - Multiple market makers with different strategies
        Some quote aggressively, others conservatively

        When - Auction matches orders:

        | Order Details       |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |---------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [MM1:100,TRADER:50] | 150   | 100.00 |  100  | [MM1:100]        | 150     | 100      | 100       | Cross ✓ |
        | [MM2:50]            |   50  | 99.75  |  150  | [MM2:150]        | 200     | 0        | 0         |         |
        | [MM3:25]            |   25  | 99.50  |       |                  | 225     | 0        | 0         |         |

        Then - MM1 with aggressive two-sided quotes gets fills
        MM2 with wide spread gets no fills
        Aggressive pricing rewarded in batch auction
        """
        # Buy orders from MMs and trader
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="buy",
                quantity=100,
                price=100.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="TRADER1",
                side="buy",
                quantity=50,
                price=100.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="buy",
                quantity=50,
                price=99.75,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM3",
                side="buy",
                quantity=25,
                price=99.50,
            ),
        ]

        # Sell orders from MMs
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="sell",
                quantity=100,
                price=100.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="sell",
                quantity=150,
                price=100.25,  # Fixed to create a reasonable spread
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        # At 100.00: buy=150, sell=100, so 100 shares trade
        # At 100.25: buy=150, sell=250, so 150 shares trade
        # Maximum volume is at 100.25
        assert result.clearing_price == 100.00  # Only price that allows trades
        assert result.max_volume == 100  # Limited by MM1's sell side
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price allows trades
    # fmt: on
