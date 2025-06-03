# Hedge Fund Research Guide

## Your Edge

You receive advance warning of volatility regime changes:
- **Accuracy**: 66%
- **Lead time**: 1-5 ticks before the event
- **Content**: Current regime, next regime, transition probability

Combined with your delta neutrality constraint (±50 deltas), this creates a systematic gamma trading opportunity where you profit from rehedging during volatility transitions.

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

Your mission is to align implied volatility with realized volatility through gamma trading. You need to model:

**Gamma dynamics:**
- How much gamma should you hold before each regime type?
- Which strikes/expirations provide optimal gamma exposure?
- How does gamma decay affect your rehedging profits?

**Rehedging dynamics:**
- How frequently should you rehedge to capture gamma scalping profits?
- What's the optimal rehedging threshold given transaction costs?
- How does the ±50 delta constraint affect your rehedging strategy?

**Regime-specific strategies:**
- **High vol regime**: Long gamma positions to profit from frequent rehedging
- **Low vol regime**: Short gamma to collect premium with minimal rehedging
- **Transitions**: How to position before and manage during regime changes

### 3. Making Trading Decisions

Transform your research into executable gamma trading strategies:

**Position construction:**
- Delta-neutral structures (straddles, strangles) to isolate gamma
- Strike selection for maximum gamma per dollar
- Expiration choice balancing gamma vs. theta decay
- Dynamic adjustment to maintain ±50 delta limit

**Sizing framework:**
- Gamma exposure per volatility regime
- Position sizing based on expected rehedging frequency
- Risk limits considering false signal scenarios
- Position limits (150 per option, 500 total)

**Rehedging discipline:**
- Delta threshold triggers (must stay within ±50)
- Underlying vs. options for rehedging
- Transaction cost optimization
- Gamma scalping execution during high vol periods

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

1. **Gamma Trading Analysis**
   - Calculate P&L from rehedging at different delta thresholds
   - Compare gamma scalping profits across volatility regimes
   - Optimize rehedging frequency vs. transaction costs

2. **Regime-Specific Gamma Study**
   - Measure actual realized vol in each regime
   - Calculate optimal gamma exposure per regime
   - Analyze gamma decay patterns and timing

3. **Delta Constraint Impact**
   - How does ±50 delta limit affect strategy choice?
   - Optimal structures to maximize gamma within delta constraints
   - Rehedging costs vs. gamma profits under different scenarios

### Simple Framework to Build On

```python
# Skeleton - expand based on your research
def evaluate_gamma_opportunity(signal, current_positions):
    """
    signal: {current_regime, next_regime, probability, ticks_until}
    current_positions: {options, underlying, net_delta, net_gamma}

    returns: {target_gamma, structure, rehedge_plan}
    """
    # Determine optimal gamma exposure for predicted regime
    pass

def manage_delta_constraint(portfolio_delta, gamma, underlying_price):
    """
    Maintain ±50 delta limit through dynamic rehedging
    Consider gamma impact on delta as underlying moves
    Balance rehedging costs vs. gamma scalping profits
    """
    pass

def calculate_rehedge_threshold(volatility_regime, gamma, transaction_costs):
    """
    Optimize rehedging frequency based on:
    - Expected underlying movement in regime
    - Current gamma exposure
    - Cost of rehedging
    """
    pass
```

## What Success Looks Like

A successful hedge fund team will:

1. **Master gamma trading mechanics** - understand how gamma generates P&L through rehedging
2. **Optimize for delta constraints** - use the ±50 limit as a feature, not a bug
3. **Match gamma to volatility regimes** - long gamma for high vol, short for low vol
4. **Execute disciplined rehedging** - systematic approach to delta management
5. **Measure window-based performance** - track P&L from event to event, not just daily
