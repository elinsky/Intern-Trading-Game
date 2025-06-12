# Price Generation

## Underlying Price Movement

The simulation generates realistic price paths using geometric Brownian motion (GBM) with regime-switching volatility.

### Base Model

Price evolution follows continuous geometric Brownian motion:

```
dS/S = μdt + σdW
```

In discrete time steps:

```
S(t+Δt) = S(t) × exp((μ - σ²/2)Δt + σ√Δt × Z)
```

Where:

- S(t) = Current price
- μ = Drift (typically small or zero)
- σ = Volatility (depends on regime)
- Δt = Time increment (very small, ~1 second)
- Z = Standard normal random variable
- dW = Brownian motion increment

### SPX Price Generation

SPX serves as the primary underlying:

- Starting price: ~4,400
- Continuous price updates based on current volatility regime
- Trading Tuesday & Thursday only (9:30 AM - 3:00 PM CT)
- Price evolution continues only during trading hours
- Updates multiple times per second for realistic market dynamics

### SPY Price Derivation

SPY tracks SPX with intentional imperfections:

```
SPY(t) = SPX(t)/10 × (1 + ε) + η
```

Where:

- Base ratio: SPX/10
- ε = Tracking error component (~0.1-0.3%)
- η = Additional noise term
- Small lag (seconds) in following SPX moves

This creates arbitrage opportunities when SPY diverges from its theoretical value.

## Volatility Regimes

### Three Volatility States

| Regime | Annualized Vol | Daily Std Dev | Typical per-second Move |
|--------|----------------|---------------|------------------------|
| **Low** | ~10% | 0.63% | ±0.0016% |
| **Medium** | ~20% | 1.26% | ±0.0032% |
| **High** | ~50% | 3.15% | ±0.0080% |

### Regime Persistence

- Regimes typically persist for extended periods
- Average duration: 30 minutes to 2 hours
- Sudden changes possible due to news events

### Transition Mechanics

Regime changes occur through:

1. **Scheduled transitions**: Natural regime evolution
2. **Event-driven shifts**: News triggers with known probabilities
3. **Random switches**: Small probability throughout the day

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
