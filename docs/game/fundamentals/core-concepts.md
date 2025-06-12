# Core Concepts

Understanding these fundamental concepts is essential for success in the Intern Trading Game.

## Market Participants

### Trading Desks

Each intern team operates as one of three specialized trading desks:

- **Market Makers**: Provide liquidity by continuously quoting bid/ask prices
- **Hedge Funds**: Take directional or volatility positions using signals
- **Arbitrage Desks**: Exploit price discrepancies between SPX and SPY

### Retail Flow

Automated simulation adds realistic retail trading patterns, market noise, and liquidity.

## Key Trading Terms

### Order Types

- **Limit Order**: Buy/sell at a specific price or better
- **Market Order**: Buy/sell immediately at best available price
- **Quote**: Simultaneous bid and ask (market makers only)

### Market Mechanics

- **Bid**: Price at which someone is willing to buy
- **Ask**: Price at which someone is willing to sell
- **Spread**: Difference between bid and ask prices
- **Tick**: 5-minute interval when new prices are generated

### Options Terminology

- **Strike Price**: Price at which option can be exercised
- **Expiration**: Date when option expires
- **European Style**: Can only be exercised at expiration
- **Call Option**: Right to buy at strike price
- **Put Option**: Right to sell at strike price

## Information Flow

### Market Data

All participants receive:

- Current bid/ask prices for all instruments
- Last trade prices and volumes
- Order book depth (top 5 levels)
- Historical tick data

### News Events

Published every 1-4 hours with known probability impacts:

- May trigger volatility regime changes
- May cause price jumps
- Create trading opportunities

### Alpha Signals

Role-specific information advantages:

- **Hedge Funds**: Advance volatility regime warnings
- **Arbitrage Desks**: SPX-SPY tracking error signals
- **Market Makers**: Must infer from price action

## Risk Management

### Position Limits

Each role has specific constraints:

- Maximum positions per instrument
- Total portfolio limits
- Inventory management requirements

### Performance Metrics

- P&L
- Role-specific KPIs
- Strategy effectiveness


## Next Steps

With these concepts understood, explore:

- [Market Structure](market-structure.md) - Detailed instrument specifications
- [Game Mechanics](game-mechanics.md) - How the simulation operates
- Your specific [role documentation](../roles/overview.md)
