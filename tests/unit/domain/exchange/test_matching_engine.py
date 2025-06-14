"""Comprehensive test suite for order matching engines.

This module tests both continuous and batch matching engines with a focus on:
1. Core functionality and happy paths
2. Edge cases and error conditions
3. Fair randomization in batch mode
4. Integration with ExchangeVenue

The tests are organized into sections for clarity and cover all the scenarios
identified in our design phase.
"""

import random
from collections import Counter

import pytest

from intern_trading_game.domain.exchange import (
    BatchMatchingEngine,
    ContinuousMatchingEngine,
    ExchangeVenue,
    Order,
    OrderBook,
)
from intern_trading_game.domain.exchange.core.instrument import Instrument

# Test fixtures


@pytest.fixture
def test_instrument():
    """Create a test instrument for use in tests."""
    return Instrument(symbol="TEST", underlying="TEST")


@pytest.fixture
def continuous_engine():
    """Create a continuous matching engine."""
    return ContinuousMatchingEngine()


@pytest.fixture
def batch_engine():
    """Create a batch matching engine."""
    return BatchMatchingEngine()


@pytest.fixture
def order_book():
    """Create an empty order book."""
    return OrderBook("TEST")


def create_test_order(
    instrument_id: str = "TEST",
    side: str = "buy",
    price: float = 100.0,
    quantity: int = 10,
    trader_id: str = "trader1",
    order_id: str = None,
) -> Order:
    """Helper to create test orders with sensible defaults."""
    if order_id is None:
        # Generate unique order ID
        order_id = f"ORD-{random.randint(1000, 9999)}"

    return Order(
        instrument_id=instrument_id,
        side=side,
        quantity=quantity,
        price=price,
        trader_id=trader_id,
        order_id=order_id,
    )


# ============================================================================
# CORE FUNCTIONALITY TESTS
# ============================================================================


def test_continuous_matching_engine_immediate_fill(
    continuous_engine, order_book
):
    """Test that continuous engine matches orders immediately when possible."""
    # GIVEN - Order book with a resting sell order
    # A seller has placed a limit sell order at $99.00 for 10 units.
    # This order is resting in the order book waiting for a buyer.
    sell_order = create_test_order(side="sell", price=99.0, trader_id="seller")
    order_book.add_order(sell_order)

    # WHEN - Submit a buy order that crosses the spread
    # A buyer submits a limit buy order at $100.00 for 10 units.
    # Since the buy price ($100) exceeds the sell price ($99),
    # these orders should match immediately in continuous mode.
    buy_order = create_test_order(side="buy", price=100.0, trader_id="buyer")
    result = continuous_engine.submit_order(buy_order, order_book)

    # THEN - Order should be filled immediately at the sell price
    # The trade executes at the passive (resting) order's price of $99.
    # Both orders are completely filled with no remaining quantity.
    assert result.status == "filled"
    assert len(result.fills) == 1
    assert result.fills[0].price == 99.0  # Matches at sell price
    assert result.remaining_quantity == 0


def test_continuous_matching_engine_partial_fill(
    continuous_engine, order_book
):
    """Test partial fills in continuous mode."""
    # GIVEN - Small sell order in the book
    # A seller offers only 5 units at $100.00.
    # This creates limited liquidity on the sell side.
    sell_order = create_test_order(side="sell", price=100.0, quantity=5)
    order_book.add_order(sell_order)

    # WHEN - Submit a larger buy order
    # A buyer wants to purchase 10 units at $100.00.
    # This buy order exceeds the available sell liquidity.
    buy_order = create_test_order(side="buy", price=100.0, quantity=10)
    result = continuous_engine.submit_order(buy_order, order_book)

    # THEN - Partial fill should occur
    # Only 5 units can be matched (the available sell quantity).
    # The remaining 5 units of the buy order stay in the book.
    assert result.status == "partially_filled"  # Not fully filled
    assert len(result.fills) == 1
    assert result.fills[0].quantity == 5
    assert result.remaining_quantity == 5


def test_batch_matching_engine_collects_orders(batch_engine, order_book):
    """Test that batch engine collects orders without immediate matching."""
    # GIVEN - A batch matching engine in collection phase
    # The batch engine is designed to collect all orders during
    # the submission window without executing any matches.

    # WHEN - Submit multiple crossing orders
    # A buyer wants 10 units at $100.00 and a seller offers at $99.00.
    # These orders would match immediately in continuous mode,
    # but batch mode holds them for later processing.
    order1 = create_test_order(side="buy", price=100.0)
    order2 = create_test_order(side="sell", price=99.0)

    result1 = batch_engine.submit_order(order1, order_book)
    result2 = batch_engine.submit_order(order2, order_book)

    # THEN - Orders should be pending, not matched
    # Both orders receive 'pending_new' status indicating they're
    # queued for batch processing. No trades occur yet.
    # The engine tracks 2 pending orders for this instrument.
    assert result1.status == "pending_new"
    assert result2.status == "pending_new"
    assert len(result1.fills) == 0
    assert len(result2.fills) == 0
    assert batch_engine.get_pending_count("TEST") == 2


