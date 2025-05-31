# Intern-Trading-Game


# Intern Trading Game — Belvedere Summer 2025

Welcome to the Intern Trading Game! This repo contains the core simulation engine, matching logic, and reference tools for a role-based, options market-making game.

Intern teams develop automated trading strategies using Jupyter notebooks and compete in a simulated market driven by configurable economic fundamentals.

---

## Game Overview

- **Products**: European options on simulated SPX and SPY underlyings  
- **Tick Frequency**: Every 5 minutes (configurable)  
- **Submission**: Intern bots submit orders  
- **Execution**: Matching engine runs per tick, fills orders, updates P&L  
- **Evaluation**: Role-specific KPIs and strategy quality

---

## Roles

Each intern team plays one of the following:

| Role          | Objective                                      | Tools / Signals                        |
|---------------|-----------------------------------------------|----------------------------------------|
| Market Maker  | Quote fairly and manage inventory risk        | Product-specific, delta hedging allowed |
| Hedge Fund    | Exploit vol regime shifts & implied/realized edge | Delayed vol signal, full product access |
| Arbitrage Desk| Trade mispriced spreads between SPX/SPY       | Tracking signal, fast execution         |
| Retail Trader | (Employees only) Add flow and realism         | No signal, limited trade size           |

---

## Market Fundamentals (Configurable)

- Volatility regimes
- Implied vs realized vol skew
- SPX/SPY tracking error
- Retail aggression levels
- Signal accuracy and delay
- Latency tiers

Each role exploits one or more of these dynamics to generate P&L.