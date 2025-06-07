# API Reference

## Exchange Components

<div class="doc-api-card" markdown="1">

### ExchangeVenue

Main exchange venue that handles order submission and matching.

**Parameters:**

- **matching_engine** : `MatchingEngine`, optional
    - The matching engine to use for order processing. Defaults to `ContinuousMatchingEngine` if not provided.

**Attributes:**

- **order_books** : `Dict[str, OrderBook]`
    - Map of instrument IDs to their order books
- **instruments** : `Dict[str, Instrument]`
    - Map of instrument IDs to their instrument objects
- **matching_engine** : `MatchingEngine`
    - The engine responsible for order matching logic

**Examples:**

```python
# Create exchange with continuous matching (default)
exchange = ExchangeVenue()

# Create exchange with batch matching
from intern_trading_game.exchange import BatchMatchingEngine
exchange = ExchangeVenue(matching_engine=BatchMatchingEngine())

# List an instrument
instrument = Instrument(symbol="SPX_CALL_5000", underlying="SPX")
exchange.list_instrument(instrument)

# Submit an order
order = Order(
    instrument_id="SPX_CALL_5000",
    side="buy",
    quantity=10,
    price=25.50,
    trader_id="MM1"
)
result = exchange.submit_order(order)

# Cancel an order
cancelled = exchange.cancel_order(order.order_id, "MM1")
```

**See Also:**

- `BatchMatchingEngine` : For batch order matching with randomization
- `ContinuousMatchingEngine` : For immediate order matching
- `Order` : Order data structure
- `OrderBook` : Order book implementation

</div>

<div class="doc-api-card" markdown="1">

### BatchMatchingEngine

Implements batch order matching with fair randomization at same price levels.

**Description:**

This engine collects orders during a submission window and processes them all simultaneously at a designated time. Orders at the same price level are randomized to ensure fairness, preventing timing advantages.

**Mathematical Guarantees:**

For orders at the same price level:

- P(Order A fills before Order B) = 1/2
- P(Order i in position j) = 1/n for n orders

**Methods:**

- **submit_order(order, order_book)** : Collect order for batch processing
- **execute_batch(order_books)** : Process all pending orders with randomization
- **get_pending_count(instrument_id)** : Get count of pending orders

**Examples:**

```python
# Create batch matching engine
engine = BatchMatchingEngine()

# Orders are collected, not matched immediately
order1 = Order(instrument_id="SPX_CALL", side="buy",
               quantity=10, price=25.50, trader_id="MM1")
result1 = engine.submit_order(order1, order_book)
assert result1.status == "pending_new"

# Execute batch to process all orders
results = engine.execute_batch({"SPX_CALL": order_book})
```

**Notes:**

Batch matching is ideal for game environments where fairness is paramount. It eliminates speed advantages and ensures all participants have equal opportunity to trade at each price level.

</div>

## Core Models

<div class="doc-api-card" markdown="1">

### Order

Represents a trading order with all necessary attributes.

**Parameters:**

- **instrument_id** : `str`
    - The ID of the instrument being traded
- **side** : `str`
    - Either "buy" or "sell"
- **quantity** : `int`
    - Number of contracts to trade
- **price** : `float`, optional
    - Limit price (None for market orders)
- **trader_id** : `str`
    - ID of the trader submitting the order
- **order_id** : `str`, optional
    - Unique order identifier (auto-generated if not provided)
- **client_order_id** : `str`, optional
    - Client's reference ID for order tracking

**Attributes:**

- **remaining_quantity** : `int`
    - Unfilled portion of the order
- **is_filled** : `bool`
    - Whether the order is completely filled
- **timestamp** : `datetime`
    - When the order was created

**Examples:**

```python
# Create a limit order
order = Order(
    instrument_id="SPX_PUT_4900",
    side="sell",
    quantity=5,
    price=15.25,
    trader_id="HF1"
)

# Create a market order
market_order = Order(
    instrument_id="SPY_CALL_490",
    side="buy",
    quantity=20,
    price=None,  # Market order
    trader_id="RT1"
)
```

</div>

<div class="doc-api-card" markdown="1">

### Trade

Represents an executed trade between two orders.

**Attributes:**

- **instrument_id** : `str`
    - The instrument that was traded
- **buyer_order_id** : `str`
    - ID of the buy order
- **seller_order_id** : `str`
    - ID of the sell order
- **buyer_id** : `str`
    - ID of the buying trader
- **seller_id** : `str`
    - ID of the selling trader
- **price** : `float`
    - Execution price
- **quantity** : `int`
    - Number of contracts traded
- **timestamp** : `datetime`
    - When the trade occurred
- **aggressor_side** : `str`
    - Which side initiated the trade ('buy' or 'sell')

**Examples:**

```python
# Trades are typically created by the matching engine
# This example shows the structure:
trade = Trade(
    instrument_id="SPX_CALL_5000",
    buyer_order_id="BUY-001",
    seller_order_id="SELL-001",
    buyer_id="MM1",
    seller_id="HF1",
    price=25.50,
    quantity=10
)
```

</div>

## Game Components

<div class="doc-api-card" markdown="1">

### GameLoop

Main game controller that orchestrates the 5-minute tick cycles.

**Parameters:**

- **config** : `GameConfig`
    - Configuration for the game session
- **exchange** : `ExchangeVenue`
    - The exchange for order matching
- **price_model** : `PriceModel`, optional
    - Model for generating underlying prices

**Methods:**

- **run_tick()** : Execute one complete 5-minute tick cycle
- **start_game()** : Begin the game session
- **stop_game()** : End the game session gracefully

**Tick Phases:**

1. **T+0:00** : New prices published
2. **T+0:30 to T+3:00** : Order submission window
3. **T+3:30** : Batch matching execution
4. **T+4:00** : Position updates and P&L calculation
5. **T+5:00** : Tick complete, prepare for next

**Examples:**

```python
# Create and configure game loop
config = GameConfig(
    duration_hours=2,
    tick_interval_minutes=5,
    matching_mode="batch"
)

game = GameLoop(
    config=config,
    exchange=ExchangeVenue(BatchMatchingEngine())
)

# Run one tick
game.run_tick()
```

</div>