def test_batch_matching_engine_price_priority(batch_engine):
    """Test that batch engine respects price priority."""
    # Given - Multiple orders at different prices
    orders = [
        create_test_order(side="buy", price=102.0, trader_id="buyer1"),
        create_test_order(side="buy", price=101.0, trader_id="buyer2"),
        create_test_order(side="buy", price=103.0, trader_id="buyer3"),
        create_test_order(side="sell", price=102.0, trader_id="seller1"),
    ]

    # When - Submit all orders and execute batch
    order_books = {"TEST": OrderBook("TEST")}
    for order in orders:
        batch_engine.submit_order(order, order_books["TEST"])

    results = batch_engine.execute_batch(order_books)

    # Then - Highest buy price (103) should fill first
    assert results["TEST"][orders[2].order_id].status == "filled"
    assert results["TEST"][orders[0].order_id].status == "new"  # Lower price
    assert results["TEST"][orders[1].order_id].status == "new"  # Lowest price
    assert (
        results["TEST"][orders[3].order_id].status == "filled"
    )  # Sell order should also fill


def test_batch_matching_engine_randomizes_same_price(batch_engine):
    """Test that orders at the same price are randomized fairly."""
    # This is a statistical test - we'll run multiple iterations
    # and check that order execution is roughly uniform

    fill_counts = Counter()
    iterations = 1000  # More iterations for stable statistics

    for iter_num in range(iterations):
        # Reset engine for each iteration
        engine = BatchMatchingEngine()
        order_books = {"TEST": OrderBook("TEST")}

        # Create 3 buy orders at same price, 1 sell order
        # Use iter_num to ensure unique order IDs
        buy_orders = [
            create_test_order(
                side="buy",
                price=100.0,
                trader_id=f"buyer{i}",
                order_id=f"BUY-{iter_num}-{i}",
            )
            for i in range(3)
        ]
        sell_order = create_test_order(
            side="sell",
            price=100.0,
            quantity=10,
            trader_id="seller",
            order_id=f"SELL-{iter_num}",
        )

        # Submit orders
        for order in buy_orders:
            engine.submit_order(order, order_books["TEST"])
        engine.submit_order(sell_order, order_books["TEST"])

        # Execute batch and see which buy order filled
        results = engine.execute_batch(order_books)

        for i, order in enumerate(buy_orders):
            if results["TEST"][order.order_id].status == "filled":
                fill_counts[i] += 1

    # Then - Each order should fill roughly 1/3 of the time
    # Using chi-square test bounds for fairness
    expected = iterations / 3
    for count in fill_counts.values():
        assert (
            expected * 0.7 < count < expected * 1.3
        ), f"Unfair randomization: {fill_counts}"


def test_batch_matching_engine_clears_after_batch(batch_engine, order_book):
    """Test that batch engine clears pending orders after execution."""
    # Given - Orders in the batch
    order1 = create_test_order(side="buy", price=100.0)
    batch_engine.submit_order(order1, order_book)
    assert batch_engine.get_pending_count("TEST") == 1

    # When - Execute batch
    order_books = {"TEST": order_book}
    batch_engine.execute_batch(order_books)

    # Then - Pending orders should be cleared
    assert batch_engine.get_pending_count("TEST") == 0


# ============================================================================
# EDGE CASES & SCENARIOS
# ============================================================================


def test_batch_matching_empty_batch(batch_engine):
    """Test executing batch with no pending orders."""
    # When - Execute empty batch
    order_books = {"TEST": OrderBook("TEST")}
    results = batch_engine.execute_batch(order_books)

    # Then - Should return empty results
    assert results == {}


def test_batch_matching_single_order(batch_engine, order_book):
    """Test batch with only one order."""
    # Given - Single order
    order = create_test_order(side="buy", price=100.0)
    batch_engine.submit_order(order, order_book)

    # When - Execute batch
    order_books = {"TEST": order_book}
    results = batch_engine.execute_batch(order_books)

    # Then - Order should be accepted (no match possible)
    assert results["TEST"][order.order_id].status == "new"


def test_batch_matching_no_crosses(batch_engine, order_book):
    """Test batch where no orders cross."""
    # Given - Buy below sell
    buy_order = create_test_order(side="buy", price=99.0)
    sell_order = create_test_order(side="sell", price=101.0)

    batch_engine.submit_order(buy_order, order_book)
    batch_engine.submit_order(sell_order, order_book)

    # When - Execute batch
    order_books = {"TEST": order_book}
    results = batch_engine.execute_batch(order_books)

    # Then - Both orders should be accepted (no match)
    assert results["TEST"][buy_order.order_id].status == "new"
    assert results["TEST"][sell_order.order_id].status == "new"


