"""
Tests for the exchange system.
"""

import pytest

from intern_trading_game.domain.exchange.core.instrument import Instrument
from intern_trading_game.domain.exchange.order import Order
from intern_trading_game.domain.exchange.venue import ExchangeVenue


@pytest.fixture
def exchange():
    """Create an exchange with a test instrument."""
    exchange = ExchangeVenue()

    # Create a test instrument
    test_instrument = Instrument(
        symbol="TEST_INSTRUMENT",
        strike=100.0,
        expiry="2024-12-31",
        option_type="call",
        underlying="TEST",
    )

    exchange.list_instrument(test_instrument)
    return exchange


def test_instrument_creation():
    """Test that instruments can be created correctly."""
    # Given - Parameters for creating different types of instruments
    # We need to test both stock and option instrument creation with valid parameters,
    # as well as validation for invalid parameters.

    # Stock parameters
    stock_symbol = "AAPL"
    stock_underlying = "AAPL"

    # Option parameters
    option_symbol = "AAPL_150C_DEC"
    option_strike = 150.0
    option_expiry = "2024-12-20"
    option_type = "call"
    option_underlying = "AAPL"

    # Invalid parameters
    invalid_option_type = "invalid_type"  # Should be 'call' or 'put'
    invalid_expiry_date = "invalid-date"  # Should be in ISO format

    # When - Creating a stock instrument
    # We create a basic stock instrument with just a symbol and underlying
    stock = Instrument(symbol=stock_symbol, underlying=stock_underlying)

    # Then - Stock instrument is created with correct attributes
    # The stock should have the specified symbol and underlying,
    # and option-specific attributes should be None
    assert stock.symbol == "AAPL"
    assert stock.underlying == "AAPL"
    assert stock.option_type is None
    assert stock.strike is None
    assert stock.expiry is None

    # When - Creating an option instrument
    # We create an option with all required option parameters
    option = Instrument(
        symbol=option_symbol,
        strike=option_strike,
        expiry=option_expiry,
        option_type=option_type,
        underlying=option_underlying,
    )

    # Then - Option instrument is created with correct attributes
    # The option should have all the specified attributes set correctly
    assert option.symbol == "AAPL_150C_DEC"
    assert option.strike == 150.0
    assert option.expiry == "2024-12-20"
    assert option.option_type == "call"
    assert option.underlying == "AAPL"

    # When - Creating an instrument with invalid option type
    # Then - Validation error is raised
    # The Instrument class should validate the option_type and raise a ValueError
    with pytest.raises(ValueError):
        Instrument(
            symbol="INVALID",
            option_type=invalid_option_type,
        )

    # When - Creating an instrument with invalid expiry date format
    # Then - Validation error is raised
    # The Instrument class should validate the expiry date format and raise a ValueError
    with pytest.raises(ValueError):
        Instrument(
            symbol="INVALID",
            expiry=invalid_expiry_date,
        )


