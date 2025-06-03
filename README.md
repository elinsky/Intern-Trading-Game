# Intern-Trading-Game

Welcome to the Intern Trading Game! This repo contains the core simulation engine, matching logic, and reference tools for a role-based, options market-making game.

---

## Game Overview

- **Underlying Assets**: Simulated SPX and SPY spot prices
- **Instruments**: European options on SPX and SPY (~15 strikes covering ±30%, weekly expiries)
- **Trading Schedule**: Tuesday & Thursday only, 9:30 AM - 3:00 PM CT
- **Tick Frequency**: Every 5 minutes (66 ticks per trading day)
- **Submission**: Intern bots submit orders during 2-3 minute window
- **Evaluation**: Role-specific KPIs and quantitative research quality

---

## Core Gameplay Loop

1. **Tick Starts**
   - A new underlying price is simulated
   - A news event is published (may or may not trigger a volatility regime change)
   - Option prices are implied (but not published)

2. **Bot Submission Window (2–3 min)**
   - Intern bots read from the market data and news
   - Bots submit orders (limit/market)
   - Teams receive only the market data feeds, news feeds, and alpha signals

3. **Tick Processes**
   - Matching engine executes trades, applies fees, and updates P&L
   - Full market snapshot is published (order book, fills, position, P&L)

4. **Results and Analysis**
   - Interns can access dashboards or query data
   - Bots sleep or wait until the next tick

## Roles

Each intern team is assigned one of three trading roles. Each role exploits different structural fundamentals of the simulated market and comes with its own constraints, signals, and scoring objective.

### 1. Market Maker

**Objective**: Capture edge by quoting fair and profitable options prices

- **Signal Access**: None
- **Constraints**:
  - Must quote ≥80% of instruments each tick across both products
  - Position limits: ±50 per option, ±200 total
  - Enhanced fee structure: +$0.02 maker, -$0.01 taker
- **Scoring Focus**:
  - Spread capture per trade
  - Inventory risk management
  - Quoting coverage

### 2. Hedge Fund

**Objective**: Exploit advance knowledge of volatility regime changes

- **Signal Access**: Volatility regime forecast (66% accuracy, 1-5 ticks early)
- **Constraints**:
  - Position limits: 150 per option, 500 total
  - Cannot quote two-sided
  - Standard fees: +$0.01 maker, -$0.02 taker
- **Scoring Focus**:
  - Signal utilization effectiveness
  - Risk-adjusted returns
  - Volatility trading P&L

### 3. Arbitrage Desk

**Objective**: Exploit temporary mispricing between SPX and SPY options

- **Signal Access**: Tracking error signal (80% accuracy, real-time)
- **Constraints**:
  - Must maintain paired trades (target 10:1 SPX:SPY value ratio)
  - Position limits: 100 per option, 300 total
  - Standard fees: +$0.01 maker, -$0.02 taker
- **Scoring Focus**:
  - Profit from convergence trades
  - Precision of execution
  - Market neutrality maintenance

---

## Automated Retail Flow

**Objective**: Create realistic market noise and liquidity

- **Order Generation**: Poisson frequency (mean 3/tick), exponential sizing
- **Constraints**:
  - Max position: 50 contracts
  - Predominantly takes liquidity
  - Fees: -$0.01 maker, -$0.03 taker

## Market Fundamentals (Configurable)

The simulated market is controlled by a backend configuration that defines key structural dynamics. These parameters are not exposed directly, but interns may infer them through research.

| Fundamental | Description | Exploited By |
|-------------|-------------|--------------|
| Volatility Regimes | Market operates in low/medium/high vol states | Hedge Fund (via signal) |
| SPX-SPY Tracking Error | SPY diverges from theoretical SPX/10 relationship | Arbitrage Desk (via signal) |
| Spread Capture | Bid-ask spread with enhanced maker rebates | Market Maker |
| Retail Flow Patterns | Automated retail creates predictable flow | All roles |
| Information Asymmetry | Different roles receive different signals | Role-specific advantages |

Each role exploits one or more of these dynamics to generate P&L.

---


## Evaluation & Scoring

Each team is evaluated on role-specific KPIs:

| Role         | Key Metrics                                                       |
|--------------|--------------------------------------------------------------------|
| Market Maker | Spread P&L, quote uptime, inventory skew                          |
| Hedge Fund   | Vol trading edge (IV vs RV), risk-adjusted return, adaptability   |
| Arb Desk     | Spread convergence profit, fill efficiency, neutral compliance    |

Other qualitative factors:
- Research insight and postmortem quality
- Strategy evolution over time
- Code quality and clarity (optional)

## Future Extensions

- Enable earnings-style news events with clustered jumps
