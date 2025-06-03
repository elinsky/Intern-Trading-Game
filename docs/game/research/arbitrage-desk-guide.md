# Arbitrage Desk Research Guide

## Your Edge

You receive real-time tracking error signals when SPY diverges from SPX:
- **Accuracy**: 80%
- **Timing**: Immediate notification when divergence exceeds threshold
- **Content**: Price divergence magnitude, direction, confidence score

This signal identifies mispricings between related products. Your job is to capture the convergence.

## The Core Research Problem

### 1. Understanding Your Signal

Your signal is more accurate than others, but convergence timing is uncertain:

- What does 80% accuracy mean for convergence trades?
- How long do mispricings typically persist?
- What causes the 20% of false signals?

Key questions to investigate:
- What's the typical convergence time distribution?
- Do certain market conditions create more reliable signals?
- How does signal magnitude relate to profit potential?

### 2. Modeling the Opportunity

SPX-SPY divergences create option pricing dislocations. You need to model:

**Convergence dynamics:**
- How fast do prices converge after signal?
- What's the convergence path - linear, exponential, jumpy?
- Do options converge differently than underlyings?

**Spread relationships:**
- How do equivalent options misprice (SPX 4400 call vs SPY 440 call)?
- Which strikes/expirations show largest divergences?
- Cross-product Greeks behavior during divergence

**Risk dynamics:**
- What if convergence takes longer than expected?
- How do you maintain market neutrality?
- Paired trade ratio management (target 10:1 by value)

### 3. Making Trading Decisions

Transform divergence signals into profitable paired trades:

**Pair construction:**
- Direct underlying arbitrage vs. options arbitrage
- Strike/expiration matching methodology
- Managing the 10:1 value ratio requirement
- Execution sequencing and leg risk

**Sizing framework:**
- Position size vs. divergence magnitude
- Accounting for convergence time uncertainty
- Position limits (100 per option, 300 total)

**Exit discipline:**
- Target convergence levels
- Time-based stops
- What if divergence widens further?
- Managing paired positions that drift

## Measuring Success

### Primary Metrics

**Signal Effectiveness:**
```
Convergence Capture Rate = Actual P&L / Theoretical Convergence Value
Signal Hit Rate = Profitable Convergence Trades / Total Signals
Average Convergence Time = Time from Entry to Exit
```

**Arbitrage Purity:**
```
Market Neutrality = |Beta to Market| (target: <0.1)
Paired Trade Balance = Time Spent Within Ratio Limits / Total Time
Leg Risk Incidents = Unhedged Exposure Events
```

**Risk-Adjusted Performance:**
```
Sharpe Ratio (target: >2.5 given lower risk)
Maximum Divergence Drawdown
Win Rate vs. Average Win/Loss
Capital Efficiency = P&L / Average Capital Deployed
```

### Research Quality Indicators

Track your understanding of the arbitrage mechanism:

1. **Convergence Modeling**: How accurately do you predict convergence times?
2. **False Signal Analysis**: Can you identify patterns in failed trades?
3. **Execution Efficiency**: Slippage and timing analysis
4. **Market Regime Performance**: Does your strategy work in all volatility regimes?

## Starting Points

### Data Analysis Questions

1. **Historical Divergence Patterns**
   - Distribution of divergence magnitudes
   - Autocorrelation of tracking errors
   - Mean reversion half-life estimation

2. **Options Arbitrage Analysis**
   - Compare option vs. underlying arbitrage profitability
   - Implied volatility surface divergences
   - Greeks alignment between products

3. **Execution Study**
   - Optimal leg ordering
   - Market impact of paired trades
   - Transaction cost analysis

### Simple Framework to Build On

```python
# Skeleton - expand based on your research
def evaluate_divergence(signal, market_state):
    """
    signal: {spx_price, spy_price, theoretical_spy, divergence_pct, confidence}
    market_state: {option_prices, recent_convergence_times, positions}

    returns: {trade_pairs, sizes, urgency, expected_convergence_time}
    """
    # Your research determines the logic
    pass

def construct_paired_trade(divergence, instruments_available):
    """
    Maintain market neutrality while capturing convergence
    Handle the 10:1 value ratio requirement
    Minimize leg risk
    """
    pass

def manage_convergence_risk(position_pair, time_elapsed, current_divergence):
    """
    When to add to positions vs. exit
    Handle divergence expansion scenarios
    Maintain paired trade discipline
    """
    pass
```

## What Success Looks Like

A successful arbitrage desk will:

1. **Master convergence timing** - knowing when to enter and when to wait
2. **Maintain strict neutrality** - never become directionally exposed
3. **Execute efficiently** - minimal slippage on paired trades
4. **Scale intelligently** - size based on convergence probability and timeframe
5. **Stay disciplined** - resist trading non-converging divergences
