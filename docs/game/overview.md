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

The market operates with **continuous trading** throughout the day:

1. **9:30 AM - Opening Rotation**: Batch auction determines opening prices
2. **9:30 AM - 3:00 PM - Continuous Trading**:
   - Submit orders anytime
   - Immediate order matching
   - Real-time position updates
3. **Throughout the Day**:
   - Underlying prices update continuously
   - News events occur randomly (1-4 hours apart)
   - Role-specific signals provided in real-time

## Choose Your Role

Each team is assigned one trading role with unique advantages and constraints:

| Role | Strategy Focus | Key Advantage | Main Challenge |
|------|----------------|---------------|----------------|
| **Market Maker** | Provide liquidity | +$0.02 maker rebates | Must quote 80% uptime |
| **Hedge Fund** | Gamma trading | Advance vol signals | ±50 delta neutrality |
| **Arbitrage Desk** | SPX-SPY convergence | Tracking error signals | Maintain paired trades |

## Evaluation

Teams are scored on:

- **P&L Performance**: Risk-adjusted returns
- **Role Compliance**: Meeting specific constraints
- **Strategy Quality**: Sophistication and robustness
- **Research Output**: Quality of analysis and documentation

## Trading Schedule

- **Days**: Tuesday and Thursday only
- **Hours**: 9:30 AM - 3:00 PM CT
- **Duration**: 4 weeks (8 trading days total)

## Key Features

### Real-time Market Data

- Live order books with depth
- Continuous price updates
- Immediate trade confirmations

### Advanced Signals

- Role-specific alpha signals
- Volatility regime indicators
- Cross-asset correlations

### Risk Management

- Position limits by instrument
- Real-time P&L tracking
- Automated compliance checks

## Success Factors

1. **Technical Excellence**: Robust, low-latency trading infrastructure
2. **Quantitative Edge**: Data-driven strategy development
3. **Risk Discipline**: Consistent position and exposure management
4. **Role Mastery**: Leveraging your desk's unique advantages

## Getting Started

1. Review [Core Concepts](fundamentals/core-concepts.md)
2. Study your assigned [Role](roles/overview.md)
3. Understand [Trading Rules](trading/order-types.md)
4. Set up your [Development Environment](../technical/index.md)
5. Begin strategy research and backtesting

## Support Resources

- Game rules documentation (this guide)
- Technical API documentation
- Example trading bots
- Historical market data for backtesting
- Discord channel for questions

Remember: Success comes from understanding your role's edge, managing risk effectively, and executing a well-researched strategy consistently.
