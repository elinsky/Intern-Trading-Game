"""Unit tests for edge cases in batch auction pricing strategy.

These tests verify the MaximumVolumePricingStrategy handles edge cases correctly,
including no overlap, single orders, empty sides, and extreme imbalances.
"""

from intern_trading_game.domain.exchange.book.batch_auction_strategies import (
    MaximumVolumePricingStrategy,
)
from intern_trading_game.domain.exchange.components.core.models import Order


class TestEdgeCaseAuctions:
    """Test edge cases that the auction must handle gracefully."""

    def setup_method(self):
        """Set up test fixtures."""
        # Just create the strategy directly - no need for exchange
        self.strategy = MaximumVolumePricingStrategy()

        # We'll use a simple instrument ID for all tests
        self.instrument_id = "TEST_INSTRUMENT"

    # fmt: off
    def test_no_crossing_orders_no_trades(self):
        """Test auction with no overlapping prices.

        Given - Buy and sell orders with no price overlap
        Wide spread between bid and ask

        When - The auction executes with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        |                  |       | 129.00 |  100  | [100]            | 0       | 200      | 0         |         |
        |                  |       | 128.00 |  100  | [100]            | 0       | 100      | 0         |         |
        | [100]            |  100  | 127.00 |       |                  | 100     | 0        | 0         |         |
        | [100]            |  100  | 126.00 |       |                  | 200     | 0        | 0         |         |

        Then - No trades should occur
        All orders remain in the book
        Clearing price is 0 (no valid price)
        """
        # Buy orders below sell orders
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=100,
                price=127.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER2",
                side="buy",
                quantity=100,
                price=126.00,
            ),
        ]

        # Sell orders above buy orders
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=100,
                price=129.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER2",
                side="sell",
                quantity=100,
                price=128.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify no trades should occur
        assert result.clearing_price == 0.0  # No valid price
        assert result.max_volume == 0  # No trades possible
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # No crossing prices
    # fmt: on

    # fmt: off
    def test_single_order_each_side(self):
        """Test simplest case: one buyer, one seller.

        Given - Exactly one buy order and one sell order

        When - The auction executes with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [100]            |  100  | 128.00 |       |                  | 100     | 100      | 100       | Cross ✓ |
        |                  |       | 127.00 |  100  | [100]            | 100     | 100      | 100       | Cross ✓ |

        Then - Orders match at the midpoint
        Clearing price = (127.00 + 128.00) / 2 = 127.50
        """
        # Single buy order
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=100,
                price=128.00,
            )
        ]

        # Single sell order
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=100,
                price=127.00,
            )
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 127.50  # Midpoint of 127-128
        assert result.max_volume == 100  # Full match
        assert result.algorithm == "maximum_volume"
        assert result.price_range == (127.00, 128.00)  # Both prices allow 100 shares
    # fmt: on

    # fmt: off
    def test_identical_prices_maximum_matching(self):
        """Test when all orders are at the same price.

        Given - Multiple orders all at exactly the same price

        When - The auction executes with this order book:

        | Order Details         |  Buy  | Price  | Sell  | Order Details        | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |-----------------------|-------|--------|-------|----------------------|---------|----------|-----------|---------|
        | [100,50,75]           |  225  | 100.00 |  150  | [75,75]              | 225     | 150      | 150       | Cross ✓ |

        Then - All trades occur at that single price
        Random allocation determines who gets matched
        """
        # Multiple buy orders at same price
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=100,
                price=100.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER2",
                side="buy",
                quantity=50,
                price=100.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER3",
                side="buy",
                quantity=75,
                price=100.00,
            ),
        ]

        # Multiple sell orders at same price
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=75,
                price=100.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER2",
                side="sell",
                quantity=75,
                price=100.00,
            ),
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 100.00  # Only crossing price
        assert result.max_volume == 150  # Limited by sell side
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price
    # fmt: on

    # fmt: off
    def test_empty_one_side(self):
        """Test auction with orders on only one side.

        Given - Only buy orders, no sell orders

        When - The auction executes with this order book:

        | Order Details    |  Buy  | Price  | Sell  | Order Details    | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------|-------|--------|-------|------------------|---------|----------|-----------|---------|
        | [200]            |  200  | 130.00 |       |                  | 200     | 0        | 0         |         |
        | [100]            |  100  | 129.00 |       |                  | 300     | 0        | 0         |         |

        Then - No trades occur
        Orders rest in book waiting for other side
        """
        # Only buy orders
        buy_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER1",
                side="buy",
                quantity=200,
                price=130.00,
            ),
            Order(
                instrument_id=self.instrument_id,
                trader_id="BUYER2",
                side="buy",
                quantity=100,
                price=129.00,
            ),
        ]

        # No sell orders
        sell_orders = []

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify no trades should occur
        assert result.clearing_price == 0.0  # No valid price
        assert result.max_volume == 0  # No trades possible
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # No crossing prices
    # fmt: on

    # fmt: off
    def test_huge_imbalance_handles_gracefully(self):
        """Test extreme imbalance between buy and sell.

        Given - Massive buy interest vs tiny sell interest

        When - The auction executes with this order book:

        | Order Details                      |  Buy   | Price  | Sell | Order Details | Buy Cum | Sell Cum | Vol@Price | Zone    |
        |------------------------------------|--------|--------|------|---------------|---------|----------|-----------|---------|
        | [500,500,500,500,500,500,500,500]  th| 4000   | 100.00 |   10 | [10]          | 4000    | 10       | 10        | Cross ✓ |

        Then - Only 10 shares trade (limited by sell side)
        Random selection among 4000 shares of demand
        System handles the imbalance without issues
        """
        # Create many large buy orders
        buy_orders = []
        for i in range(8):
            order = Order(
                instrument_id=self.instrument_id,
                trader_id=f"BUYER{i+1}",
                side="buy",
                quantity=500,
                price=100.00,
            )
            buy_orders.append(order)

        # One tiny sell order
        sell_orders = [
            Order(
                instrument_id=self.instrument_id,
                trader_id="SELLER1",
                side="sell",
                quantity=10,
                price=100.00,
            )
        ]

        # Call the strategy directly
        result = self.strategy.calculate_clearing_price(buy_orders, sell_orders)

        # Verify the results
        assert result.clearing_price == 100.00  # Only crossing price
        assert result.max_volume == 10  # Limited by tiny sell side
        assert result.algorithm == "maximum_volume"
        assert result.price_range is None  # Only one price
    # fmt: on
