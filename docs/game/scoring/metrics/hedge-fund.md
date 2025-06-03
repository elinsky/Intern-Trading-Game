# Hedge Fund Scoring Metrics

## Primary KPIs (40% of Score)

### 1. Total P&L Generation
**Definition**: Absolute profit generated over the game period

**Measurement**:
```
Total P&L = Final Portfolio Value - Starting Value
Daily P&L = Sum of (Trade P&L + Position Mark-to-Market)
```

**Benchmarks**:
- Excellent: >15% return on notional
- Good: 10-15% return
- Acceptable: 5-10% return
- Poor: <5% return

**Considerations**:
- Raw P&L normalized by role
- Consistency valued over single large wins
- Drawdowns heavily penalized

### 2. Risk-Adjusted Returns (Sharpe Ratio)
**Definition**: Return per unit of risk taken

**Calculation**:
```
Sharpe = (Average Return - Risk Free Rate) / Std Dev of Returns
Annualized Sharpe = Daily Sharpe × √252
```

**Targets**:
- Excellent: >2.5
- Good: 1.5-2.5
- Acceptable: 0.8-1.5
- Poor: <0.8

**Optimization**:
- Size positions based on conviction
- Reduce trading during uncertain periods
- Maintain consistent risk levels

### 3. Signal Utilization Rate
**Definition**: How effectively you use the volatility forecast signal

**Metrics**:
```
Signal Trading Rate = Trades Triggered by Signal / Total Signals
Signal P&L = P&L from Signal-Based Trades / Total P&L
Signal Accuracy = Profitable Signal Trades / Total Signal Trades
```

**Scoring**:
- Excellent: >80% signals acted upon profitably
- Good: 60-80% effective usage
- Acceptable: 40-60% usage
- Poor: <40% or ignoring signals

### 4. Gamma Trading Performance
**Definition**: Profit from gamma scalping and premium collection through dynamic hedging

**Measurement**:
```
Rehedging P&L = Sum of (Underlying trades × Price moves)
Gamma P&L = Total Option P&L - Premium paid/received - Rehedging P&L
Delta Compliance = Ticks within ±50 delta / Total ticks
```

**Strategies Scored**:
- Gamma scalping profits in high vol regimes
- Premium collection in low vol regimes
- Rehedging efficiency and timing
- Delta neutrality maintenance

## Position Management (15% of Score)

### Position Limits & Delta Compliance
**Limits**:
- 150 contracts per option
- 500 total across all options
- ±50 portfolio delta at all times
- One-sided positions only

**Scoring**:
- Always compliant: Full marks
- Delta breaches: -2% per tick over limit
- Position breaches: -5% to -10%
- Gross violations: Major penalties

### Position Sizing Excellence
**Metrics**:
```
Kelly Fraction Used = Actual Size / Optimal Size
Concentration = Largest Position / Total Portfolio
Utilization = Average Position / Position Limit
```

**Best Practices**:
- Scale with signal confidence
- Diversify across strikes/expiries
- Reserve capacity for opportunities

## Risk Management (15% of Score)

### Maximum Drawdown Control
**Definition**: Largest peak-to-trough decline

**Targets**:
- Excellent: <10%
- Good: 10-15%
- Acceptable: 15-20%
- Poor: >20%

**Recovery Metrics**:
- Time to recover from drawdown
- Drawdown frequency
- Risk reduction during losses

### Trade Win Rate
**Calculation**:
```
Win Rate = Profitable Trades / Total Trades
Profit Factor = Gross Profits / Gross Losses
```

**Benchmarks**:
- Win Rate: 45-65% (quality over quantity)
- Profit Factor: >1.5
- Average Win/Loss Ratio: >1.2

## Strategy Sophistication

### Gamma Positioning
**Scored Elements**:
- Gamma exposure matching volatility regime
- Delta-neutral entry structures
- Rehedging frequency optimization
- Transaction cost management

