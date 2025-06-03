# Probability Tables

## News Event Probabilities

All participants have access to these probability tables, which indicate the likelihood of various outcomes when news events occur.

### Major Market Events

These events have the highest impact potential and occur less frequently.

| News Headline | Regime Shift | Price Jump | Direction | Magnitude |
|---------------|--------------|------------|-----------|-----------|
| Fed announces emergency meeting | 85% | 60% | Negative | 1-3% |
| Geopolitical tensions escalate | 70% | 30% | Negative | 0.5-2% |
| Major bank reports losses | 65% | 45% | Negative | 1-2% |
| Surprise rate decision | 75% | 50% | Either | 1-2.5% |
| Tech giant acquisition announced | 40% | 50% | Positive | 0.5-1.5% |

### Economic Data Releases

Regular economic announcements with moderate impact.

| News Headline | Regime Shift | Price Jump | Direction | Magnitude |
|---------------|--------------|------------|-----------|-----------|
| Fed hints at tightening | 60% | 20% | Negative | 0.3-1% |
| Strong jobs report | 40% | 10% | Positive | 0.2-0.5% |
| Inflation data surprises | 55% | 35% | Either | 0.5-1% |
| GDP beats expectations | 35% | 25% | Positive | 0.3-0.8% |
| Manufacturing data weak | 45% | 15% | Negative | 0.2-0.6% |

### Market Commentary

Analyst opinions and market color with lower impact.

| News Headline | Regime Shift | Price Jump | Direction | Magnitude |
|---------------|--------------|------------|-----------|-----------|
| Analysts upgrade sector | 15% | 10% | Positive | 0.1-0.3% |
| Technical breakout observed | 30% | 25% | Either | 0.3-0.7% |
| Options flow unusual | 25% | 5% | None | 0% |
| Earnings season begins | 20% | 10% | Either | 0.2-0.4% |
| Year-end rebalancing | 10% | 5% | Either | 0.1-0.2% |

### Neutral Events

Low-impact or non-events for calibration.

| News Headline | Regime Shift | Price Jump | Direction | Magnitude |
|---------------|--------------|------------|-----------|-----------|
| Markets quiet ahead of data | 5% | 0% | None | 0% |
| Trading range-bound | 5% | 5% | Either | 0.1% |
| Light volume expected | 0% | 0% | None | 0% |
| No major news today | 0% | 0% | None | 0% |

## Volatility Regime Transition Probabilities

### Natural Transition Matrix

When no news events occur, regimes evolve according to:

```
From/To           Low Vol   Med Vol   High Vol
Low Volatility    95%       4%        1%
Medium Volatility 2%        94%       4%
High Volatility   1%        9%        90%
```

### Event-Triggered Transitions

When regime shift events occur (based on tables above):

```
From/To           Low Vol   Med Vol   High Vol
Low Volatility    0%        70%       30%
Medium Volatility 10%       0%        90%
High Volatility   5%        85%       10%
```

## Signal Accuracy Tables

### Hedge Fund Volatility Signal

| Actual Outcome | Signal Predicts | Probability |
|----------------|-----------------|-------------|
| Regime shifts | Regime shifts | 66% |
| Regime shifts | No shift | 34% |
| No shift | No shift | 66% |
| No shift | Regime shifts | 34% |

**Confusion Matrix**:
```
                 Predicted Shift  Predicted Stable
Actual Shift     66%             34%
Actual Stable    34%             66%
```

### Arbitrage Desk Tracking Signal

| Tracking Error Size | Signal Accuracy | False Positive Rate |
|-------------------|-----------------|-------------------|
| <0.10% | 60% | 40% |
| 0.10-0.20% | 75% | 25% |
| 0.20-0.50% | 80% | 20% |
| >0.50% | 85% | 15% |

## Event Frequency Distributions

### News Event Timing

**Poisson Distribution Parameters**:
- Average interval: 2.5 hours
- Minimum gap: 30 minutes
- Maximum gap: 6 hours

**Daily Pattern**:
| Time Period | Relative Frequency |
|-------------|-------------------|
| 9 AM - 12 PM | 1.5x |
| 12 PM - 2 PM | 0.8x |
| 2 PM - 4 PM | 1.2x |
| After 4 PM | 0.5x |

### Volatility Regime Durations

| Regime | Average Duration | Std Dev | Min | Max |
|--------|-----------------|---------|-----|-----|
| Low | 100 ticks | 40 ticks | 50 | 200 |
| Medium | 65 ticks | 25 ticks | 30 | 100 |
| High | 30 ticks | 15 ticks | 10 | 50 |

## Price Impact Calculations

### Jump Magnitudes by Event Type

**Distribution**: Log-normal
```
Jump Size = Sign × exp(μ + σ × Z)
Where:
- μ = log(expected_magnitude)
- σ = 0.3 (volatility of jump size)
- Z = standard normal random
```

### SPY Tracking Error Distribution

**Normal Distribution**:
- Mean: 0%
- Daily Std Dev: 0.15%
- Intraday Autocorrelation: 0.85
- Mean Reversion Half-life: 7 ticks

## Using Probability Tables

### For Hedge Funds
1. **Pre-position** when high-probability events approach
2. **Size trades** based on regime shift probability
3. **Combine** with volatility signal for confirmation

### For Market Makers
1. **Widen spreads** before high-impact events
2. **Reduce size** proportional to total probability
3. **Skew quotes** based on likely direction

### For Arbitrage Desks
1. **Expect divergence** during regime shifts
2. **Size larger** when volatility increases
3. **Quick entry** after event confirmation

## Important Notes

1. **Probabilities are known** - All participants see these tables
2. **Outcomes are random** - Actual results follow these distributions
3. **Signals add edge** - Some roles know outcomes in advance
4. **History doesn't repeat** - Each event is independent

## Quick Reference Card

### High Impact Events (>50% total probability)
- Fed emergency meeting: 85% + 60% = 145% combined
- Surprise rate decision: 75% + 50% = 125% combined
- Geopolitical tensions: 70% + 30% = 100% combined

### Medium Impact Events (25-50% total probability)
- Fed hints at tightening: 60% + 20% = 80% combined
- Inflation surprises: 55% + 35% = 90% combined
- Technical breakout: 30% + 25% = 55% combined

### Low Impact Events (<25% total probability)
- Analyst upgrades: 15% + 10% = 25% combined
- Markets quiet: 5% + 0% = 5% combined
- No news: 0% + 0% = 0% combined

Remember: These probabilities are your map to navigate market events. Study them, plan around them, and use them to manage risk effectively.