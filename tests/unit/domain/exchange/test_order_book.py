"""
Unit tests for the OrderBook class.

These tests verify the core order matching functionality of the exchange,
including price-time priority, partial fills, order cancellation, and
market data generation.
"""

import pytest

from intern_trading_game.domain.exchange.order_book import OrderBook
from tests.fixtures import (
    create_test_order,
)


# Test Fixtures
@pytest.fixture
def empty_book():
    """Create empty SPX option order book."""
    return OrderBook("SPX_CALL_4500_20240315")


@pytest.fixture
def book_with_liquidity():
    """
    Create order book with buy/sell orders at multiple price levels.

    Initial state:
    - Asks: 100.0 (20), 100.5 (15), 101.0 (10)
    - Bids: 99.5 (15), 99.0 (20), 98.5 (10)
    """
    book = OrderBook("SPX_CALL_4500_20240315")

    # Add custom orders to match the original test's expectations
    book.add_order(
        create_test_order(
            side="sell", price=100.0, quantity=20, trader_id="mm1"
        )
    )
    book.add_order(
        create_test_order(
            side="sell", price=100.5, quantity=15, trader_id="mm2"
        )
    )
    book.add_order(
        create_test_order(
            side="sell", price=101.0, quantity=10, trader_id="mm3"
        )
    )

    # Add buy orders (bids)
    book.add_order(
        create_test_order(side="buy", price=99.5, quantity=15, trader_id="mm4")
    )
    book.add_order(
        create_test_order(side="buy", price=99.0, quantity=20, trader_id="mm5")
    )
    book.add_order(
        create_test_order(side="buy", price=98.5, quantity=10, trader_id="mm6")
    )

    return book


class TestOrderBookBasics:
    """Test basic order book initialization and validation."""

    def test_orderbook_initialization(self, empty_book):
        # Given - A newly created order book for an SPX option
        # When - We check its initial state
        # Then - The book should be empty with correct instrument ID
        assert empty_book.instrument_id == "SPX_CALL_4500_20240315"
        assert len(empty_book.bids) == 0
        assert len(empty_book.asks) == 0
        assert len(empty_book.order_ids) == 0
        assert empty_book.best_bid() is None
        assert empty_book.best_ask() is None

    def test_add_order_wrong_instrument(self, empty_book):
        # Given - An order book for SPX options
        # When - We try to add an order for a different instrument (SPY)
        # Then - The order should be rejected with a clear error message
        spy_order = create_test_order(instrument_id="SPY_CALL_450_20240315")

        with pytest.raises(
            ValueError,
            match="Order instrument SPY_CALL_450_20240315 does not match",
        ):
            empty_book.add_order(spy_order)

    def test_add_order_duplicate_id(self, empty_book):
        # Given - An order book with an existing order
        # The exchange needs to prevent duplicate order IDs to maintain
        # order integrity and prevent accidental double-submission.
        order1 = create_test_order(price=100.0)
        empty_book.add_order(order1)

        # When - We try to add another order with the same ID
        # This might happen if a trader's system has a bug or network issues
        # cause a retry with the same order ID.
        order2 = create_test_order(price=101.0)
        order2.order_id = order1.order_id

        # Then - The duplicate should be rejected
        with pytest.raises(
            ValueError, match=f"Order ID {order1.order_id} already exists"
        ):
            empty_book.add_order(order2)

    def test_empty_orderbook_state(self, empty_book):
        # Given - An empty order book with no orders
        # When - We query various market data
        # Then - All queries should return empty/None appropriately
        assert empty_book.best_bid() is None
        assert empty_book.best_ask() is None
        assert empty_book.get_order("nonexistent") is None
        assert empty_book.cancel_order("nonexistent") is None

        depth = empty_book.depth_snapshot()
        assert depth["bids"] == []
        assert depth["asks"] == []

        trades = empty_book.get_recent_trades()
        assert trades == []


