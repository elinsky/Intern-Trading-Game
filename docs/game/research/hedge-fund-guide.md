# Hedge Fund Research Guide

## Your Edge

You receive advance warning of volatility regime changes:
- **Accuracy**: 66%
- **Lead time**: 1-5 ticks before the event
- **Content**: Current regime, next regime, transition probability

This is your only systematic advantage. Everything else depends on how well you model and exploit this signal.

## The Core Research Problem

### 1. Understanding Your Signal

Your signal is imperfect. You need to understand:

- What does 66% accuracy actually mean for your P&L?
- How does signal value decay over the 1-5 tick window?
- When should you trust the signal vs. when should you fade it?

Key questions to investigate:
- If the signal says "going to high vol", what's the actual probability?
- How often do you get consecutive false signals?
- Does signal accuracy vary by regime type or market conditions?

### 2. Modeling the Opportunity

Volatility regime changes create pricing dislocations. You need to model:

**Price dynamics:**
- How do option prices behave during regime transitions?
- What's the typical magnitude of repricing?
- Which strikes/expirations offer the best risk/reward?

**Timing dynamics:**
- How quickly does the market incorporate regime changes?
- What's the optimal entry point given your lead time?
- When do you exit - immediately after transition or hold longer?

**Risk dynamics:**
- What happens when your signal is wrong?
- How do you size positions with uncertain information?
- What's your maximum acceptable drawdown from false signals?

### 3. Making Trading Decisions

Transform your research into executable strategies:

**Position construction:**
- Single options vs. spreads vs. complex structures
- Strike selection methodology
- Expiration preferences
- SPX vs. SPY allocation

**Sizing framework:**
- How much capital per signal?
- Scaling with confidence/market conditions
- Position limits (150 per option, 500 total)

**Execution discipline:**
- Entry triggers and timing
- Exit criteria (profit targets, stop losses, time-based)
- What to do when signals conflict with market action

## Measuring Success

### Primary Metrics

**Signal Effectiveness:**
```
Signal Sharpe = (Avg Return per Signal) / (Std Dev of Signal Returns)
Signal Hit Rate = Profitable Signals / Total Signals
Signal Capture = Actual P&L / Theoretical Maximum P&L
```

**Risk-Adjusted Performance:**
```
Overall Sharpe Ratio (target: >2.0)
Maximum Drawdown (target: <15%)
Downside Deviation
Recovery Time from Drawdowns
```

**Strategy Efficiency:**
```
Avg P&L per Signal Used
Percentage of Signals Acted Upon
False Signal Loss Ratio
Win/Loss Ratio
```

### Research Quality Indicators

You're not just trading - you're doing research. Track:

1. **Model Accuracy**: How well do your predictions match reality?
2. **Parameter Stability**: Do your models need constant retuning?
3. **Out-of-Sample Performance**: Does your edge persist?
4. **Regime Analysis**: Performance breakdown by volatility regime

## Starting Points

### Data Analysis Questions

1. **Historical Signal Analysis**
   - Plot actual regime changes vs. signal predictions
   - Calculate conditional probabilities
   - Identify patterns in false signals

2. **Price Behavior Study**
   - How do ATM options reprice during transitions?
   - What about skew changes?
   - Time decay during different regimes

3. **Optimal Structure Analysis**
   - Backtest simple structures: long calls/puts, straddles, spreads
   - Compare risk/reward profiles
   - Account for transaction costs

### Simple Framework to Build On

```python
# Skeleton - expand based on your research
def evaluate_signal(signal, market_context):
    """
    signal: {current_regime, next_regime, probability, ticks_until}
    market_context: {current_prices, recent_moves, positions}

    returns: {trade_decision, size, structure, confidence}
    """
    # Your research determines what goes here
    pass

def size_position(confidence, expected_edge, risk_parameters):
    """
    Don't just use Kelly blindly - understand why
    Consider signal decay, regime duration, false signal cost
    """
    pass
```

## What Success Looks Like

A successful hedge fund team will:

1. **Deeply understand their signal** - not just use it blindly
2. **Develop a coherent framework** - linking signal → model → trades → P&L
3. **Show clear research process** - hypotheses, tests, conclusions
4. **Adapt over time** - strategies should evolve with market data
5. **Manage risk intelligently** - especially around false signals
