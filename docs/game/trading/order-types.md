# Order Types

## Available Order Types

### Limit Orders

The most common order type, allowing precise price control.

**Characteristics:**
- Specify exact price (or better)
- Rest in order book if not immediately fillable
- Can partially fill
- Expire at tick end if unfilled

**Syntax Example:**
```json
{
  "type": "LIMIT",
  "instrument": "SPX_4400_CALL_2024-02-15",
  "side": "BUY",
  "quantity": 10,
  "price": 25.50
}
```

**Use Cases:**
- Providing liquidity (earn maker rebate)
- Precise entry/exit points
- Building positions gradually

### Market Orders

Execute immediately at best available price.

**Characteristics:**
- No price specification
- Immediate execution (or reject)
- Take liquidity from book
- May experience slippage

**Syntax Example:**
```json
{
  "type": "MARKET",
  "instrument": "SPY_440_PUT_2024-02-15",
  "side": "SELL",
  "quantity": 20
}
```

**Use Cases:**
- Urgent position changes
- Capturing signals quickly
- Risk management (stop-loss)

### Quotes (Market Makers Only)

Simultaneous two-sided markets providing both bid and ask.

**Characteristics:**
- Must specify both bid and ask
- Counts as two orders for limits
- Can be one-click cancelled
- Earn enhanced maker rebates

**Syntax Example:**
```json
{
  "type": "QUOTE",
  "instrument": "SPX_4400_CALL_2024-02-15",
  "bid_price": 25.40,
  "bid_quantity": 50,
  "ask_price": 25.60,
  "ask_quantity": 50
}
```

**Requirements:**
- Market Maker role only
- Minimum 80% quote uptime
- Reasonable spread widths

## Order Attributes

### Required Fields

| Field      | Description    | Valid Values               |
| ---------- | -------------- | -------------------------- |
| type       | Order type     | LIMIT, MARKET, QUOTE       |
| instrument | Trading symbol | Valid option/underlying    |
| side       | Direction      | BUY, SELL (not for quotes) |
| quantity   | Size           | 1-1000 (role dependent)    |

### Optional Fields

| Field       | Description    | Default            |
| ----------- | -------------- | ------------------ |
| price       | Limit price    | Required for LIMIT |
| client_id   | Your reference | None               |
| strategy_id | Strategy tag   | None               |

## Order Constraints

### Size Limits by Role

| Role           | Min Size | Max Size | Max Orders/Tick |
| -------------- | -------- | -------- | --------------- |
| Market Maker   | 1        | 1000     | 100             |
| Hedge Fund     | 1        | 500      | 50              |
| Arbitrage Desk | 1        | 500      | 75              |
| Retail         | 1        | 100      | 5               |

### Price Constraints

- Minimum tick: $0.01
- Must be positive
- Options: Cannot trade below intrinsic value
- Reasonable limits enforced

### Quote Constraints (Market Makers)

- Maximum spread: 10% of mid-price
- Minimum size: 10 contracts per side
- Must maintain 80% uptime
- Both sides must be valid

## Order Lifecycle

### 1. Submission

```
Bot → API → Validation → Order Book
```

### 2. Validation Checks

- Size limits
- Price validity
- Position limits
- Risk checks

### 3. Book Placement

- Immediate execution if crossable
- Rest in book if not
- Price-time priority

### 4. Execution

- Full or partial fills
- Fee calculation
- Position update
- P&L impact

### 5. Reporting

- Fill confirmation
- Remaining quantity
- Average price
- Fees charged

## Execution Priority

### Price-Time Priority

1. **Price Priority**: Better prices execute first
   - Higher bids ranked first
   - Lower asks ranked first

2. **Time Priority**: Same price → earlier first
   - Microsecond timestamp precision
   - No queue jumping

## Order Management

### No Modifications

- Cannot modify existing orders
- Must cancel and replace
- Cancellations immediate
- No cancel-replace atomic operation

### Bulk Operations

- Submit multiple orders per message
- Cancel all orders by instrument
- Cancel all orders globally
- Useful for risk management

### Order Tracking

Each order receives:

- Unique order ID
- Timestamp
- Status updates
- Fill reports

## Next Steps

- Understand [Trading Constraints](constraints.md)
- Review [Execution Rules](execution-rules.md)
- Learn [Signal Access](signals-access.md) by role