class TestPriceTimePriority:
    """Test price-time priority matching algorithm."""

    def test_price_priority_buy_orders(self, empty_book):
        # Given - Multiple sell orders at different prices in the book
        # A market maker has posted asks at 100, 101, and 102 to provide
        # liquidity. These represent increasing price levels where the MM
        # is willing to sell the option.
        ask1 = create_test_order(
            side="sell", price=101.0, quantity=10, trader_id="mm1"
        )
        ask2 = create_test_order(
            side="sell", price=100.0, quantity=10, trader_id="mm2"
        )
        ask3 = create_test_order(
            side="sell", price=102.0, quantity=10, trader_id="mm3"
        )

        # Add in random order to test sorting
        empty_book.add_order(ask1)
        empty_book.add_order(ask2)
        empty_book.add_order(ask3)

        # When - An aggressive buy order arrives that can match multiple levels
        # A trader submits a buy order at 101.5, willing to pay up to that price
        buy_order = create_test_order(side="buy", price=101.5, quantity=25)
        trades = empty_book.add_order(buy_order)

        # Then - The order matches the lowest ask first (best price for buyer)
        # Price priority ensures the buyer gets the best available prices
        assert len(trades) == 2
        assert trades[0].price == 100.0  # Best ask matched first
        assert trades[0].quantity == 10
        assert trades[1].price == 101.0  # Second best ask
        assert trades[1].quantity == 10

        # Remaining 5 shares added to book as bid
        assert empty_book.best_bid() == (101.5, 5)

    def test_price_priority_sell_orders(self, empty_book):
        # Given - Multiple buy orders at different prices
        # Market participants have posted bids at various price levels,
        # representing demand for the option at those prices.
        bid1 = create_test_order(
            side="buy", price=99.0, quantity=10, trader_id="mm1"
        )
        bid2 = create_test_order(
            side="buy", price=100.0, quantity=10, trader_id="mm2"
        )
        bid3 = create_test_order(
            side="buy", price=98.0, quantity=10, trader_id="mm3"
        )

        # Add in random order to test sorting
        empty_book.add_order(bid1)
        empty_book.add_order(bid2)
        empty_book.add_order(bid3)

        # When - An aggressive sell order arrives
        # A trader needs to sell quickly and is willing to accept 98.5
        sell_order = create_test_order(side="sell", price=98.5, quantity=25)
        trades = empty_book.add_order(sell_order)

        # Then - The order matches the highest bid first (best price for seller)
        assert len(trades) == 2
        assert trades[0].price == 100.0  # Best bid matched first
        assert trades[0].quantity == 10
        assert trades[1].price == 99.0  # Second best bid
        assert trades[1].quantity == 10

        # Remaining 5 shares added to book as ask
        assert empty_book.best_ask() == (98.5, 5)

    def test_time_priority_same_price(self, empty_book):
        # Given - Multiple orders at the same price level
        # Three market makers post sell orders at the same price.
        # In real markets, being first at a price level gives priority.
        order1 = create_test_order(
            side="sell", price=100.0, quantity=5, trader_id="mm1"
        )
        order2 = create_test_order(
            side="sell", price=100.0, quantity=5, trader_id="mm2"
        )
        order3 = create_test_order(
            side="sell", price=100.0, quantity=5, trader_id="mm3"
        )

        # Track order IDs to verify FIFO
        order_ids = [order1.order_id, order2.order_id, order3.order_id]

        empty_book.add_order(order1)
        empty_book.add_order(order2)
        empty_book.add_order(order3)

        # When - A buy order arrives that will match all three
        # The buyer wants 15 shares at 100 or better
        buy_order = create_test_order(side="buy", price=100.0, quantity=15)
        trades = empty_book.add_order(buy_order)

        # Then - Orders are matched in FIFO order (time priority)
        # This rewards market makers who were first to provide liquidity
        assert len(trades) == 3
        for i, trade in enumerate(trades):
            assert trade.seller_order_id == order_ids[i]
            assert trade.price == 100.0
            assert trade.quantity == 5

    def test_price_improvement_scenario(self, book_with_liquidity):
        # Given - A wide market with 99.5 bid / 100.0 ask
        # The half-dollar spread represents an opportunity for price improvement
        assert book_with_liquidity.best_bid() == (99.5, 15)
        assert book_with_liquidity.best_ask() == (100.0, 20)

        # When - A new participant improves the bid to 99.75
        # This trader is willing to pay more than the current best bid,
        # narrowing the spread and providing better prices for sellers
        improved_bid = create_test_order(side="buy", price=99.75, quantity=10)
        book_with_liquidity.add_order(improved_bid)

        # Then - The next market sell order gets the better price
        # Price improvement benefits the seller who gets 99.75 instead of 99.5
        market_sell = create_test_order(side="sell", price=None, quantity=5)
        trades = book_with_liquidity.add_order(market_sell)

        assert len(trades) == 1
        assert trades[0].price == 99.75  # Improved price
        assert trades[0].quantity == 5


