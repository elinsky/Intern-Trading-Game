# Trading Bot Order Scenarios: Client Experience

## Overview

This document describes the order submission experience from a trading bot's perspective. It covers the different scenarios a bot encounters when submitting orders via the REST API and the corresponding responses they receive.

Trading bots interact with the system through a simple request-response pattern: submit an order, get a definitive result. The complexity of internal processing is hidden behind a clean API contract.

## Core API Pattern

**Basic Flow:**
1. Bot submits order via `POST /exchange/orders`
2. API blocks for 10-500ms while order processes
3. Bot receives **one final response** with definitive result
4. Bot optionally receives follow-up WebSocket notifications

**No Intermediate Statuses:** Bots never see "pending" or "processing" responses. They get the final result or a timeout.

## Standard Response Structure

All responses follow the **ApiResponse** format:

**Success Response:**
```json
{
  "success": true,
  "request_id": "req_1234567890",
  "order_id": "ORD_12345",
  "data": {
    // OrderResponse details here
  },
  "error": null,
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "request_id": "req_1234567890",
  "order_id": null,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {
      // Additional context
    }
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

## Order Submission Scenarios

### Scenario 1: Market Order - Immediate Fill

**Bot Action:**
```json
POST /exchange/orders
{
  "instrument_id": "SPX_4500_CALL",
  "order_type": "market",
  "side": "buy",
  "quantity": 10
}
```

**Bot Receives (within 50ms):**
```json
HTTP 200 OK
{
  "success": true,
  "request_id": "req_1234567890",
  "order_id": "ORD_12345",
  "data": {
    "order_id": "ORD_12345",
    "status": "filled",
    "timestamp": "2024-01-15T10:30:45.123Z",
    "filled_quantity": 10,
    "average_price": 128.50,
    "fees": -0.50,
    "liquidity_type": "taker"
  },
  "error": null,
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

**Follow-up WebSocket (optional):**
```json
{
  "type": "execution_report",
  "order_id": "ORD_12345",
  "fills": [
    {"price": 128.50, "quantity": 10, "timestamp": "2024-01-15T10:30:45.120Z"}
  ]
}
```

**Bot Experience:** Immediate confirmation of execution with complete fill details.

---

### Scenario 2: Limit Order - Resting in Book

**Bot Action:**
```json
POST /exchange/orders
{
  "instrument_id": "SPX_4500_CALL",
  "order_type": "limit",
  "side": "buy",
  "quantity": 20,
  "price": 127.00
}
```

**Bot Receives (within 100ms):**
```json
HTTP 200 OK
{
  "success": true,
  "request_id": "req_1234567891",
  "order_id": "ORD_12346",
  "data": {
    "order_id": "ORD_12346",
    "status": "new",
    "timestamp": "2024-01-15T10:30:45.200Z",
    "filled_quantity": 0,
    "average_price": null,
    "fees": 0.0,
    "liquidity_type": null
  },
  "error": null,
  "timestamp": "2024-01-15T10:30:45.200Z"
}
```

**Later WebSocket (when order fills):**
```json
{
  "type": "execution_report",
  "order_id": "ORD_12346",
  "fills": [
    {"price": 127.00, "quantity": 5, "timestamp": "2024-01-15T10:35:12.456Z"}
  ],
  "remaining_quantity": 15
}
```

**Bot Experience:** Immediate confirmation that order is working, with later notifications as fills occur.

---

### Scenario 3: Limit Order - Partial Immediate Fill

**Bot Action:**
```json
POST /exchange/orders
{
  "instrument_id": "SPX_4500_CALL",
  "order_type": "limit",
  "side": "sell",
  "quantity": 50,
  "price": 128.00
}
```

**Bot Receives (within 150ms):**
```json
HTTP 200 OK
{
  "success": true,
  "request_id": "req_1234567892",
  "order_id": "ORD_12347",
  "data": {
    "order_id": "ORD_12347",
    "status": "partially_filled",
    "timestamp": "2024-01-15T10:30:45.350Z",
    "filled_quantity": 20,
    "average_price": 128.00,
    "fees": 0.40,
    "liquidity_type": "mixed"
  },
  "error": null,
  "timestamp": "2024-01-15T10:30:45.350Z"
}
```

**Bot Experience:** Immediate feedback showing partial execution and remaining working quantity.

---

### Scenario 4: Order Rejection - Validation Failure

**Bot Action:**
```json
POST /exchange/orders
{
  "instrument_id": "SPX_4500_CALL",
  "order_type": "limit",
  "side": "buy",
  "quantity": 100,
  "price": 130.00
}
```

**Bot Receives (within 25ms):**
```json
HTTP 400 Bad Request
{
  "success": false,
  "request_id": "req_1234567893",
  "order_id": null,
  "data": null,
  "error": {
    "code": "POSITION_LIMIT_EXCEEDED",
    "message": "Order would exceed position limit of ±50",
    "details": {
      "current_position": 45,
      "order_quantity": 100,
      "position_limit": 50
    }
  },
  "timestamp": "2024-01-15T10:30:45.025Z"
}
```

**Bot Experience:** Fast rejection with clear explanation of constraint violation.

---

### Scenario 5: Order Rejection - Invalid Instrument

**Bot Action:**
```json
POST /exchange/orders
{
  "instrument_id": "INVALID_SYMBOL",
  "order_type": "market",
  "side": "buy",
  "quantity": 10
}
```

**Bot Receives (within 10ms):**
```json
HTTP 400 Bad Request
{
  "success": false,
  "request_id": "req_1234567894",
  "order_id": null,
  "data": null,
  "error": {
    "code": "INVALID_INSTRUMENT",
    "message": "Unknown instrument: INVALID_SYMBOL",
    "details": {
      "requested_instrument": "INVALID_SYMBOL",
      "available_instruments": ["SPX_4500_CALL", "SPX_4500_PUT"]
    }
  },
  "timestamp": "2024-01-15T10:30:45.010Z"
}
```

**Bot Experience:** Very fast rejection for basic validation errors.

---

### Scenario 6: System Timeout

**Bot Action:**
```json
POST /exchange/orders
{
  "instrument_id": "SPX_4500_CALL",
  "order_type": "market",
  "side": "buy",
  "quantity": 10
}
```

**Bot Receives (after 5000ms):**
```json
HTTP 504 Gateway Timeout
{
  "success": false,
  "request_id": "req_1234567895",
  "order_id": null,
  "data": null,
  "error": {
    "code": "PROCESSING_TIMEOUT",
    "message": "Order processing exceeded time limit",
    "details": {
      "timeout_ms": 5000,
      "stage": "matching"
    }
  },
  "timestamp": "2024-01-15T10:30:50.000Z"
}
```

**Bot Experience:** Clear timeout indication when system is overloaded.

---

### Scenario 7: System Error

**Bot Action:**
```json
POST /exchange/orders
{
  "instrument_id": "SPX_4500_CALL",
  "order_type": "market",
  "side": "buy",
  "quantity": 10
}
```

**Bot Receives (within 200ms):**
```json
HTTP 500 Internal Server Error
{
  "success": false,
  "request_id": "req_1234567896",
  "order_id": null,
  "data": null,
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Internal system error during order processing",
    "details": {
      "support_reference": "ERR_20240115_103045_789",
      "stage": "settlement"
    }
  },
  "timestamp": "2024-01-15T10:30:45.200Z"
}
```

**Bot Experience:** Clear system error with reference for support escalation.

## Order Cancellation Scenarios

### Successful Cancellation

**Bot Action:**
```http
DELETE /exchange/orders/ORD_12346
```

**Bot Receives:**
```json
HTTP 200 OK
{
  "success": true,
  "request_id": "req_1234567897",
  "order_id": "ORD_12346",
  "data": {
    "order_id": "ORD_12346",
    "status": "cancelled",
    "timestamp": "2024-01-15T10:32:15.123Z",
    "filled_quantity": 5,
    "average_price": 127.00,
    "fees": -0.10,
    "liquidity_type": "maker"
  },
  "error": null,
  "timestamp": "2024-01-15T10:32:15.123Z"
}
```

### Failed Cancellation - Already Filled

**Bot Action:**
```http
DELETE /exchange/orders/ORD_12345
```

**Bot Receives:**
```json
HTTP 400 Bad Request
{
  "success": false,
  "request_id": "req_1234567898",
  "order_id": "ORD_12345",
  "data": null,
  "error": {
    "code": "CANCEL_FAILED",
    "message": "Order not found or already filled",
    "details": {
      "order_id": "ORD_12345",
      "reason": "already_filled"
    }
  },
  "timestamp": "2024-01-15T10:32:15.456Z"
}
```

## WebSocket Integration

**Connection Pattern:**
```javascript
// Connect with API key
const ws = new WebSocket('ws://localhost:8000/ws?api_key=your_key');

// Receive real-time updates
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch(message.type) {
    case 'execution_report':
      handleFill(message);
      break;
    case 'position_snapshot':
      updatePositions(message);
      break;
    case 'order_cancel_ack':
      handleCancellation(message);
      break;
  }
};
```

**Message Types Bots Receive:**
- `execution_report`: Individual trade fills
- `position_snapshot`: Current position summary
- `order_cancel_ack`: Cancellation confirmations
- `order_cancel_reject`: Cancellation failures

## Response Time Expectations

**Normal Operations:**
- Simple validation errors: < 25ms
- Market orders: 25-100ms
- Limit orders: 50-200ms
- Complex orders: 100-500ms

**Degraded Performance:**
- High load: up to 2 seconds
- System stress: up to 5 seconds (then timeout)

**SLA Guarantees:**
- 95% of orders processed within 500ms
- 99% of orders processed within 2 seconds
- 100% of requests get response within 5 seconds (or timeout)

## Bot Implementation Patterns

### Synchronous Pattern (Recommended)
```python
# Submit order and wait for definitive result
response = requests.post('/exchange/orders', json=order_data)
result = response.json()

if result['success']:
    order_data = result['data']
    handle_order_accepted(order_data)
else:
    error_info = result['error']
    handle_order_rejected(error_info)
```

### Error Handling Pattern
```python
def submit_order_with_retry(order_data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post('/exchange/orders', json=order_data)
            result = response.json()

            # Success or client error (400s) - don't retry
            if result['success'] or response.status_code < 500:
                return result

            # Server error (500s) - retry with backoff
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

        except requests.RequestException:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    raise OrderSubmissionFailed("Max retries exceeded")
```

### Response Processing Pattern
```python
def process_order_response(response):
    """Process order response with proper error handling."""
    result = response.json()

    if not result['success']:
        error = result['error']
        raise OrderError(
            code=error['code'],
            message=error['message'],
            details=error.get('details', {})
        )

    order_data = result['data']
    return OrderResult(
        order_id=result['order_id'],
        status=order_data['status'],
        filled_quantity=order_data['filled_quantity'],
        average_price=order_data['average_price'],
        fees=order_data['fees']
    )
```

## Summary

From a trading bot's perspective, order submission follows a consistent pattern:
1. **Submit order** via REST API with proper request format
2. **Get ApiResponse** wrapper with success/failure indication
3. **Extract order details** from `data` field on success
4. **Handle errors** from `error` field on failure
5. **Optionally listen** for WebSocket updates

The unified ApiResponse structure ensures consistent error handling and makes bot implementation straightforward and reliable.
