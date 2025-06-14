# Bot Developer Guide

A practical guide for building trading bots for the Intern Trading Game, showing how to effectively use the 5 core API operations.

## Quick Start

The API provides exactly 5 operations - everything you need to build a sophisticated trading bot:

1. **Submit Order** - Place buy/sell orders
2. **Cancel Order** - Cancel resting orders
3. **Get Open Orders** - See your working orders
4. **Get Positions** - Check your inventory
5. **Register Team** - Get your API key

## Setting Up Your Bot

### 1. Register Your Team

First, register to get your API key:

```python
import requests

response = requests.post(
    "http://localhost:8000/auth/register",
    json={
        "team_name": "MyTradingBot",
        "role": "market_maker"  # or hedge_fund, arbitrage, retail
    }
)

if response.json()["success"]:
    data = response.json()["data"]
    api_key = data["api_key"]  # Save this! Shown only once
    team_id = data["team_id"]
    print(f"Registered! API Key: {api_key}")
```

### 2. Basic Bot Structure

```python
import requests
import websocket
import json
import threading
from typing import Dict, Optional

class TradingBot:
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.positions = {}
        self.open_orders = {}

    def api_call(self, method: str, endpoint: str, data: Optional[Dict] = None):
        """Make an API call and return the response."""
        url = f"{self.base_url}{endpoint}"

        if method == "GET":
            response = requests.get(url, headers=self.headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=self.headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=self.headers)

        result = response.json()

        if not result["success"]:
            print(f"API Error: {result['error']['code']} - {result['error']['message']}")

        return result
```

## Core Operations

### 1. Submitting Orders

```python
def submit_order(self, instrument: str, side: str, quantity: int, price: Optional[float] = None):
    """Submit a limit or market order."""
    order_data = {
        "instrument_id": instrument,
        "side": side,
        "quantity": quantity,
        "request_id": f"req_{time.time()}"
    }

    # Add price for limit orders
    if price is not None:
        order_data["price"] = price

    # Optional: track your own orders
    order_data["client_order_id"] = f"my_{instrument}_{side}_{time.time()}"

    response = self.api_call("POST", "/orders", order_data)

    if response["success"]:
        order_id = response["order_id"]
        print(f"Order {order_id} submitted")
        return order_id

    return None

# Examples
bot.submit_order("SPX_CALL_4500_20240315", "buy", 10, 100.0)  # Limit order
bot.submit_order("SPX_PUT_4500_20240315", "sell", 5)          # Market order
```

### 2. Managing Orders

```python
def get_open_orders(self):
    """Get all open orders."""
    response = self.api_call("GET", "/orders")

    if response["success"]:
        self.open_orders = {
            order["order_id"]: order
            for order in response["data"]["orders"]
        }
        return response["data"]["orders"]

    return []

def cancel_order(self, order_id: str):
    """Cancel a specific order."""
    response = self.api_call("DELETE", f"/orders/{order_id}")

    if response["success"]:
        print(f"Order {order_id} cancelled")
        return True

    return False

def cancel_all_orders(self):
    """Cancel all open orders."""
    orders = self.get_open_orders()
    for order in orders:
        self.cancel_order(order["order_id"])
```

### 3. Position Management

```python
def get_positions(self):
    """Get current positions."""
    response = self.api_call("GET", "/positions")

    if response["success"]:
        self.positions = response["data"]["positions"]
        return self.positions

    return {}

def get_net_position(self, instrument: str) -> int:
    """Get position for a specific instrument."""
    return self.positions.get(instrument, 0)

def is_position_within_limit(self, instrument: str, additional: int, limit: int = 50) -> bool:
    """Check if a new order would exceed position limits."""
    current = self.get_net_position(instrument)
    new_position = current + additional
    return abs(new_position) <= limit
```

## Common Bot Patterns

### Market Making Bot

