# WebSocket Integration with REST API

This guide explains how WebSocket notifications integrate with REST API operations in the Intern Trading Game.

## Overview

The trading system uses a hybrid approach:
- **REST API** for active operations (submitting orders, querying positions)
- **WebSocket** for real-time notifications (order updates, executions)

## Architecture

```
Bot -> REST API -> Order Queue -> Validator -> Matching -> Exchange
         ↓                         ↓           ↓          ↓
    WebSocket ← ← ← ← ← ← ← ← Reject ← ← ← Accept ← ← Fill
```

## Order Lifecycle

When you submit an order via REST API, you'll receive WebSocket notifications at each stage:

### 1. Order Submission (REST)
```python
# Submit order via REST
response = requests.post(
    "http://localhost:8000/orders",
    headers={"X-API-Key": api_key},
    json={
        "instrument_id": "SPX_4500_CALL",
        "order_type": "limit",
        "side": "buy",
        "quantity": 10,
        "price": 100.0,
        "client_order_id": "MY_ORDER_001"
    }
)

# Immediate response
{
    "order_id": "ORD_123456",
    "status": "accepted",
    "timestamp": "2024-01-15T10:00:00Z",
    "filled_quantity": 0,
    "average_price": null,
    "fees": 0.0,
    "liquidity_type": null
}
```

### 2. Order Acknowledgment (WebSocket)
```json
{
    "seq": 2,
    "type": "new_order_ack",
    "timestamp": "2024-01-15T10:00:00.123456Z",
    "data": {
        "order_id": "ORD_123456",
        "client_order_id": "MY_ORDER_001",
        "instrument_id": "SPX_4500_CALL",
        "side": "buy",
        "quantity": 10,
        "price": 100.0,
        "status": "new"
    }
}
```

### 3. Trade Execution (WebSocket)
```json
{
    "seq": 3,
    "type": "execution_report",
    "timestamp": "2024-01-15T10:00:01.234567Z",
    "data": {
        "order_id": "ORD_123456",
        "client_order_id": "MY_ORDER_001",
        "trade_id": "TRD_789012",
        "instrument_id": "SPX_4500_CALL",
        "side": "buy",
        "executed_quantity": 10,
        "executed_price": 100.0,
        "remaining_quantity": 0,
        "order_status": "filled",
        "liquidity_type": "maker",
        "fees": -0.20
    }
}
```

## Message Flow Details

### Successful Order Flow

1. **REST Submit** -> Synchronous response with order_id
2. **Validator** -> If accepted, continues to matching
3. **Matching Engine** -> Sends `new_order_ack` via WebSocket
4. **Exchange** -> If filled, sends `execution_report` via WebSocket

### Rejected Order Flow

1. **REST Submit** -> Synchronous response with order_id
2. **Validator** -> If rejected, sends `new_order_reject` via WebSocket
3. **REST Response** -> Returns rejected status

## Example Integration

```python
import asyncio
import json
import requests
import websockets

class TradingBot:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://localhost:8000"
        self.ws_uri = f"ws://localhost:8000/ws?api_key={api_key}"
        self.pending_orders = {}

    async def run(self):
        # Connect WebSocket for notifications
        async with websockets.connect(self.ws_uri) as websocket:
            # Handle messages in background
            ws_task = asyncio.create_task(self.handle_websocket(websocket))

            # Submit order via REST
            order_id = self.submit_order()

            # Wait for execution via WebSocket
            await self.wait_for_fill(order_id)

    def submit_order(self):
        """Submit order via REST API."""
        response = requests.post(
            f"{self.base_url}/orders",
            headers={"X-API-Key": self.api_key},
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 10,
                "price": 100.0,
                "client_order_id": f"BOT_{time.time()}"
            }
        )
        data = response.json()
        self.pending_orders[data["order_id"]] = "submitted"
        return data["order_id"]

    async def handle_websocket(self, websocket):
        """Process WebSocket messages."""
        async for message in websocket:
            msg = json.loads(message)

            if msg["type"] == "new_order_ack":
                order_id = msg["data"]["order_id"]
                if order_id in self.pending_orders:
                    self.pending_orders[order_id] = "acknowledged"
                    print(f"Order {order_id} acknowledged by exchange")

            elif msg["type"] == "execution_report":
                order_id = msg["data"]["order_id"]
                if order_id in self.pending_orders:
                    self.pending_orders[order_id] = "filled"
                    print(f"Order {order_id} filled: {msg['data']['executed_quantity']} @ {msg['data']['executed_price']}")

    async def wait_for_fill(self, order_id):
        """Wait for order to be filled."""
        while self.pending_orders.get(order_id) != "filled":
            await asyncio.sleep(0.1)
```

## Threading Architecture

The system uses dedicated threads for each stage:

1. **Thread 2: Validator** - Validates orders, sends rejections
2. **Thread 3: Matching** - Submits to exchange, sends acknowledgments
3. **Thread 4: Publisher** - Updates positions, sends execution reports
4. **Thread 8: WebSocket** - Handles all async WebSocket operations

## Key Design Decisions

### Why Separate Threads?

- REST API remains synchronous and simple
- WebSocket operations are async and isolated
- No blocking between REST and WebSocket operations
- Clean separation of concerns

### Message Timing

- **Acknowledgment** sent AFTER exchange accepts (not just validation)
- **Execution** sent immediately when trade occurs
- **Position updates** included in execution reports

### Error Handling

- WebSocket failures don't affect REST operations
- Disconnected clients don't block the queue
- Messages for disconnected clients are dropped

## Best Practices

1. **Always connect WebSocket before trading** - Ensures you don't miss notifications
2. **Track orders by client_order_id** - Your reference stays consistent
3. **Handle reconnections** - WebSocket may disconnect, plan for it
4. **Don't rely solely on WebSocket** - REST responses are authoritative
5. **Process messages asynchronously** - Don't block the message handler

## Common Patterns

### Pattern 1: Fire and Forget
```python
# Submit order and move on
response = submit_order()
if response["status"] != "rejected":
    # Continue trading, handle fills via WebSocket
    pass
```

### Pattern 2: Wait for Fill
```python
# Submit and wait for execution
order_id = submit_order()["order_id"]
execution = await wait_for_websocket_message("execution_report", order_id)
```

### Pattern 3: Bulk Order Management
```python
# Track multiple orders
pending = {}
for signal in signals:
    order = submit_order(signal)
    pending[order["order_id"]] = signal

# Process executions as they arrive
async for msg in websocket:
    if msg["type"] == "execution_report":
        signal = pending.pop(msg["data"]["order_id"])
        handle_fill(signal, msg["data"])
```

## Troubleshooting

### Missing Messages

- Ensure WebSocket is connected before submitting orders
- Check sequence numbers for gaps
- Verify API key has correct permissions

### Delayed Messages

- Network latency can delay WebSocket delivery
- REST response arrives before WebSocket notification
- Use client_order_id to correlate across both channels

### Connection Issues

- Implement exponential backoff for reconnections
- Always re-subscribe to position snapshot on reconnect
- Queue orders locally during disconnection
