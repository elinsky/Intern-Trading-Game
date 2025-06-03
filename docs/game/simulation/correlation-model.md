# SPX-SPY Correlation Model

## Relationship Overview

SPY is designed to track SPX but with realistic imperfections that create trading opportunities. Understanding this relationship is crucial for all participants, especially arbitrage desks.

### Base Relationship

```
Theoretical SPY Price = SPX / 10
Actual SPY Price = Theoretical Price × (1 + tracking_error) + noise
```

### Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Base Ratio | 10:1 | SPY ≈ SPX/10 |
| Correlation | ~0.98 | High but imperfect |
| Tracking Error | 0.1-0.3% | Daily deviation |
| Lag | 1-2 ticks | SPY follows SPX |
| Noise | ±0.05% | Additional randomness |

## Tracking Error Components

### Systematic Factors

**1. Execution Lag**
- SPY updates 1-2 ticks after SPX moves
- Creates temporary arbitrage windows
- More pronounced during volatile periods

**2. Liquidity Differences**
- SPY may overshoot on large moves
- Different market depths affect pricing
- Rebalancing flows impact correlation

**3. Volatility Sensitivity**
- Tracking error increases in high volatility
- Correlation weakens during stress
- Mean reversion strengthens in calm markets

### Random Factors

**1. Microstructure Noise**
- Independent random component
- Zero mean over time
- Increases intraday volatility

**2. Flow Imbalances**
- Retail preferences for SPY
- Institutional SPX hedging
- Creates temporary dislocations

## Arbitrage Opportunities

### Types of Mispricings

| Type | Frequency | Typical Size | Duration |
|------|-----------|--------------|----------|
| **Lag Arbitrage** | Every major move | 0.1-0.2% | 1-2 ticks |
| **Volatility Divergence** | High vol periods | 0.2-0.5% | 3-5 ticks |
| **Mean Reversion** | Several per hour | 0.15-0.3% | 5-10 ticks |
| **Event Dislocation** | News events | 0.3-1.0% | 2-8 ticks |

### Convergence Patterns

**Fast Convergence (1-3 ticks)**
- Simple lag corrections
- Small mispricings
- High probability trades

**Slow Convergence (5-15 ticks)**
- Larger dislocations
- Volatility-driven divergence
- Requires patience

**Failed Convergence**
- Regime changes mid-trade
- News events interfere
- Risk management critical

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

## Statistical Properties

### Correlation by Regime

| Volatility Regime | Correlation | Tracking Error Std |
|-------------------|-------------|-------------------|
| Low | 0.99 | 0.05% |
| Medium | 0.98 | 0.10% |
| High | 0.95 | 0.20% |

### Mean Reversion

- Half-life: ~5-10 ticks
- Stronger in low volatility
- Weaker during events

### Cointegration

- Long-term relationship stable
- Short-term deviations profitable
- Error correction mechanism

## Implementation Tips

### For Arbitrage Desks

1. **Monitor Continuously**: Opportunities are short-lived
2. **Size Appropriately**: Account for convergence time
3. **Hedge Greeks**: Maintain market neutrality
4. **Use Limits**: Don't chase bad fills

### For Other Roles

**Market Makers**: 
- Adjust quotes based on correlation
- Widen during divergence periods

**Hedge Funds**:
- Use as risk indicator
- Trade extremes directionally

## Advanced Patterns

### Volatility Term Structure

- Front months track better
- Long-dated options diverge more
- Creates calendar spread opportunities

### Skew Differences

- SPX typically has steeper put skew
- SPY more retail-influenced
- Exploitable during stress

### Event Response

- SPX leads on macro news
- SPY can lead on ETF flows
- Different response speeds

## Next Steps

- Review [Arbitrage Desk Role](../roles/arbitrage-desk.md)
- Study [Trading Signals](../trading/signals-access.md)
- Understand [Execution Rules](../trading/execution-rules.md)