```python
class MarketMaker(TradingBot):
    def __init__(self, api_key: str, spread: float = 1.0):
        super().__init__(api_key)
        self.spread = spread
        self.instruments = [
            "SPX_CALL_4500_20240315",
            "SPX_PUT_4500_20240315"
        ]

    def quote_market(self, instrument: str, fair_value: float, size: int = 10):
        """Post two-sided quotes around fair value."""
        # Cancel existing quotes
        self.cancel_instrument_orders(instrument)

        # Check position limits before quoting
        if not self.can_quote_safely(instrument, size):
            return

        # Submit new quotes
        bid_price = fair_value - self.spread / 2
        ask_price = fair_value + self.spread / 2

        self.submit_order(instrument, "buy", size, bid_price)
        self.submit_order(instrument, "sell", size, ask_price)

    def cancel_instrument_orders(self, instrument: str):
        """Cancel all orders for a specific instrument."""
        orders = self.get_open_orders()
        for order in orders:
            if order["instrument_id"] == instrument:
                self.cancel_order(order["order_id"])

    def can_quote_safely(self, instrument: str, size: int) -> bool:
        """Check if we can quote without exceeding limits."""
        position = self.get_net_position(instrument)

        # Would a full fill on either side exceed limits?
        if abs(position + size) > 45:  # Leave buffer below 50
            return False
        if abs(position - size) > 45:
            return False

        return True
```

### Momentum Trading Bot

```python
class MomentumTrader(TradingBot):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.last_prices = {}

    def check_momentum_signal(self, instrument: str, current_price: float) -> Optional[str]:
        """Detect momentum and return signal."""
        if instrument not in self.last_prices:
            self.last_prices[instrument] = current_price
            return None

        last_price = self.last_prices[instrument]
        price_change = (current_price - last_price) / last_price

        # Simple momentum thresholds
        if price_change > 0.02:  # 2% up move
            return "buy"
        elif price_change < -0.02:  # 2% down move
            return "sell"

        self.last_prices[instrument] = current_price
        return None

    def execute_momentum_trade(self, instrument: str, signal: str, size: int = 5):
        """Execute a momentum trade with risk checks."""
        # Check position limits
        current_pos = self.get_net_position(instrument)
        if signal == "buy" and current_pos >= 40:
            return  # Already too long
        if signal == "sell" and current_pos <= -40:
            return  # Already too short

        # Submit market order
        self.submit_order(instrument, signal, size)
```

## WebSocket Integration

```python
def connect_websocket(bot: TradingBot):
    """Connect to WebSocket for real-time updates."""

    def on_message(ws, message):
        data = json.loads(message)
        msg_type = data.get("type")

        if msg_type == "position_snapshot":
            # Initial position state
            bot.positions = data["data"]["positions"]

        elif msg_type == "new_order_ack":
            # Order entered book
            order_id = data["data"]["order_id"]
            print(f"Order {order_id} acknowledged by exchange")

        elif msg_type == "execution_report":
            # Trade occurred
            order_id = data["data"]["order_id"]
            quantity = data["data"]["executed_quantity"]
            price = data["data"]["executed_price"]
            print(f"Order {order_id}: Filled {quantity} @ {price}")

        elif msg_type == "order_cancelled":
            # Cancellation confirmed
            order_id = data["data"]["order_id"]
            print(f"Order {order_id} cancelled by exchange")

    ws_url = f"ws://localhost:8000/ws?api_key={bot.api_key}"
    ws = websocket.WebSocketApp(ws_url, on_message=on_message)

    # Run in separate thread
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    return ws
```

## Error Handling

```python
class RobustBot(TradingBot):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.error_counts = {}

    def handle_api_error(self, error_code: str, details: Optional[Dict] = None):
        """Handle different error types appropriately."""

        # Track error frequency
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1

        if error_code == "RATE_LIMIT_EXCEEDED":
            # Back off exponentially
            retry_after = details.get("retry_after", 1.0) if details else 1.0
            time.sleep(retry_after * (2 ** min(self.error_counts[error_code], 5)))

        elif error_code == "POSITION_LIMIT_EXCEEDED":
            # Reduce position before continuing
            self.reduce_positions()

        elif error_code == "ORDER_NOT_FOUND":
            # Order already filled/cancelled, update local state
            self.sync_open_orders()

        elif error_code == "INSUFFICIENT_BALANCE":
            # Stop trading, alert operator
            self.emergency_stop()
```

## Best Practices

### 1. State Synchronization

Always sync state on startup and after disconnections:

```python
def sync_state(self):
    """Synchronize bot state with exchange."""
    # Get current positions
    self.get_positions()

    # Get open orders
    self.get_open_orders()

    # Log current state
    print(f"Positions: {self.positions}")
    print(f"Open orders: {len(self.open_orders)}")
```

