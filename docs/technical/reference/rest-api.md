# REST API Reference

Complete reference for the Intern Trading Game REST API.

## Base URL

```
http://localhost:8000
```

## Authentication

All endpoints except `/` and `/auth/register` require authentication via API key.

Include your API key in the `X-API-Key` header:

```
X-API-Key: itg_your_api_key_here
```

## Endpoints

### System

#### GET /

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "Intern Trading Game API",
  "threads": {
    "validator": true,
    "matching": true,
    "publisher": true
  }
}
```

### Authentication

#### POST /auth/register

Register a new trading team.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| team_name | string | Yes | Display name (1-50 chars) |
| role | string | Yes | Trading role (currently only "market_maker") |

**Response:** `TeamInfo`
```json
{
  "team_id": "TEAM_001",
  "team_name": "AlphaBot",
  "role": "market_maker",
  "api_key": "itg_AbCdEfGhIjKlMnOpQrStUvWxYz...",
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Errors:**
- `400`: Invalid role specified

### Trading

#### POST /orders

Submit a new order to the exchange.

**Headers:**

- `X-API-Key`: Required

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| instrument_id | string | Yes | Instrument to trade |
| order_type | string | Yes | "limit" or "market" |
| side | string | Yes | "buy" or "sell" |
| quantity | integer | Yes | Number of contracts (> 0) |
| price | number | Conditional | Required for limit orders |

**Response:** `OrderResponse`

```json
{
  "order_id": "ORD_123456",
  "status": "accepted",
  "timestamp": "2024-01-15T10:00:01Z",
  "filled_quantity": 10,
  "average_price": 25.50,
  "error_code": null,
  "error_message": null
}
```

**Status Values:**

- `accepted`: Order accepted, may be resting in book
- `filled`: Order completely filled
- `rejected`: Order rejected by validator
- `error`: Exchange error

**Errors:**

- `400`: Invalid parameters
- `401`: Missing/invalid API key
- `504`: Processing timeout

### Market Data

#### GET /positions/{team_id}

Get current positions for a team.

**Headers:**

- `X-API-Key`: Required

**Path Parameters:**

- `team_id`: Your team ID (e.g., "TEAM_001")

**Response:** `PositionResponse`

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

**Errors:**

- `401`: Missing/invalid API key
- `403`: Cannot query other teams' positions

## Data Models

### OrderRequest

```typescript
{
  instrument_id: string     // e.g., "SPX_4500_CALL"
  order_type: string        // "limit" | "market"
  side: string              // "buy" | "sell"
  quantity: number          // > 0
  price?: number            // Required for limit orders
}
```

### OrderResponse
```typescript
{
  order_id: string
  status: string            // "accepted" | "filled" | "rejected" | "error"
  timestamp: datetime
  filled_quantity: number   // Default: 0
  average_price?: number    // Present if filled > 0
  error_code?: string       // Present if rejected
  error_message?: string    // Present if rejected
}
```

### TeamInfo
```typescript
{
  team_id: string           // e.g., "TEAM_001"
  team_name: string
  role: string              // "market_maker"
  api_key: string           // "itg_..."
  created_at: datetime
}
```

### PositionResponse
```typescript
{
  team_id: string
  positions: {
    [instrument_id: string]: number  // Positive = long, negative = short
  }
  last_updated: datetime
}
```

### ErrorResponse
```typescript
{
  error: string
  detail?: string
  timestamp: datetime
}
```

## Queue Architecture

The API uses a multi-threaded queue architecture:

1. **Order Queue**: API → Validator thread
2. **Validation Queue**: Validator → Matching thread
3. **Match Queue**: For matching engine
4. **Trade Queue**: Matching → Publisher thread

This ensures:
- Non-blocking order submission
- Thread-safe processing
- Consistent state updates

## Constraints

### Market Maker Role

Current constraints for market makers:
- **Position Limit**: ±50 contracts per instrument
- **Order Types**: limit, market
- **Instruments**: SPX_4500_CALL, SPX_4500_PUT

## Examples

### cURL

```bash
# Register team
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"team_name": "TestBot", "role": "market_maker"}'

# Submit order
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-API-Key: itg_your_key" \
  -d '{
    "instrument_id": "SPX_4500_CALL",
    "order_type": "limit",
    "side": "buy",
    "quantity": 10,
    "price": 25.50
  }'

# Get positions
curl http://localhost:8000/positions/TEAM_001 \
  -H "X-API-Key: itg_your_key"
```

### Python

```python
import requests

# Register
resp = requests.post(
    "http://localhost:8000/auth/register",
    json={"team_name": "PyBot", "role": "market_maker"}
)
team = resp.json()

# Submit order
headers = {"X-API-Key": team["api_key"]}
resp = requests.post(
    "http://localhost:8000/orders",
    headers=headers,
    json={
        "instrument_id": "SPX_4500_CALL",
        "order_type": "limit",
        "side": "buy",
        "quantity": 10,
        "price": 25.50
    }
)
print(resp.json())
```
