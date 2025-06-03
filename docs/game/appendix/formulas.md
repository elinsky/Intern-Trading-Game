# Mathematical Formulas

## Price Generation

### Geometric Brownian Motion

The underlying price evolution follows:

```
S(t+Δt) = S(t) × exp((μ - σ²/2)Δt + σ√Δt × Z)
```

Where:
- `S(t)` = Price at time t
- `μ` = Drift (typically 0 for intraday)
- `σ` = Volatility (depends on regime)
- `Δt` = Time increment (5 minutes = 5/(252×390) years)
- `Z` = Standard normal random variable

### SPY Tracking Formula

```
SPY(t) = (SPX(t) / 10) × (1 + ε(t)) + η(t)
```

Where:
- `ε(t)` = Tracking error (~N(0, 0.0015²) daily)
- `η(t)` = Additional noise (~N(0, 0.0005²) per tick)

## Option Pricing

### Black-Scholes Formula

For European options:

**Call Option**:
```
C = S₀ × N(d₁) - K × e^(-rT) × N(d₂)
```

**Put Option**:
```
P = K × e^(-rT) × N(-d₂) - S₀ × N(-d₁)
```

Where:
```
d₁ = [ln(S₀/K) + (r + σ²/2)T] / (σ√T)
d₂ = d₁ - σ√T
```

Parameters:
- `S₀` = Current underlying price
- `K` = Strike price
- `r` = Risk-free rate (assume 0 for simplicity)
- `T` = Time to expiration
- `σ` = Implied volatility
- `N(x)` = Cumulative normal distribution

## Greeks Calculations

### Delta (Δ)
Rate of change of option price with respect to underlying:

**Call Delta**:
```
Δ_call = N(d₁)
```

**Put Delta**:
```
Δ_put = N(d₁) - 1
```

### Gamma (Γ)
Rate of change of delta:

```
Γ = φ(d₁) / (S₀ × σ × √T)
```

Where φ(x) is the standard normal PDF.

### Vega (ν)
Sensitivity to volatility:

```
ν = S₀ × φ(d₁) × √T
```

### Theta (Θ)
Time decay:

**Call Theta**:
```
Θ_call = -(S₀ × φ(d₁) × σ) / (2√T) - rK × e^(-rT) × N(d₂)
```

## Performance Metrics

### Sharpe Ratio

```
Sharpe = (R_p - R_f) / σ_p
```

Where:
- `R_p` = Portfolio return
- `R_f` = Risk-free rate (typically 0 for intraday)
- `σ_p` = Standard deviation of returns

**Annualized Sharpe**:
```
Sharpe_annual = Sharpe_daily × √252
```

### Maximum Drawdown

```
MDD = max_t∈[0,T] [max_s∈[0,t] P(s) - P(t)] / max_s∈[0,t] P(s)
```

Where P(t) is portfolio value at time t.

### Information Ratio

For signal-based strategies:

```
IR = (R_strategy - R_benchmark) / σ_tracking_error
```

## Position Sizing

### Kelly Criterion

Optimal position size:

```
f* = (p × b - q) / b
```

Where:
- `f*` = Fraction of capital to bet
- `p` = Probability of win
- `q` = Probability of loss (1-p)
- `b` = Odds (win/loss ratio)

**Practical Kelly** (with safety factor):
```
f_practical = f* × safety_factor
```
Where safety_factor ∈ [0.25, 0.5]

### Position Limits Check

```
Available = min(
    Role_Limit - |Current_Position|,
    Total_Limit - Σ|All_Positions|
)
```

## Fee Calculations

### Net Trading Cost

```
Net_Cost = (Taker_Volume × Taker_Fee) - (Maker_Volume × Maker_Rebate)
```

### Break-Even Spread (Market Maker)

```
BE_Spread = 2 × (Taker_Fee / (1 + Hit_Rate))
```

Where Hit_Rate is the fraction of quotes that get filled.

## Arbitrage Metrics

### Tracking Error

```
Tracking_Error = (SPY_Actual - SPY_Theoretical) / SPY_Theoretical × 100%
```

Where:
```
SPY_Theoretical = SPX / 10
```

### Z-Score for Mean Reversion

```
Z = (Current_Spread - Mean_Spread) / Std_Spread
```

Trade when |Z| > threshold (typically 2).

### Convergence Probability

Using Ornstein-Uhlenbeck process:

```
P(converge by time T) = 1 - exp(-2θT)
```

Where θ is the mean reversion speed.

## Risk Metrics

### Value at Risk (VaR)

**Parametric VaR** (95% confidence):
```
VaR_95 = Portfolio_Value × 1.645 × σ_daily
```

### Beta Calculation

```
β = Cov(R_portfolio, R_market) / Var(R_market)
```

For arbitrage desks, β should be close to 0.

### Correlation

```
ρ_XY = Cov(X,Y) / (σ_X × σ_Y)
```

SPX-SPY correlation typically ~0.98.

## Execution Metrics

### Implementation Shortfall

```
IS = (Execution_Price - Decision_Price) / Decision_Price × Direction
```

### Effective Spread

```
Effective_Spread = 2 × |Execution_Price - Mid_Price|
```

### Price Impact

```
Impact = |Post_Trade_Mid - Pre_Trade_Mid| / Pre_Trade_Mid
```

## Signal Processing

### Signal-to-Noise Ratio

```
SNR = E[Signal²] / E[Noise²]
```

### Exponential Moving Average

For adaptive parameters:

```
EMA_t = α × Value_t + (1 - α) × EMA_t-1
```

Where α = 2/(N+1) for N-period EMA.

## Market Maker Specific

### Optimal Quote Width

```
Spread* = 2/γ × ln(1 + γ/k)
```

Where:
- `γ` = Risk aversion parameter
- `k` = Order arrival rate

### Inventory Penalty

```
Penalty = λ × (Current_Inventory / Max_Inventory)²
```

Skew quotes by Penalty × Base_Spread.

## Quick Reference

### Common Values

| Parameter | Value | Usage |
|-----------|-------|-------|
| Trading minutes/day | 390 | Time scaling |
| Trading days/year | 252 | Annualization |
| Minutes/year | 98,280 | Volatility scaling |
| Ticks/day | 78 | 5-minute ticks |

### Volatility Conversions

```
σ_5min = σ_annual / √(252 × 78)
σ_daily = σ_annual / √252
σ_tick = σ_daily / √78
```

### Position Scaling

For SPX/SPY pairs:
```
SPY_Contracts = SPX_Contracts × 10 × (SPX_Price / SPY_Price)
```

Target ratio: 10:1 by value.