def test_batch_matching_multiple_instruments(batch_engine):
    """Test batch matching across multiple instruments."""
    # Given - Orders for different instruments
    order_books = {
        "TEST1": OrderBook("TEST1"),
        "TEST2": OrderBook("TEST2"),
    }

    # Orders for TEST1
    buy1 = create_test_order(instrument_id="TEST1", side="buy", price=100.0)
    sell1 = create_test_order(instrument_id="TEST1", side="sell", price=100.0)

    # Orders for TEST2
    buy2 = create_test_order(instrument_id="TEST2", side="buy", price=200.0)
    sell2 = create_test_order(instrument_id="TEST2", side="sell", price=200.0)

    # Submit all orders
    batch_engine.submit_order(buy1, order_books["TEST1"])
    batch_engine.submit_order(sell1, order_books["TEST1"])
    batch_engine.submit_order(buy2, order_books["TEST2"])
    batch_engine.submit_order(sell2, order_books["TEST2"])

    # When - Execute batch
    results = batch_engine.execute_batch(order_books)

    # Then - Both instruments should have matches
    assert "TEST1" in results
    assert "TEST2" in results
    assert results["TEST1"][buy1.order_id].status == "filled"
    assert results["TEST2"][buy2.order_id].status == "filled"


def test_batch_matching_all_orders_same_price(batch_engine):
    """Test batch with many orders at the same price."""
    # Given - 10 buy orders and 10 sell orders all at price 100
    order_books = {"TEST": OrderBook("TEST")}

    buy_orders = [
        create_test_order(side="buy", price=100.0, trader_id=f"buyer{i}")
        for i in range(10)
    ]
    sell_orders = [
        create_test_order(side="sell", price=100.0, trader_id=f"seller{i}")
        for i in range(10)
    ]

    # Submit all orders
    for order in buy_orders + sell_orders:
        batch_engine.submit_order(order, order_books["TEST"])

    # When - Execute batch
    results = batch_engine.execute_batch(order_books)

    # Then - All orders should match (equal buy/sell)
    for order in buy_orders + sell_orders:
        assert results["TEST"][order.order_id].status == "filled"


def test_batch_matching_more_buyers_than_sellers(batch_engine):
    """Test batch with more demand than supply."""
    # Given - 5 buyers, 2 sellers
    order_books = {"TEST": OrderBook("TEST")}

    buy_orders = [
        create_test_order(
            side="buy", price=100.0, quantity=10, trader_id=f"buyer{i}"
        )
        for i in range(5)
    ]
    sell_orders = [
        create_test_order(
            side="sell", price=100.0, quantity=10, trader_id=f"seller{i}"
        )
        for i in range(2)
    ]

    # Submit all orders
    for order in buy_orders + sell_orders:
        batch_engine.submit_order(order, order_books["TEST"])

    # When - Execute batch
    results = batch_engine.execute_batch(order_books)

    # Then - All sells should fill, only some buys
    filled_buys = sum(
        1 for o in buy_orders if results["TEST"][o.order_id].status == "filled"
    )
    filled_sells = sum(
        1
        for o in sell_orders
        if results["TEST"][o.order_id].status == "filled"
    )

    assert filled_sells == 2  # All sells fill
    assert filled_buys == 2  # Only 2 buys can fill


# ============================================================================
# ORDER PRIORITY TESTS
# ============================================================================


def test_batch_matching_buy_price_priority(batch_engine):
    """Test that higher buy prices have priority."""
    # Given - Multiple buy orders at different prices, one sell
    order_books = {"TEST": OrderBook("TEST")}

    buy_orders = [
        create_test_order(side="buy", price=98.0, trader_id="low"),
        create_test_order(side="buy", price=100.0, trader_id="high"),
        create_test_order(side="buy", price=99.0, trader_id="mid"),
    ]
    sell_order = create_test_order(side="sell", price=98.0, quantity=10)

    # Submit orders
    for order in buy_orders:
        batch_engine.submit_order(order, order_books["TEST"])
    batch_engine.submit_order(sell_order, order_books["TEST"])

    # When - Execute batch
    results = batch_engine.execute_batch(order_books)

    # Then - Highest price (100) should fill
    assert results["TEST"][buy_orders[1].order_id].status == "filled"
    assert results["TEST"][buy_orders[0].order_id].status == "new"
    assert results["TEST"][buy_orders[2].order_id].status == "new"


def test_batch_matching_sell_price_priority(batch_engine):
    """Test that lower sell prices have priority."""
    # Given - Multiple sell orders at different prices, one buy
    order_books = {"TEST": OrderBook("TEST")}

    sell_orders = [
        create_test_order(side="sell", price=102.0, trader_id="high"),
        create_test_order(side="sell", price=100.0, trader_id="low"),
        create_test_order(side="sell", price=101.0, trader_id="mid"),
    ]
    buy_order = create_test_order(side="buy", price=102.0, quantity=10)

    # Submit orders
    for order in sell_orders:
        batch_engine.submit_order(order, order_books["TEST"])
    batch_engine.submit_order(buy_order, order_books["TEST"])

    # When - Execute batch
    results = batch_engine.execute_batch(order_books)

    # Then - Lowest price (100) should fill
    assert results["TEST"][sell_orders[1].order_id].status == "filled"
    assert results["TEST"][sell_orders[0].order_id].status == "new"
    assert results["TEST"][sell_orders[2].order_id].status == "new"


