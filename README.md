# Intern-Trading-Game

Welcome to the Intern Trading Game! This repo contains the core simulation engine, matching logic, and reference tools for a role-based, options market-making game.

## Quick Links

- **[Game Documentation](docs/game/)** - Complete game rules and mechanics
- **[Role Guides](docs/game/roles/)** - Detailed information for each trading role
- **[Research Guides](docs/game/research/)** - Quantitative research frameworks
- **[Trading Rules](docs/game/trading/)** - Order types, constraints, and execution
- **[Configuration](docs/game/configuration/)** - Game parameters and schedule

---

## Game Overview

- **Underlying Assets**: Simulated SPX and SPY spot prices
- **Instruments**: European options on SPX and SPY (~15 strikes covering ±30%, weekly expiries)
- **Trading Schedule**: Tuesday & Thursday only, 9:30 AM - 3:00 PM CT
- **Market Structure**: Continuous trading with opening rotation
- **Order Processing**: Real-time matching with immediate execution
- **Evaluation**: Role-specific KPIs and quantitative research quality

---

## Core Trading Flow

1. **Market Open (9:30 AM)**

   - Opening rotation determines initial prices
   - All pre-market orders participate in batch auction
   - Continuous trading begins after rotation

2. **Continuous Trading (9:30 AM - 3:00 PM)**

   - Underlying prices update continuously
   - Orders processed immediately upon receipt
   - Real-time position and P&L updates
   - News events occur throughout the day

3. **Market Dynamics**

   - Price-time priority matching
   - Immediate execution for crossing orders
   - Market data updates in real-time

4. **Risk Management**

   - Position limits enforced continuously
   - Real-time compliance monitoring
   - Instant execution reports

## Roles

Each intern team is assigned one of three trading roles. Each role exploits different structural fundamentals of the simulated market and comes with its own constraints, signals, and scoring objective.

### 1. Market Maker

**Objective**: Capture edge by quoting fair and profitable options prices

- **Signal Access**: None
- **Constraints**:
  - Must quote ≥80% of instruments continuously across both products
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

## Getting Started

1. **[Read the Game Overview](docs/game/overview.md)** - Understand the basic mechanics
2. **[Study Your Role](docs/game/roles/)** - Deep dive into your assigned role
3. **[Review Research Guide](docs/game/research/)** - Understand your quantitative problem
4. **[Learn Trading Rules](docs/game/trading/)** - Master order types and constraints
5. **[Check Schedule](docs/game/configuration/schedule.md)** - Know when trading happens

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

## Documentation

### Core Documentation

- **[Game Overview](docs/game/)** - Start here
- **[Fundamentals](docs/game/fundamentals/)** - Core concepts and mechanics
- **[Simulation Details](docs/game/simulation/)** - Price generation and events
- **[Scoring System](docs/game/scoring/)** - How teams are evaluated

### Reference Materials

- **[Probability Tables](docs/game/appendix/probability-tables.md)** - Event probabilities
- **[Mathematical Formulas](docs/game/appendix/formulas.md)** - Key calculations
- **[Glossary](docs/game/appendix/glossary.md)** - Trading terminology

### Technical Documentation

- **[API Reference](docs/reference/)** - For bot development
- **[Implementation Guide](docs/technical/)** - Technical setup

## Future Extensions

- Enable earnings-style news events with clustered jumps