### 2. Graceful Shutdown

Clean up orders on exit:

```python
def shutdown(self):
    """Gracefully shutdown the bot."""
    print("Shutting down...")

    # Cancel all open orders
    self.cancel_all_orders()

    # Log final position
    final_positions = self.get_positions()
    print(f"Final positions: {final_positions}")
```

### 3. Risk Management

Implement position and order limits:

```python
def validate_order(self, instrument: str, side: str, quantity: int) -> bool:
    """Validate order against risk limits."""
    # Check position limits
    current = self.get_net_position(instrument)
    new_position = current + quantity if side == "buy" else current - quantity

    if abs(new_position) > 45:  # Conservative limit
        print(f"Order would exceed position limit: {new_position}")
        return False

    # Check order count limits
    open_count = len(self.open_orders)
    if open_count >= 20:  # Max open orders
        print(f"Too many open orders: {open_count}")
        return False

    return True
```

### 4. Logging and Monitoring

```python
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Log all trades
logger.info(f"Order submitted: {order_id} - {instrument} {side} {quantity} @ {price}")
logger.error(f"Order failed: {error_code} - {error_message}")
```

## Complete Example Bot

```python
import time
import logging
from typing import Dict, List

class SimpleTradingBot(TradingBot):
    """A complete example bot that makes markets in options."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
        self.instruments = [
            "SPX_CALL_4500_20240315",
            "SPX_PUT_4500_20240315"
        ]

    def start(self):
        """Start the bot."""
        self.logger.info("Starting bot...")
        self.running = True

        # Sync initial state
        self.sync_state()

        # Connect WebSocket
        self.ws = connect_websocket(self)

        # Main trading loop
        while self.running:
            try:
                self.trading_loop()
                time.sleep(1)  # Run every second
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                time.sleep(5)  # Wait before retrying

        self.shutdown()

    def trading_loop(self):
        """Main trading logic."""
        for instrument in self.instruments:
            # Cancel stale quotes
            self.cancel_stale_orders(instrument)

            # Calculate fair value (simplified)
            fair_value = self.calculate_fair_value(instrument)

            # Post new quotes
            if self.should_quote(instrument):
                self.quote_market(instrument, fair_value)

    def calculate_fair_value(self, instrument: str) -> float:
        """Calculate theoretical value (placeholder)."""
        # In reality, use Black-Scholes or other model
        return 100.0

    def should_quote(self, instrument: str) -> bool:
        """Decide whether to quote this instrument."""
        # Check position
        position = self.get_net_position(instrument)
        if abs(position) > 40:
            return False

        # Check if we already have quotes
        orders = [o for o in self.open_orders.values()
                 if o["instrument_id"] == instrument]
        if len(orders) >= 2:
            return False

        return True

    def quote_market(self, instrument: str, fair_value: float):
        """Submit two-sided quotes."""
        spread = 1.0
        size = 10

        # Submit bid
        bid_price = fair_value - spread / 2
        self.submit_order(instrument, "buy", size, bid_price)

        # Submit ask
        ask_price = fair_value + spread / 2
        self.submit_order(instrument, "sell", size, ask_price)

    def cancel_stale_orders(self, instrument: str):
        """Cancel orders older than 30 seconds."""
        current_time = time.time()
        orders = self.get_open_orders()

        for order in orders:
            if order["instrument_id"] != instrument:
                continue

            # Parse order time (simplified)
            order_age = current_time - self.parse_order_time(order)
            if order_age > 30:
                self.cancel_order(order["order_id"])

# Run the bot
if __name__ == "__main__":
    API_KEY = "your_api_key_here"
    bot = SimpleTradingBot(API_KEY)
    bot.start()
```

## Next Steps

1. **Implement proper option pricing** - Use Black-Scholes or other models
2. **Add risk management** - Track Greeks, implement stop losses
3. **Optimize execution** - Smart order routing, iceberg orders
4. **Monitor performance** - Track P&L, hit rates, queue position
5. **Handle edge cases** - Network failures, partial fills, race conditions

Remember: Start simple, test thoroughly, and gradually add complexity as you understand the market dynamics better.
