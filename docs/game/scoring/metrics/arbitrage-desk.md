# Arbitrage Desk Scoring Metrics

## Primary KPIs (40% of Score)

### 1. Convergence Capture Rate
**Definition**: Profit extracted from SPX-SPY convergence opportunities

**Calculation**:
```
Convergence P&L = Sum of (Entry Spread - Exit Spread) × Position Size
Capture Rate = Actual P&L / Theoretical Maximum P&L
```

**Benchmarks**:
- Excellent: >70% capture rate
- Good: 50-70% capture rate
- Acceptable: 30-50% capture rate
- Poor: <30% capture rate

**Key Factors**:
- Entry timing precision
- Exit patience/discipline
- Position sizing accuracy
- Execution cost minimization

### 2. Signal Response Efficiency
**Definition**: How quickly and effectively you act on tracking error signals

**Metrics**:
```
Response Time = Trade Timestamp - Signal Timestamp
Signal Hit Rate = Profitable Signal Trades / Total Signals Received
Signal P&L Ratio = P&L from Signaled Trades / Total P&L
```

**Scoring Criteria**:
- Response within 1 tick: Full marks
- Response within 2-3 ticks: 80% marks
- Response within 4-5 ticks: 60% marks
- Slower responses: Declining value

### 3. Paired Trade Maintenance
**Definition**: How well you maintain balanced SPX/SPY positions

**Requirements**:
- Target ratio: 10:1 (SPX:SPY) by value
- Acceptable range: 8:1 to 12:1
- Both legs executed within same tick

**Scoring**:
```
Balance Score = Time in Balance / Total Time
Ratio Deviation = Average |Actual Ratio - 10| / 10
```

**Penalties**:
- Unbalanced >5 ticks: -5% score
- Single-leg exposure: -10% score
- Persistent imbalance: -20% score

### 4. Risk-Neutral P&L
**Definition**: Returns excluding directional market moves

**Calculation**:
```
Market-Neutral P&L = Total P&L - (Beta × Market Return)
Where Beta ≈ 0 for properly hedged positions
```

**Targets**:
- Consistent positive returns regardless of market direction
- Low correlation with SPX/SPY movements
- Minimal directional risk

## Position Management (15% of Score)

### Position Limits Compliance
**Constraints**:
- 100 contracts per option maximum
- 300 total portfolio limit
- Must maintain paired positions

**Scoring Impact**:
- Perfect compliance: 100% score
- Minor violations (<10%): -5%
- Major violations (10-25%): -15%
- Severe violations (>25%): -30%

### Leg Ratio Management
**Ideal Execution**:
```python
# Example proper ratio
spx_position = -10  # Short 10 SPX calls
spy_position = 100  # Long 100 SPY calls
value_ratio = (spx_position * spx_price) / (spy_position * spy_price)
# Should be close to -1 for market neutrality
```

## Risk Management (15% of Score)

### Convergence Risk Control
**Key Metrics**:
- Maximum time in position
- Drawdown per trade
- Win/loss ratio
- Recovery speed

**Best Practices**:
1. **Stop Losses**: Exit if divergence widens beyond threshold
2. **Time Stops**: Close positions not converging within expected timeframe
3. **Size Limits**: Scale based on signal confidence