def test_order_creation():
    """Test that orders can be created correctly."""
    # Given - Parameters for creating different types of orders
    # We need to test both limit and market orders with valid parameters,
    # as well as validation for invalid parameters.

    # Limit buy order parameters
    buy_instrument_id = "TEST"
    buy_side = "buy"
    buy_quantity = 10
    buy_price = 5.25
    buy_trader_id = "trader1"

    # Market sell order parameters
    sell_instrument_id = "TEST"
    sell_side = "sell"
    sell_quantity = 5
    sell_price = None  # Market order has no price
    sell_trader_id = "trader2"

    # Invalid parameters
    invalid_quantity = -5  # Quantity must be positive
    invalid_price = -10.0  # Price must be positive for limit orders

    # When - Creating a limit buy order
    # We create a limit buy order with a specific price
    buy_order = Order(
        instrument_id=buy_instrument_id,
        side=buy_side,
        quantity=buy_quantity,
        price=buy_price,
        trader_id=buy_trader_id,
    )

    # Then - Limit buy order is created with correct attributes
    # The order should have all the specified attributes and derived properties
    assert buy_order.instrument_id == "TEST"
    assert buy_order.is_buy
    assert not buy_order.is_sell
    assert buy_order.quantity == 10
    assert buy_order.price == 5.25
    assert buy_order.trader_id == "trader1"
    assert buy_order.is_limit_order
    assert not buy_order.is_market_order
    assert buy_order.remaining_quantity == 10

    # When - Creating a market sell order
    # We create a market sell order with no price specified
    sell_order = Order(
        instrument_id=sell_instrument_id,
        side=sell_side,
        quantity=sell_quantity,
        price=sell_price,  # Market order
        trader_id=sell_trader_id,
    )

    # Then - Market sell order is created with correct attributes
    # The order should be recognized as a market order and a sell order
    assert sell_order.instrument_id == "TEST"
    assert sell_order.is_sell
    assert not sell_order.is_buy
    assert sell_order.quantity == 5
    assert sell_order.price is None
    assert sell_order.trader_id == "trader2"
    assert sell_order.is_market_order
    assert not sell_order.is_limit_order
    assert sell_order.remaining_quantity == 5

    # When - Creating an order with invalid quantity
    # Then - Validation error is raised
    # The Order class should validate the quantity and raise a ValueError
    with pytest.raises(ValueError):
        Order(
            instrument_id="TEST",
            side="buy",
            quantity=invalid_quantity,
            price=10.0,
            trader_id="trader1",
        )

    # When - Creating a limit order with invalid price
    # Then - Validation error is raised
    # The Order class should validate the price and raise a ValueError
    with pytest.raises(ValueError):
        Order(
            instrument_id="TEST",
            side="buy",
            quantity=5,
            price=invalid_price,
            trader_id="trader1",
        )


def test_order_matching(exchange):
    """Test that orders are matched correctly."""
    # Given - Market setup with a resting buy order
    # We have an exchange venue with a test instrument listed for trading.
    # A trader (trader1) places a buy order for 10 contracts at $5.25,
    # which should be accepted and added to the order book.
    buy_order = Order(
        instrument_id="TEST_INSTRUMENT",
        side="buy",
        quantity=10,
        price=5.25,
        trader_id="trader1",
    )

    result = exchange.submit_order(buy_order)
    assert result.status == "new"
    assert result.remaining_quantity == 10
    assert len(result.fills) == 0

    # When - A matching sell order arrives in the market
    # A second trader (trader2) submits a sell order for 5 contracts at the same price ($5.25),
    # which should trigger the matching engine to execute a trade between the two orders.
    sell_order = Order(
        instrument_id="TEST_INSTRUMENT",
        side="sell",
        quantity=5,
        price=5.25,
        trader_id="trader2",
    )

    result = exchange.submit_order(sell_order)

    # Then - Order matching creates a trade with correct details
    # The sell order should be completely filled since its quantity (5) is less than
    # the resting buy order's quantity (10).
    # A trade should be created at the price of $5.25 for 5 contracts.
    # The buy order should remain in the book with 5 contracts remaining.
    assert result.status == "filled"
    assert result.remaining_quantity == 0
    assert len(result.fills) == 1

    # Verify trade details
    trade = result.fills[0]
    assert trade.buyer_id == "trader1"
    assert trade.seller_id == "trader2"
    assert trade.price == 5.25
    assert trade.quantity == 5
    assert trade.value == 5.25 * 5

    # Verify order book state after matching
    book = exchange.get_order_book("TEST_INSTRUMENT")
    assert book.best_bid() == (5.25, 5)  # 5 remaining from the buy order
    assert book.best_ask() is None  # Sell order was fully filled


