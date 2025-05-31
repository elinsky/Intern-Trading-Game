"""
Example usage of the Intern Trading Game exchange system.

This module demonstrates how to use the exchange system with a simple example.
"""

from intern_trading_game.exchange.order import Order
from intern_trading_game.exchange.venue import ExchangeVenue
from intern_trading_game.instruments.instrument import Instrument


def run_example():
    """Run a simple example of the exchange system."""
    # Create an exchange venue
    exchange = ExchangeVenue()

    # Create and list some instruments
    tsla_call = Instrument(
        symbol="TSLA_100C_JUN",
        strike=100.0,
        expiry="2024-06-21",
        option_type="call",
        underlying="TSLA",
    )

    aapl_stock = Instrument(symbol="AAPL", underlying="AAPL")

    exchange.list_instrument(tsla_call)
    exchange.list_instrument(aapl_stock)

    instruments = [i.symbol for i in exchange.get_all_instruments()]
    print(f"Listed instruments: {instruments}")

    # Submit some orders
    print("\n--- Submitting orders ---")

    # Buy order for TSLA calls
    buy_order = Order(
        instrument_id="TSLA_100C_JUN",
        side="buy",
        quantity=10,
        price=5.25,
        trader_id="alpha_fund",
    )

    result = exchange.submit_order(buy_order)
    order_id = buy_order.order_id
    print(f"Submitted buy order: {order_id}," f" status: {result.status}")

    # No matching sell orders yet, so the order should be accepted
    # but not filled
    print(f"Order remaining quantity: {result.remaining_quantity}")

    # Check the order book
    order_book = exchange.get_order_book("TSLA_100C_JUN")
    print(f"Best bid: {order_book.best_bid()}")
    print(f"Best ask: {order_book.best_ask()}")

    # Submit a matching sell order
    sell_order = Order(
        instrument_id="TSLA_100C_JUN",
        side="sell",
        quantity=5,
        price=5.25,  # Same price as the buy order
        trader_id="beta_fund",
    )

    result = exchange.submit_order(sell_order)
    print(
        f"\nSubmitted sell order: {sell_order.order_id}, "
        f"status: {result.status}"
    )

    # This should match with the existing buy order
    print(f"Order remaining quantity: {result.remaining_quantity}")
    print(f"Generated {len(result.fills)} trades")

    # Print trade details
    for trade in result.fills:
        print(f"\nTrade: {trade.trade_id}")
        print(f"  Buyer: {trade.buyer_id}, Seller: {trade.seller_id}")
        print(f"  Price: {trade.price}, Quantity: {trade.quantity}")
        print(f"  Value: {trade.value}")

    # Check the order book again
    print("\n--- Order Book After Matching ---")
    print(
        f"Best bid: {order_book.best_bid()}"
    )  # Should still have 5 remaining
    print(f"Best ask: {order_book.best_ask()}")  # Should be None

    # Submit another sell order at a higher price
    sell_order2 = Order(
        instrument_id="TSLA_100C_JUN",
        side="sell",
        quantity=8,
        price=5.50,  # Higher price
        trader_id="gamma_fund",
    )

    result = exchange.submit_order(sell_order2)
    print(
        f"\nSubmitted second sell order: {sell_order2.order_id}, "
        f"status: {result.status}"
    )

    # Check the order book depth
    print("\n--- Order Book Depth ---")
    depth = order_book.depth_snapshot()
    print("Bids:")
    for price, quantity in depth["bids"]:
        print(f"  {price}: {quantity}")
    print("Asks:")
    for price, quantity in depth["asks"]:
        print(f"  {price}: {quantity}")

    # Get trade history
    print("\n--- Trade History ---")
    trades = exchange.get_trade_history("TSLA_100C_JUN")
    for trade in trades:
        print(f"Trade at {trade.timestamp}: {trade.quantity} @ {trade.price}")

    # Cancel the remaining buy order
    cancelled = exchange.cancel_order(buy_order.order_id, "alpha_fund")
    print(f"\nCancelled buy order: {cancelled}")

    # Check the order book again
    print("\n--- Order Book After Cancellation ---")
    print(f"Best bid: {order_book.best_bid()}")  # Should be None
    print(
        f"Best ask: {order_book.best_ask()}"
    )  # Should still have the sell order


if __name__ == "__main__":
    run_example()
