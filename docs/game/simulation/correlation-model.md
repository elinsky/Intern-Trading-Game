# SPX-SPY Correlation Model

## Relationship Overview

SPY is designed to track SPX but with realistic imperfections that create trading opportunities. Understanding this relationship is crucial for all participants, especially arbitrage desks.

### Base Relationship

```
Theoretical SPY Price = SPX / 10
Actual SPY Price = Theoretical Price × (1 + tracking_error) + noise
```

### Key Parameters

| Parameter      | Value     | Description           |
| -------------- | --------- | --------------------- |
| Base Ratio     | 10:1      | SPY ≈ SPX/10          |
| Correlation    | ~0.98     | High but imperfect    |
| Tracking Error | 0.1-0.3%  | Daily deviation       |
| Lag            | 1-2 ticks | SPY follows SPX       |
| Noise          | ±0.05%    | Additional randomness |

## Tracking Error Components

### Systematic Factors

**1. Execution Lag**
- SPY updates 1-2 ticks after SPX moves
- Creates temporary arbitrage windows
- More pronounced during volatile periods

### Random Factors

**1. Microstructure Noise**
- Independent random component
- Zero mean over time
- Increases intraday volatility

## Tracking Error Signal

### Arbitrage Desk Advantage

Arbitrage desks receive a proprietary signal indicating current mispricing:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "spx_price": 4400.00,
  "spy_price": 441.25,
  "theoretical_spy": 440.00,
  "tracking_error": 0.28,
  "direction": "SPY_OVERVALUED",
  "confidence": 0.80
}
```

### Signal Interpretation

| Tracking Error | Magnitude | Action |
|----------------|-----------|--------|
| < 0.1% | Negligible | No trade |
| 0.1-0.2% | Small | Consider if low risk |
| 0.2-0.5% | Medium | Standard trade |
| > 0.5% | Large | High conviction |

### Signal Accuracy

- Overall accuracy: ~80%
- False signals: Usually small magnitude
- Best in medium volatility
- Less reliable during events

## Options Arbitrage

### Cross-Product Strategies

Since options exist on both underlyings:


**Relative Value**
- SPX calls vs SPY calls (scaled)
- Put spread arbitrage
- Volatility surface differences

**Example Trade**
```
Signal: SPY overvalued by 0.3%
Action:

- Sell 10 SPY 440 calls
- Buy 1 SPX 4400 calls
- Hold until convergence
```

### Risk Considerations

**Execution Risk**
- Need to leg into trades
- Market impact on both sides
- Timing crucial

**Correlation Risk**
- Relationship can break down
- Events cause divergence
- Position sizing important

## Next Steps

- Review [Arbitrage Desk Role](../roles/arbitrage-desk.md)
- Study [Trading Signals](../trading/signals-access.md)
- Understand [Execution Rules](../trading/execution-rules.md)