def test_order_book_depth(exchange):
    """Test the order book depth functionality."""
    # Given - Market setup with multiple orders at different price levels
    # We have an exchange venue with a test instrument listed for trading.
    # Multiple orders are submitted to create a realistic order book with
    # different price levels on both the bid and ask sides.

    # Add two buy orders at different prices
    exchange.submit_order(
        Order(
            instrument_id="TEST_INSTRUMENT",
            side="buy",
            quantity=10,
            price=5.00,
            trader_id="trader1",
        )
    )

    exchange.submit_order(
        Order(
            instrument_id="TEST_INSTRUMENT",
            side="buy",
            quantity=5,
            price=5.25,  # Higher price than the first buy order
            trader_id="trader1",
        )
    )

    # Add two sell orders at different prices
    exchange.submit_order(
        Order(
            instrument_id="TEST_INSTRUMENT",
            side="sell",
            quantity=8,
            price=5.50,
            trader_id="trader2",
        )
    )

    exchange.submit_order(
        Order(
            instrument_id="TEST_INSTRUMENT",
            side="sell",
            quantity=12,
            price=5.75,  # Higher price than the first sell order
            trader_id="trader2",
        )
    )

    # When - We request a depth snapshot of the order book
    # The depth snapshot should provide a view of the current state of the
    # order book, showing the price levels and quantities on both sides.
    book = exchange.get_order_book("TEST_INSTRUMENT")
    depth = book.depth_snapshot()

    # Then - The depth snapshot correctly represents the order book state
    # The bids should be sorted in descending order by price (highest first)
    # The asks should be sorted in ascending order by price (lowest first)
    # Each side should contain the correct prices and quantities.

    # Verify bid side ordering and prices
    assert depth["bids"][0][0] == 5.25  # Highest bid first
    assert depth["bids"][1][0] == 5.00

    # Verify ask side ordering and prices
    assert depth["asks"][0][0] == 5.50  # Lowest ask first
    assert depth["asks"][1][0] == 5.75


def test_market_orders(exchange):
    """Test market orders."""
    # Given - Market setup with a resting sell order
    # We have an exchange venue with a test instrument listed for trading.
    # A trader (trader1) places a limit sell order for 10 contracts at $5.25,
    # which establishes the best ask price in the order book.
    exchange.submit_order(
        Order(
            instrument_id="TEST_INSTRUMENT",
            side="sell",
            quantity=10,
            price=5.25,
            trader_id="trader1",
        )
    )

    # When - A market buy order arrives
    # A second trader (trader2) submits a market buy order for 5 contracts,
    # which should execute immediately at the best available ask price ($5.25).
    result = exchange.submit_order(
        Order(
            instrument_id="TEST_INSTRUMENT",
            side="buy",
            quantity=5,
            price=None,  # Market order
            trader_id="trader2",
        )
    )

    # Then - Market order executes at the best available price
    # The market buy order should be completely filled at the price of the resting sell order.
    # A trade should be created at $5.25 for 5 contracts.
    # The sell order should remain in the book with 5 contracts remaining.
    assert result.status == "filled"
    assert len(result.fills) == 1
    assert result.fills[0].price == 5.25
    assert result.fills[0].quantity == 5

    # Verify order book state after matching
    book = exchange.get_order_book("TEST_INSTRUMENT")
    assert book.best_ask() == (5.25, 5)  # 5 remaining from the sell order


def test_cancel_order(exchange):
    """Test cancelling orders."""
    # Given - Market setup with a resting buy order
    # We have an exchange venue with a test instrument listed for trading.
    # A trader (trader1) places a buy order for 10 contracts at $5.25,
    # which is added to the order book.
    order = Order(
        instrument_id="TEST_INSTRUMENT",
        side="buy",
        quantity=10,
        price=5.25,
        trader_id="trader1",
    )

    exchange.submit_order(order)

    # When - The trader cancels their order
    # The trader who placed the order requests to cancel it by providing
    # the order ID and their trader ID for verification.
    result = exchange.cancel_order(order.order_id, "trader1")

    # Then - The order is successfully cancelled
    # The cancel operation should return True, indicating success.
    # The order should be removed from the order book.
    assert result is True

    # Verify order book state after cancellation
    book = exchange.get_order_book("TEST_INSTRUMENT")
    assert book.best_bid() is None  # Order should be gone

    # Given - Attempt to cancel a non-existent order
    # When - A trader attempts to cancel an order that doesn't exist
    result = exchange.cancel_order("non_existent_id", "trader1")

    # Then - The cancellation fails
    # The cancel operation should return False, indicating failure.
    assert result is False

    # Given - Market setup with a resting buy order
    # A trader (trader1) places another buy order.
    exchange.submit_order(order)

    # When - A different trader attempts to cancel the order
    # Then - The cancellation is rejected with an error
    # The exchange should verify trader ownership and raise a ValueError.
    with pytest.raises(ValueError):
        exchange.cancel_order(order.order_id, "wrong_trader")