class TestMarketOrders:
    """Test market order handling and execution."""

    def test_market_buy_immediate_fill(self, book_with_liquidity):
        # Given - An order book with sell orders (asks) available
        # The book has liquidity at 100.0, 100.5, and 101.0
        assert book_with_liquidity.best_ask() == (100.0, 20)

        # When - A market buy order is submitted
        # Market orders indicate urgency - the trader wants immediate execution
        # at the best available price, regardless of what that price is
        market_buy = create_test_order(side="buy", price=None, quantity=15)
        trades = book_with_liquidity.add_order(market_buy)

        # Then - The order fills immediately at the best ask price
        # No remainder is added to the book (market orders never rest)
        assert len(trades) == 1
        assert trades[0].price == 100.0
        assert trades[0].quantity == 15
        assert trades[0].aggressor_side == "buy"

        # Verify the ask was partially filled
        assert book_with_liquidity.best_ask() == (100.0, 5)

    def test_market_sell_immediate_fill(self, book_with_liquidity):
        # Given - An order book with buy orders (bids) available
        # The book has liquidity at 99.5, 99.0, and 98.5
        assert book_with_liquidity.best_bid() == (99.5, 15)

        # When - A market sell order is submitted
        # The trader needs to exit their position immediately
        market_sell = create_test_order(side="sell", price=None, quantity=10)
        trades = book_with_liquidity.add_order(market_sell)

        # Then - The order fills immediately at the best bid price
        assert len(trades) == 1
        assert trades[0].price == 99.5
        assert trades[0].quantity == 10
        assert trades[0].aggressor_side == "sell"

        # Verify the bid was partially filled
        assert book_with_liquidity.best_bid() == (99.5, 5)

    def test_market_order_partial_fill(self, empty_book):
        # Given - Limited liquidity in the book
        # Only 15 shares are available at the ask, but trader wants 25
        ask = create_test_order(
            side="sell", price=100.0, quantity=15, trader_id="mm1"
        )
        empty_book.add_order(ask)

        # When - A large market buy order is submitted
        # The trader wants 25 shares immediately, accepting partial fills
        market_buy = create_test_order(side="buy", price=None, quantity=25)
        trades = empty_book.add_order(market_buy)

        # Then - Only the available liquidity is filled
        # The remaining 10 shares are NOT added to the book (market orders don't rest)
        assert len(trades) == 1
        assert trades[0].quantity == 15

        # Book should now be empty on the ask side
        assert empty_book.best_ask() is None
        assert empty_book.best_bid() is None  # Unfilled portion not added

    def test_market_order_no_liquidity(self, empty_book):
        # Given - No liquidity on the opposite side of the market
        # This can happen in illiquid options or during market stress
        assert empty_book.best_ask() is None

        # When - A market buy order is submitted
        # Trader wants immediate execution but there's nothing to match
        market_buy = create_test_order(side="buy", price=None, quantity=10)
        trades = empty_book.add_order(market_buy)

        # Then - No trades occur and order is not added to book
        # Market orders that can't execute are typically cancelled
        assert len(trades) == 0
        assert empty_book.best_bid() is None  # Not added as limit order


