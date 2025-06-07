# Execution Rules

## Order Matching Engine

### Price-Time Priority

The exchange uses a standard price-time priority algorithm:


1. **Price Priority**: Best prices execute first

   - Highest bids match before lower bids
   - Lowest asks match before higher asks

2. **Time Priority**: Among same-priced orders

   - Earlier orders execute first
   - Microsecond timestamp precision
   - No queue jumping allowed

### Matching Process

```
For each instrument:

1. Sort buy orders by price (descending) then time (ascending)
2. Sort sell orders by price (ascending) then time (ascending)
3. Match crossing orders until no more crosses exist
4. Remaining orders rest in book
```

## Trade Execution

### Execution Scenarios

**Scenario 1: Immediate Fill**
```
Book: Ask @ 25.50
Order: Buy 10 @ 25.60 (market or aggressive limit)
Result: Filled 10 @ 25.50
```

**Scenario 2: Partial Fill**
```
Book: Ask 5 @ 25.50, Ask 10 @ 25.55
Order: Buy 10 @ 25.55
Result: Filled 5 @ 25.50, 5 @ 25.55
```

**Scenario 3: Resting Order**
```
Book: Ask @ 25.50
Order: Buy 10 @ 25.40
Result: Order rests as best bid
```

### Fill Allocation

When multiple orders exist at the same price:

- Strict time priority (no pro-rata)
- Full fills before partial fills
- Minimum fill size: 1 contract

## Fee Calculation

### Maker vs Taker

**Maker**: Order adds liquidity (rests in book)
**Taker**: Order removes liquidity (executes immediately)

### Fee Examples

**Market Maker Buying**:
```
Scenario: Post bid @ 25.40, later filled
Contracts: 100
Maker rebate: +$0.02 per contract
Total: +$2.00 credit
```

**Hedge Fund Aggressive Buy**:
```
Scenario: Buy 50 @ market, fills @ 25.50
Contracts: 50
Taker fee: -$0.02 per contract
Total: -$1.00 charge
```

## Order Lifecycle

### 1. Submission Phase

- Order received by exchange
- Timestamp assigned
- Initial validation performed

### 2. Validation Checks

```python
def validate_order(order, role, current_position):
    # Check role permissions

    if order.type == "QUOTE" and role != "MARKET_MAKER":
        return "REJECT: Only market makers can quote"

    # Check position limits

    new_position = current_position + order.quantity
    if abs(new_position) > role.position_limit:
        return "REJECT: Would exceed position limit"

    # Check price validity

    if order.price <= 0:
        return "REJECT: Invalid price"

    return "ACCEPT"
```

### 3. Book Interaction

- Check for immediate execution
- Place in book if not crossing
- Update market data feed

### 4. Execution Reports

Execution reports are sent in real-time via WebSocket:

```json
{
  "order_id": "ORD-12345",
  "status": "FILLED",
  "filled_quantity": 50,
  "average_price": 25.52,
  "fee": -1.00,
  "liquidity_type": "taker",
  "timestamp": "2024-01-15T10:30:00.123Z"
}
```

The `liquidity_type` field indicates whether the order was a maker (provided liquidity) or taker (removed liquidity), which affects fee calculations.

## Special Situations

### Self-Trading

- Allowed (you can trade with yourself)
- Still incur fees

### Order Rejection

Common rejection reasons:

- Position limit exceeded
- Invalid instrument

## Priority Examples

### Example 1: Simple Match

```
Bids:

- 25.45 @ 10:30:00.100 (Trader A, 50 lots)
- 25.45 @ 10:30:00.200 (Trader B, 30 lots)
- 25.40 @ 10:30:00.050 (Trader C, 100 lots)

New Sell Order: 60 @ 25.40

Execution:

1. Fill 50 @ 25.45 with Trader A
2. Fill 10 @ 25.45 with Trader B
3. Trader B has 20 remaining
4. Trader C's order untouched
```

### Example 2: Quote vs Limit

```
Market Maker Quote: Bid 25.40 / Ask 25.60
Hedge Fund Limit: Buy 100 @ 25.60

Result:

- HF order takes liquidity, fills @ 25.60
- HF pays taker fee
- MM earns maker rebate
```

## Next Steps

- Review [Order Types](order-types.md) available
- Understand [Trading Constraints](constraints.md)
- Practice in test environment
- Develop execution algorithm
