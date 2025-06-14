# WebSocket API Reference

## Overview

The Intern Trading Game provides WebSocket endpoints for real-time data streaming, enabling bots to receive immediate updates on trades, market data, and game events without polling the REST API.

## Connection Details

### Endpoint

```
ws://localhost:8000/ws
```

### Authentication

WebSocket connections require authentication via API key:

```python
import websockets
import json

async def connect():
    uri = "ws://localhost:8000/ws?api_key=YOUR_API_KEY"
    async with websockets.connect(uri) as websocket:
        # Connection established
        await process_messages(websocket)
```

### Connection Lifecycle

1. **Connection** - Establish WebSocket connection with API key
2. **Authentication** - Server validates API key
3. **Position Snapshot** - Initial position state sent to client
4. **Ready** - Connection ready for real-time updates
5. **Disconnection** - Graceful close or timeout

## Message Format

All messages follow a consistent JSON structure:

```json
{
    "seq": 123,                    // Sequence number (incrementing)
    "type": "message_type",        // Message type identifier
    "timestamp": "2024-01-15T10:30:45.123456Z",  // ISO 8601 timestamp
    "data": {                      // Message-specific payload
        // ... fields vary by message type
    }
}
```

## Message Types

### Important Note on Validation

**Validation rejections are NOT sent via WebSocket.** They are returned synchronously in the REST API response. WebSocket only sends execution-related events that happen after validation.

See [API Communication Design](../explanation/api-communication-design.md) for the complete communication model.

### Order Messages

#### new_order_ack

Sent when an order is accepted by the exchange and enters the order book.

```json
{
    "seq": 1,
    "type": "new_order_ack",
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "data": {
        "order_id": "ORD-123456",
        "client_order_id": "MY-ORDER-001",  // If provided
        "instrument_id": "SPX_4500_CALL",
        "side": "buy",
        "quantity": 10,
        "order_type": "limit",
        "price": 128.50,
        "status": "new"
    }
}
```

Note: This message indicates the order has been accepted by the exchange, not just validated.

#### execution_report

Sent when an order is filled (partially or completely).

```json
{
    "seq": 3,
    "type": "execution_report",
    "timestamp": "2024-01-15T10:30:46.345678Z",
    "data": {
        "order_id": "ORD-123456",
        "client_order_id": "MY-ORDER-001",
        "trade_id": "TRD-789012",
        "instrument_id": "SPX_4500_CALL",
        "side": "buy",
        "executed_quantity": 5,
        "executed_price": 128.45,
        "remaining_quantity": 5,
        "order_status": "partially_filled",
        "liquidity_type": "taker",
        "fees": 0.10
    }
}
```

#### order_cancelled

Sent when an order is successfully cancelled at the exchange.

```json
{
    "seq": 4,
    "type": "order_cancelled",
    "timestamp": "2024-01-15T10:30:47.456789Z",
    "data": {
        "order_id": "ORD-123456",
        "client_order_id": "MY-ORDER-001",
        "status": "cancelled",
        "cancelled_quantity": 5,
        "reason": "user_requested"
    }
}
```

Note: Cancellation success/failure is returned synchronously via the REST API. This WebSocket message provides additional details after the cancellation is processed by the exchange.

### Market Data Messages

#### market_data

Sent when market prices update.

```json
{
    "seq": 6,
    "type": "market_data",
    "timestamp": "2024-01-15T10:30:48.678901Z",
    "data": {
        "instrument_id": "SPX_4500_CALL",
        "bid": 128.25,
        "ask": 128.75,
        "last": 128.50,
        "bid_size": 50,
        "ask_size": 75
    }
}
```

### Game State Messages

#### position_snapshot

Sent immediately after connection establishment.

```json
{
    "seq": 1,
    "type": "position_snapshot",
    "timestamp": "2024-01-15T10:30:00.000000Z",
    "data": {
        "positions": {
            "SPX_4500_CALL": 10,
            "SPX_4500_PUT": -5
        }
    }
}
```

### Signal Messages (Role-Specific)

#### signal

Sent to teams with appropriate role permissions.

```json
{
    "seq": 9,
    "type": "signal",
    "timestamp": "2024-01-15T10:35:15.123456Z",
    "data": {
        "signal_type": "volatility_forecast",
        "forecast": "high",
        "confidence": 0.75,
        "horizon_minutes": 15
    }
}
```

### System Messages

#### connection_status

Sent for connection lifecycle events.

```json
{
    "seq": 1,
    "type": "connection_status",
    "timestamp": "2024-01-15T10:30:00.123456Z",
    "data": {
        "status": "authenticated",
        "message": "Connection authenticated for team TEAM-001"
    }
}
```

#### event

Sent for market events and news.

```json
{
    "seq": 10,
    "type": "event",
    "timestamp": "2024-01-15T10:36:00.000000Z",
    "data": {
        "event_type": "news",
        "headline": "Fed announces rate decision",
        "impact": "high"
    }
}
```

## Error Handling

### Connection Errors

- `1000` - Normal closure
- `1001` - Going away (server shutdown)
- `1002` - Protocol error
- `1003` - Unsupported data
- `1008` - Policy violation (auth failure)
- `1011` - Internal server error

### Message Sequence Numbers

Clients should track sequence numbers to detect missed messages:

```python
last_seq = 0

async def process_message(msg):
    global last_seq

    if msg['seq'] != last_seq + 1:
        print(f"Missed messages! Expected {last_seq + 1}, got {msg['seq']}")

    last_seq = msg['seq']
    # Process message...
```

## Rate Limits

- Maximum 1 connection per team
- No rate limits on received messages
- Slow clients may be disconnected if unable to keep up

## Example Client

```python
import asyncio
import websockets
import json

async def trading_bot():
    uri = "ws://localhost:8000/ws?api_key=YOUR_API_KEY"

    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            msg = json.loads(message)

            # Process different message types
            if msg['type'] == 'position_snapshot':
                print(f"Current positions: {msg['data']['positions']}")

            elif msg['type'] == 'execution_report':
                data = msg['data']
                print(f"Trade executed: {data['executed_quantity']} @ {data['executed_price']}")
                print(f"Remaining: {data['remaining_quantity']}, Fees: {data['fees']}")

# Run the bot
asyncio.run(trading_bot())
```

## Best Practices

1. **Reconnection Logic** - Implement automatic reconnection with exponential backoff
2. **Message Handling** - Process messages asynchronously to avoid blocking
3. **Error Recovery** - Handle partial messages and connection drops gracefully
4. **State Synchronization** - Use position snapshot to verify local state
5. **Sequence Tracking** - Monitor sequence numbers to detect missed messages

## See Also

- [REST API Reference](rest-api.md) - For order submission and queries
- [How to Use WebSockets](../how-to/use-websockets.md) - Integration guide
- [Order Types](../../game/trading/order-types.md) - Order type details
