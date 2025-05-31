"""
Tests for the exchange system.
"""

import pytest

from intern_trading_game.exchange.order import Order
from intern_trading_game.exchange.venue import ExchangeVenue
from intern_trading_game.instruments.instrument import Instrument


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
    # Create a stock
    stock = Instrument(symbol="AAPL", underlying="AAPL")
    assert stock.symbol == "AAPL"
    assert stock.underlying == "AAPL"
    assert stock.option_type is None

    # Create an option
    option = Instrument(
        symbol="AAPL_150C_DEC",
        strike=150.0,
        expiry="2024-12-20",
        option_type="call",
        underlying="AAPL",
    )
    assert option.symbol == "AAPL_150C_DEC"
    assert option.strike == 150.0
    assert option.expiry == "2024-12-20"
    assert option.option_type == "call"
    assert option.underlying == "AAPL"

    # Test validation
    with pytest.raises(ValueError):
        Instrument(
            symbol="INVALID",
            option_type="invalid_type",  # Should be 'call' or 'put'
        )

    with pytest.raises(ValueError):
        Instrument(
            symbol="INVALID", expiry="invalid-date"
        )  # Should be in ISO format


def test_order_creation():
    """Test that orders can be created correctly."""
    # Create a limit buy order
    buy_order = Order(
        instrument_id="TEST",
        side="buy",
        quantity=10,
        price=5.25,
        trader_id="trader1",
    )
    assert buy_order.instrument_id == "TEST"
    assert buy_order.is_buy
    assert not buy_order.is_sell
    assert buy_order.quantity == 10
    assert buy_order.price == 5.25
    assert buy_order.trader_id == "trader1"
    assert buy_order.is_limit_order
    assert not buy_order.is_market_order
    assert buy_order.remaining_quantity == 10

    # Create a market sell order
    sell_order = Order(
        instrument_id="TEST",
        side="sell",
        quantity=5,
        price=None,  # Market order
        trader_id="trader2",
    )
    assert sell_order.instrument_id == "TEST"
    assert sell_order.is_sell
    assert not sell_order.is_buy
    assert sell_order.quantity == 5
    assert sell_order.price is None
    assert sell_order.trader_id == "trader2"
    assert sell_order.is_market_order
    assert not sell_order.is_limit_order
    assert sell_order.remaining_quantity == 5

    # Test validation
    with pytest.raises(ValueError):
        Order(
            instrument_id="TEST",
            side="buy",
            quantity=-5,  # Invalid quantity
            price=10.0,
            trader_id="trader1",
        )

    with pytest.raises(ValueError):
        Order(
            instrument_id="TEST",
            side="buy",
            quantity=5,
            price=-10.0,  # Invalid price
            trader_id="trader1",
        )


def test_order_matching(exchange):
    """Test that orders are matched correctly."""
    # Submit a buy order
    buy_order = Order(
        instrument_id="TEST_INSTRUMENT",
        side="buy",
        quantity=10,
        price=5.25,
        trader_id="trader1",
    )

    result = exchange.submit_order(buy_order)
    assert result.status == "accepted"
    assert result.remaining_quantity == 10
    assert len(result.fills) == 0

    # Submit a matching sell order
    sell_order = Order(
        instrument_id="TEST_INSTRUMENT",
        side="sell",
        quantity=5,
        price=5.25,
        trader_id="trader2",
    )

    result = exchange.submit_order(sell_order)
    assert result.status == "filled"
    assert result.remaining_quantity == 0
    assert len(result.fills) == 1

    # Check the trade details
    trade = result.fills[0]
    assert trade.buyer_id == "trader1"
    assert trade.seller_id == "trader2"
    assert trade.price == 5.25
    assert trade.quantity == 5
    assert trade.value == 5.25 * 5

    # Check the order book
    book = exchange.get_order_book("TEST_INSTRUMENT")
    assert book.best_bid() == (5.25, 5)  # 5 remaining from the buy order
    assert book.best_ask() is None  # Sell order was fully filled


def test_order_book_depth(exchange):
    """Test the order book depth functionality."""
    # Submit orders at different price levels
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
            price=5.25,
            trader_id="trader1",
        )
    )

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
            price=5.75,
            trader_id="trader2",
        )
    )

    # Check the order book depth
    book = exchange.get_order_book("TEST_INSTRUMENT")
    depth = book.depth_snapshot()

    # Bids should be in descending order (highest first)
    assert depth["bids"][0][0] == 5.25
    assert depth["bids"][1][0] == 5.00

    # Asks should be in ascending order (lowest first)
    assert depth["asks"][0][0] == 5.50
    assert depth["asks"][1][0] == 5.75


def test_market_orders(exchange):
    """Test market orders."""
    # Submit a limit sell order first
    exchange.submit_order(
        Order(
            instrument_id="TEST_INSTRUMENT",
            side="sell",
            quantity=10,
            price=5.25,
            trader_id="trader1",
        )
    )

    # Submit a market buy order
    result = exchange.submit_order(
        Order(
            instrument_id="TEST_INSTRUMENT",
            side="buy",
            quantity=5,
            price=None,  # Market order
            trader_id="trader2",
        )
    )

    # Market order should be filled at the best available price
    assert result.status == "filled"
    assert len(result.fills) == 1
    assert result.fills[0].price == 5.25
    assert result.fills[0].quantity == 5

    # Check the order book
    book = exchange.get_order_book("TEST_INSTRUMENT")
    assert book.best_ask() == (5.25, 5)  # 5 remaining from the sell order


def test_cancel_order(exchange):
    """Test cancelling orders."""
    # Submit an order
    order = Order(
        instrument_id="TEST_INSTRUMENT",
        side="buy",
        quantity=10,
        price=5.25,
        trader_id="trader1",
    )

    exchange.submit_order(order)

    # Cancel the order
    result = exchange.cancel_order(order.order_id, "trader1")
    assert result is True

    # Check the order book
    book = exchange.get_order_book("TEST_INSTRUMENT")
    assert book.best_bid() is None  # Order should be gone

    # Try to cancel a non-existent order
    result = exchange.cancel_order("non_existent_id", "trader1")
    assert result is False

    # Try to cancel an order with the wrong trader ID
    exchange.submit_order(order)
    with pytest.raises(ValueError):
        exchange.cancel_order(order.order_id, "wrong_trader")
