# Intern Trading Game: Overview

## Game Objective

Create a realistic, role-based market simulation where each intern team acts as a trading desk. Teams develop automated trading strategies, compete on role-specific performance metrics, and gain hands-on experience in quantitative trading.

## What You'll Build

Each team develops a trading bot that:
- Connects to the market simulation
- Analyzes real-time market data and signals
- Executes trades based on your strategy
- Manages risk within role constraints

## Market Structure

The game simulates two correlated underlyings with options:

| Instrument | Description | Key Features |
|------------|-------------|--------------|
| **SPX** | S&P 500 Index | High-dollar value, moderate volatility |
| **SPY** | S&P 500 ETF | Tracks SPX with noise and lag |
| **Options** | European calls/puts | ~5 strikes, 2-3 expirations per underlying |

## How It Works

Every **5 minutes**, a new market tick occurs with precise timing:

1. **T+0:00 - Price Generation**: New underlying prices calculated
2. **T+0:30 to T+3:00 - Order Window**: Bots submit orders (2.5 minute window)
3. **T+3:00 - Order Cutoff**: No new orders accepted after this point
4. **T+3:30 - Trade Matching**: All orders processed and trades executed
5. **T+4:00 - Results Published**: Positions, P&L, and market data updated

## Choose Your Role

Each team is assigned one trading role with unique advantages and constraints:

| Role | Strategy Focus | Key Advantage | Main Challenge |
|------|----------------|---------------|----------------|
| **Market Maker** | Provide liquidity | +$0.02 maker rebates | Must quote 80% uptime |
| **Hedge Fund** | Gamma trading | Advance vol signals | ±50 delta neutrality |
| **Arbitrage Desk** | SPX-SPY convergence | Tracking error signals | Maintain paired trades |

## Evaluation

Teams are scored on:
- **Quantitative Performance**: Role-specific metrics (P&L, Sharpe, spread capture)
- **Strategy Development**: Code quality, innovation, and adaptation
- **Research & Analysis**: Backtesting, signal validation, risk management
- **Final Presentation**: Insights, learnings, and recommendations

## Getting Started

1. **Understand Your Role**: Read your specific [role documentation](roles/)
2. **Learn the Mechanics**: Review [game fundamentals](fundamentals/core-concepts.md)
3. **Build Your Bot**: Follow the [technical documentation](../../technical/)
4. **Test Strategies**: Use historical data for backtesting
5. **Iterate & Improve**: Analyze results and refine your approach

## Timeline

- **Week 1-2**: Learn mechanics, build initial bot
- **Week 3-6**: Live trading, strategy refinement
- **Week 7-8**: Final optimization and presentations

**Trading Schedule**: Tuesdays & Thursdays only, 9:30 AM - 3:00 PM CT
**Non-Trading Days**: Monday (prep), Wednesday (analysis), Friday (retrospective)

Ready to start? Proceed to [Core Concepts](fundamentals/core-concepts.md)
