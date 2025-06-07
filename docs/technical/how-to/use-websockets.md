# How to Use WebSockets

This guide explains how to integrate WebSocket connections into your trading bot for real-time market data and trade notifications.

## Why Use WebSockets?

WebSockets provide real-time, bidirectional communication between your bot and the exchange:

- **Immediate Updates** - No polling delay for trade executions
- **Lower Latency** - Faster than REST API for market data
- **Efficient** - Single persistent connection vs multiple HTTP requests
- **Event-Driven** - React to market changes as they happen

## Basic Connection

```python
import asyncio
import websockets
import json

class TradingBot:
    def __init__(self, api_key):
        self.api_key = api_key
        self.uri = f"ws://localhost:8000/ws?api_key={api_key}"
        self.positions = {}

    async def connect(self):
        async with websockets.connect(self.uri) as websocket:
            print("Connected to exchange WebSocket")
            await self.handle_messages(websocket)

    async def handle_messages(self, websocket):
        async for message in websocket:
            msg = json.loads(message)
            await self.process_message(msg)

    async def process_message(self, msg):
        msg_type = msg['type']
        data = msg['data']

        if msg_type == 'position_snapshot':
            self.positions = data['positions']
            print(f"Positions initialized: {self.positions}")

        elif msg_type == 'execution_report':
            print(f"Order {data['order_id']} executed: "
                  f"{data['executed_quantity']} @ ${data['executed_price']}")
            # Update local position tracking
            self.update_position(data)

        elif msg_type == 'tick_start':
            print(f"Tick {data['tick_number']} started")
            # Trigger trading logic for new tick

    def update_position(self, execution):
        instrument = execution['instrument_id']
        quantity = execution['executed_quantity']
        if execution['side'] == 'buy':
            self.positions[instrument] = self.positions.get(instrument, 0) + quantity
        else:
            self.positions[instrument] = self.positions.get(instrument, 0) - quantity

# Run the bot
bot = TradingBot("YOUR_API_KEY")
asyncio.run(bot.connect())
```

## Combining REST and WebSocket APIs

Use REST API for active operations and WebSocket for passive updates:

```python
import aiohttp
import asyncio
import websockets
import json

class HybridBot:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://localhost:8000"
        self.ws_uri = f"ws://localhost:8000/ws?api_key={api_key}"
        self.headers = {"X-API-Key": api_key}

    async def run(self):
        # Start WebSocket connection for real-time updates
        ws_task = asyncio.create_task(self.websocket_handler())

        # Run main trading loop
        await self.trading_loop()

    async def websocket_handler(self):
        async with websockets.connect(self.ws_uri) as websocket:
            async for message in websocket:
                msg = json.loads(message)
                await self.process_ws_message(msg)

    async def trading_loop(self):
        async with aiohttp.ClientSession() as session:
            while True:
                # Wait for tick start via WebSocket
                await self.wait_for_tick_start()

                # Submit orders via REST API
                await self.submit_orders(session)

    async def submit_orders(self, session):
        order = {
            "instrument_id": "SPX_4500_CALL",
            "side": "buy",
            "quantity": 10,
            "order_type": "limit",
            "price": 128.50,
            "client_order_id": f"ORDER-{asyncio.get_event_loop().time()}"
        }

        async with session.post(
            f"{self.base_url}/orders",
            json=order,
            headers=self.headers
        ) as response:
            result = await response.json()
            print(f"Order submitted: {result}")

    async def process_ws_message(self, msg):
        if msg['type'] == 'execution_report':
            # React to fills immediately
            data = msg['data']
            if data['order_status'] == 'filled':
                print(f"Order filled! Checking for hedging opportunities...")
                # Implement hedging logic
```

## Handling Disconnections

Implement robust reconnection logic:

