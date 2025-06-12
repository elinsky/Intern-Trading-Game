# Batch Matching Explained

## Overview

The Intern Trading Game supports two order matching modes:


1. **Continuous Matching**: Orders match immediately upon submission (traditional exchange behavior)
2. **Batch Matching**: Orders are collected during a window and matched simultaneously

This document explains why batch matching is important for fair gameplay and how our implementation ensures randomized fairness.

## Continuous vs Batch Matching

### Continuous Matching

In continuous matching, orders are processed in the exact sequence they arrive:

```
Time 10:00:00.001: Trader A submits buy @ $100
Time 10:00:00.002: Trader B submits sell @ $100
Result: Immediate match between A and B

Time 10:00:00.003: Trader C submits buy @ $100
Result: No match available (liquidity already consumed)
```

**Advantages:**

- Immediate feedback
- Real-time price discovery
- Simple mental model

**Disadvantages:**

- Speed advantages matter (faster bots win)
- Can discourage liquidity provision
- "Winner takes all" dynamics

### Batch Matching

In batch matching, all orders submitted during a window are collected and matched simultaneously:

```
Window: 10:00:00 - 10:03:00
- Trader A submits buy @ $100
- Trader B submits sell @ $100
- Trader C submits buy @ $100

At 10:03:30: Batch execution
- All orders are considered together
- Orders at same price are randomized
- Crossing orders match against each other in the batch
```

**Advantages:**

- No speed advantages within the batch window
- Fairer for all participants
- Encourages liquidity provision

**Disadvantages:**

- Delayed execution feedback
- More complex implementation

Batch matching ensures:


- All strategies have equal opportunity to react to new prices
- No advantage from submitting orders milliseconds faster
- Fair allocation when multiple orders compete for limited liquidity
- More realistic simulation of opening/closing auctions

## Randomization at Same Price Level

The key innovation in our batch matching is fair randomization:

### Traditional Approach (Time Priority)
```python
# Orders at price $100 in submission order:

1. Trader A (submitted at 0:31)
2. Trader B (submitted at 0:45)
3. Trader C (submitted at 1:30)

# If only 1 sell order available, Trader A always gets it
```

### Our Approach (Random Priority)

```python
# Orders at price $100 are randomized:
# Possible orderings (equal probability):
# 1. A, B, C
# 2. A, C, B
# 3. B, A, C
# 4. B, C, A
# 5. C, A, B
# 6. C, B, A
#
# Each trader has 1/3 chance of being first
```

## Implementation Details

### Critical Batch Matching Behavior

The most important aspect of batch matching is that orders within a batch are matched against each other, not processed sequentially. This is a fundamental difference from continuous matching.

#### Toy Example: Why This Matters

Consider a batch with these orders submitted during the window:
```text
Order 1: Buy 10 @ $102 (Trader A)
Order 2: Buy 10 @ $101 (Trader B)
Order 3: Buy 10 @ $100 (Trader C)
Order 4: Sell 10 @ $101 (Trader D)
```

**Sequential Processing (INCORRECT for batch matching):**
```text
Step 1: Process buy orders by adding to book
  - Add Buy @ $102 to book
  - Add Buy @ $101 to book
  - Add Buy @ $100 to book
  - Book state: Bids at 102, 101, 100

Step 2: Process sell order
  - Sell @ $101 matches against Buy @ $102 (best bid)
  - Result: Trader A (102) trades with Trader D (101) at $101
```

**Batch Matching (CORRECT implementation):**
```python
# Step 1: Collect all orders
buys = [Buy@102, Buy@101, Buy@100]
sells = [Sell@101]

# Step 2: Sort by price (with randomization at same level)
sorted_buys = [Buy@102, Buy@101, Buy@100]  # Descending
sorted_sells = [Sell@101]  # Ascending

# Step 3: Match crossing orders
# Buy@102 crosses with Sell@101? Yes (102 >= 101)
# Match: Trader A trades with Trader D at $101

# Step 4: Remaining unmatched orders go to book
# Book state: Bids at 101, 100
```

In both cases Trader A gets the fill, but the key difference is:

- Sequential: Orders are processed one by one, each seeing the book state left by previous orders
- Batch: All orders are matched simultaneously against each other

#### When The Difference Really Shows

The distinction becomes critical when there are multiple crossing orders:

```text
Batch contains:

- Buy 10 @ $100 (Trader A)
- Buy 10 @ $100 (Trader B)
- Buy 10 @ $100 (Trader C)
- Sell 30 @ $100 (Trader D)
```

**Sequential (INCORRECT):** First buy gets added to book, second buy gets added, third buy gets added, then sell matches against all three in the order they were added.

**Batch (CORRECT):** All three buys are randomized first, then matched against the sell. Each buyer has equal 1/3 chance of being filled first, second, or third.

### Single-Pass Randomization

We use an efficient single-pass sort with random tiebreaker:

```python
def _randomize_same_price_orders(self, orders: List[Order], descending: bool) -> List[Order]:
    return sorted(
        orders,
        key=lambda o: (
            -o.price if descending else o.price,  # Price priority
            random.random()  # Random tiebreaker
        )
    )
```

This approach:

- Maintains strict price priority
- Randomizes only within same price
- O(n log n) complexity
- No intermediate data structures needed

### Order Organization

Orders are organized by instrument during collection:

```python
self.pending_orders: Dict[str, List[Order]] = {
    "SPX_CALL_5000": [order1, order2, ...],
    "SPX_PUT_4900": [order3, order4, ...],
}
```

This pre-organization makes batch execution more efficient.

## Mathematical Guarantees

For orders at the same price level:


- **Fairness**: P(Order A executes before Order B) = 0.5
- **Uniform Distribution**: Each order has equal probability of any position
- **Independence**: Previous batch results don't affect future batches

## Example Scenario

Consider a batch with:

- 3 buy orders at $100 (from traders A, B, C)
- 1 sell order at $100 with quantity for only 1 buyer

Traditional time priority: First submitter always wins
Our batch matching: Each buyer has 33.3% chance of matching

Over many trading sessions, this ensures fair opportunity for all participants.

## Integration with Game Loop

The GameLoop integrates batch matching at the appropriate tick phase:

```python
# At T+3:30 in the tick cycle
if self.current_phase == TickPhase.BATCH_MATCHING:
    results = self.exchange.execute_batch()
    # Process results, update positions, notify traders
```

## Configuration

To use batch matching:

```python
from intern_trading_game.exchange import ExchangeVenue, BatchMatchingEngine

# Create exchange with batch matching
exchange = ExchangeVenue(matching_engine=BatchMatchingEngine())

# Orders submitted will be pending
result = exchange.submit_order(order)
assert result.status == "pending"

# Execute batch at designated time
batch_results = exchange.execute_batch()
```

## Best Practices

1. **Strategy Design**: Strategies should not assume immediate fills in batch mode
2. **Order Submission**: Submit all desired orders before the window closes
3. **Result Processing**: Handle batch results appropriately after execution
4. **Testing**: Test strategies in both continuous and batch modes
