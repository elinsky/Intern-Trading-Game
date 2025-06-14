# API Design Principles

This document explains the design philosophy behind the Intern Trading Game REST API, documenting our minimalist approach and the business logic for each operation.

## Core Philosophy

The API follows a **minimalist design** principle: provide exactly what trading bots need, nothing more.

### Design Goals

1. **Essential Operations Only** - Just 5 endpoints for everything a bot needs
2. **Single Responsibility** - Each endpoint does ONE thing well
3. **Fast and Predictable** - Validation-only responses in ~1ms
4. **Stateless** - No sessions, no complex state management
5. **Consistent Structure** - Every response uses the same format

### What We DON'T Include (And Why)

- **No order status endpoint** - Use WebSocket for real-time updates
- **No order history** - Focus on current state, not past trades
- **No market data endpoints** - WebSocket is better for streaming data
- **No modify order** - Cancel and replace is clearer and safer
- **No complex order types** - Market and limit orders cover 99% of needs
- **No batch operations** - Simple is better than clever

## Universal Response Format

**Every** API response uses the same `ApiResponse` structure:

```typescript
interface ApiResponse {
  success: boolean;              // Did the request succeed?
  request_id: string;            // Echo of client's request ID
  order_id?: string;             // For order operations (when success=true)
  data?: object;                 // For query operations (when success=true)
  error?: ApiError;              // Present when success=false
  timestamp: string;             // ISO 8601 server timestamp
}

interface ApiError {
  code: string;                  // Machine-readable error code
  message: string;               // Human-readable explanation
  details?: object;              // Additional context (optional)
}
```

This means bots only need ONE response parser:

```python
def handle_response(response):
    if response.success:
        if response.order_id:
            # Order operation succeeded
            track_order(response.order_id)
        elif response.data:
            # Query operation succeeded
            process_data(response.data)
    else:
        # Any operation failed
        handle_error(response.error.code, response.error.message)
```

## The 5 Core Operations

Every trading bot needs exactly 5 operations to function:

### 1. Submit Order - `POST /orders`

**Purpose**: Place a new order to buy or sell an option

**Request**:
```json
{
  "instrument_id": "SPX_CALL_4500_20240315",
  "side": "buy",
  "quantity": 10,
  "price": 100.0,
  "client_order_id": "my_order_001",
  "request_id": "req_12345"
}
```

**Success Response**:
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

**Failure Response**:
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

**Business Logic**:

1. Validate parameters (instrument exists, quantity > 0, etc.)
2. Check role-based constraints (position limits, order types)
3. Check rate limits (orders per second)
4. If valid: Generate order_id, queue for matching, return success
5. If invalid: Return specific error immediately

**Key Points**:

- Response in ~1ms (validation only)
- Execution details via WebSocket later
- `order_id` is exchange-generated
- `client_order_id` is optional bot reference

### 2. Cancel Order - `DELETE /orders/{order_id}`

**Purpose**: Cancel a resting order in the order book

**Success Response**:
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

**Failure Response**:
```json
{
  "success": false,
  "request_id": "req_12346",
  "order_id": null,
  "data": null,
  "error": {
    "code": "CANCEL_FAILED",
    "message": "Order not found",
    "details": null
  },
  "timestamp": "2024-01-15T10:00:01.001Z"
}
```

**Business Logic**:

1. Verify order exists and caller owns it
2. Check if cancellable (not filled)
3. If yes: Remove from book, return success
4. If no: Return generic error (for security, don't reveal specific reasons)

**Common Errors**:

- `CANCEL_FAILED` - Order not found (covers all cancellation failures for security)

### 3. Get Open Orders - `GET /orders`

**Purpose**: Retrieve all resting orders for the authenticated team

**Success Response**:
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
        "client_order_id": "my_order_002",
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

**Business Logic**:

1. Authenticate caller
2. Get all orders with status "open" or "partially_filled"
3. Sort by submission time (oldest first)
4. Return full snapshot

**Key Points**:

- Always returns array (empty if no orders)
- Includes partially filled orders
- Shows remaining quantity
- No pagination needed

### 4. Get Positions - `GET /positions`

**Purpose**: Get current net position for each instrument

**Success Response**:
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

**Business Logic**:

1. Authenticate caller
2. Get current positions
3. Return net position per instrument
4. Include zero positions for traded instruments

**Key Points**:

- Positive = long, negative = short
- Real-time snapshot
- Flat map structure
- No complex nesting

### 5. Register Team - `POST /auth/register`

**Purpose**: One-time registration to get API credentials

**Request**:
```json
{
  "team_name": "AlphaBot",
  "role": "market_maker"
}
```

**Success Response**:
```json
{
  "success": true,
  "request_id": "req_12349",
  "order_id": null,
  "data": {
    "team_id": "TEAM_123",
    "team_name": "AlphaBot",
    "role": "market_maker",
    "api_key": "itg_abc123xyz789",
    "created_at": "2024-01-15T10:00:00Z"
  },
  "error": null,
  "timestamp": "2024-01-15T10:00:00.001Z"
}
```

**Failure Response**:
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

**Business Logic**:

1. Validate team name (unique, appropriate)
2. Validate role selection
3. Generate team_id and API key
4. Store registration
5. Return credentials ONCE

**Security Notes**:

- No auth required (public endpoint)
- API key shown only at registration
- No retrieval endpoint

## Error Code Reference

### Validation Errors

- `INVALID_INSTRUMENT` - Unknown instrument_id
- `INVALID_QUANTITY` - Quantity <= 0 or not integer
- `INVALID_PRICE` - Price <= 0 for limit order
- `INVALID_SIDE` - Not "buy" or "sell"
- `MISSING_PRICE` - Limit order without price

### Constraint Errors

- `POSITION_LIMIT_EXCEEDED` - Would exceed role limit
- `ORDER_TYPE_NOT_ALLOWED` - Role can't use this type
- `RATE_LIMIT_EXCEEDED` - Too many requests

### Business Errors

- `CANCEL_FAILED` - Order cancellation failed (generic for security)

### System Errors

- `INTERNAL_ERROR` - Server problem
- `SERVICE_UNAVAILABLE` - System overloaded

## Rate Limiting

Limits per team:

- **Orders**: 10 per second
- **Cancels**: 10 per second  
- **Queries**: 100 per second

Exceeded limits return:
```json
{
  "success": false,
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

## Best Practices

### 1. Always Handle Both Cases
```python
response = api.call_any_endpoint()
if response.success:
    # Handle success
    if response.order_id:
        track_order(response.order_id)
    elif response.data:
        process_data(response.data)
else:
    # Handle failure
    handle_error(response.error)
```

### 2. Use Request IDs for Correlation
```python
request_id = f"{strategy}_{timestamp}_{random()}"
# Include in request, match in response
```

### 3. Implement Exponential Backoff
```python
if error.code == "RATE_LIMIT_EXCEEDED":
    wait_time = error.details.get("retry_after", 1.0)
    await asyncio.sleep(wait_time * (2 ** retry_count))
```

### 4. Sync State on Connect
```python
# On startup or reconnect
positions = await api.get_positions()
open_orders = await api.get_open_orders()
reconcile_internal_state(positions.data, open_orders.data)
```

## Summary

This API design achieves:

- **One response format** - Simplifies client code
- **Five endpoints** - Everything a bot needs
- **Fast responses** - ~1ms validation only
- **Clear errors** - Actionable error codes

The key insight: consistency and simplicity trump features. By using the same response structure everywhere, bots can focus on trading logic instead of API parsing.