```python
import asyncio
import websockets
import json
from datetime import datetime

class ResilientBot:
    def __init__(self, api_key):
        self.api_key = api_key
        self.uri = f"ws://localhost:8000/ws?api_key={api_key}"
        self.reconnect_delay = 1  # Start with 1 second
        self.max_reconnect_delay = 60  # Max 60 seconds

    async def run(self):
        while True:
            try:
                await self.connect()
            except Exception as e:
                print(f"Connection failed: {e}")
                print(f"Reconnecting in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
                # Exponential backoff
                self.reconnect_delay = min(
                    self.reconnect_delay * 2,
                    self.max_reconnect_delay
                )

    async def connect(self):
        async with websockets.connect(self.uri) as websocket:
            print(f"Connected at {datetime.now()}")
            self.reconnect_delay = 1  # Reset on successful connection

            # Send heartbeat every 30 seconds
            heartbeat_task = asyncio.create_task(
                self.heartbeat(websocket)
            )

            try:
                await self.handle_messages(websocket)
            finally:
                heartbeat_task.cancel()

    async def heartbeat(self, websocket):
        while True:
            await asyncio.sleep(30)
            await websocket.ping()

    async def handle_messages(self, websocket):
        async for message in websocket:
            msg = json.loads(message)
            # Process messages...
```

## Message Sequencing

Track sequence numbers to detect missed messages:

```python
class SequenceTracker:
    def __init__(self):
        self.last_seq = 0
        self.missed_messages = []

    def check_sequence(self, msg):
        current_seq = msg['seq']
        expected_seq = self.last_seq + 1

        if current_seq != expected_seq:
            # Missed messages
            for seq in range(expected_seq, current_seq):
                self.missed_messages.append(seq)
            print(f"WARNING: Missed messages {expected_seq} to {current_seq-1}")

        self.last_seq = current_seq

    async def process_message(self, msg):
        self.check_sequence(msg)
        # Continue processing...
```

## Role-Specific Signals

Different roles receive different signals:

```python
class RoleAwareBot:
    def __init__(self, api_key, role):
        self.api_key = api_key
        self.role = role

    async def process_signal(self, signal_data):
        signal_type = signal_data['signal_type']

        if self.role == 'hedge_fund' and signal_type == 'volatility_forecast':
            # Hedge funds get volatility forecasts
            forecast = signal_data['forecast']
            confidence = signal_data['confidence']
            print(f"Vol forecast: {forecast} (confidence: {confidence})")
            # Adjust option positions based on forecast

        elif self.role == 'arbitrage' and signal_type == 'tracking_error':
            # Arbitrage desks get tracking error signals
            error = signal_data['tracking_error']
            print(f"Tracking error signal: {error}")
            # Execute SPX/SPY arbitrage trades
```

## Performance Tips

1. **Async Processing** - Don't block the message handler
2. **Local State** - Maintain positions locally, update from messages
3. **Batch Operations** - Collect updates before acting
4. **Error Handling** - Gracefully handle malformed messages

```python
async def optimized_handler(self, websocket):
    # Buffer for batch processing
    execution_buffer = []

    async for message in websocket:
        try:
            msg = json.loads(message)

            if msg['type'] == 'execution_report':
                execution_buffer.append(msg['data'])

                # Process in batches
                if len(execution_buffer) >= 10:
                    await self.process_executions(execution_buffer)
                    execution_buffer.clear()
            else:
                # Process other messages immediately
                await self.process_message(msg)

        except json.JSONDecodeError:
            print("Invalid JSON received")
        except Exception as e:
            print(f"Error processing message: {e}")
```

## Testing Your WebSocket Integration

```python
# Test script to verify WebSocket connection
import asyncio
import websockets
import json

async def test_connection(api_key):
    uri = f"ws://localhost:8000/ws?api_key={api_key}"

    async with websockets.connect(uri) as websocket:
        print("✓ Connected successfully")

        # Wait for position snapshot
        msg = await websocket.recv()
        data = json.loads(msg)

        if data['type'] == 'position_snapshot':
            print("✓ Received position snapshot")
            print(f"  Positions: {data['data']['positions']}")

        # Wait for a few more messages
        for i in range(5):
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"✓ Received {data['type']} (seq: {data['seq']})")

        print("✓ All tests passed!")

# Run test
asyncio.run(test_connection("YOUR_API_KEY"))
```

## Common Issues

### Connection Refused
- Verify the server is running
- Check the WebSocket URL and port
- Ensure firewall allows WebSocket connections

### Authentication Failed
- Verify API key is correct
- Check API key is passed in query parameter
- Ensure team is registered

### Missing Messages
- Implement sequence number tracking
- Add reconnection logic
- Buffer messages if processing is slow

### Memory Leaks
- Clear old data periodically
- Limit message history size
- Use weak references for callbacks

## Next Steps

- Review [WebSocket API Reference](../reference/websocket-api.md) for all message types
- Study [Trading Examples](../tutorials/market-maker-tutorial.md) for role-specific strategies
- Implement error handling and monitoring
