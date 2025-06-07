# How to Submit Orders to the Exchange

This guide explains how to create and submit orders to the Intern Trading Game exchange.

## Order Types

The exchange supports two types of orders:

- **Limit Orders**: Specify a price at which you're willing to buy or sell
- **Market Orders**: Execute immediately at the best available price

## Creating an Order

To create an order, you'll need to use the `Order` class from the `intern_trading_game.exchange.order` module:

```python
from intern_trading_game.exchange.order import Order

# Create a limit buy order
limit_buy = Order(
    instrument_id="AAPL_150C_DEC",  # The instrument to trade
    side="buy",                      # "buy" or "sell"
    quantity=10,                     # How many contracts
    price=5.25,                      # Limit price (omit for market orders)
    trader_id="your_trader_id"       # Your unique trader ID
)

# Create a market sell order
market_sell = Order(
    instrument_id="AAPL_150C_DEC",
    side="sell",
    quantity=5,
    price=None,                      # None indicates a market order
    trader_id="your_trader_id"
)
```

## Submitting Orders to the Exchange

Once you've created an order, you can submit it to the exchange:

```python
from intern_trading_game.exchange.venue import ExchangeVenue

# Get a reference to the exchange
exchange = ExchangeVenue()

# Submit the order
result = exchange.submit_order(limit_buy)

# Check the result
if result.status == "filled":
    print(f"Order filled! Generated {len(result.fills)} trades")
    for trade in result.fills:
        print(f"Trade: {trade.quantity} @ {trade.price}")
elif result.status == "accepted":
    print(f"Order accepted with ID: {result.order_id}")
    print(f"Remaining quantity: {result.remaining_quantity}")
```

## Cancelling Orders

### Via Direct Exchange API

To cancel an order directly through the exchange:

```python
# Cancel an order (requires the order ID and your trader ID)
success = exchange.cancel_order(order_id=limit_buy.order_id, trader_id="your_trader_id")

if success:
    print("Order cancelled successfully")
else:
    print("Failed to cancel order (may not exist or already filled)")
```

### Via REST API

To cancel an order through the REST API:

```python
import requests

# Cancel an order using DELETE request
response = requests.delete(
    f"http://localhost:8000/orders/{order_id}",
    headers={"X-API-Key": "your_api_key"}
)

if response.json()["status"] == "cancelled":
    print("Order cancelled successfully")
else:
    print(f"Cancel failed: {response.json()['error_message']}")
```

## Checking the Order Book

You can examine the current state of the order book for an instrument:

```python
# Get the order book for an instrument
order_book = exchange.get_order_book("AAPL_150C_DEC")

# Check the best bid and ask
best_bid = order_book.best_bid()  # Returns (price, quantity) or None
best_ask = order_book.best_ask()  # Returns (price, quantity) or None

print(f"Best bid: {best_bid}")
print(f"Best ask: {best_ask}")

# Get a full depth snapshot
depth = order_book.depth_snapshot(levels=5)  # Get 5 levels of depth

print("Bids:")
for price, quantity in depth["bids"]:
    print(f"  {price}: {quantity}")

print("Asks:")
for price, quantity in depth["asks"]:
    print(f"  {price}: {quantity}")
```

## Best Practices

1. **Error Handling**: Always wrap order submission in try/except blocks to handle potential errors
2. **Order Tracking**: Keep track of your outstanding orders to manage your positions
3. **Rate Limiting**: Don't submit too many orders too quickly
4. **Validation**: Verify that your orders make sense before submitting them

## Example: Simple Order Submission Loop

```python
def trading_loop(exchange, instrument_id, trader_id):
    """A simple trading loop that submits and tracks orders."""
    active_orders = {}  # Track active orders by ID

    try:
        # Submit a buy order
        buy_order = Order(
            instrument_id=instrument_id,
            side="buy",
            quantity=10,
            price=5.25,
            trader_id=trader_id
        )

        result = exchange.submit_order(buy_order)
        if result.status == "accepted":
            active_orders[result.order_id] = buy_order
            print(f"Order {result.order_id} accepted")

        # Wait for some time
        import time
        time.sleep(5)

        # Cancel any remaining orders
        for order_id, order in list(active_orders.items()):
            if exchange.cancel_order(order_id, trader_id):
                del active_orders[order_id]
                print(f"Order {order_id} cancelled")

    except Exception as e:
        print(f"Error in trading loop: {e}")
        # Cancel all orders on error
        for order_id in active_orders:
            exchange.cancel_order(order_id, trader_id)
