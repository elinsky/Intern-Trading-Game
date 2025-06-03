# Scoring & Evaluation Overview

## Scoring Philosophy

Teams are evaluated on both quantitative performance and qualitative factors. Each role has distinct KPIs that reflect their unique constraints and objectives. Success requires not just profitability, but also adherence to role requirements and demonstration of learning.

## Scoring Components

### Quantitative Metrics (70%)

| Component | Weight | Description |
|-----------|--------|-------------|
| **Primary KPIs** | 40% | Role-specific performance metrics |
| **Position Compliance** | 15% | Adherence to position limits |
| **Risk Management** | 15% | Drawdown control, volatility management |

### Qualitative Factors (30%)

| Component | Weight | Description |
|-----------|--------|-------------|
| **Research Quality** | 15% | Backtesting, analysis, insights |
| **Code & Documentation** | 10% | Implementation quality |
| **Team Collaboration** | 5% | Effective teamwork |

## Role-Specific Evaluation

Each role is scored on different primary KPIs that align with their trading mandate:

### Market Maker Focus
- Spread capture efficiency
- Quote uptime (≥80% required)
- Volume share
- Inventory turnover

[Detailed Market Maker Metrics](metrics/market-maker.md)

### Hedge Fund Focus
- Total P&L generation
- Risk-adjusted returns (Sharpe)
- Signal utilization effectiveness
- Volatility edge capture

[Detailed Hedge Fund Metrics](metrics/hedge-fund.md)

### Arbitrage Desk Focus
- Convergence trade profitability
- Signal response efficiency
- Paired trade maintenance
- Risk-neutral performance

[Detailed Arbitrage Desk Metrics](metrics/arbitrage-desk.md)

## Position Limit Compliance

Staying within position limits is crucial for scoring:

### Penalty Structure

| Violation Level | Over Limit | Score Impact |
|----------------|------------|--------------|
| **Minor** | <10% | -5% penalty |
| **Major** | 10-25% | -15% penalty |
| **Severe** | >25% | -30% penalty |

### Monitoring
- Real-time position tracking
- Automatic warnings at 80% of limit
- Daily compliance reports

## Fee Structure Normalization

Different fee structures are normalized in scoring:

- **Market Makers**: Expected higher gross P&L due to rebates
- **Others**: Lower gross margins factored into scoring
- **Comparison**: Performance ranked within role groups

## Evaluation Periods

### Weekly Reviews
- Position compliance check
- P&L progression
- Strategy effectiveness
- Quick feedback provided

### Mid-Game Assessment
- Comprehensive performance review
- Strategy pivot opportunities
- Additional guidance offered

### Final Evaluation
- Complete quantitative analysis
- Code review
- Research assessment
- Presentation scores

## What Makes a Winning Team

### Quantitative Excellence
1. **Consistent Profitability**: Not just final P&L, but steady growth
2. **Risk Control**: Low drawdowns relative to returns
3. **Role Mastery**: Fully utilizing role advantages
4. **Compliance**: Perfect position limit adherence

### Qualitative Distinction
1. **Innovation**: Creative strategies within constraints
2. **Adaptation**: Improving strategies based on results
3. **Understanding**: Deep knowledge of market mechanics
4. **Documentation**: Clear explanation of approach

## Final Presentation (Week 8)

### Required Components
1. **Performance Summary**
   - P&L curves and key metrics
   - Position limit compliance record
   - Risk statistics

2. **Strategy Explanation**
   - How you exploited your role's edge
   - Key innovations or insights
   - Technical implementation details

3. **Lessons Learned**
   - What worked well
   - What failed and why
   - Key market insights gained

4. **Future Improvements**
   - Specific recommendations
   - Unexplored opportunities
   - Scaling considerations

### Presentation Format
- 15-minute presentation
- 10-minute Q&A
- Visual aids encouraged
- Code demos optional

## Common Pitfalls to Avoid

### Quantitative Mistakes
- Ignoring position limits until too late
- Over-trading and fee bleeding
- Not using role advantages fully
- Poor risk management

### Qualitative Errors
- Lack of documentation
- No strategy iteration
- Poor team coordination
- Weak final presentation

## Success Tips

1. **Start Strong**: Build robust infrastructure early
2. **Monitor Continuously**: Track all metrics daily
3. **Iterate Quickly**: Test and improve strategies
4. **Document Everything**: Keep detailed records
5. **Collaborate**: Leverage team strengths

## Next Steps

- Review your [role-specific metrics](metrics/)
- Understand [evaluation periods](evaluation-periods.md)
- Plan your strategy with scoring in mind
- Set up metric tracking in your bot