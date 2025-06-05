# Explaining Order Matching in the Intern Trading Game

This document explains the order matching algorithm used in the Intern Trading Game exchange system.

## Overview

The order matching engine is the core of any trading system. It's responsible for:


1. Maintaining the order book (the collection of all outstanding buy and sell orders)
2. Matching incoming orders against existing orders
3. Generating trades when orders match
4. Ensuring price-time priority is respected

## Price-Time Priority

The Intern Trading Game exchange uses a **price-time priority** matching algorithm, which is the standard for most financial exchanges. This means:


1. **Price Priority**: Better prices get matched first
   - For buy orders (bids): Higher prices have priority
   - For sell orders (asks): Lower prices have priority

2. **Time Priority**: When prices are the same, earlier orders get matched first
   - First-in, first-out (FIFO) at each price level

## Order Book Structure

The order book for each instrument is organized into price levels:

```
                  Quantity
                     ▲
                     │
      BIDS           │           ASKS
(Buy Orders)         │      (Sell Orders)
                     │
 10 @ $5.25 ◄────────┼────────► 15 @ $5.30
  5 @ $5.20 ◄────────┼────────► 20 @ $5.35
 15 @ $5.15 ◄────────┼────────► 10 @ $5.40
                     │
                     │
                     └────────────────► Price
```

- The **bid side** contains buy orders, sorted by price in descending order (highest first)
- The **ask side** contains sell orders, sorted by price in ascending order (lowest first)
- At each price level, orders are sorted by time (oldest first)

## Matching Process

When a new order arrives, the matching process follows these steps:

### 1. Determine the Opposite Side

- If the new order is a buy order, it will try to match against the ask side
- If the new order is a sell order, it will try to match against the bid side

### 2. Check for Matching Prices

For a limit order to match:

- A buy order's price must be >= the best ask price
- A sell order's price must be <= the best bid price

Market orders always match at the best available price.

### 3. Execute Trades

When a match is found:

- Create a trade at the price of the resting order
- Reduce the quantities of both orders
- If the resting order is fully filled, remove it from the book
- Continue matching until the new order is fully filled or no more matches are possible

### 4. Add Remaining Quantity to the Book

If the new order is not fully filled and it's a limit order, add the remaining quantity to the appropriate side of the book.

## Example: Order Matching Process

Let's walk through an example of the matching process:


**Current Order Book:**
- Best Bid: $5.25 (10 contracts)
- Best Ask: $5.30 (15 contracts)

**Scenario 1: Incoming Limit Buy Order**

A new limit buy order arrives: Buy 20 @ $5.32

1. This order's price ($5.32) is higher than the best ask ($5.30), so it will match
2. A trade is created for 15 contracts at $5.30 (the price of the resting ask order)
3. The resting ask order is fully filled and removed from the book
4. The incoming buy order has 5 contracts remaining
5. There are no more ask orders at or below $5.32
6. The remaining 5 contracts are added to the bid side at $5.32

**Scenario 2: Incoming Market Sell Order**

A new market sell order arrives: Sell 15 (no price specified)

1. This is a market order, so it will match at the best available bid price
2. The best bid is $5.32 for 5 contracts
3. A trade is created for 5 contracts at $5.32
4. The next best bid is $5.25 for 10 contracts
5. A second trade is created for 10 contracts at $5.25
6. The market sell order is now fully filled

## Implementation Details

The matching algorithm is implemented in the `OrderBook._match_order` method. Here's a simplified version of the algorithm:

```python
def _match_order(self, order):
    trades = []

    # Determine which side of the book to match against
    opposite_side = self.asks if order.is_buy else self.bids

    # Keep matching until the order is filled or no more matches are possible
    while not order.is_filled and opposite_side:
        best_price_level = opposite_side[0]

        # For limit orders, check if the price is acceptable
        if order.is_limit_order:
            if (order.is_buy and best_price_level.price > order.price) or \
               (order.is_sell and best_price_level.price < order.price):
                break  # No more acceptable prices

        # Get the first order at this price level
        matching_order = best_price_level.orders[0]

        # Determine the fill quantity
        fill_qty = min(order.remaining_quantity, matching_order.remaining_quantity)

        # Create a trade
        trade = Trade(
            instrument_id=self.instrument_id,
            buyer_id=order.trader_id if order.is_buy else matching_order.trader_id,
            seller_id=matching_order.trader_id if order.is_buy else order.trader_id,
            price=best_price_level.price,
            quantity=fill_qty,
            buyer_order_id=order.order_id if order.is_buy else matching_order.order_id,
            seller_order_id=matching_order.order_id if order.is_buy else order.order_id,
        )

        trades.append(trade)

        # Update the orders
        order.fill(fill_qty)
        matching_order.fill(fill_qty)

        # If the matching order is filled, remove it
        if matching_order.is_filled:
            best_price_level.remove_order(matching_order.order_id)

            # If the price level is empty, remove it
            if best_price_level.is_empty():
                opposite_side.pop(0)

    return trades
```

## Edge Cases and Considerations

### 1. Self-Trading Prevention

In a real exchange, traders are typically prevented from matching against their own orders. This is not currently implemented in the Intern Trading Game but could be added as an enhancement.

### 2. Pro-Rata Matching

Some exchanges use pro-rata matching instead of or in addition to time priority. In pro-rata matching, fills are allocated proportionally to the size of the resting orders at a given price level.

### 3. Iceberg/Hidden Orders

Many exchanges support iceberg orders (where only a portion of the total quantity is visible) or completely hidden orders. These are not currently implemented in the Intern Trading Game.

### 4. Market Order Protections

In real exchanges, market orders often have protections to prevent them from executing at extreme prices. The Intern Trading Game currently allows market orders to match at any price, which could be improved.

## TradingContext

The order matching algorithm operates within the following trading context:


- European-style options on simulated SPX and SPY underlyings
- Tick-based simulation (not continuous time)
- No fees or commissions
- No position limits
- Perfect liquidity for hedging in the underlying

## Conclusion

The price-time priority matching algorithm used in the Intern Trading Game is a simplified but realistic implementation of how modern financial exchanges operate. Understanding this algorithm is crucial for developing effective trading strategies, as it determines how and when your orders will be filled.