def test_batch_matching_aggressive_cross_multiple_levels(batch_engine):
    """Test aggressive order that crosses multiple price levels."""
    # Given - Multiple sell orders at different prices
    order_books = {"TEST": OrderBook("TEST")}

    sell_orders = [
        create_test_order(
            side="sell", price=100.0, quantity=5, trader_id="sell1"
        ),
        create_test_order(
            side="sell", price=101.0, quantity=5, trader_id="sell2"
        ),
        create_test_order(
            side="sell", price=102.0, quantity=5, trader_id="sell3"
        ),
    ]

    # Large aggressive buy order
    buy_order = create_test_order(side="buy", price=102.0, quantity=12)

    # Submit orders
    for order in sell_orders:
        batch_engine.submit_order(order, order_books["TEST"])
    batch_engine.submit_order(buy_order, order_books["TEST"])

    # When - Execute batch
    results = batch_engine.execute_batch(order_books)

    # Then - Buy should fill against first two sells completely
    assert results["TEST"][sell_orders[0].order_id].status == "filled"
    assert results["TEST"][sell_orders[1].order_id].status == "filled"
    assert (
        results["TEST"][sell_orders[2].order_id].status == "partially_filled"
    )  # Partial
    assert (
        len(results["TEST"][buy_order.order_id].fills) == 3
    )  # 3 partial fills


def test_batch_matching_partial_fills_multiple_orders(batch_engine):
    """Test complex partial fill scenario."""
    # Given - Large sell order, multiple smaller buys
    order_books = {"TEST": OrderBook("TEST")}

    sell_order = create_test_order(side="sell", price=100.0, quantity=25)
    buy_orders = [
        create_test_order(
            side="buy", price=100.0, quantity=10, trader_id=f"buy{i}"
        )
        for i in range(3)
    ]

    # Submit orders
    batch_engine.submit_order(sell_order, order_books["TEST"])
    for order in buy_orders:
        batch_engine.submit_order(order, order_books["TEST"])

    # When - Execute batch
    results = batch_engine.execute_batch(order_books)

    # Then - Two buys should fill completely, one partial
    filled_count = sum(
        1 for o in buy_orders if results["TEST"][o.order_id].status == "filled"
    )
    partial_count = sum(
        1
        for o in buy_orders
        if results["TEST"][o.order_id].status == "partially_filled"
    )

    assert filled_count == 2
    assert partial_count == 1
    assert (
        results["TEST"][sell_order.order_id].status == "filled"
    )  # Sell order completely filled (25 qty)

    # The partially filled buy order should have 5 remaining
    partial_order = next(
        o
        for o in buy_orders
        if results["TEST"][o.order_id].status == "partially_filled"
    )
    assert results["TEST"][partial_order.order_id].remaining_quantity == 5


# ============================================================================
# RANDOMIZATION TESTING
# ============================================================================


def test_batch_randomization_is_fair():
    """Statistical test for randomization fairness."""
    # Run many iterations to ensure statistical fairness
    position_counts = {i: Counter() for i in range(3)}
    iterations = 1000  # More iterations for better statistical confidence

    for _ in range(iterations):
        # Three orders at same price
        orders = [
            create_test_order(side="buy", price=100.0, trader_id=f"trader{i}")
            for i in range(3)
        ]

        # Use the engine's sorting method directly on the orders
        engine = BatchMatchingEngine()
        sorted_orders = engine._randomize_same_price_orders(
            orders, descending=True
        )

        for position, order in enumerate(sorted_orders):
            trader_index = int(order.trader_id[-1])
            position_counts[trader_index][position] += 1

    # Check that each trader gets each position roughly equally
    expected = iterations / 3
    tolerance = 0.2  # 20% tolerance with 1000 iterations should be stable

    for trader_index, counts in position_counts.items():
        for position, count in counts.items():
            assert (
                expected * (1 - tolerance)
                <= count
                <= expected * (1 + tolerance)
            ), f"Trader {trader_index} unfairly gets position {position}: {count} times"


def test_batch_randomization_preserves_price_priority():
    """Ensure randomization never violates price priority."""
    engine = BatchMatchingEngine()

    # Orders at different prices
    orders = [
        create_test_order(side="buy", price=101.0, trader_id="high1"),
        create_test_order(side="buy", price=100.0, trader_id="mid1"),
        create_test_order(side="buy", price=101.0, trader_id="high2"),
        create_test_order(side="buy", price=99.0, trader_id="low1"),
        create_test_order(side="buy", price=100.0, trader_id="mid2"),
    ]

    # Randomize using the engine's method
    sorted_orders = engine._randomize_same_price_orders(
        orders, descending=True
    )

    # Check price priority is maintained
    prices = [o.price for o in sorted_orders]
    assert prices == sorted(prices, reverse=True), "Price priority violated"

    # Check that orders at same price are together
    price_groups = {}
    for i, order in enumerate(sorted_orders):
        if order.price not in price_groups:
            price_groups[order.price] = []
        price_groups[order.price].append(i)

    # Verify groups are contiguous
    for indices in price_groups.values():
        assert indices == list(range(indices[0], indices[-1] + 1))


