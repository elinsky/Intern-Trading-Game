# Intern Trading Game

Welcome to the Intern Trading Game! This is a role-based options trading simulation where intern teams compete by building trading bots.

## Game Overview

- **Products**: European options on simulated SPX and SPY underlyings
- **Tick Frequency**: Every 5 minutes (configurable)
- **Submission**: Intern bots submit orders
- **Execution**: Matching engine runs per tick, fills orders, updates P&L
- **Evaluation**: Role-specific KPIs and strategy quality

## Roles

Each intern team plays one of the following:

| Role          | Objective                                      | Tools / Signals                        |
|---------------|-----------------------------------------------|----------------------------------------|
| Market Maker  | Quote fairly and manage inventory risk        | Product-specific, delta hedging allowed |
| Hedge Fund    | Exploit vol regime shifts & implied/realized edge | Advance vol signal with transition matrix, full product access |
| Arbitrage Desk| Trade mispriced spreads between SPX/SPY       | Tracking signal, fast execution         |
| Retail Trader | (Employees only) Add flow and realism         | No signal, limited trade size           |

## Documentation Structure

This documentation covers:


1. **Game Fundamentals**: Core concepts, mechanics, and market structure
2. **Trading Rules**: Constraints, execution rules, and order types
3. **Role Details**: Specific requirements and strategies for each role
4. **Game Configuration**: Parameters and settings

## Getting Started

To understand the game mechanics, start with:


1. [Game Overview](game/overview.md) - High-level introduction
2. [Core Concepts](game/fundamentals/core-concepts.md) - Key terminology and ideas
3. [Your Role](game/roles/overview.md) - Choose and understand your trading role

Good luck, and may the best trading strategy win!