class TestLimitOrders:
    """Test limit order handling and execution."""

    def test_limit_order_crosses_spread(self, book_with_liquidity):
        # Given - Current market is 99.5 bid / 100.0 ask
        # A typical spread in liquid option markets
        assert book_with_liquidity.best_bid() == (99.5, 15)
        assert book_with_liquidity.best_ask() == (100.0, 20)

        # When - A buy limit order is placed above the ask
        # This is an "aggressive" or "marketable" limit order that
        # will execute immediately but protects against bad fills
        aggressive_buy = create_test_order(
            side="buy", price=100.5, quantity=30
        )
        trades = book_with_liquidity.add_order(aggressive_buy)

        # Then - The order executes at the ask prices (price improvement)
        # The trader was willing to pay 100.5 but gets filled at better prices
        assert len(trades) == 2
        assert trades[0].price == 100.0  # First 20 shares at best ask
        assert trades[0].quantity == 20
        assert trades[1].price == 100.5  # Next 10 shares at second level
        assert trades[1].quantity == 10

        # No remaining quantity becomes new best bid (30 total filled)
        assert book_with_liquidity.best_bid() == (99.5, 15)  # Unchanged
        assert book_with_liquidity.best_ask() == (
            100.5,
            5,
        )  # 15 - 10 remaining

    def test_limit_order_adds_liquidity(self, book_with_liquidity):
        # Given - Current market is 99.5 bid / 100.0 ask
        # Half-dollar wide spread provides room for liquidity providers
        initial_ask = book_with_liquidity.best_ask()

        # When - A participant adds a buy limit order inside the spread
        # This "passive" order narrows the spread and adds liquidity
        passive_buy = create_test_order(side="buy", price=99.75, quantity=5)
        trades = book_with_liquidity.add_order(passive_buy)

        # Then - No immediate execution, order added to book
        # The order improves the market by tightening the spread
        assert len(trades) == 0
        assert book_with_liquidity.best_bid() == (99.75, 5)
        assert book_with_liquidity.best_ask() == initial_ask

    def test_aggressive_limit_sweeps_book(self, empty_book):
        # Given - Multiple price levels of liquidity
        # Market makers have layered their offers at different prices
        empty_book.add_order(
            create_test_order(
                side="sell", price=100.0, quantity=10, trader_id="mm1"
            )
        )
        empty_book.add_order(
            create_test_order(
                side="sell", price=100.5, quantity=10, trader_id="mm2"
            )
        )
        empty_book.add_order(
            create_test_order(
                side="sell", price=101.0, quantity=10, trader_id="mm3"
            )
        )

        # When - A large aggressive limit order "sweeps" multiple levels
        # This might be a trader urgently building a position
        sweep_buy = create_test_order(side="buy", price=102.0, quantity=35)
        trades = empty_book.add_order(sweep_buy)

        # Then - The order fills across multiple price levels
        # Executes at progressively worse prices as it sweeps the book
        assert len(trades) == 3
        assert trades[0].price == 100.0
        assert trades[0].quantity == 10
        assert trades[1].price == 100.5
        assert trades[1].quantity == 10
        assert trades[2].price == 101.0
        assert trades[2].quantity == 10

        # Remaining 5 shares posted as new best bid
        assert empty_book.best_bid() == (102.0, 5)


class TestPartialFills:
    """Test partial fill scenarios and order state management."""

    def test_partial_fill_updates_quantities(self, empty_book):
        # Given - A large sell order in the book
        # A market maker posts size at a price level
        large_sell = create_test_order(
            side="sell", price=100.0, quantity=100, trader_id="mm1"
        )
        empty_book.add_order(large_sell)

        # When - A smaller buy order partially fills it
        # Retail trader takes some but not all liquidity
        small_buy = create_test_order(side="buy", price=100.0, quantity=60)
        trades = empty_book.add_order(small_buy)

        # Then - Trade occurs and quantities update correctly
        assert len(trades) == 1
        assert trades[0].quantity == 60

        # Verify remaining quantity in book
        assert empty_book.best_ask() == (100.0, 40)

        # Check the order itself was updated
        remaining_order = empty_book.get_order(large_sell.order_id)
        assert remaining_order.remaining_quantity == 40
        assert remaining_order.filled_quantity == 60

    def test_multiple_partial_fills(self, empty_book):
        # Given - A large resting order that will be hit multiple times
        # Institutional order provides significant liquidity at one price
        large_order = create_test_order(
            side="sell", price=100.0, quantity=100, trader_id="inst1"
        )
        empty_book.add_order(large_order)

        # When - Multiple smaller orders chip away at it
        # Various traders take liquidity over time
        fills = []
        for i, qty in enumerate([30, 25, 20, 15]):
            buy = create_test_order(
                side="buy", price=100.0, quantity=qty, trader_id=f"trader{i}"
            )
            trades = empty_book.add_order(buy)
            fills.extend(trades)

        # Then - Each fill reduces the remaining quantity correctly
        assert len(fills) == 4
        assert sum(trade.quantity for trade in fills) == 90

        # 10 shares should remain
        assert empty_book.best_ask() == (100.0, 10)
        remaining = empty_book.get_order(large_order.order_id)
        assert remaining.remaining_quantity == 10
        assert remaining.filled_quantity == 90

    def test_partial_fill_order_state(self, empty_book):
        # Given - An order that will be partially filled
        sell_order = create_test_order(side="sell", price=100.0, quantity=50)
        empty_book.add_order(sell_order)

        # When - A partial fill occurs
        buy_order = create_test_order(side="buy", price=100.0, quantity=30)
        _ = empty_book.add_order(buy_order)

        # Then - Order state reflects the partial fill
        order = empty_book.get_order(sell_order.order_id)
        assert not order.is_filled  # Still open
        assert order.remaining_quantity == 20
        assert order.filled_quantity == 30

        # Order should still be in the book's tracking structures
        assert sell_order.order_id in empty_book.order_ids
        assert sell_order.order_id in empty_book.order_price_map


