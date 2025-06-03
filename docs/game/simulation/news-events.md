# News Events

## Event System Overview

News events drive market dynamics by potentially triggering volatility regime changes, price jumps, or serving as false signals. All participants see headlines, but only some know the true impact.

### Event Frequency

- Average: Every 1-4 hours
- Distribution: Poisson process
- Clustering: Possible during "active" periods
- Quiet periods: Can go 6+ hours without events

### Event Types

| Type | Effect | Frequency | Example |
|------|--------|-----------|---------|
| **Regime Shifter** | Changes volatility state | 40% | "Fed hints at tightening" |
| **Price Jumper** | Immediate price move | 30% | "Surprise earnings beat" |
| **False Signal** | No effect | 30% | "Analyst maintains rating" |

## Probability Tables

All participants have access to these published probabilities:

### Major Events

| News Headline | Regime Shift Chance | Price Jump Chance |
|--------------|-------------------|------------------|
| "Fed hints at tightening" | 60% | 20% |
| "Geopolitical tensions rise" | 70% | 30% |
| "Major acquisition announced" | 40% | 50% |
| "Economic data surprises" | 50% | 40% |

### Minor Events

| News Headline | Regime Shift Chance | Price Jump Chance |
|--------------|-------------------|------------------|
| "Strong jobs report" | 40% | 10% |
| "Earnings meet expectations" | 20% | 15% |
| "Technical breakout observed" | 30% | 25% |
| "Analyst upgrades sector" | 15% | 10% |

### Neutral Events

| News Headline | Regime Shift Chance | Price Jump Chance |
|--------------|-------------------|------------------|
| "Markets quiet ahead of data" | 5% | 0% |
| "Trading range-bound" | 5% | 5% |
| "No major news today" | 0% | 0% |

## Information Asymmetry

### What Everyone Sees

When an event occurs, all participants immediately see:
- News headline text
- Timestamp
- Historical probability table

Example broadcast:
```
[T+0:10] NEWS: "Fed hints at tightening"
```

### What Hedge Funds See

With their volatility signal, hedge funds also receive:
- Actual outcome (regime shift: yes/no)
- New regime (if changing)
- Advance timing (1-5 ticks early)

Example signal:
```json
{
  "event": "Fed hints at tightening",
  "regime_shift": true,
  "new_regime": "high",
  "current_regime": "medium",
  "ticks_until_effect": 2
}
```

### Market Maker Challenge

Market makers must:
- React only to the headline
- Use probability tables
- Infer actual impact from price action
- Adjust quotes defensively

## Event Impact Mechanics

### Regime Shift Events

When a regime shift occurs:
1. Current tick continues in old regime
2. Transition happens at tick boundary
3. New regime persists until next event
4. Minimum duration before next shift

### Price Jump Events

Immediate price impacts:
- Magnitude: 0.5-2.0% move
- Direction: Correlated with news sentiment
- SPY follows with lag and noise
- Options reprice instantly

### False Signals

No actual market impact:
- Tests participant reaction
- Can trigger overtrading
- Reveals strategy robustness

## Strategic Considerations

### Pre-Event Positioning

**For Hedge Funds:**
- Maintain readiness for signals
- Balance position for quick adjustment
- Consider pre-event hedges

**For Market Makers:**
- Widen spreads before known event times
- Reduce position sizes
- Prepare for increased flow

**For Arbitrage Desks:**
- Expect larger tracking errors
- Position for convergence post-event
- Monitor correlation breakdown

### Post-Event Actions

**Confirmed Regime Shift:**
- Adjust option positions
- Modify risk parameters
- Update pricing models

**Price Jump:**
- Capture new equilibrium
- Trade mean reversion
- Exploit temporary dislocations

**False Signal:**
- Avoid overreaction
- Maintain discipline
- Learn from market response

## Event Patterns

### Clustering
- Events often cluster in time
- Active news cycles create opportunities
- Quiet periods allow position building

### Predictable Windows
- Certain times have higher event probability
- Market open/close analogues
- Weekly patterns exist

### Serial Correlation
- Some events increase probability of others
- Regime shifts often follow patterns
- Price jumps may cascade

## Risk Management

### Event Risk Hedging
- Straddles before known events
- Reduced position sizes
- Diversification across strikes

### Information Advantage
- Hedge funds monetize advance knowledge
- Others must hedge uncertainty
- Speed of reaction crucial

## Next Steps

- Study [Correlation Model](correlation-model.md) for arbitrage
- Review [Trading Signals](../trading/signals-access.md)
- Understand role-specific strategies in [Roles](../roles/)