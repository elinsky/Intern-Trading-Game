# Game Mechanics

## Continuous Trading System

The game operates with continuous order matching throughout the trading day, similar to real financial markets.

### Trading Hours

- **Market Open**: 9:30 AM CT
- **Market Close**: 3:00 PM CT
- **Trading Days**: Tuesday & Thursday only

### Market Open Process

**9:30 AM - Opening Rotation**:

- All pre-market orders participate in a batch auction
- Single clearing price determined for each instrument
- Provides initial price discovery
- After rotation completes, continuous trading begins

### Continuous Matching

After the opening rotation, the market operates continuously:

- **Order Submission**: Accept orders anytime during market hours
- **Immediate Matching**: Crossing orders execute immediately
- **Price-Time Priority**: Standard exchange matching rules apply
- **Real-time Updates**: Positions and P&L update instantly

### What Happens During Trading

**1. Price Generation**

- Underlying prices update continuously using geometric Brownian motion
- Volatility regime determines price movement magnitude
- SPY price derived from SPX with noise and lag
- Price updates occur multiple times per second

**2. News & Events**

- News headlines published throughout the day
- May trigger volatility regime changes
- Some participants receive advance signals
- Events occur at random intervals (1-4 hours apart)

**3. Order Processing**

- Orders processed immediately upon receipt
- All orders timestamped with microsecond precision
- Validation checks performed in real-time
- Execution reports sent immediately

**4. Trade Settlement**

- Trades settle immediately (T+0)
- Positions updated in real-time
- P&L calculated continuously
- Fees applied upon execution

## Order Processing

### Matching Algorithm

Orders are matched using price-time priority:

1. **Best Price First**: Orders offering better prices execute first
2. **Time Priority**: Among same-priced orders, earlier orders execute first
3. **Partial Fills**: Large orders may be partially filled

### Execution Rules

- Market orders execute against best available liquidity
- Limit orders rest in book if not immediately executable
- Quotes create two-sided markets (market makers only)
- Orders remain active until filled, canceled, or market close

### Trade Settlement

- Trades settle immediately (T+0)
- Positions updated in real-time
- No settlement risk or failures
- All fees calculated and applied instantly

## Information Dissemination

### Public Information

Available to all participants in real-time:

- Current market prices
- Order book (top 5 levels)
- Trade prints
- News headlines

### Private Information

Role-specific signals with continuous updates:

- Hedge Fund: Volatility regime predictions
- Arbitrage Desk: Tracking error measurements
- Market Maker: Order flow (from their own trades)

### Timing of Information

| Information Type   | When Published        | Who Sees   |
| ------------------ | -------------------- | ---------- |
| Underlying prices  | Continuous          | Everyone   |
| News headlines     | Random (1-4 hrs)    | Everyone   |
| Volatility signals | 60 seconds advance  | Hedge Fund |
| Tracking signals   | Real-time           | Arb Desk   |
| Trade results      | Immediately         | Everyone   |

## Bot Interaction

### Connection Protocol

1. Authenticate with credentials
2. Subscribe to market data feeds
3. Receive real-time market updates
4. Submit orders anytime during market hours
5. Receive immediate execution reports

### Error Handling

- Invalid orders rejected immediately with reason
- Connection issues handled gracefully
- Automatic reconnection supported

## Performance Considerations

### Latency

- Order acknowledgment: < 1ms
- Execution reports: < 5ms
- Market data updates: < 10ms

### Rate Limits

- Maximum 10 orders per second per participant
- Market data updates throttled to 10 per second
- No limits on passive data consumption

## Next Steps

- Review [Simulation Details](../simulation/price-generation.md)
- Understand [Trading Rules](../trading/order-types.md)
- Begin [Strategy Development](../../technical/index.md)