class TestOrderCancellation:
    """Test order cancellation functionality."""

    def test_cancel_resting_order(self, empty_book):
        # Given - An order resting in the book
        # Trader has posted a limit order and wants to cancel it
        order = create_test_order(side="buy", price=99.0, quantity=10)
        empty_book.add_order(order)
        assert empty_book.best_bid() == (99.0, 10)

        # When - The trader cancels their order
        # This is a common operation when market conditions change
        cancelled = empty_book.cancel_order(order.order_id)

        # Then - Order is removed from book completely
        assert cancelled is not None
        assert cancelled.order_id == order.order_id
        assert empty_book.best_bid() is None
        assert order.order_id not in empty_book.order_ids
        assert order.order_id not in empty_book.order_price_map

    def test_cancel_nonexistent_order(self, empty_book):
        # Given - An order ID that doesn't exist in the book
        # When - Someone tries to cancel it (could be duplicate request)
        # Then - Should return None without errors
        result = empty_book.cancel_order("fake_order_id")
        assert result is None

    def test_cancel_updates_price_level(self, empty_book):
        # Given - Multiple orders at the same price level
        # Several traders have orders at the same price
        order1 = create_test_order(
            side="buy", price=99.0, quantity=10, trader_id="t1"
        )
        order2 = create_test_order(
            side="buy", price=99.0, quantity=15, trader_id="t2"
        )
        order3 = create_test_order(
            side="buy", price=99.0, quantity=5, trader_id="t3"
        )

        empty_book.add_order(order1)
        empty_book.add_order(order2)
        empty_book.add_order(order3)

        assert empty_book.best_bid() == (99.0, 30)

        # When - One trader cancels their order
        empty_book.cancel_order(order2.order_id)

        # Then - Price level quantity is updated correctly
        assert empty_book.best_bid() == (99.0, 15)  # 30 - 15

        # Other orders remain unaffected
        assert empty_book.get_order(order1.order_id) is not None
        assert empty_book.get_order(order3.order_id) is not None

    def test_cancel_removes_empty_level(self, empty_book):
        # Given - A single order at a price level
        # Only one trader has an order at this price
        order = create_test_order(side="buy", price=99.0, quantity=10)
        empty_book.add_order(order)

        # Verify internal structure
        assert len(empty_book.bids) == 1

        # When - That order is cancelled
        empty_book.cancel_order(order.order_id)

        # Then - The empty price level is removed entirely
        # This keeps the book structure efficient
        assert len(empty_book.bids) == 0
        assert empty_book.best_bid() is None


