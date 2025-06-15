# REST API Reference

Complete reference for the Intern Trading Game REST API.

## Base URL

```
http://localhost:8000
```

## Authentication

All endpoints except `/game/teams/register` require authentication via API key.

Include your API key in the `X-API-Key` header:

```
X-API-Key: itg_your_api_key_here
```

## Response Format

**All** API responses use a unified `ApiResponse` structure:

```typescript
interface ApiResponse {
  success: boolean;           // Did the request succeed?
  request_id: string;         // Echo of client's request ID
  order_id?: string;          // For order operations (when success=true)
  data?: object;              // For query operations (when success=true)
  error?: ApiError;           // Present when success=false
  timestamp: string;          // ISO 8601 timestamp
}

interface ApiError {
  code: string;               // Machine-readable error code
  message: string;            // Human-readable explanation
  details?: object;           // Additional context (optional)
}
```

## Core Endpoints

### 1. Submit Order

`POST /exchange/orders`

Submit a new order to buy or sell an option.

**Request Headers:**
- `X-API-Key`: Required
- `Content-Type`: application/json

**Request Body:**

| Field           | Type    | Required | Description                                |
|-----------------|---------|----------|--------------------------------------------|
| instrument_id   | string  | Yes      | Instrument to trade (e.g., "SPX_CALL_4500_20240315") |
| side            | string  | Yes      | "buy" or "sell"                           |
| quantity        | integer | Yes      | Number of contracts (> 0)                 |
| price           | number  | No       | Limit price (required for limit orders)   |
| client_order_id | string  | No       | Your reference ID for tracking            |
| request_id      | string  | No       | Request correlation ID                    |

**Success Response:**
```json
{
  "success": true,
  "request_id": "req_12345",
  "order_id": "ORD_67890",
  "data": null,
  "error": null,
  "timestamp": "2024-01-15T10:00:00.001Z"
}
```

**Validation Failure:**
```json
{
  "success": false,
  "request_id": "req_12345",
  "order_id": null,
  "data": null,
  "error": {
    "code": "POSITION_LIMIT_EXCEEDED",
    "message": "Order would exceed position limit of 50",
    "details": {
      "current_position": 45,
      "order_quantity": 10,
      "limit": 50
    }
  },
  "timestamp": "2024-01-15T10:00:00.001Z"
}
```

**Notes:**

- Response arrives in ~1ms with validation result only
- Order type is inferred: price present = limit, price absent = market
- Execution details arrive via WebSocket

### 2. Cancel Order

`DELETE /exchange/orders/{order_id}`

Cancel a resting order in the order book.

**Request Headers:**

- `X-API-Key`: Required

**Path Parameters:**

- `order_id`: The exchange-assigned order ID to cancel

**Success Response:**
```json
{
  "success": true,
  "request_id": "req_12346",
  "order_id": "ORD_67890",
  "data": null,
  "error": null,
  "timestamp": "2024-01-15T10:00:01.001Z"
}
```

**Failure Response:**
```json
{
  "success": false,
  "request_id": "req_12346",
  "order_id": null,
  "data": null,
  "error": {
    "code": "CANCEL_FAILED",
    "message": "Cancel failed: Order not found",
    "details": null
  },
  "timestamp": "2024-01-15T10:00:01.001Z"
}
```

**Error Code:**

