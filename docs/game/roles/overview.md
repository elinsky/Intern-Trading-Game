# Trading Roles Overview

## Role Comparison

Each team is assigned one of three primary trading roles, each with unique advantages, constraints, and performance metrics.

### Quick Comparison Table

| Aspect | Market Maker | Hedge Fund | Arbitrage Desk |
|--------|--------------|------------|----------------|
| **Primary Goal** | Provide liquidity | Align IV with RV | Capture mispricings |
| **Key Advantage** | +$0.02 maker rebate | Volatility signals | Tracking error signals |
| **Main Constraint** | 80% quote uptime | ±50 delta limit | Maintain paired trades |
| **Position Limits** | ±50 per option | 150 per option | 100 per option |
| **Order Types** | All (quotes required) | Limit/Market only | Limit/Market only |
| **Products** | SPX & SPY options | SPX & SPY options | SPX & SPY options |
| **Risk Profile** | Inventory risk | Gamma risk | Convergence risk |

## Role Descriptions

### Market Maker

**Mission**: Continuously provide two-sided quotes to ensure market liquidity

Market makers are the backbone of the options market, required to quote bid and ask prices at least 80% of the time. They earn enhanced rebates (+$0.02) for providing liquidity but must carefully manage inventory within tight limits (±50 contracts per option).

**Best Suited For**: Teams interested in high-frequency trading, automated market making, and inventory management.

[Detailed Market Maker Guide](market-maker.md)

### Hedge Fund

**Mission**: Keep implied volatility aligned with realized volatility through gamma trading

Hedge funds receive advance volatility regime signals (66% accuracy) allowing them to position gamma before regime changes. They must maintain delta neutrality (±50 deltas) which forces continuous rehedging, enabling profits from gamma scalping in high vol periods or premium collection in low vol periods.

**Best Suited For**: Teams interested in volatility trading, gamma scalping, and dynamic hedging strategies.

[Detailed Hedge Fund Guide](hedge-fund.md)

### Arbitrage Desk

**Mission**: Exploit price discrepancies between SPX and SPY options

Arbitrage desks receive real-time tracking error signals (80% accuracy) indicating when SPY has diverged from its theoretical relationship with SPX. They must maintain balanced positions across both products to capture convergence profits.

**Best Suited For**: Teams interested in statistical arbitrage, pairs trading, and market-neutral strategies.

[Detailed Arbitrage Desk Guide](arbitrage-desk.md)
