# Intern Trading Game

Welcome to the Intern Trading Game documentation! This site contains comprehensive documentation for the core simulation engine, matching logic, and reference tools for a role-based, options market-making game.

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

This documentation is organized into four main sections:


1. **Tutorials**: Step-by-step guides to help you get started with the Intern Trading Game.
2. **How-To Guides**: Practical guides for accomplishing specific tasks.
3. **Reference**: Detailed API documentation and technical specifications.
4. **Explanation**: In-depth explanations of concepts and design decisions.

## Getting Started

To get started with the Intern Trading Game, check out the [Market Maker Tutorial](technical/tutorials/market-maker-tutorial.md).

For more information on how to submit orders, see the [How to Submit Orders](technical/how-to/how-to-submit-orders.md) guide.
