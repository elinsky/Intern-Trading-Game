# Price Generation

## Underlying Price Movement

The simulation generates realistic price paths using geometric Brownian motion (GBM) with regime-switching volatility.

### Base Model

For each tick, the price evolution follows:

```
S(t+1) = S(t) × exp((μ - σ²/2)Δt + σ√Δt × Z)
```

Where:

- S(t) = Current price
- μ = Drift (typically small or zero)
- σ = Volatility (depends on regime)
- Δt = Time increment (5 minutes)
- Z = Standard normal random variable

### SPX Price Generation

SPX serves as the primary underlying:

- Starting price: ~4,400
- Tick-to-tick moves based on current volatility regime
- Trading Tuesday & Thursday only (9:30 AM - 3:00 PM CT)
- Price evolution continues only during trading hours

### SPY Price Derivation

SPY tracks SPX with intentional imperfections:

```
SPY(t) = SPX(t)/10 × (1 + ε) + η
```

Where:

- Base ratio: SPX/10
- ε = Tracking error component (~0.1-0.3%)
- η = Additional noise term
- 1-2 tick lag in following SPX moves

This creates arbitrage opportunities when SPY diverges from its theoretical value.

## Volatility Regimes

### Three Volatility States

| Regime | Annualized Vol | Daily Std Dev | Typical 5-min Move |
|--------|----------------|---------------|-------------------|
| **Low** | ~10% | 0.63% | ±0.04% |
| **Medium** | ~20% | 1.26% | ±0.09% |
| **High** | ~50% | 3.15% | ±0.22% |

### Regime Persistence

- Regimes typically persist for multiple ticks
- Average duration: 20-100 ticks
- Sudden changes possible due to news events

### Transition Mechanics

Regime changes occur through:

1. **Scheduled transitions**: Natural regime evolution
2. **Event-driven shifts**: News triggers with known probabilities
3. **Random switches**: Small probability each tick

## Price Jump Events

### Discrete Jumps

Occasionally, prices experience discrete jumps:

- Magnitude: 0.5-2.0% instantaneous moves
- Frequency: 1-2 per day on average
- Can be positive or negative

### Jump Triggers

- Major news events
- Volatility regime changes
- Random occurrences

## Next Steps

- Understand [Volatility Regimes](volatility-regimes.md) in detail
- Learn about [News Events](news-events.md) and their impacts
- Study [SPX-SPY Correlation](correlation-model.md)
