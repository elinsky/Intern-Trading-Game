# Trading Constraints

## Overview

Each role operates under specific constraints designed to create realistic trading dynamics and ensure balanced gameplay.

## Constraints by Role

| Role | Fees (Maker/Taker) | Order Limit | Position Limits | Special Requirements |
|------|--------------------|-------------|-----------------|---------------------|
| **Market Maker** | +$0.02 / -$0.01 | 10/second | ±50 per option<br>±200 total | • ≥80% quote uptime<br>• Two-sided quotes |
| **Hedge Fund** | +$0.01 / -$0.02 | 5/second | 150 per option<br>500 total | • No two-sided quotes<br>• ±50 delta limit<br>• Volatility signals |
| **Arbitrage Desk** | +$0.01 / -$0.02 | 7/second | 100 per option<br>300 total | • Paired trades only<br>• Tracking signals |
| **Retail Flow** | -$0.01 / -$0.03 | 1/second | 50 total | • Automated only<br>• Behavioral patterns |

## Position Limits

### Market Maker

- **Per Option**: ±50 contracts
- **Total Portfolio**: ±200 contracts
- **Purpose**: Force active inventory management
- **Measurement**: Net position (long - short)

### Hedge Fund

- **Per Option**: 150 contracts (one-sided)
- **Total Portfolio**: 500 contracts
- **Delta Limit**: ±50 deltas (portfolio-wide)
- **Purpose**: Enable gamma trading with forced rehedging
- **Measurement**: Absolute position for size, net delta for neutrality

### Arbitrage Desk

- **Per Option**: 100 contracts
- **Total Portfolio**: 300 contracts
- **Paired Trade Requirement**: 2:1 SPX:SPY ratio
- **Purpose**: Maintain market neutrality

### Retail Trader

- **Total Portfolio**: 50 contracts
- **Per Trade**: 10 contracts maximum
- **Purpose**: Realistic retail constraints

## Order Limits

### Submission Rates

- Orders per second vary by role
- Bulk submission allowed
- No modifications (cancel/replace only)

### Size Constraints

| Role | Min Order | Max Order | Quote Size |
|------|-----------|-----------|------------|
| Market Maker | 1 | 1000 | 10-1000 |
| Hedge Fund | 1 | 500 | N/A |
| Arbitrage Desk | 1 | 500 | N/A |
| Retail | 1 | 100 | N/A |

## Fee Structure

### Maker/Taker Model

- **Maker**: Add liquidity (limit orders that rest)
- **Taker**: Remove liquidity (market orders or crossing limits)

### Fee Calculation

```
Net Fee = (Maker Rebate × Maker Volume) - (Taker Fee × Taker Volume)
```

### Role Advantages

- Market Makers: Enhanced maker rebates encourage liquidity
- Others: Standard fees incentivize thoughtful execution

## Quote Requirements (Market Makers Only)

### 80% Uptime Rule

- Must maintain active quotes 80% of trading time
- Measured per instrument on rolling 5-minute basis
- Both bid and ask required

### Spread Constraints

- Maximum: 10% of mid-price
- Minimum: $0.01
- Must be reasonable for market conditions

### Penalty for Non-Compliance

- Warning at 70% uptime
- Reduced rebates below 80%
- Possible role reassignment below 60%

## Special Constraints

### Hedge Fund Limitations

- **No Two-Sided Quoting**: Cannot simultaneously bid and ask
- **Delta Neutrality**: Must maintain portfolio delta within ±50
- **Signal Usage**: Expected to utilize volatility signals for gamma positioning
- **Rehedging Requirement**: Must adjust positions when delta limit approached
- **Performance Focus**: Continuous P&L from gamma scalping/premium collection

### Arbitrage Desk Requirements

- **Paired Trades**: Must maintain balanced SPX/SPY positions
- **Ratio Maintenance**: Target 10:1 value ratio
- **Convergence Focus**: Scored on arbitrage capture, not directional P&L

### Retail Restrictions

- **Order Types**: Market and limit only (no quotes)
- **Frequency**: Maximum 1 order per second
- **No Signals**: Trade on public information only

## Risk Controls

### Pre-Trade Checks

All orders validated for:

- Position limit compliance
- Order size limits
- Role permissions
- Price reasonability

### Real-Time Monitoring

- Position tracking continuous
- P&L calculation real-time
- Fee accumulation immediate
- Constraint violations logged instantly

## Strategic Implications

### For Market Makers

- Balance inventory within tight limits
- Use rebates to offset risk
- Quick position flipping

### For Hedge Funds

- Position gamma based on volatility signals
- Maintain delta neutrality through rehedging

### For Arbitrage Desks

- Maintain ratio discipline
- Size based on convergence confidence
- Monitor both legs equally

## Next Steps

- Review [Execution Rules](execution-rules.md)
- Understand [Signal Access](signals-access.md)
- Study your specific [Role Requirements](../roles/overview.md)