class TestBestPrices:
    """Test best bid/ask tracking and updates."""

    def test_best_bid_tracking(self, empty_book):
        # Given - Multiple bid levels added in random order
        # Traders submit bids at different price points
        empty_book.add_order(
            create_test_order(side="buy", price=98.0, quantity=10)
        )
        empty_book.add_order(
            create_test_order(side="buy", price=99.0, quantity=15)
        )
        empty_book.add_order(
            create_test_order(side="buy", price=97.5, quantity=5)
        )

        # When - We query the best bid
        # Then - Returns the highest price and total quantity at that level
        best = empty_book.best_bid()
        assert best == (99.0, 15)

    def test_best_ask_tracking(self, empty_book):
        # Given - Multiple ask levels added in random order
        empty_book.add_order(
            create_test_order(side="sell", price=101.0, quantity=10)
        )
        empty_book.add_order(
            create_test_order(side="sell", price=100.0, quantity=20)
        )
        empty_book.add_order(
            create_test_order(side="sell", price=102.0, quantity=5)
        )

        # When - We query the best ask
        # Then - Returns the lowest price and total quantity at that level
        best = empty_book.best_ask()
        assert best == (100.0, 20)

    def test_best_prices_after_fills(self, book_with_liquidity):
        # Given - Initial best prices
        # Market is 99.5 x 100.0 with size on both sides
        assert book_with_liquidity.best_bid() == (99.5, 15)
        assert book_with_liquidity.best_ask() == (100.0, 20)

        # When - Orders partially fill the best levels
        # A 12-share buy order hits the ask
        buy = create_test_order(side="buy", price=100.0, quantity=12)
        book_with_liquidity.add_order(buy)

        # Then - Best prices show updated quantities
        assert book_with_liquidity.best_ask() == (100.0, 8)  # 20 - 12
        assert book_with_liquidity.best_bid() == (99.5, 15)  # Unchanged

    def test_best_prices_empty_book(self, empty_book):
        # Given - An empty order book with no orders
        # When - We query best bid and ask
        # Then - Both return None to indicate no market
        assert empty_book.best_bid() is None
        assert empty_book.best_ask() is None


class TestMarketDepth:
    """Test market depth snapshot functionality."""

    def test_depth_snapshot_multiple_levels(self, book_with_liquidity):
        # Given - An order book with multiple price levels
        # The book has 3 levels on each side with various quantities

        # When - We request a 5-level depth snapshot
        # Market data feeds typically show top 5 levels
        depth = book_with_liquidity.depth_snapshot(levels=5)

        # Then - Returns available levels with aggregated quantities
        assert len(depth["bids"]) == 3  # Only 3 levels available
        assert len(depth["asks"]) == 3

        # Verify bid levels (highest to lowest)
        assert depth["bids"][0] == (99.5, 15)
        assert depth["bids"][1] == (99.0, 20)
        assert depth["bids"][2] == (98.5, 10)

        # Verify ask levels (lowest to highest)
        assert depth["asks"][0] == (100.0, 20)
        assert depth["asks"][1] == (100.5, 15)
        assert depth["asks"][2] == (101.0, 10)

    def test_depth_snapshot_fewer_levels(self, empty_book):
        # Given - A book with only 2 price levels per side
        empty_book.add_order(
            create_test_order(side="buy", price=99.0, quantity=10)
        )
        empty_book.add_order(
            create_test_order(side="buy", price=98.0, quantity=5)
        )
        empty_book.add_order(
            create_test_order(side="sell", price=100.0, quantity=10)
        )
        empty_book.add_order(
            create_test_order(side="sell", price=101.0, quantity=5)
        )

        # When - We request 5 levels of depth
        depth = empty_book.depth_snapshot(levels=5)

        # Then - Returns only available levels, not padded
        assert len(depth["bids"]) == 2
        assert len(depth["asks"]) == 2

    @pytest.mark.parametrize("levels", [1, 3, 5, 10])
    def test_depth_snapshot_various_depths(self, book_with_liquidity, levels):
        # Given - A book with 3 levels per side
        # When - We request various depth levels
        depth = book_with_liquidity.depth_snapshot(levels=levels)

        # Then - Returns up to the requested number of levels
        assert len(depth["bids"]) == min(levels, 3)
        assert len(depth["asks"]) == min(levels, 3)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_quantity_order(self):
        # Given - An order with zero quantity
        # This should be caught by Order validation, not OrderBook
        # When/Then - Order creation should fail
        with pytest.raises(
            ValueError, match="Order quantity must be positive"
        ):
            create_test_order(quantity=0)

    def test_negative_price_order(self):
        # Given - An order with negative price
        # Negative prices don't make sense for options
        # When/Then - Order creation should fail
        with pytest.raises(
            ValueError, match="Limit orders must have a positive price"
        ):
            create_test_order(price=-10.0)

    def test_fractional_price_order(self):
        # Given - Orders with fractional cent prices
        # Options trade in penny increments, not fractional pennies
        # When - We try to create orders with fractional prices
        # Then - Should raise validation error
        with pytest.raises(
            ValueError, match="Order price must be in penny increments"
        ):
            create_test_order(price=100.123)  # $100.123 not allowed

    def test_self_trade(self, empty_book):
        # Given - Orders from the same trader on both sides
        # Some exchanges prevent self-trading, but this implementation doesn't
        sell = create_test_order(
            side="sell", price=100.0, quantity=10, trader_id="trader1"
        )
        buy = create_test_order(
            side="buy", price=100.0, quantity=10, trader_id="trader1"
        )

        empty_book.add_order(sell)
        trades = empty_book.add_order(buy)

        # Then - Self-trade is allowed (no prevention)
        assert len(trades) == 1
        assert trades[0].buyer_id == "trader1"
        assert trades[0].seller_id == "trader1"