def test_batch_randomization_different_each_time():
    """Test that randomization produces different results."""
    engine = BatchMatchingEngine()

    # Same orders each time
    def create_orders():
        return [
            create_test_order(side="buy", price=100.0, trader_id=f"trader{i}")
            for i in range(5)
        ]

    # Run multiple times and collect results
    results = []
    for _ in range(10):
        orders = create_orders()
        sorted_orders = engine._randomize_same_price_orders(
            orders, descending=True
        )
        order_sequence = [o.trader_id for o in sorted_orders]
        results.append(tuple(order_sequence))

    # Should have different sequences (very unlikely to have all same)
    unique_sequences = len(set(results))
    assert unique_sequences > 1, "Randomization appears to be deterministic"


# ============================================================================
# STATE MANAGEMENT TESTS
# ============================================================================


def test_batch_engine_pending_orders_isolated_by_instrument(batch_engine):
    """Test that pending orders are properly isolated by instrument."""
    # Given - Orders for different instruments
    order1 = create_test_order(instrument_id="TEST1", side="buy")
    order2 = create_test_order(instrument_id="TEST2", side="buy")
    order3 = create_test_order(instrument_id="TEST1", side="sell")

    # Submit orders
    batch_engine.submit_order(order1, OrderBook("TEST1"))
    batch_engine.submit_order(order2, OrderBook("TEST2"))
    batch_engine.submit_order(order3, OrderBook("TEST1"))

    # Then - Counts should be isolated
    assert batch_engine.get_pending_count("TEST1") == 2
    assert batch_engine.get_pending_count("TEST2") == 1
    assert batch_engine.get_pending_count("TEST3") == 0  # Non-existent


def test_continuous_engine_execute_batch_is_noop(continuous_engine):
    """Test that continuous engine's execute_batch does nothing."""
    # Given - Some order books
    order_books = {
        "TEST1": OrderBook("TEST1"),
        "TEST2": OrderBook("TEST2"),
    }

    # When - Execute batch
    results = continuous_engine.execute_batch(order_books)

    # Then - Should return empty
    assert results == {}


