# Intern Trading Game

Welcome to the Intern Trading Game documentation! This is a role-based options trading simulation where intern teams compete by building trading bots.

## Game Overview

- **Products**: European options on simulated SPX and SPY underlyings
- **Tick Frequency**: Every 5 minutes (configurable)
- **Submission**: Intern bots submit orders
- **Execution**: Matching engine runs per tick, fills orders, updates P&L
- **Evaluation**: Role-specific KPIs and strategy quality

## Roles

Each intern team plays one of the following:

| Role           | Objective                                         | Tools / Signals                                                |
| -------------- | ------------------------------------------------- | -------------------------------------------------------------- |
| Market Maker   | Quote fairly and manage inventory risk            | Product-specific, delta hedging allowed                        |
| Hedge Fund     | Exploit vol regime shifts & implied/realized edge | Advance vol signal with transition matrix, full product access |
| Arbitrage Desk | Trade mispriced spreads between SPX/SPY           | Tracking signal, fast execution                                |
| Retail Trader  | (Employees only) Add flow and realism             | No signal, limited trade size                                  |

## Getting Started

### For Game Participants

1. [Game Overview](game/overview.md) - High-level introduction
2. [Core Concepts](game/fundamentals/core-concepts.md) - Key terminology and ideas
3. [Your Role](game/roles/overview.md) - Choose and understand your trading role
4. [Trading Constraints](game/trading/constraints.md) - Understand your role's limitations

### For Bot Developers

1. [Market Maker Tutorial](technical/tutorials/market-maker-tutorial.md) - Step-by-step guide
2. [How to Submit Orders](technical/how-to/how-to-submit-orders.md) - Order submission guide
3. [REST API](technical/reference/rest-api.md) - API endpoints reference
4. [WebSocket API](technical/reference/websocket-api.md) - Real-time data streams

## Documentation Sections

### Game Documentation

- **[Fundamentals](game/fundamentals/core-concepts.md)** - Core concepts, mechanics, and market structure
- **[Trading Rules](game/trading/order-types.md)** - Order types, constraints, and execution
- **[Roles](game/roles/overview.md)** - Detailed role descriptions and strategies
- **[Simulation](game/simulation/price-generation.md)** - Price models, volatility, and events
- **[Scoring](game/scoring/overview.md)** - Performance metrics and evaluation
- **[Configuration](game/configuration/game-parameters.md)** - Game parameters and settings
- **[Appendix](game/appendix/glossary.md)** - Glossary, formulas, and probability tables

### Technical Documentation

#### Architecture & Design

- **[Architecture v4](technical/architecture-v4.md)** - Service-oriented architecture (current)
- **[Architecture Overview](technical/architecture.md)** - Original system design
- **[Build Order](technical/build-order.md)** - Implementation roadmap
- **[Implementation Guide](technical/implementation-guide.md)** - Technical setup details

#### Tutorials & Guides

- **[Market Maker Tutorial](technical/tutorials/market-maker-tutorial.md)** - Complete bot example
- **[How to Submit Orders](technical/how-to/how-to-submit-orders.md)** - Order submission guide
- **[Use REST API](technical/how-to/use-rest-api.md)** - REST API usage
- **[Use WebSockets](technical/how-to/use-websockets.md)** - WebSocket connection guide
- **[WebSocket Integration](technical/how-to/websocket-integration.md)** - Advanced WebSocket patterns

#### API Reference

- **[API Overview](technical/reference/api-overview.md)** - API architecture
- **[Exchange API](technical/reference/exchange-api.md)** - Core exchange interface
- **[REST API](technical/reference/rest-api.md)** - HTTP endpoints
- **[WebSocket API](technical/reference/websocket-api.md)** - Real-time streams
- **[Validation API](technical/reference/validation-api.md)** - Order validation rules
- **[Math Examples](technical/reference/math-examples.md)** - Mathematical formulas

#### Explanations

- **[Order Matching](technical/explanation/order-matching.md)** - Matching engine logic
- **[Batch Matching](technical/explanation/batch-matching.md)** - Batch processing
- **[Trading Phases](technical/explanation/trading-phases.md)** - Tick lifecycle
- **[Order Validator Design](technical/explanation/order-validator-design.md)** - Validation patterns

#### Contributing

- **[Math in Docstrings](technical/contributing/docstring-math-guide.md)** - Documentation standards

## Quick Links

- **For Participants**: Start with [Game Overview](game/overview.md) and [Core Concepts](game/fundamentals/core-concepts.md)
- **For Developers**: Jump to [Market Maker Tutorial](technical/tutorials/market-maker-tutorial.md) or [REST API](technical/reference/rest-api.md)
- **For Reference**: See [Glossary](game/appendix/glossary.md) and [Formulas](game/appendix/formulas.md)

Good luck, and may the best trading strategy win!