class TestTradingScenarios:
    """Test realistic trading scenarios."""

    def test_market_maker_spread_capture(self, empty_book):
        # Given - A market maker quotes both sides of the market
        # MM posts a 99.50 bid and 100.50 ask, earning the $1 spread
        # plus any maker rebates from the exchange
        mm_bid = create_test_order(
            side="buy", price=99.50, quantity=10, trader_id="mm1"
        )
        mm_ask = create_test_order(
            side="sell", price=100.50, quantity=10, trader_id="mm1"
        )

        empty_book.add_order(mm_bid)
        empty_book.add_order(mm_ask)

        # When - Retail flow crosses the spread on both sides
        # Retail trader buys at the ask
        retail_buy = create_test_order(
            side="buy", price=None, quantity=5, trader_id="retail1"
        )
        buy_trades = empty_book.add_order(retail_buy)

        # Another retail trader sells at the bid
        retail_sell = create_test_order(
            side="sell", price=None, quantity=5, trader_id="retail2"
        )
        sell_trades = empty_book.add_order(retail_sell)

        # Then - Market maker captures the full spread
        # MM sold at 100.50 and bought at 99.50, earning $1 per share
        assert len(buy_trades) == 1
        assert buy_trades[0].price == 100.50
        assert buy_trades[0].seller_id == "mm1"

        assert len(sell_trades) == 1
        assert sell_trades[0].price == 99.50
        assert sell_trades[0].buyer_id == "mm1"

        # Spread profit = (100.50 - 99.50) * 5 = $5

    def test_momentum_trading_sweep(self, empty_book):
        # Given - Multiple ask levels representing sell-side liquidity
        # Market makers have layered their offers at increasing prices
        for i, (price, qty) in enumerate(
            [(100.0, 20), (100.5, 15), (101.0, 10), (101.5, 5)]
        ):
            empty_book.add_order(
                create_test_order(
                    side="sell", price=price, quantity=qty, trader_id=f"mm{i}"
                )
            )

        # When - A large buy order sweeps through multiple levels
        # This could be momentum trader or someone covering a short position
        sweep_order = create_test_order(side="buy", price=102.0, quantity=40)
        trades = empty_book.add_order(sweep_order)

        # Then - The order executes at progressively worse prices
        # This demonstrates the market impact of large orders
        assert len(trades) == 3
        assert trades[0].price == 100.0  # First 20 shares
        assert trades[1].price == 100.5  # Next 15 shares
        assert trades[2].price == 101.0  # Final 5 shares

        total_cost = sum(t.price * t.quantity for t in trades)
        avg_price = total_cost / 40
        assert avg_price > 100.0  # Paid more than initial ask

    def test_price_discovery_scenario(self, empty_book):
        # Given - An empty book with no price reference
        # This might happen at market open or for newly listed options

        # When - Market participants gradually discover fair value
        # First participant thinks fair value is around 100
        order1 = create_test_order(
            side="buy", price=98.0, quantity=5, trader_id="trader1"
        )
        empty_book.add_order(order1)

        # Another thinks it's worth more
        order2 = create_test_order(
            side="buy", price=99.0, quantity=10, trader_id="trader2"
        )
        empty_book.add_order(order2)

        # Seller appears willing to sell at market (or just below best bid)
        order3 = create_test_order(
            side="sell", price=98.5, quantity=8, trader_id="trader3"
        )
        trades = empty_book.add_order(order3)

        # Then - First trade establishes market price
        # The sell order at 98.5 will match the best bid at 99.0
        assert len(trades) == 1
        assert trades[0].price == 99.0  # Discovered price (best bid)
        assert trades[0].quantity == 8

        # Market now has remaining bids and the unfilled sell order added
        assert empty_book.best_bid() == (99.0, 2)  # 10 - 8 remaining
        assert empty_book.best_ask() is None  # Sell order was fully filled


