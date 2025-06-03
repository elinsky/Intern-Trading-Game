# Volatility Regimes

## Understanding Volatility States

The market operates in one of three volatility regimes at any time, fundamentally affecting price movements and option values.

### Regime Characteristics

| Regime | Market Condition | Price Behavior | Option Impacts |
|--------|------------------|----------------|----------------|
| Low | Calm markets | Small, predictable moves | Low option premiums |
| Medium | Normal trading | Moderate fluctuations | Fair option values |
| High | Stressed/uncertain | Large, erratic moves | Expensive options |

### Detailed Parameters

**Low Volatility (σ ≈ 0.1)**
- Annualized: 10%
- Daily moves: ±0.5-1%
- 5-minute moves: ±0.04%
- Typical duration: 50-200 ticks

**Medium Volatility (σ ≈ 0.2)**
- Annualized: 20%
- Daily moves: ±1-2%
- 5-minute moves: ±0.09%
- Typical duration: 30-100 ticks

**High Volatility (σ ≈ 0.5)**
- Annualized: 50%
- Daily moves: ±3-5%
- 5-minute moves: ±0.22%
- Typical duration: 10-50 ticks

## Regime Transitions

### Natural Evolution

Regimes follow a Markov process with transition probabilities:

```
From\To   Low    Medium   High
Low       0.95   0.04     0.01
Medium    0.02   0.94     0.04
High      0.01   0.09     0.90
```

### Event-Triggered Changes

News events can force regime transitions:
- Override natural transition probabilities
- Immediate effect at next tick
- Known probabilities (see [News Events](news-events.md))

### Transition Patterns

Common patterns observed:
- **Low to Medium**: Gradual uncertainty increase
- **Medium to High**: Sudden market stress
- **High to Medium**: Volatility normalization
- **Direct Low/High**: Rare but possible

## Trading Implications

### For Market Makers
- **Low Vol**: Tight spreads, stable inventory
- **Medium Vol**: Balanced risk/reward
- **High Vol**: Wide spreads, active inventory management

### For Hedge Funds
- **Low Vol**: Sell premium strategies
- **Medium Vol**: Mixed strategies
- **High Vol**: Buy volatility, larger positions

### For Arbitrage Desks
- **Low Vol**: Small, frequent trades
- **Medium Vol**: Standard convergence plays
- **High Vol**: Larger mispricings, bigger opportunities

## Volatility Signals

### Hedge Fund Advantage

Hedge funds receive advance warning of regime changes:
- **Timing**: 1-5 ticks before transition
- **Content**: Next regime and transition probability
- **Accuracy**: ~66% reliable

Example signal:
```json
{
  "current_regime": "medium",
  "next_regime": "high",
  "probability": 0.66,
  "ticks_until_change": 3
}
```

### Signal Usage Strategies

**Anticipatory Positioning**
- Buy options before vol increase
- Sell options before vol decrease
- Adjust position sizes

**Risk Management**
- Reduce positions before high vol
- Increase activity in low vol
- Hedge existing positions

## Historical Patterns

### Typical Day Profile

- **Morning**: Often starts in medium volatility
- **Midday**: May transition to low if quiet
- **Afternoon**: News events can trigger changes
- **Evening**: Generally calmer, trending to low

### Weekly Patterns

- **Monday**: Higher chance of regime changes
- **Tuesday-Thursday**: More stable regimes
- **Friday**: Increased event probability

## Measuring Realized Volatility

### Calculation Method

Realized volatility over N ticks:
```
RV = sqrt(sum((log(S[i]/S[i-1]))^2) × 252 × 78)
```

Where 78 = trading ticks per day

### Comparing IV vs RV

- Options priced using implied volatility
- Actual moves follow realized volatility
- Spread between IV and RV creates opportunities

## Regime Identification

### Without Signals

Market makers must infer regime from:
- Recent price movements
- Option premium levels
- Order flow patterns
- News interpretation

### Statistical Methods

- Rolling standard deviation
- GARCH models
- Regime-switching models
- Machine learning approaches

## Next Steps

- Learn about [News Events](news-events.md) that trigger changes
- Understand [Price Generation](price-generation.md) within each regime
- Review role-specific strategies in [Roles](../roles/)