**Example Strategies**:
```python
# Signal-based gamma positioning
if volatility_signal.next_regime == "high" and confidence > 0.6:
    # Build long gamma position (buy straddle/strangle)
    # Plan frequent rehedging to capture gamma profits
elif volatility_signal.next_regime == "low":
    # Build short gamma position (sell straddle/strangle)
    # Collect premium with minimal rehedging
```

### Delta-Neutral Strategies
**Types Valued**:
1. **High Vol Regime**
   - Long gamma via straddles/strangles
   - Active rehedging to scalp gamma
   - Profit from underlying movement

2. **Low Vol Regime**
   - Short gamma positions
   - Premium collection focus
   - Minimal rehedging needed

3. **Transition Management**
   - Pre-position gamma before signals
   - Adjust strikes for optimal exposure
   - Balance gamma vs theta decay

### Event-Driven Trading
**Approach**:
- Pre-position before news
- React to probability tables
- Combine with vol signals
- Quick profit taking

## Signal Analysis Scoring

### Signal Reception Quality
**Tracking**:
```python
signals_received = []
signal_latency = []
signal_accuracy_realized = []
```

### Signal Response Time
**Metrics**:
- Average time to trade after signal
- Percentage traded within 1 tick
- P&L decay by response time

### Signal Enhancement
**Advanced Usage**:
- Combine with other indicators
- Filter false positives
- Size based on signal strength
- Track signal regime performance

## Fee Impact Analysis

### Execution Cost Management
**Your Reality**: -$0.02 taker fee, +$0.01 maker rebate

**Optimization**:
```
Execution Cost = (Taker Volume × 0.02) - (Maker Volume × 0.01)
Cost as % of P&L = Execution Cost / Gross P&L
```

**Targets**:
- Keep costs <20% of gross P&L
- Use limit orders when possible
- Balance urgency vs cost

## Daily Checklist

### Pre-Market Preparation
- [ ] Review overnight signals
- [ ] Check position capacity
- [ ] Set volatility expectations
- [ ] Plan entry/exit levels

### Active Trading
- [ ] Monitor signal feed
- [ ] Track position sizes
- [ ] Calculate real-time P&L
- [ ] Adjust for regime changes

### Post-Market Analysis
- [ ] Review signal performance
- [ ] Calculate daily metrics
- [ ] Update strategy parameters
- [ ] Document lessons learned

## Common Hedge Fund Pitfalls

### 1. Delta Limit Violations
- Failing to rehedge promptly
- Taking directional bets
- Ignoring gamma's impact on delta

### 2. Poor Gamma Management
- Wrong gamma sign for regime
- Over/under hedging positions
- Ignoring transaction costs

### 3. Signal Misuse
- Not pre-positioning gamma
- Trading gamma without signals
- Missing regime transitions

## Advanced Scoring Considerations

### Strategy Innovation
**Bonus Points For**:
- Novel signal interpretations
- Creative option strategies
- Regime-specific adaptations
- Cross-product opportunities

### Research Quality
**Evaluated On**:
- Backtesting thoroughness
- Parameter optimization
- Out-of-sample validation
- Economic rationale

### Adaptation Speed
**Measured By**:
- Strategy changes over time
- Performance improvement curve
- Learning from losses
- Market regime adjustments

## Success Formula

### Week 1-2: Foundation
1. Build robust signal handler
2. Implement core strategies
3. Test position sizing logic

### Week 3-6: Optimization
1. Refine signal filters
2. Add strategy variations
3. Improve execution timing

### Week 7-8: Polish
1. Focus on consistency
2. Document everything
3. Prepare presentation

## Key Differentiators

### What Separates Winners

1. **Signal Mastery**
   - Creative interpretation
   - High hit rate
   - Optimal sizing

2. **Risk Discipline**
   - Consistent position sizes
   - Quick loss cutting
   - Drawdown recovery

3. **Execution Excellence**
   - Cost consciousness
   - Timing precision
   - Order type selection

Remember: Hedge funds win through disciplined gamma trading. Your volatility signal tells you when to be long or short gamma, while the delta constraint forces profitable rehedging. Master this dynamic to align IV with RV and capture consistent profits.
