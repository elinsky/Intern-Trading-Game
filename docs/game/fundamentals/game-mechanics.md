# Game Mechanics

## Tick-Based Simulation

The game operates on a tick-based system where market state updates every 5 minutes.

### Tick Lifecycle

```
T+0:00    Price Generation & News Publication
T+0:30    Order Window Opens (HARD START)
T+3:00    Order Window Closes (HARD CUTOFF)
T+3:30    Matching & Execution
T+4:00    Results Published
T+5:00    Next Tick Begins
```

**Critical Timing**:
- Orders submitted before T+0:30 are rejected
- Orders submitted after T+3:00 are rejected
- No modifications allowed after submission
- All timestamps are server-side (no client clock issues)

### What Happens Each Tick

**1. Price Generation**
- New underlying prices calculated using geometric Brownian motion
- Volatility regime determines price movement magnitude
- SPY price derived from SPX with noise and lag

**2. News & Events**
- News headlines published (if any)
- May trigger volatility regime changes
- Some participants receive advance signals

**3. Order Collection**
- Bots read market data and signals
- Submit orders based on strategy
- All orders timestamped and queued

**4. Order Matching**
- Price-time priority matching
- Crossed orders execute immediately
- Partial fills allowed

**5. Settlement**
- Trades confirmed and booked
- Positions updated
- P&L calculated
- Fees applied

## Order Processing

### Matching Algorithm

Orders are matched using price-time priority:

1. **Best Price First**: Orders offering better prices execute first
2. **Time Priority**: Among same-priced orders, earlier orders execute first
3. **Pro-Rata**: Large orders may be partially filled

### Execution Rules

- Market orders execute against best available liquidity
- Limit orders rest in book if not immediately executable
- Quotes create two-sided markets (market makers only)
- All orders expire at tick end if not filled

### Trade Settlement

- Trades settle immediately (T+0)
- Positions updated in real-time
- No settlement risk or failures

## Information Dissemination

### Public Information

Available to all participants:
- Current market prices
- Order book (top 5 levels)
- Trade prints
- News headlines

### Private Information

Role-specific signals:
- Hedge Fund: Volatility regime predictions
- Arbitrage Desk: Tracking error measurements
- Market Maker: Order flow (from their own trades)

### Timing of Information

| Information Type   | When Published           | Who Sees   |
| ------------------ | ------------------------ | ---------- |
| Underlying prices  | Start of tick            | Everyone   |
| News headlines     | T+10 seconds             | Everyone   |
| Volatility signals | T-60 seconds (next tick) | Hedge Fund |
| Tracking signals   | Start of tick            | Arb Desk   |
| Trade results      | After matching           | Everyone   |

## Bot Interaction

### Connection Protocol

1. Authenticate with credentials
2. Subscribe to market data feeds
3. Receive tick notifications
4. Submit orders within window
5. Receive execution reports

### Error Handling

- Invalid orders rejected with reason

## Next Steps

- Review [Simulation Details](../simulation/)
- Understand [Trading Rules](../trading/)
- Begin [Strategy Development](../../technical/)