class TestPerformance:
    """Test performance with large numbers of orders."""

    @pytest.mark.slow
    def test_orderbook_with_1000_orders(self, empty_book):
        # Given - We add 1000 orders across many price levels
        # This simulates a very active, liquid market
        import time

        # Add 500 buy orders from 90.0 to 99.9
        for i in range(500):
            price = 90.0 + (i * 0.02)
            order = create_test_order(
                side="buy",
                price=round(price, 2),
                quantity=10,
                trader_id=f"buyer{i}",
            )
            empty_book.add_order(order)

        # Add 500 sell orders from 100.0 to 109.9
        for i in range(500):
            price = 100.0 + (i * 0.02)
            order = create_test_order(
                side="sell",
                price=round(price, 2),
                quantity=10,
                trader_id=f"seller{i}",
            )
            empty_book.add_order(order)

        # When - A new order needs to match
        start_time = time.time()
        market_buy = create_test_order(side="buy", price=100.5, quantity=50)
        trades = empty_book.add_order(market_buy)
        execution_time = time.time() - start_time

        # Then - Matching completes within reasonable time
        assert len(trades) == 5  # Should match 5 orders at 100.0, 100.02, etc
        assert execution_time < 0.1  # Should be fast even with 1000 orders

        # Verify book consistency
        assert len(empty_book.order_ids) == 995  # 1000 - 5 filled

    @pytest.mark.slow
    def test_rapid_order_cancellations(self, empty_book):
        # Given - A full order book with many orders that won't match
        # Use separate price ranges for buys and sells to avoid matching
        order_ids = []
        for i in range(100):
            if i % 2 == 0:  # Buy orders at lower prices
                price = 95.0 + (i % 10) * 0.1  # 95.0 to 95.9
                side = "buy"
            else:  # Sell orders at higher prices
                price = 105.0 + (i % 10) * 0.1  # 105.0 to 105.9
                side = "sell"

            order = create_test_order(
                side=side, price=price, quantity=10, trader_id=f"trader{i}"
            )
            empty_book.add_order(order)
            order_ids.append(order.order_id)

        # Verify all orders were added (no matching occurred)
        assert len(empty_book.order_ids) == 100

        # When - We rapidly cancel half the orders randomly
        import random

        random.shuffle(order_ids)
        cancelled_count = 0

        for order_id in order_ids[:50]:
            result = empty_book.cancel_order(order_id)
            if result:
                cancelled_count += 1

        # Then - Book remains consistent after mass cancellations
        assert cancelled_count == 50
        assert len(empty_book.order_ids) == 50

        # Verify no orphaned data
        for order_id in empty_book.order_ids:
            assert order_id in empty_book.order_price_map
            assert empty_book.get_order(order_id) is not None


class TestFairness:
    """Test fairness of matching algorithm."""

    def test_time_priority_fairness(self, empty_book):
        # Given - 100 orders at the same price submitted in sequence
        # This tests that time priority is strictly maintained
        order_ids = []
        for i in range(100):
            order = create_test_order(
                side="sell", price=100.0, quantity=1, trader_id=f"trader{i}"
            )
            empty_book.add_order(order)
            order_ids.append(order.order_id)

        # When - We match against all orders
        # A large buy order takes all available liquidity
        buy_order = create_test_order(side="buy", price=100.0, quantity=100)
        trades = empty_book.add_order(buy_order)

        # Then - Orders are filled in exact submission order (FIFO)
        assert len(trades) == 100
        for i, trade in enumerate(trades):
            assert trade.seller_order_id == order_ids[i]

        # This ensures fair treatment of all participants
        # First to provide liquidity gets first priority
