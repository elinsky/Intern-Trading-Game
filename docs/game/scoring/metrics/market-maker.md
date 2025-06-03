# Market Maker Scoring Metrics

## Primary KPIs (40% of Score)

### 1. Spread Capture Efficiency
**Definition**: P&L generated per dollar of spread quoted

**Calculation**:
```
Spread Capture = (Sell Price - Buy Price) - (Mid Price Movement)
Efficiency = Total Spread Capture / Total Quoted Spread Value
```

**Targets**:
- Excellent: >60% capture rate
- Good: 40-60% capture rate  
- Acceptable: 25-40% capture rate
- Poor: <25% capture rate

**Tips**:
- Tighter spreads with higher turnover often beat wide spreads
- Adjust spreads based on volatility regime
- Skew quotes based on inventory position

### 2. Quote Coverage (Uptime)
**Definition**: Percentage of time actively quoting each instrument

**Requirements**:
- Minimum 80% uptime per instrument
- Both bid and ask must be present
- Reasonable spread width required

**Scoring**:
- 95-100% uptime: Full marks
- 85-95% uptime: 90% of marks
- 80-85% uptime: 75% of marks
- <80% uptime: Severe penalties

**Monitoring**:
```python
uptime = (ticks_with_quotes / total_ticks) * 100
coverage = (instruments_quoted / total_instruments) * 100
```

### 3. Volume Share
**Definition**: Percentage of total market volume traded

**Calculation**:
```
Volume Share = Your Volume / Total Market Volume
```

**Benchmarks**:
- Market leader: >40% share
- Strong competitor: 25-40%
- Average: 15-25%
- Below average: <15%

### 4. Inventory Turnover
**Definition**: How quickly positions are cycled

**Calculation**:
```
Turnover = Total Volume Traded / Average Absolute Position
```

**Targets**:
- High frequency: >20x daily
- Medium frequency: 10-20x daily
- Low frequency: 5-10x daily
- Poor: <5x daily

## Position Management (15% of Score)

### Inventory Limits
**Hard Limits**:
- ±50 contracts per option
- ±200 total portfolio

**Scoring Impact**:
- Within limits always: Full marks
- Minor breaches (<10%): -5% penalty
- Major breaches (10-25%): -15% penalty
- Severe breaches (>25%): -30% penalty

### Inventory Distribution
**Ideal Profile**:
- Mean position near zero
- Quick mean reversion
- Avoid persistent directional bias

**Metrics**:
```python
mean_position = average(daily_positions)
position_volatility = stdev(positions)
max_position = max(abs(positions))
```

## Risk-Adjusted Performance (15% of Score)

### Sharpe Ratio
**Calculation**:
```
Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
```

**Benchmarks**:
- Excellent: >3.0
- Good: 2.0-3.0
- Acceptable: 1.0-2.0
- Poor: <1.0

### Maximum Drawdown
**Definition**: Largest peak-to-trough decline

**Targets**:
- Excellent: <5% of capital
- Good: 5-10%
- Acceptable: 10-15%
- Poor: >15%

### P&L Volatility
**Measurement**: Standard deviation of 5-minute P&L

**Goals**:
- Consistent small profits
- Avoid large swings
- Quick recovery from losses

## Fee Optimization

### Maker Rebate Capture
**Your Advantage**: +$0.02 per contract (2x normal)

**Optimization Strategies**:
1. **Maximize Passive Fills**
   - Post limits early
   - Avoid aggressive orders
   - Use quote orders efficiently

2. **Volume Generation**
   - High turnover at tight spreads
   - Multiple strikes simultaneously
   - Both SPX and SPY products

3. **Expected Impact**
   ```
   Daily Rebate = Volume × Hit Rate × $0.02
   Example: 10,000 × 0.6 × $0.02 = $120/day
   ```

## Advanced Metrics

### Quote-to-Fill Ratio
**Definition**: Percentage of quotes that get filled

**Targets**:
- Optimal: 40-60% (balanced)
- Too high: >70% (quotes too aggressive)
- Too low: <30% (quotes too wide)

### Bid-Ask Balance
**Measurement**: Ratio of bid fills to ask fills

**Ideal**: Close to 1:1
- Skewed ratios indicate poor inventory management
- Adjust quote prices to rebalance

### Speed Metrics
**Response Time**: Speed to update quotes after fills
- Target: <100ms
- Faster updates capture more edge

## Daily Performance Checklist

### Pre-Market
- [ ] Check system connectivity
- [ ] Verify position limits configuration
- [ ] Review overnight positions (should be zero)
- [ ] Set initial quote widths

### During Trading
- [ ] Monitor uptime percentage
- [ ] Track inventory levels
- [ ] Adjust spreads for volatility
- [ ] Rebalance skewed positions

### Post-Market
- [ ] Calculate daily metrics
- [ ] Review P&L attribution
- [ ] Analyze quote efficiency
- [ ] Plan improvements

## Common Market Maker Mistakes

### 1. Quote Width Problems
- **Too Tight**: Excessive adverse selection
- **Too Wide**: Lost volume and rebates
- **Static**: Not adjusting for conditions

### 2. Inventory Mismanagement
- Letting positions drift
- Not skewing quotes to rebalance
- Hitting position limits

### 3. Uptime Failures
- System disconnections
- Not quoting all products
- Removing quotes during volatility

## Optimization Strategies

### Dynamic Spread Adjustment
```python
base_spread = 0.20  # $0.20 base
vol_adjustment = current_vol / normal_vol
inventory_skew = position / position_limit * 0.5
final_spread = base_spread * vol_adjustment * (1 + abs(inventory_skew))
```

### Inventory-Based Skewing
```python
if position > 0:  # Long inventory
    bid_price = mid - spread/2 - skew
    ask_price = mid + spread/2  # Normal ask
else:  # Short inventory
    bid_price = mid - spread/2  # Normal bid
    ask_price = mid + spread/2 + skew
```

### Cross-Product Hedging
- Use SPX/SPY correlation
- Offset inventory across products
- Maintain total portfolio limits

## Success Factors

### Technical Excellence
1. **Low Latency**: Sub-second quote updates
2. **High Reliability**: 99%+ system uptime
3. **Smart Execution**: Efficient order management

### Strategic Sophistication
1. **Dynamic Pricing**: Adapt to market conditions
2. **Risk Management**: Stay within limits always
3. **Edge Optimization**: Maximize rebate capture

### Continuous Improvement
1. **Metric Tracking**: Monitor all KPIs real-time
2. **Strategy Iteration**: Test and refine approaches
3. **Competition Analysis**: Learn from others' trades

Remember: Consistent small profits with high volume beats sporadic large wins. Focus on reliability, efficiency, and strict risk management.