# Market Structure

## Tradable Instruments

### Underlyings

The game features two correlated equity indices:

| Instrument | Type  | Typical Price | Volatility | Key Features                     |
| ---------- | ----- | ------------- | ---------- | -------------------------------- |
| **SPX**    | Index | ~4,400        | Moderate   | S&P 500 Index, high dollar value |
| **SPY**    | ETF   | ~440          | Moderate   | Tracks SPX/10 with noise and lag |

### Correlation Model

SPY is designed to track SPX with imperfections:

- Base correlation: ~0.98
- Tracking error: 0.1-0.3% daily
- Lag: 1-2 ticks
- Additional noise component

This creates arbitrage opportunities between the two products.

### Options

Each underlying has listed options with:


**Strike Selection**

- Sufficient strikes to cover ±30% moves
- Ensures all delta ranges (0.05 to 0.95) are tradeable
- Typical setup for SPX at 4400:

  - Downside: 3080, 3300, 3520, 3740, 3960, 4180
  - ATM area: 4290, 4400, 4510
  - Upside: 4620, 4840, 5060, 5280, 5500, 5720
- Similar proportional coverage for SPY

**Expirations**

- Weekly expirations only
- Typically 4-6 weeks available at any time
- Rolling weekly cycle

**Option Style**

- European exercise only
- Cash settlement at expiration
- Standard multiplier (100 for SPY, 100 for SPX)

## Order Book Structure

### Price Levels

- Top 5 bid/ask levels visible
- Price-time priority matching
- Minimum tick size: $0.01

### Order Types Supported

| Order Type       | Description           | Available To       |
| ---------------- | --------------------- | ------------------ |
| **Limit Order**  | Specify exact price   | All roles          |
| **Market Order** | Execute at best price | All roles          |
| **Quote**        | Simultaneous bid/ask  | Market Makers only |

### Fee Structure

Fees vary by role and order type:

| Role           | Maker Fee | Taker Fee |
| -------------- | --------- | --------- |
| Market Maker   | +$0.02    | -$0.01    |
| Hedge Fund     | +$0.01    | -$0.02    |
| Arbitrage Desk | +$0.01    | -$0.02    |
| Retail         | -$0.01    | -$0.03    |

## Trading Sessions

### Trading Schedule

- **Trading Days**: Tuesday and Thursday only
- **Trading Hours**: 9:30 AM - 3:00 PM Central Time
- **Ticks**: Every 5 minutes during trading hours (66 per day)
- **Non-Trading Days**: Monday (prep), Wednesday (analysis), Friday (retrospective)

### Order Submission Window

- 2-3 minutes per tick
- All orders collected simultaneously
- Batch processing at tick close

## Market Data Feed

### Real-Time Data

Each tick provides:

- Current bid/ask for all instruments
- Last trade price and size
- Order book depth (5 levels)

### Historical Data

- All previous tick snapshots
- Complete trade history
- Position tracking

## Next Steps

- Understand [Game Mechanics](game-mechanics.md)
- Review [Trading Constraints](../trading/constraints.md)
- Study your [Role Requirements](../roles/)
