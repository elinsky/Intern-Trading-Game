# How to Use the REST API

This guide shows how to interact with the Intern Trading Game REST API to build trading bots.

## Getting Started

### 1. Start the API Server

```bash
cd intern_trading_game
python -m intern_trading_game.api.main
```

The API will start on `http://localhost:8000`.

### 2. Register Your Team

Before trading, you must register your team to get an API key:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "team_name": "AlphaBot",
    "role": "market_maker"
  }'
```

Response:
```json
{
  "team_id": "TEAM_001",
  "team_name": "AlphaBot",
  "role": "market_maker",
  "api_key": "itg_AbCdEfGhIjKlMnOpQrStUvWxYz...",
  "created_at": "2024-01-15T10:00:00Z"
}
```

Save your API key - you'll need it for all other requests.

### 3. Submit Orders

Use your API key in the `X-API-Key` header:

```bash
# Submit a limit order
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-API-Key: itg_AbCdEfGhIjKlMnOpQrStUvWxYz..." \
  -d '{
    "instrument_id": "SPX_4500_CALL",
    "order_type": "limit",
    "side": "buy",
    "quantity": 10,
    "price": 25.50
  }'
```

### 4. Check Your Positions

```bash
curl -X GET http://localhost:8000/positions/TEAM_001 \
  -H "X-API-Key: itg_AbCdEfGhIjKlMnOpQrStUvWxYz..."
```

## Python Bot Example

```python
import requests
import time

class TradingBot:
    def __init__(self, api_key, base_url="http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
        self.team_id = None

    def submit_order(self, instrument, order_type, side, quantity, price=None):
        """Submit an order to the exchange."""
        data = {
            "instrument_id": instrument,
            "order_type": order_type,
            "side": side,
            "quantity": quantity
        }
        if price is not None:
            data["price"] = price

        response = requests.post(
            f"{self.base_url}/orders",
            json=data,
            headers=self.headers
        )
        return response.json()

    def get_positions(self):
        """Get current positions."""
        response = requests.get(
            f"{self.base_url}/positions/{self.team_id}",
            headers=self.headers
        )
        return response.json()

    def run_market_maker_strategy(self):
        """Simple market making strategy."""
        instrument = "SPX_4500_CALL"
        spread = 0.20
        base_price = 25.50

        while True:
            # Post bid
            bid_result = self.submit_order(
                instrument, "limit", "buy",
                10, base_price - spread/2
            )
            print(f"Bid: {bid_result}")

            # Post ask
            ask_result = self.submit_order(
                instrument, "limit", "sell",
                10, base_price + spread/2
            )
            print(f"Ask: {ask_result}")

            # Check positions
            positions = self.get_positions()
            print(f"Positions: {positions}")

            # Wait before next update
            time.sleep(5)

# Register and run bot
def main():
    # First register
    response = requests.post(
        "http://localhost:8000/auth/register",
        json={"team_name": "MMBot", "role": "market_maker"}
    )
    team_info = response.json()

    # Create bot
    bot = TradingBot(team_info["api_key"])
    bot.team_id = team_info["team_id"]

    # Run strategy
    bot.run_market_maker_strategy()

if __name__ == "__main__":
    main()
```

## API Endpoints

### Authentication

#### POST /auth/register
Register a new team.

**Request:**
```json
{
  "team_name": "string",
  "role": "market_maker"
}
```

**Response:**
```json
{
  "team_id": "TEAM_001",
  "team_name": "string",
  "role": "market_maker",
  "api_key": "itg_...",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### Trading

#### POST /orders
Submit a new order.

**Headers:**
- `X-API-Key`: Your API key

**Request:**
```json
{
  "instrument_id": "SPX_4500_CALL",
  "order_type": "limit",
  "side": "buy",
  "quantity": 10,
  "price": 25.50
}
```

**Response:**
```json
{
  "order_id": "ORD_123456",
  "status": "accepted",
  "timestamp": "2024-01-15T10:00:01Z",
  "filled_quantity": 0,
  "average_price": null,
  "error_code": null,
  "error_message": null
}
```

### Market Data

#### GET /positions/{team_id}
Get your current positions.

**Headers:**
- `X-API-Key`: Your API key

**Response:**
```json
{
  "team_id": "TEAM_001",
  "positions": {
    "SPX_4500_CALL": 10,
    "SPX_4500_PUT": -5
  },
  "last_updated": "2024-01-15T10:00:00Z"
}
```

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `401`: Authentication failed
- `403`: Forbidden (accessing other team's data)
- `404`: Resource not found
- `504`: Request timeout

Error responses include details:

```json
{
  "error": "Invalid order type",
  "detail": "Order type must be 'limit' or 'market'",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

## Rate Limits

Currently no rate limits are enforced, but be respectful:

- Don't submit more than 10 orders per second
- Don't poll positions more than once per second

## Next Steps

1. Review the [Order Validation Rules](../reference/validation-api.md)
2. Understand [Trading Phases](../explanation/trading-phases.md)
3. Build your trading strategy!