### Execution Risk Management
**Challenges**:
- Leg risk (one side fills, other doesn't)
- Slippage on entry/exit
- Market impact on larger trades

**Scoring Elements**:
```
Execution Efficiency = (Mid Price at Signal - Actual Fill Price) / Spread
Leg Success Rate = Complete Pairs / Attempted Pairs
```

## Signal Utilization Excellence

### Signal Quality Assessment
**Your Advantage**: 80% accurate tracking error signals

**Optimal Usage**:
```python
def should_trade_signal(signal):
    if abs(signal.tracking_error) < 0.15:
        return False  # Too small
    if signal.z_score < 1.5:
        return False  # Not significant
    if not check_position_capacity():
        return False  # At limits
    return True
```

### Signal Filtering
**Advanced Strategies**:
1. **Magnitude Filters**: Only trade errors >0.20%
2. **Statistical Filters**: Z-score >2 for high conviction
3. **Regime Filters**: Adjust for volatility environment
4. **Capacity Filters**: Reserve space for best signals

### Multi-Signal Strategies
**Combining Indicators**:
- Tracking error signal (primary)
- Volatility regime (context)
- Recent convergence speed
- Market microstructure

## Arbitrage-Specific Metrics

### Spread Mean Reversion
**Analysis**:
```
Half-Life = -ln(2) / ln(autocorrelation)
Expected Profit = Entry Spread × (1 - e^(-time/half_life))
```

**Scoring Factors**:
- Accurate half-life estimation
- Optimal holding periods
- Entry point selection

### Cross-Product Greeks Management
**Considerations**:
- Delta neutrality maintenance
- Vega exposure from both legs
- Gamma differences
- Theta decay balance

**Example Hedge**:
```python
spx_delta = -10 * 0.5  # -5 delta from SPX position
spy_delta = 100 * 0.5  # +50 delta from SPY position
net_delta = spx_delta + spy_delta/10  # Scaled by price ratio
# Should be close to zero
```

## Fee Optimization

### Execution Cost Analysis
**Your Fees**: +$0.01 maker, -$0.02 taker

**Cost Minimization**:
```
Per Trade Cost = 2 × (Leg Size × Taker Fee)
Cost as % = Trade Cost / Expected Profit
```

**Strategies**:
- Use limit orders when possible
- Size trades to justify costs
- Quick execution for strong signals

## Daily Performance Tracking

### Pre-Market Setup
- [ ] Check signal system status
- [ ] Review overnight positions (should be flat)
- [ ] Calculate position capacity
- [ ] Set signal thresholds

### Live Trading
- [ ] Monitor tracking error signals
- [ ] Execute paired trades atomically
- [ ] Track leg ratios real-time
- [ ] Manage position limits

### Post-Market Review
- [ ] Calculate convergence P&L
- [ ] Analyze signal performance
- [ ] Review execution quality
- [ ] Update parameters

## Common Arbitrage Pitfalls

### 1. Leg Risk Disasters
- One leg fills, other rejected
- Naked directional exposure
- Panic closing at loss

### 2. Over-Trading Small Edges
- Trading every minor signal
- Fee bleed on small profits
- Capacity wasted on low-value trades

### 3. Convergence Impatience
- Closing too early
- Not waiting for full convergence
- Missing larger moves

## Advanced Scoring Elements

### Strategy Sophistication
**Bonus Points For**:
1. **Dynamic Thresholds**: Adjusting for market conditions
2. **Portfolio Optimization**: Multiple positions with correlation
3. **Options Surface Arb**: Exploiting vol differences
4. **Term Structure**: Calendar spread opportunities

### Research & Innovation
**Evaluated On**:
- Statistical analysis depth
- Convergence modeling
- Risk factor decomposition
- Out-of-sample testing

### Operational Excellence
**Measured By**:
- System uptime
- Execution precision
- Error recovery
- Position reconciliation

## Winning Formula

### Core Competencies

1. **Signal Discipline**
   - Trade only quality signals
   - Size based on conviction
   - Patient convergence waiting

2. **Execution Precision**
   - Atomic paired trades
   - Minimal slippage
   - Cost consciousness

3. **Risk Neutrality**
   - True market neutrality
   - Balanced Greeks
   - No directional bias

### Week-by-Week Focus

**Weeks 1-2**: Infrastructure
- Build paired execution system
- Test signal handling
- Verify ratio calculations

**Weeks 3-6**: Optimization
- Refine signal filters
- Improve execution timing
- Scale position sizing

**Weeks 7-8**: Consistency
- Focus on reliability
- Document strategies
- Prepare analysis

## Key Success Factors

### Technical Requirements
1. **Fast Execution**: Both legs within seconds
2. **Accurate Ratios**: Maintain 10:1 consistently
3. **Signal Processing**: Sub-second response

### Strategic Excellence
1. **Patient Convergence**: Wait for full mean reversion
2. **Selective Trading**: Quality over quantity
3. **Risk Discipline**: Stop losses on divergence

### Analytical Depth
1. **Statistical Modeling**: Understand convergence dynamics
2. **Market Microstructure**: Exploit temporary dislocations
3. **Performance Attribution**: Know your edge sources

Remember: Arbitrage profits come from discipline and precision. Your tracking error signal is highly accurate—trust it, execute flawlessly, and let convergence work in your favor. Success requires patience, technical excellence, and unwavering market neutrality.