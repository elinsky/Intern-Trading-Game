# Intern-Trading-Game

Welcome to the Intern Trading Game! This repo contains the core simulation engine, matching logic, and reference tools for a role-based, options market-making game.

---

## Game Overview

- **Underlying Assets**: Simulated SPX and SPY spot prices
- **Instruments**: European options on SPX and SPY (5–10 strikes, 2–3 expiries)
- **Tick Frequency**: Every 5 minutes (configurable)
- **Submission**: Intern bots submit orders
- **Execution**: Matching engine runs per tick, fills orders, updates P&L
- **Evaluation**: Role-specific KPIs and strategy quality

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

- **Product Access**: SPX *or* SPY only (assigned)
- **Delta Hedging**: Allowed
- **Signal Access**: None
- **Latency**: Medium (can trade every tick)
- **Constraints**:
  - Must quote 80% of instruments each tick
  - Must stay delta-neutral
- **Scoring Focus**:
  - Spread capture per trade
  - Inventory risk management
  - Quoting coverage

### 2. Hedge Fund

**Objective**: Exploit mis-pricings in implied vs. realized volatility

- **Product Access**: SPX and SPY
- **Delta Hedging**: Allowed
- **Signal Access**: Volatility regime signal (delayed 1 tick)
- **Latency**: Slow
- **Constraints**:
  - Capital charges on large positions
  - Fees on all trades
- **Scoring Focus**:
  - Realized vs. implied volatility P&L
  - Strategy adaptiveness
  - Risk-adjusted return

### 3. Arbitrage Desk

**Objective**: Exploit temporary mispricing between SPX and SPY options

- **Product Access**: SPX and SPY
- **Delta Hedging**: Must stay near delta-neutral
- **Signal Access**: Tracking error signal (real-time)
- **Latency**: Fast (no delay)
- **Constraints**:
  - Must submit paired, cross-product trades
  - No directional risk allowed
- **Scoring Focus**:
  - Profit from convergence trades
  - Precision of execution
  - Frequency of profitable round-trips

---

## Optional: Retail Traders (Employees)

**Objective**: Create flow and noise to enrich the game environment

- **Product Access**: SPX and/or SPY
- **Signal Access**: None
- **Constraints**:
  - Max 1–3 trades per tick
  - Not scored
- **Participation**: Voluntary, open to all employees

## Market Fundamentals (Configurable)

The simulated market is controlled by a backend configuration that defines key structural dynamics. These parameters are not exposed directly, but interns may infer them through research.

| Fundamental                  | Description                                    | Exploited By   |
| ---------------------------- | ---------------------------------------------- | -------------- |
| Volatility Regimes           | Underlying has multi-state vol (e.g. low/high) | Hedge Fund     |
| Implied vs. Realized Vol Gap | IV is structurally rich vs realized            | Market Maker   |
| SPX-SPY Tracking Error       | SPY drifts from SPX and mean-reverts           | Arbitrage Desk |
| Retail Flow Aggression       | Retail orders are randomly aggressive          | Market Maker   |
| Signal Delay                 | HF signal arrives with 1-tick delay            | Hedge Fund     |
| Latency Advantage            | Arb desk trades instantly; MM/HF do not        | Arbitrage Desk |

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
