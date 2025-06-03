# Trading Roles Overview

## Role Comparison

Each team is assigned one of three primary trading roles, each with unique advantages, constraints, and performance metrics.

### Quick Comparison Table

| Aspect | Market Maker | Hedge Fund | Arbitrage Desk |
|--------|--------------|------------|----------------|
| **Primary Goal** | Provide liquidity | Generate alpha | Capture mispricings |
| **Key Advantage** | +$0.02 maker rebate | Volatility signals | Tracking error signals |
| **Main Constraint** | 80% quote uptime | No two-sided quotes | Maintain paired trades |
| **Position Limits** | ±50 per option | 150 per option | 100 per option |
| **Order Types** | All (quotes required) | Limit/Market only | Limit/Market only |
| **Products** | SPX & SPY options | SPX & SPY options | SPX & SPY options |
| **Risk Profile** | Inventory risk | Directional risk | Convergence risk |

## Role Descriptions

### Market Maker

**Mission**: Continuously provide two-sided quotes to ensure market liquidity

Market makers are the backbone of the options market, required to quote bid and ask prices at least 80% of the time. They earn enhanced rebates (+$0.02) for providing liquidity but must carefully manage inventory within tight limits (±50 contracts per option).

**Best Suited For**: Teams interested in high-frequency trading, automated market making, and inventory management.

[Detailed Market Maker Guide](market-maker.md)

### Hedge Fund

**Mission**: Generate superior risk-adjusted returns using directional and volatility strategies

Hedge funds enjoy maximum flexibility in trading strategies and receive advance volatility regime signals (66% accuracy). They can take large directional positions (up to 150 contracts per option) but cannot quote two-sided markets.

**Best Suited For**: Teams interested in signal processing, directional trading, and volatility strategies.

[Detailed Hedge Fund Guide](hedge-fund.md)

### Arbitrage Desk

**Mission**: Exploit price discrepancies between SPX and SPY options

Arbitrage desks receive real-time tracking error signals (80% accuracy) indicating when SPY has diverged from its theoretical relationship with SPX. They must maintain balanced positions across both products to capture convergence profits.

**Best Suited For**: Teams interested in statistical arbitrage, pairs trading, and market-neutral strategies.

[Detailed Arbitrage Desk Guide](arbitrage-desk.md)

## Performance Metrics by Role

### Market Maker KPIs
1. **Spread Capture**: Profit from bid-ask spread
2. **Quote Uptime**: Percentage of time actively quoting
3. **Volume Share**: Portion of total market volume
4. **Inventory Turnover**: How quickly positions are flipped
5. **Risk-Adjusted P&L**: Sharpe ratio considering inventory risk

### Hedge Fund KPIs
1. **Total P&L**: Absolute profit generation
2. **Sharpe Ratio**: Risk-adjusted returns
3. **Signal Utilization**: How well volatility signals are used
4. **Hit Rate**: Percentage of profitable trades
5. **Maximum Drawdown**: Largest peak-to-trough loss

### Arbitrage Desk KPIs
1. **Arbitrage Capture**: Profit from convergence trades
2. **Signal Efficiency**: Percentage of signals traded
3. **Convergence Time**: Average time to close trades
4. **Position Balance**: How well paired trades are maintained
5. **Risk-Neutral P&L**: Returns excluding directional moves

## Strategy Considerations

### Market Maker Strategies
- Dynamic spread adjustment based on volatility
- Inventory-based quote skewing
- Cross-product hedging
- Mean reversion trading around inventory targets

### Hedge Fund Strategies
- Volatility regime trading (buying before vol increases)
- Directional momentum following
- Event-driven positioning
- Option spread strategies (calendars, verticals)

### Arbitrage Desk Strategies
- Pure convergence trades when signal fires
- Statistical mean reversion
- Cross-product option arbitrage
- Volatility surface arbitrage

## Choosing Your Approach

### Questions to Consider

1. **Risk Appetite**
   - Market Maker: Constant small risks
   - Hedge Fund: Larger directional risks
   - Arbitrage: Convergence timing risk

2. **Technical Complexity**
   - Market Maker: Requires fastest execution
   - Hedge Fund: Requires signal interpretation
   - Arbitrage: Requires precise pair management

3. **Team Strengths**
   - Strong coding: Market Maker
   - Strong analysis: Hedge Fund
   - Strong math/stats: Arbitrage

## Role Flexibility

While you cannot change roles during the game:
- You can adapt strategies within your role
- Innovation within constraints is encouraged
- Best teams often find creative approaches

## Automated Retail Flow

The market includes simulated retail trading activity:
- Configurable random order generation
- Behavioral patterns (momentum chasing, panic selling)
- Realistic biases (bullish tendency, OTM preference)
- Adds market noise and liquidity

[Retail Flow Configuration](retail.md)

## Success Factors

### Universal Requirements
- Strong programming skills for bot development
- Understanding of options pricing
- Risk management discipline
- Continuous strategy iteration

### Role-Specific Success Factors

**Market Makers Need**:
- Ultra-low latency execution
- Sophisticated inventory management
- Dynamic pricing models

**Hedge Funds Need**:
- Signal interpretation skills
- Position sizing expertise
- Market timing ability

**Arbitrage Desks Need**:
- Statistical modeling capability
- Patience for convergence
- Precise execution timing

## Next Steps

1. **Choose Your Role**: Discuss with your team which role aligns with your strengths
2. **Deep Dive**: Read your specific role documentation thoroughly
3. **Strategy Planning**: Begin designing your trading approach
4. **Technical Setup**: Start building your trading bot
5. **Practice**: Use historical data to backtest strategies

Remember: Success comes from deeply understanding your role's advantages and constraints, then building strategies that maximize the former while managing the latter.