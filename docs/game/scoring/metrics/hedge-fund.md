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

### 4. Volatility Edge Capture
**Definition**: Profit from implied vs realized volatility trades

**Measurement**:
```
Vol P&L = Option P&L - Delta-Hedged Stock P&L
IV vs RV = (Implied Vol at Trade - Realized Vol) × Vega × Size
```

**Strategies Scored**:
- Long vol before regime shifts
- Short vol in stable regimes
- Volatility arbitrage across strikes
- Term structure trades

## Position Management (15% of Score)

### Position Limits Compliance
**Limits**:
- 150 contracts per option
- 500 total across all options
- One-sided positions only

**Scoring**:
- Always compliant: Full marks
- Minor breaches: -5% to -10%
- Major breaches: -15% to -30%
- Gross violations: Disqualification risk

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

### Directional Trading
**Scored Elements**:
- Entry timing with signals
- Position sizing logic
- Exit discipline
- Trend vs mean reversion balance

**Example Strategies**:
```python
# Signal-based directional trade
if volatility_signal.next_regime == "high" and confidence > 0.6:
    # Buy calls/puts based on additional indicators
    size = base_size * confidence * volatility_multiplier
```

### Volatility Strategies
**Types Valued**:
1. **Regime Trading**
   - Long vol before shifts
   - Short vol in calm periods
   
2. **Spread Strategies**
   - Calendars for term structure
   - Verticals for directional vol
   
3. **Premium Selling**
   - Iron condors in low vol
   - Strangles with edge

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

### 1. Over-Trading
- Acting on every signal
- Excessive position turnover
- Fee bleed from impatience

### 2. Poor Signal Discipline
- Ignoring high-confidence signals
- Trading against signals
- Not waiting for confirmation

### 3. Risk Mismanagement
- Position sizing too large
- No stop-loss discipline
- Correlation concentration

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

Remember: Hedge funds win through strategic thinking and disciplined execution. Your volatility signal is a powerful edge—use it wisely, size appropriately, and manage risk religiously.