def test_exchange_venue_batch_matching_preserves_order_ids():
    """Test that order IDs are preserved through batch matching."""
    # Given - Exchange with batch engine
    exchange = ExchangeVenue(BatchMatchingEngine())
    exchange.list_instrument(Instrument(symbol="TEST", underlying="TEST"))

    # Create orders with specific IDs
    order_ids = ["ORDER-001", "ORDER-002", "ORDER-003"]
    orders = [
        create_test_order(side="buy", price=100.0, order_id=order_id)
        for order_id in order_ids
    ]

    # Submit orders
    for order in orders:
        result = exchange.submit_order(order)
        assert result.order_id == order.order_id

    # Execute batch
    results = exchange.execute_batch()

    # Check all order IDs are in results
    assert "TEST" in results
    for order_id in order_ids:
        assert order_id in results["TEST"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_exchange_venue_with_continuous_engine():
    """Test ExchangeVenue integration with continuous engine."""
    # Given - Default exchange (continuous)
    exchange = ExchangeVenue()
    exchange.list_instrument(Instrument(symbol="TEST", underlying="TEST"))

    # Verify mode
    assert exchange.get_matching_mode() == "continuous"

    # Submit crossing orders
    sell_order = create_test_order(side="sell", price=100.0)
    buy_order = create_test_order(side="buy", price=100.0)

    sell_result = exchange.submit_order(sell_order)
    buy_result = exchange.submit_order(buy_order)

    # Buy should match immediately
    assert sell_result.status == "new"
    assert buy_result.status == "filled"


def test_exchange_venue_with_batch_engine():
    """Test ExchangeVenue integration with batch engine."""
    # Given - Exchange with batch engine
    exchange = ExchangeVenue(BatchMatchingEngine())
    exchange.list_instrument(Instrument(symbol="TEST", underlying="TEST"))

    # Verify mode
    assert exchange.get_matching_mode() == "batch"

    # Submit crossing orders
    sell_order = create_test_order(side="sell", price=100.0)
    buy_order = create_test_order(side="buy", price=100.0)

    sell_result = exchange.submit_order(sell_order)
    buy_result = exchange.submit_order(buy_order)

    # Both should be pending
    assert sell_result.status == "pending_new"
    assert buy_result.status == "pending_new"

    # Execute batch
    results = exchange.execute_batch()

    # Now they should be filled
    assert results["TEST"][sell_order.order_id].status == "filled"
    assert results["TEST"][buy_order.order_id].status == "filled"


def test_exchange_venue_batch_multiple_instruments():
    """Test batch execution across multiple instruments."""
    # Given - Exchange with multiple instruments
    exchange = ExchangeVenue(BatchMatchingEngine())
    exchange.list_instrument(Instrument(symbol="SPX", underlying="SPX"))
    exchange.list_instrument(Instrument(symbol="SPY", underlying="SPY"))

    # Orders for each instrument
    spx_buy = create_test_order(instrument_id="SPX", side="buy", price=5000.0)
    spx_sell = create_test_order(
        instrument_id="SPX", side="sell", price=5000.0
    )
    spy_buy = create_test_order(instrument_id="SPY", side="buy", price=500.0)
    spy_sell = create_test_order(instrument_id="SPY", side="sell", price=500.0)

    # Submit all orders
    for order in [spx_buy, spx_sell, spy_buy, spy_sell]:
        exchange.submit_order(order)

    # Execute batch
    results = exchange.execute_batch()

    # Both instruments should have matches
    assert "SPX" in results
    assert "SPY" in results
    assert len(results["SPX"]) == 2
    assert len(results["SPY"]) == 2


def test_exchange_venue_batch_with_invalid_instrument(batch_engine):
    """Test batch execution when pending orders reference invalid instrument."""
    # Given - Batch engine with pending order for non-existent instrument
    order_books = {"TEST": OrderBook("TEST")}
    order = create_test_order(instrument_id="INVALID", side="buy")

    # Note: In reality, the order would be submitted to an "INVALID" order book
    # but for testing, we're manually adding it to pending orders
    batch_engine.pending_orders["INVALID"] = [order]

    # When - Execute batch (INVALID instrument not in order_books)
    results = batch_engine.execute_batch(order_books)

    # Then - Orders for invalid instruments get status "new" (unmatched)
    assert "INVALID" in results
    assert results["INVALID"][order.order_id].status == "new"
    assert len(results["INVALID"][order.order_id].fills) == 0


def test_exchange_venue_multiple_batches_sequential():
    """Test running multiple batches sequentially."""
    # Given - Exchange with batch engine
    exchange = ExchangeVenue(BatchMatchingEngine())
    exchange.list_instrument(Instrument(symbol="TEST", underlying="TEST"))

    # First batch
    order1 = create_test_order(side="buy", price=100.0, order_id="BATCH1-1")
    order2 = create_test_order(side="sell", price=100.0, order_id="BATCH1-2")

    exchange.submit_order(order1)
    exchange.submit_order(order2)

    results1 = exchange.execute_batch()
    assert len(results1["TEST"]) == 2

    # Second batch - should be independent
    order3 = create_test_order(side="buy", price=101.0, order_id="BATCH2-1")
    order4 = create_test_order(side="sell", price=101.0, order_id="BATCH2-2")

    exchange.submit_order(order3)
    exchange.submit_order(order4)

    results2 = exchange.execute_batch()
    assert len(results2["TEST"]) == 2

    # Results should be independent
    assert "BATCH1-1" not in results2["TEST"]
    assert "BATCH2-1" not in results1["TEST"]


# ============================================================================
# ERROR CASES
# ============================================================================


def test_batch_engine_duplicate_order_id_rejected():
    """Test that duplicate order IDs are rejected."""
    exchange = ExchangeVenue(BatchMatchingEngine())
    exchange.list_instrument(Instrument(symbol="TEST", underlying="TEST"))

    # Submit order
    order1 = create_test_order(order_id="DUP-001")
    exchange.submit_order(order1)

    # Try to submit duplicate
    order2 = create_test_order(order_id="DUP-001")
    with pytest.raises(ValueError, match="already exists"):
        exchange.submit_order(order2)


def test_continuous_engine_with_none_order_book():
    """Test continuous engine handles None order book gracefully."""
    engine = ContinuousMatchingEngine()
    order = create_test_order()

    # This should not crash - order book handles the matching
    # In practice, this shouldn't happen due to venue validation
    # but we test the engine in isolation
    with pytest.raises(AttributeError):
        engine.submit_order(order, None)


# ============================================================================
# PERFORMANCE/STRESS TESTS
# ============================================================================


@pytest.mark.slow
def test_batch_matching_thousand_orders_same_price():
    """Test batch matching performance with many orders at same price."""
    engine = BatchMatchingEngine()
    order_books = {"TEST": OrderBook("TEST")}

    # Create 1000 orders at same price
    num_orders = 1000
    buy_orders = [
        create_test_order(
            side="buy",
            price=100.0,
            quantity=1,
            trader_id=f"buyer{i}",
            order_id=f"BUY-{i:04d}",
        )
        for i in range(num_orders // 2)
    ]
    sell_orders = [
        create_test_order(
            side="sell",
            price=100.0,
            quantity=1,
            trader_id=f"seller{i}",
            order_id=f"SELL-{i:04d}",
        )
        for i in range(num_orders // 2)
    ]

    # Submit all orders
    import time

    start = time.time()

    for order in buy_orders + sell_orders:
        engine.submit_order(order, order_books["TEST"])

    # Execute batch
    results = engine.execute_batch(order_books)

    elapsed = time.time() - start

    # Verify all matched and performance is reasonable
    assert len(results["TEST"]) == num_orders
    assert (
        elapsed < 1.0
    ), f"Batch matching {num_orders} orders took {elapsed:.2f}s"


@pytest.mark.slow
def test_batch_matching_large_order_book_depth():
    """Test batch matching with many price levels."""
    engine = BatchMatchingEngine()
    order_books = {"TEST": OrderBook("TEST")}

    # Create orders at 100 different price levels
    orders = []
    for i in range(100):
        buy_price = 100.0 - i * 0.1
        sell_price = 101.0 + i * 0.1

        orders.append(
            create_test_order(
                side="buy", price=buy_price, order_id=f"BUY-{i:03d}"
            )
        )
        orders.append(
            create_test_order(
                side="sell", price=sell_price, order_id=f"SELL-{i:03d}"
            )
        )

    # Submit all orders
    for order in orders:
        engine.submit_order(order, order_books["TEST"])

    # Execute batch
    results = engine.execute_batch(order_books)

    # No orders should match (no crossing prices)
    assert all(r.status == "new" for r in results["TEST"].values())


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


@pytest.mark.parametrize(
    "engine_class", [ContinuousMatchingEngine, BatchMatchingEngine]
)
def test_engine_basic_invariants(engine_class):
    """Test basic invariants that both engines should satisfy."""
    engine = engine_class()
    order_book = OrderBook("TEST")

    # Submit non-crossing orders
    buy = create_test_order(side="buy", price=99.0)
    sell = create_test_order(side="sell", price=101.0)

    buy_result = engine.submit_order(buy, order_book)
    sell_result = engine.submit_order(sell, order_book)

    # Both engines should accept non-crossing orders
    assert buy_result.status in ["new", "pending_new"]
    assert sell_result.status in ["new", "pending_new"]

    # Mode should be correct
    assert engine.get_mode() in ["continuous", "batch"]


@pytest.mark.parametrize(
    "order_count,price_levels",
    [
        (10, 1),  # All same price
        (10, 10),  # All different prices
        (100, 5),  # Groups at each price
        (1000, 20),  # Large scale
    ],
)
def test_batch_randomization_distribution(order_count, price_levels):
    """Test randomization across different distributions."""
    engine = BatchMatchingEngine()

    # Create orders distributed across price levels
    orders = []
    for i in range(order_count):
        price_level = i % price_levels
        price = 100.0 + price_level
        orders.append(
            create_test_order(side="buy", price=price, trader_id=f"trader{i}")
        )

    # Randomize
    sorted_orders = engine._randomize_same_price_orders(
        orders, descending=True
    )

    # Verify price priority maintained
    for i in range(1, len(sorted_orders)):
        assert sorted_orders[i - 1].price >= sorted_orders[i].price


@pytest.mark.parametrize(
    "buy_orders,sell_orders,expected_trades",
    [
        ([100], [100], 1),  # Simple match
        ([100, 99], [101], 0),  # No cross
        (
            [102, 101],
            [100],
            1,
        ),  # Only one buy order can fill (limited by sell quantity)
        ([100], [100, 100], 1),  # Partial fill scenario
    ],
)
def test_batch_matching_scenarios(buy_orders, sell_orders, expected_trades):
    """Test various order matching scenarios."""
    engine = BatchMatchingEngine()
    order_books = {"TEST": OrderBook("TEST")}

    # Create and submit buy orders
    for i, price in enumerate(buy_orders):
        order = create_test_order(
            side="buy", price=float(price), order_id=f"BUY-{i}"
        )
        engine.submit_order(order, order_books["TEST"])

    # Create and submit sell orders
    for i, price in enumerate(sell_orders):
        order = create_test_order(
            side="sell", price=float(price), order_id=f"SELL-{i}"
        )
        engine.submit_order(order, order_books["TEST"])

    # Execute batch
    results = engine.execute_batch(order_books)

    # Count filled orders
    filled_count = sum(
        1 for r in results["TEST"].values() if r.status == "filled"
    )

    assert filled_count == expected_trades * 2  # Each trade involves 2 orders


# ============================================================================
# BUSINESS LOGIC TESTS
# ============================================================================


def test_batch_matching_fair_allocation():
    """Test fair allocation when limited liquidity available."""
    engine = BatchMatchingEngine()
    order_books = {"TEST": OrderBook("TEST")}

    # One seller with limited quantity
    sell_order = create_test_order(
        side="sell", price=100.0, quantity=30, trader_id="seller"
    )

    # Three buyers wanting more than available
    buy_orders = [
        create_test_order(
            side="buy", price=100.0, quantity=20, trader_id=f"buyer{i}"
        )
        for i in range(3)
    ]

    # Submit orders
    engine.submit_order(sell_order, order_books["TEST"])
    for order in buy_orders:
        engine.submit_order(order, order_books["TEST"])

    # Execute batch
    results = engine.execute_batch(order_books)

    # At least one buyer should be fully filled
    # Others might be partial or unfilled (depends on randomization)
    fill_quantities = [
        sum(t.quantity for t in results["TEST"][o.order_id].fills)
        for o in buy_orders
    ]

    assert sum(fill_quantities) == 30  # All liquidity consumed
    assert max(fill_quantities) >= 20  # At least one full fill


def test_batch_matching_self_trading():
    """Test handling of self-trading (same trader both sides)."""
    engine = BatchMatchingEngine()
    order_books = {"TEST": OrderBook("TEST")}

    # Same trader submits both buy and sell
    buy_order = create_test_order(
        side="buy", price=100.0, trader_id="trader1", order_id="BUY-001"
    )
    sell_order = create_test_order(
        side="sell", price=100.0, trader_id="trader1", order_id="SELL-001"
    )

    engine.submit_order(buy_order, order_books["TEST"])
    engine.submit_order(sell_order, order_books["TEST"])

    # Execute batch
    results = engine.execute_batch(order_books)

    # Self-trading should be allowed in our implementation
    # (Some exchanges prohibit this, but our game allows it)
    assert results["TEST"]["BUY-001"].status == "filled"
    assert results["TEST"]["SELL-001"].status == "filled"


def test_get_mode_returns_correct_value():
    """Test that get_mode returns the correct matching mode."""
    continuous = ContinuousMatchingEngine()
    batch = BatchMatchingEngine()

    assert continuous.get_mode() == "continuous"
    assert batch.get_mode() == "batch"


# ============================================================================
# ORDERRESULT STATUS COVERAGE TESTS
# ============================================================================


def test_all_order_result_statuses_covered():
    """Verify that all OrderResult statuses are tested in the matching engine.

    This test ensures we have comprehensive coverage of all statuses that can
    be returned by the matching engine:
    - 'pending_new': Orders awaiting batch execution (batch mode only)
    - 'new': Orders resting in the order book with no fills
    - 'partially_filled': Orders with some fills but quantity remaining
    - 'filled': Orders completely filled with no remaining quantity

    Note: 'rejected' and 'cancelled' are not implemented in the current
    matching engine as validation happens before reaching the engine.
    """
    # GIVEN - Different matching scenarios for each status

    # TEST 1: 'pending_new' status - batch mode only
    # WHEN - An order is submitted to batch engine
    batch_engine = BatchMatchingEngine()
    order_book = OrderBook("TEST")

    order = create_test_order(side="buy", price=100.0)
    result = batch_engine.submit_order(order, order_book)

    # THEN - Status should be pending_new
    assert result.status == "pending_new"

    # TEST 2: 'new' status - continuous mode, no match
    # WHEN - An order is submitted with no crossing orders
    continuous_engine = ContinuousMatchingEngine()
    order_book = OrderBook("TEST")

    order = create_test_order(side="buy", price=100.0)
    result = continuous_engine.submit_order(order, order_book)

    # THEN - Status should be new (resting in book)
    assert result.status == "new"

    # TEST 3: 'new' status - batch mode after execution, no match
    # WHEN - Batch executes with no crossing orders
    batch_engine = BatchMatchingEngine()
    order_books = {"TEST": OrderBook("TEST")}

    order = create_test_order(side="buy", price=100.0)
    batch_engine.submit_order(order, order_books["TEST"])
    results = batch_engine.execute_batch(order_books)

    # THEN - Status should transition from pending_new to new
    assert results["TEST"][order.order_id].status == "new"

    # TEST 4: 'partially_filled' status
    # WHEN - Order matches but not completely
    continuous_engine = ContinuousMatchingEngine()
    order_book = OrderBook("TEST")

    sell_order = create_test_order(side="sell", price=100.0, quantity=5)
    buy_order = create_test_order(side="buy", price=100.0, quantity=10)

    order_book.add_order(sell_order)
    result = continuous_engine.submit_order(buy_order, order_book)

    # THEN - Status should be partially_filled with remaining quantity
    assert result.status == "partially_filled"
    assert result.remaining_quantity == 5

    # TEST 5: 'filled' status
    # WHEN - Order matches completely
    continuous_engine = ContinuousMatchingEngine()
    order_book = OrderBook("TEST")

    sell_order = create_test_order(side="sell", price=100.0, quantity=10)
    buy_order = create_test_order(side="buy", price=100.0, quantity=10)

    order_book.add_order(sell_order)
    result = continuous_engine.submit_order(buy_order, order_book)

    # THEN - Status should be filled with zero remaining
    assert result.status == "filled"
    assert result.remaining_quantity == 0
