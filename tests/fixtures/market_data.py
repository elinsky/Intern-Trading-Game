"""Market data test fixtures for orders, instruments, and trading scenarios.

This module provides factory functions and test data constants for creating
consistent test objects across the test suite.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from intern_trading_game.domain.exchange.models.instrument import Instrument
from intern_trading_game.domain.exchange.models.order import Order
from intern_trading_game.domain.exchange.models.trade import Trade

# Test data constants
TEST_PRICES = {
    "at_the_money": 100.0,
    "in_the_money": 95.0,
    "out_of_money": 105.0,
    "deep_itm": 80.0,
    "deep_otm": 120.0,
    "near_atm_call": 101.0,
    "near_atm_put": 99.0,
    "min_tick": 0.01,
    "typical_bid": 99.50,
    "typical_ask": 100.50,
}

TEST_QUANTITIES = {
    "small": 1,
    "typical": 10,
    "medium": 25,
    "large": 100,
    "odd_lot": 7,
    "round_lot": 100,
    "max_retail": 50,
    "institutional": 500,
}

TEST_SPREADS = {
    "tight": 0.10,
    "normal": 1.00,
    "wide": 5.00,
    "penny": 0.01,
    "nickel": 0.05,
    "dime": 0.10,
    "quarter": 0.25,
}


def create_test_order(
    side: str = "buy",
    price: Optional[float] = 100.0,
    quantity: int = 10,
    trader_id: str = "test_trader",
    instrument_id: str = "SPX_CALL_4500_20240315",
) -> Order:
    """Create a test order with configurable parameters.

    Parameters
    ----------
    side : str, default="buy"
        Order side, either "buy" or "sell"
    price : float or None, default=100.0
        Limit price for the order. None creates a market order
    quantity : int, default=10
        Number of contracts
    trader_id : str, default="test_trader"
        ID of the trader placing the order
    instrument_id : str, default="SPX_CALL_4500_20240315"
        Instrument identifier

    Returns
    -------
    Order
        Configured test order

    Examples
    --------
    >>> # Simple buy order
    >>> order = create_test_order()
    >>>
    >>> # Sell order with custom price
    >>> order = create_test_order(side="sell", price=101.5)
    >>>
    >>> # Market order
    >>> order = create_test_order(price=None)
    """
    return Order(
        instrument_id=instrument_id,
        side=side,
        quantity=quantity,
        price=price,
        trader_id=trader_id,
    )


def create_spx_option(
    strike: float = 4500.0,
    expiry_days: int = 30,
    option_type: str = "call",
    symbol_suffix: str = "",
) -> Instrument:
    """Create an SPX option instrument for testing.

    Parameters
    ----------
    strike : float, default=4500.0
        Strike price of the option
    expiry_days : int, default=30
        Days until expiration from today
    option_type : str, default="call"
        Type of option, either "call" or "put"
    symbol_suffix : str, default=""
        Optional suffix for the symbol

    Returns
    -------
    Instrument
        SPX option instrument

    Examples
    --------
    >>> # ATM call expiring in 30 days
    >>> spx_call = create_spx_option()
    >>>
    >>> # OTM put expiring in 7 days
    >>> spx_put = create_spx_option(strike=4400, expiry_days=7, option_type="put")
    """
    expiry_date = datetime.now() + timedelta(days=expiry_days)
    expiry_iso = expiry_date.strftime("%Y-%m-%d")  # ISO format for Instrument
    expiry_compact = expiry_date.strftime(
        "%Y%m%d"
    )  # Compact format for symbol
    symbol = f"SPX_{option_type.upper()}_{int(strike)}_{expiry_compact}{symbol_suffix}"

    return Instrument(
        symbol=symbol,
        strike=strike,
        expiry=expiry_iso,
        option_type=option_type,
        underlying="SPX",
    )


def create_spy_option(
    strike: float = 450.0,
    expiry_days: int = 30,
    option_type: str = "call",
    symbol_suffix: str = "",
) -> Instrument:
    """Create a SPY option instrument for testing.

    Parameters
    ----------
    strike : float, default=450.0
        Strike price of the option
    expiry_days : int, default=30
        Days until expiration from today
    option_type : str, default="call"
        Type of option, either "call" or "put"
    symbol_suffix : str, default=""
        Optional suffix for the symbol

    Returns
    -------
    Instrument
        SPY option instrument

    Examples
    --------
    >>> # ATM call expiring in 30 days
    >>> spy_call = create_spy_option()
    >>>
    >>> # ITM put expiring in 14 days
    >>> spy_put = create_spy_option(strike=455, expiry_days=14, option_type="put")
    """
    expiry_date = datetime.now() + timedelta(days=expiry_days)
    expiry_iso = expiry_date.strftime("%Y-%m-%d")  # ISO format for Instrument
    expiry_compact = expiry_date.strftime(
        "%Y%m%d"
    )  # Compact format for symbol
    symbol = f"SPY_{option_type.upper()}_{int(strike)}_{expiry_compact}{symbol_suffix}"

    return Instrument(
        symbol=symbol,
        strike=strike,
        expiry=expiry_iso,
        option_type=option_type,
        underlying="SPY",
    )


def create_test_spread(
    spread_width: float = 1.0,
    mid_price: float = 100.0,
    quantity: int = 10,
    trader_id: str = "test_trader",
    instrument_id: str = "SPX_CALL_4500_20240315",
) -> Dict[str, Order]:
    """Create a bid/ask spread for testing.

    Parameters
    ----------
    spread_width : float, default=1.0
        Width of the spread in price units
    mid_price : float, default=100.0
        Midpoint price of the spread
    quantity : int, default=10
        Quantity for both orders
    trader_id : str, default="test_trader"
        Trader ID for both orders
    instrument_id : str, default="SPX_CALL_4500_20240315"
        Instrument for both orders

    Returns
    -------
    dict
        Dictionary with "bid" and "ask" Order objects

    Examples
    --------
    >>> # Create $1 wide spread around $100
    >>> spread = create_test_spread()
    >>> spread["bid"].price  # 99.5
    >>> spread["ask"].price  # 100.5
    """
    bid_price = mid_price - (spread_width / 2)
    ask_price = mid_price + (spread_width / 2)

    return {
        "bid": create_test_order(
            side="buy",
            price=bid_price,
            quantity=quantity,
            trader_id=trader_id,
            instrument_id=instrument_id,
        ),
        "ask": create_test_order(
            side="sell",
            price=ask_price,
            quantity=quantity,
            trader_id=trader_id,
            instrument_id=instrument_id,
        ),
    }


def create_ladder_orders(
    base_price: float = 100.0,
    levels: int = 5,
    step: float = 0.5,
    side: str = "buy",
    quantity_per_level: int = 10,
    trader_id: str = "test_trader",
    instrument_id: str = "SPX_CALL_4500_20240315",
) -> List[Order]:
    """Create multiple orders at different price levels.

    Parameters
    ----------
    base_price : float, default=100.0
        Starting price for the ladder
    levels : int, default=5
        Number of price levels
    step : float, default=0.5
        Price increment between levels
    side : str, default="buy"
        Side for all orders
    quantity_per_level : int, default=10
        Quantity at each level
    trader_id : str, default="test_trader"
        Trader ID for all orders
    instrument_id : str, default="SPX_CALL_4500_20240315"
        Instrument for all orders

    Returns
    -------
    list[Order]
        List of orders at different price levels

    Examples
    --------
    >>> # Create 5 buy orders from $100 to $102
    >>> orders = create_ladder_orders()
    >>> [o.price for o in orders]  # [100.0, 100.5, 101.0, 101.5, 102.0]
    """
    orders = []
    for i in range(levels):
        if side == "buy":
            # For buys, start at base and go down
            price = base_price - (i * step)
        else:
            # For sells, start at base and go up
            price = base_price + (i * step)

        orders.append(
            create_test_order(
                side=side,
                price=price,
                quantity=quantity_per_level,
                trader_id=trader_id,
                instrument_id=instrument_id,
            )
        )

    return orders


def create_order_book_scenario(
    scenario: str = "balanced",
    instrument_id: str = "SPX_CALL_4500_20240315",
) -> Dict[str, List[Order]]:
    """Create predefined order book scenarios.

    Parameters
    ----------
    scenario : str, default="balanced"
        Scenario name: "balanced", "bid_heavy", "ask_heavy", "wide_spread", "thin"
    instrument_id : str, default="SPX_CALL_4500_20240315"
        Instrument for all orders

    Returns
    -------
    dict
        Dictionary with "bids" and "asks" lists of Order objects

    Examples
    --------
    >>> # Create balanced order book
    >>> book = create_order_book_scenario("balanced")
    >>> len(book["bids"])  # 3
    >>> len(book["asks"])  # 3
    """
    scenarios = {
        "balanced": {
            "bids": [(99.5, 10), (99.0, 20), (98.5, 30)],
            "asks": [(100.5, 10), (101.0, 20), (101.5, 30)],
        },
        "bid_heavy": {
            "bids": [(99.9, 50), (99.8, 100), (99.7, 150)],
            "asks": [(100.1, 5), (100.2, 10)],
        },
        "ask_heavy": {
            "bids": [(99.8, 5), (99.7, 10)],
            "asks": [(100.0, 50), (100.1, 100), (100.2, 150)],
        },
        "wide_spread": {
            "bids": [(95.0, 10)],
            "asks": [(105.0, 10)],
        },
        "thin": {
            "bids": [(99.95, 1)],
            "asks": [(100.05, 1)],
        },
    }

    if scenario not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario}")

    scenario_data = scenarios[scenario]
    result = {"bids": [], "asks": []}

    # Create bid orders
    for i, (price, qty) in enumerate(scenario_data["bids"]):
        result["bids"].append(
            create_test_order(
                side="buy",
                price=price,
                quantity=qty,
                trader_id=f"bid_trader_{i}",
                instrument_id=instrument_id,
            )
        )

    # Create ask orders
    for i, (price, qty) in enumerate(scenario_data["asks"]):
        result["asks"].append(
            create_test_order(
                side="sell",
                price=price,
                quantity=qty,
                trader_id=f"ask_trader_{i}",
                instrument_id=instrument_id,
            )
        )

    return result


def create_matched_orders(
    price: float = 100.0,
    quantity: int = 10,
    buyer_id: str = "buyer",
    seller_id: str = "seller",
    instrument_id: str = "SPX_CALL_4500_20240315",
) -> Tuple[Order, Order]:
    """Create a pair of orders that will match when processed.

    Parameters
    ----------
    price : float, default=100.0
        Match price
    quantity : int, default=10
        Match quantity
    buyer_id : str, default="buyer"
        Buyer's trader ID
    seller_id : str, default="seller"
        Seller's trader ID
    instrument_id : str, default="SPX_CALL_4500_20240315"
        Instrument ID

    Returns
    -------
    tuple[Order, Order]
        Buy order and sell order that will match

    Examples
    --------
    >>> buy, sell = create_matched_orders(price=99.5)
    >>> # These orders will match at 99.5
    """
    buy_order = create_test_order(
        side="buy",
        price=price,
        quantity=quantity,
        trader_id=buyer_id,
        instrument_id=instrument_id,
    )

    sell_order = create_test_order(
        side="sell",
        price=price,
        quantity=quantity,
        trader_id=seller_id,
        instrument_id=instrument_id,
    )

    return buy_order, sell_order


def create_test_trade(
    price: float = 100.0,
    quantity: int = 10,
    buyer_id: str = "buyer",
    seller_id: str = "seller",
    aggressor_side: str = "buy",
    instrument_id: str = "SPX_CALL_4500_20240315",
    buyer_order_id: Optional[str] = None,
    seller_order_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    trade_id: Optional[str] = None,
) -> Trade:
    """Create a test trade object.

    Parameters
    ----------
    price : float, default=100.0
        Trade price
    quantity : int, default=10
        Trade quantity
    buyer_id : str, default="buyer"
        Buyer's trader ID
    seller_id : str, default="seller"
        Seller's trader ID
    aggressor_side : str, default="buy"
        Side that aggressed (took liquidity)
    instrument_id : str, default="SPX_CALL_4500_20240315"
        Instrument ID
    buyer_order_id : str, optional
        Buyer's order ID, auto-generated if not provided
    seller_order_id : str, optional
        Seller's order ID, auto-generated if not provided
    timestamp : datetime, optional
        Trade timestamp, defaults to current time if not provided
    trade_id : str, optional
        Trade ID, auto-generated if not provided

    Returns
    -------
    Trade
        Test trade object

    Examples
    --------
    >>> trade = create_test_trade(price=99.75, quantity=5)
    >>> trade.value  # 498.75
    """
    # Auto-generate order IDs if not provided
    if buyer_order_id is None:
        buyer_order_id = f"BUY_{buyer_id}_{id(buyer_id)}"
    if seller_order_id is None:
        seller_order_id = f"SELL_{seller_id}_{id(seller_id)}"

    return Trade(
        instrument_id=instrument_id,
        price=price,
        quantity=quantity,
        buyer_id=buyer_id,
        seller_id=seller_id,
        aggressor_side=aggressor_side,
        buyer_order_id=buyer_order_id,
        seller_order_id=seller_order_id,
        timestamp=timestamp,
        trade_id=trade_id,
    )
