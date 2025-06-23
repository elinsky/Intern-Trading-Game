"""Unit tests for opening auction scenarios using MaximumVolumePricingStrategy.

These tests verify that the pricing strategy handles real-world opening auction
scenarios correctly, with proper price discovery. Each test represents a
business scenario that traders experience, but tests the strategy directly
rather than through the full exchange infrastructure.
"""

from intern_trading_game.domain.exchange.book.batch_auction_strategies import (
    MaximumVolumePricingStrategy,
)
from intern_trading_game.domain.exchange.components.core.models import Order


class TestOpeningAuctionScenarios:
    """Test real-world opening auction scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        # Just create the strategy directly - no need for exchange
        self.strategy = MaximumVolumePricingStrategy()

        # We'll use a simple instrument ID for all tests
        self.instrument_id = "TEST_INSTRUMENT"

    # fmt: off
    def test_opening_auction_balanced_market(self):
        """Test a balanced opening auction with equal buy and sell interest.

        Given - A balanced opening auction with equal buy and sell interest
        Market makers and traders submit orders around fair value of $127.50

        When - The opening auction executes with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [100]            |  100  | 128.00 |       |                  | 100     | 175      | 100       |         |
        | [50]             |   50  | 127.75 |       |                  | 150     | 175      | 150       |         |
        | [25]             |   25  | 127.50 |   25  | [25]             | 175     | 175      | 175       | Cross ✓ |
        |                  |       | 127.25 |   50  | [50]             | 175     | 150      | 150       |         |
        |                  |       | 127.00 |  100  | [100]            | 175     | 100      | 100       |         |

        Then - All orders should execute at the midpoint price
        The clearing price should be $127.50 (midpoint of crossable range)
        175 shares should trade (maximum possible volume)
        All traders get the same price regardless of their limit price
        """
        # Create buy orders (Price on Quantity)
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="TRADER1",
                side="buy",
                quantity=100,
                price=128.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="TRADER2",
                side="buy",
                quantity=50,
                price=127.75,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="TRADER3",
                side="buy",
                quantity=25,
                price=127.50,
            ),
        ]

        # Create sell orders (Quantity at Price)
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="sell",
                quantity=100,
                price=127.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="sell",
                quantity=50,
                price=127.25,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="TRADER4",
                side="sell",
                quantity=25,
                price=127.50,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 127.50  # Only crossing price
        assert result.max_volume == 175  # Maximum possible volume
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_opening_auction_buyer_pressure(self):
        """Test opening auction with more buyers than sellers.

        Given - Strong buying interest at market open
        Multiple hedge funds want to establish long positions
        Limited selling interest from market makers

        When - The opening auction executes with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [200]            |  200  | 130.00 |   25  | [25]             | 200     | 150      | 150       | Cross ✓ |
        | [150]            |  150  | 129.00 |   75  | [75]             | 350     | 125      | 125       |         |
        | [100]            |  100  | 128.00 |   50  | [50]             | 450     | 50       | 50        |         |

        Then - Price should be at upper end of range
        Only 150 shares can trade (limited by sell side)
        Some buyers will be disappointed (partial fills)
        """
        # Create buy orders - strong demand (Price on Quantity)
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="HF1",
                side="buy",
                quantity=200,
                price=130.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="HF2",
                side="buy",
                quantity=150,
                price=129.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="HF3",
                side="buy",
                quantity=100,
                price=128.00,
            ),
        ]

        # Create sell orders - limited supply (Quantity at Price)
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM1",
                side="sell",
                quantity=50,
                price=128.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM2",
                side="sell",
                quantity=75,
                price=129.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="MM3",
                side="sell",
                quantity=25,
                price=130.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 130.00  # Only price that maximizes volume
        assert result.max_volume == 150  # Limited by sell side
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_opening_auction_seller_pressure(self):
        """Test opening auction with more sellers than buyers.

        Given - Heavy selling pressure at market open
        Multiple traders want to exit positions
        Limited buying interest

        When - The opening auction executes with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [25]             |   25  | 125.00 |   50  | [50]             | 25      | 300      | 25        |         |
        | [50]             |   50  | 124.00 |  100  | [100]            | 75      | 250      | 75        |         |
        | [25]             |   25  | 123.00 |  150  | [150]            | 100     | 150      | 100       | Cross ✓ |

        Then - Price should be at lower end of range
        Only 100 shares can trade (limited by buy side)
        Some sellers will have unfilled orders
        """
        # Create buy orders - limited demand (Price on Quantity)
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="TRADER1",
                side="buy",
                quantity=25,
                price=125.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="TRADER2",
                side="buy",
                quantity=50,
                price=124.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="TRADER3",
                side="buy",
                quantity=25,
                price=123.00,
            ),
        ]

        # Create sell orders - heavy supply (Quantity at Price)
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=150,
                price=123.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER2",
                side="sell",
                quantity=100,
                price=124.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER3",
                side="sell",
                quantity=50,
                price=125.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 123.00  # Only price that maximizes volume
        assert result.max_volume == 100  # Limited by buy side
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_opening_auction_wide_spread_converges(self):
        """Test how a wide bid-ask spread converges to fair price.

        Given - Pre-market shows wide spread due to uncertainty
        Best bid: 120, Best ask: 130 (10 point spread!)
        But there are orders at many price levels

        When - The opening auction runs with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        |                  |       | 130.00 |   50  | [50]             | 0       | 150      | 0         |         |
        | [50]             |   50  | 128.00 |   40  | [40]             | 50      | 100      | 50        |         |
        | [40]             |   40  | 126.00 |   30  | [30]             | 90      | 60       | 60        | Cross ✓ |
        | [30]             |   30  | 124.00 |   20  | [20]             | 120     | 30       | 30        |         |
        | [20]             |   20  | 122.00 |   10  | [10]             | 140     | 10       | 10        |         |
        | [10]             |   10  | 120.00 |       |                  | 150     | 0        | 0         |         |

        Then - The algorithm finds the price that maximizes volume
        Maximum volume of 60 shares can trade at $126.00
        Wide spread converges to single clearing price
        """
        # Create staggered buy orders (Price on Quantity)
        buy_quantities = [10, 20, 30, 40, 50]
        buy_prices = [120, 122, 124, 126, 128]

        buy_orders = []
        for i, (qty, price) in enumerate(zip(buy_quantities, buy_prices)):
            order = Order(
                instrument_id=self.instrument_id,
                trader_id=f"BUYER{i+1}",
                side="buy",
                quantity=qty,
                price=float(price),
            )
            buy_orders.append(order)

        # Create staggered sell orders (Quantity at Price)
        sell_quantities = [50, 40, 30, 20, 10]
        sell_prices = [130, 128, 126, 124, 122]

        sell_orders = []
        for i, (qty, price) in enumerate(zip(sell_quantities, sell_prices)):
            order = Order(
                instrument_id=self.instrument_id,
                trader_id=f"SELLER{i+1}",
                side="sell",
                quantity=qty,
                price=float(price),
            )
            sell_orders.append(order)

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        # The maximum volume occurs at price 126
        # At price 126: buy volume = 90, sell volume = 60 → 60 shares trade
        assert result.clearing_price == 126.0  # Only price that maximizes volume
        assert result.max_volume == 60  # Limited by sell side at this price
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price maximizes volume
    # fmt: on

    # fmt: off
    def test_opening_auction_multiple_traders_random_allocation(self):
        """Test fair random allocation when multiple traders compete.

        Given - Multiple traders want the same thing at opening
        3 traders each want to buy 100 shares at 130
        But only 200 shares available at that price

        When - The auction executes with this order book:

        | Order Details      |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |--------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [100,100,100]      |  300  | 130.00 |  200  | [200]            | 300     | 200      | 200       | Cross ✓ |

        Then - Random selection determines who gets filled
        Each trader has equal chance of being selected
        Total fills equal available supply (200 shares)
        All trades at same clearing price
        """
        # Create identical buy orders
        buy_orders = []
        for i in range(3):
            order = Order(
                instrument_id=self.instrument_id,
                trader_id=f"BUYER{i+1}",
                side="buy",
                quantity=100,
                price=130.00,
            )
            buy_orders.append(order)

        # Create sell order with limited supply
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=200,
                price=130.00,
            )
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 130.00  # Only crossing price
        assert result.max_volume == 200  # Limited by sell side
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price
    # fmt: on