- `CANCEL_FAILED` - Generic cancellation failure (security: doesn't reveal specific reasons)

### 3. Get Open Orders

`GET /exchange/orders`

Retrieve all open (resting) orders for your team.

**Request Headers:**
- `X-API-Key`: Required

**Success Response:**
```json
{
  "success": true,
  "request_id": "req_12347",
  "order_id": null,
  "data": {
    "orders": [
      {
        "order_id": "ORD_67890",
        "client_order_id": "my_order_001",
        "instrument_id": "SPX_CALL_4500_20240315",
        "side": "buy",
        "price": 100.0,
        "original_quantity": 10,
        "remaining_quantity": 7,
        "status": "partially_filled",
        "submitted_at": "2024-01-15T10:00:00Z"
      },
      {
        "order_id": "ORD_67891",
        "client_order_id": null,
        "instrument_id": "SPX_PUT_4500_20240315",
        "side": "sell",
        "price": 50.0,
        "original_quantity": 5,
        "remaining_quantity": 5,
        "status": "open",
        "submitted_at": "2024-01-15T10:00:30Z"
      }
    ]
  },
  "error": null,
  "timestamp": "2024-01-15T10:01:00.001Z"
}
```

**Empty Response (no open orders):**
```json
{
  "success": true,
  "request_id": "req_12347",
  "order_id": null,
  "data": {
    "orders": []
  },
  "error": null,
  "timestamp": "2024-01-15T10:01:00.001Z"
}
```

**Notes:**

- Returns only resting orders (not filled or cancelled)
- Includes partially filled orders with remaining quantity
- Sorted by submission time (oldest first)

### 4. Get Positions

`GET /positions`

Get current net position for each instrument.

**Request Headers:**

- `X-API-Key`: Required

**Success Response:**
```json
{
  "success": true,
  "request_id": "req_12348",
  "order_id": null,
  "data": {
    "positions": {
      "SPX_CALL_4500_20240315": 10,
      "SPX_PUT_4500_20240315": -5,
      "SPX_CALL_4600_20240315": 0
    }
  },
  "error": null,
  "timestamp": "2024-01-15T10:01:00.001Z"
}
```

**Notes:**

- Positive values = long position
- Negative values = short position
- Zero values included for previously traded instruments
- Real-time snapshot of current positions

### 5. Register Team

`POST /game/teams/register`

One-time registration to obtain API credentials.

**Request Headers:**
- `Content-Type`: application/json

**Request Body:**

| Field     | Type   | Required | Description                                |
|-----------|--------|----------|--------------------------------------------|
| team_name | string | Yes      | Unique team name (3-50 characters)        |
| role      | string | Yes      | Trading role: "market_maker", "hedge_fund", "arbitrage", or "retail" |

**Success Response:**
```json
{
  "success": true,
  "request_id": "req_12349",
  "order_id": null,
  "data": {
    "team_id": "TEAM_123",
    "team_name": "AlphaBot",
    "role": "market_maker",
    "api_key": "itg_AbCdEfGhIjKlMnOpQrStUvWxYz123456",
    "created_at": "2024-01-15T10:00:00Z"
  },
  "error": null,
  "timestamp": "2024-01-15T10:00:00.001Z"
}
```

**Failure Response:**
```json
{
  "success": false,
  "request_id": "req_12349",
  "order_id": null,
  "data": null,
  "error": {
    "code": "TEAM_NAME_TAKEN",
    "message": "Team name 'AlphaBot' is already registered",
    "details": null
  },
  "timestamp": "2024-01-15T10:00:00.001Z"
}
```

**Important:**

- No authentication required (public endpoint)
- API key is shown only once - save it immediately
- No API key retrieval endpoint for security

### 6. Get Order Book

`GET /exchange/orderbook/{instrument_id}`

Get the current order book depth for a specific instrument.

**Request Headers:**

- `X-API-Key`: Required

**Path Parameters:**

- `instrument_id`: The instrument to query (e.g., "SPX_CALL_4500_20240315")

**Success Response:**
```json
{
  "success": true,
  "request_id": "req_12350",
  "order_id": null,
  "data": {
    "instrument_id": "SPX_CALL_4500_20240315",
    "bids": [
      {"price": 99.50, "quantity": 15},
      {"price": 99.00, "quantity": 20},
      {"price": 98.50, "quantity": 10}
    ],
    "asks": [
      {"price": 100.50, "quantity": 5},
      {"price": 101.00, "quantity": 25},
      {"price": 101.50, "quantity": 30}
    ],
    "timestamp": "2024-01-15T10:01:00.001Z"
  },
  "error": null,
  "timestamp": "2024-01-15T10:01:00.001Z"
}
```

**Failure Response:**
```json
{
  "success": false,
  "request_id": "req_12350",
  "order_id": null,
  "data": null,
  "error": {
    "code": "INVALID_INSTRUMENT",
    "message": "Instrument SPX_INVALID not found",
    "details": null
  },
  "timestamp": "2024-01-15T10:01:00.001Z"
}
```

**Notes:**

- Returns top 5 price levels for both bid and ask sides
- Aggregates quantity at each price level
- Empty sides return empty arrays

### 7. Get Team Info

`GET /game/teams/{team_id}`

Get public information about a specific team.

**Request Headers:**

- `X-API-Key`: Required

**Path Parameters:**

- `team_id`: The team ID to query (e.g., "TEAM_123")

**Success Response:**
```json
{
  "success": true,
  "request_id": "req_12351",
  "order_id": null,
  "data": {
    "team_id": "TEAM_123",
    "team_name": "AlphaBot",
    "role": "market_maker",
    "created_at": "2024-01-15T09:00:00Z"
  },
  "error": null,
  "timestamp": "2024-01-15T10:01:00.001Z"
}
```

**Failure Response:**
```json
{
  "success": false,
  "request_id": "req_12351",
  "order_id": null,
  "data": null,
  "error": {
    "code": "TEAM_NOT_FOUND",
    "message": "Team TEAM_999 not found",
    "details": null
  },
  "timestamp": "2024-01-15T10:01:00.001Z"
}
```

**Notes:**

- API key is never included in response for security
- Can query any team's public information

## Error Codes

### Validation Errors

- `INVALID_INSTRUMENT` - Unknown instrument_id
- `INVALID_QUANTITY` - Quantity must be positive integer
- `INVALID_PRICE` - Price must be positive for limit orders
- `INVALID_SIDE` - Must be "buy" or "sell"
- `MISSING_PRICE` - Limit order requires price

### Constraint Errors

- `POSITION_LIMIT_EXCEEDED` - Would exceed role-based limit
- `ORDER_TYPE_NOT_ALLOWED` - Role cannot use this order type
- `RATE_LIMIT_EXCEEDED` - Too many requests per second

### Business Errors

- `ORDER_NOT_FOUND` - Order doesn't exist
- `ORDER_NOT_OWNED` - Security violation
- `ORDER_ALREADY_FILLED` - Cannot cancel filled order
- `ORDER_ALREADY_CANCELLED` - Duplicate cancellation
- `DUPLICATE_TEAM_NAME` - Name already registered
- `TEAM_NOT_FOUND` - Team ID doesn't exist

### System Errors
- `INTERNAL_ERROR` - Server error (rare)
- `SERVICE_UNAVAILABLE` - System overloaded

## Rate Limits

Per-team limits:

- **Submit Order**: 10 per second
- **Cancel Order**: 10 per second
- **Get Orders/Positions**: 100 per second
- **Global**: 1000 requests per second total

Rate limit errors include retry information:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Order rate limit of 10 per second exceeded",
    "details": {
      "limit": 10,
      "window": "1s",
      "retry_after": "0.1s"
    }
  }
}
```

## WebSocket Connection

For real-time updates, connect to the WebSocket endpoint:

```
ws://localhost:8000/ws?api_key=YOUR_API_KEY
```

See [WebSocket API Reference](websocket-api.md) for message types and examples.

## Quick Start Example

```python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "itg_your_api_key_here"
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Submit an order
order = {
    "instrument_id": "SPX_CALL_4500_20240315",
    "side": "buy",
    "quantity": 10,
    "price": 100.0,
    "client_order_id": "my_order_001",
    "request_id": "req_12345"
}

response = requests.post(f"{BASE_URL}/exchange/orders", json=order, headers=headers)
result = response.json()

if result["success"]:
    print(f"Order submitted: {result['order_id']}")
else:
    print(f"Order failed: {result['error']['message']}")

# Check positions
response = requests.get(f"{BASE_URL}/positions", headers=headers)
result = response.json()

if result["success"]:
    positions = result["data"]["positions"]
    for instrument, quantity in positions.items():
        print(f"{instrument}: {quantity}")
```
