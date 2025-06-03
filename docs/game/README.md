# Intern Trading Game Documentation

Welcome to the Intern Trading Game documentation. This guide contains all business and game-related information for participants.

## Quick Start

1. Read the [Game Overview](overview.md) for a high-level understanding
2. Review [Core Concepts](fundamentals/core-concepts.md) for key terminology
3. Choose your role in [Roles Overview](roles/overview.md)
4. Understand [Trading Constraints](trading/constraints.md) for your role
5. Learn about [Scoring Metrics](scoring/overview.md)

## Documentation Structure

### Fundamentals
- [Core Concepts](fundamentals/core-concepts.md) - Key terminology and concepts
- [Market Structure](fundamentals/market-structure.md) - SPX/SPY instruments and options
- [Game Mechanics](fundamentals/game-mechanics.md) - Tick structure and order flow

### Simulation
- [Price Generation](simulation/price-generation.md) - How underlying prices move
- [Volatility Regimes](simulation/volatility-regimes.md) - Low/medium/high volatility states
- [News Events](simulation/news-events.md) - Event types and impacts
- [Correlation Model](simulation/correlation-model.md) - SPX-SPY relationship

### Roles
- [Overview](roles/overview.md) - Compare all roles
- [Market Maker](roles/market-maker.md) - Continuous quoting requirements
- [Hedge Fund](roles/hedge-fund.md) - Gamma trading with delta neutrality
- [Arbitrage Desk](roles/arbitrage-desk.md) - Cross-asset opportunities
- [Retail Flow](roles/retail.md) - Automated retail simulation

### Trading
- [Order Types](trading/order-types.md) - Limit, market, and quote orders
- [Constraints](trading/constraints.md) - Role-specific limitations
- [Signal Access](trading/signals-access.md) - Information availability by role
- [Execution Rules](trading/execution-rules.md) - Matching and priority

### Scoring
- [Overview](scoring/overview.md) - Scoring philosophy
- [Market Maker Metrics](scoring/metrics/market-maker.md)
- [Hedge Fund Metrics](scoring/metrics/hedge-fund.md)
- [Arbitrage Desk Metrics](scoring/metrics/arbitrage-desk.md)
- [Evaluation Periods](scoring/evaluation-periods.md)

### Configuration
- [Game Parameters](configuration/game-parameters.md) - Configurable settings
- [Example Config](configuration/example-config.yaml) - Sample configuration
- [Schedule](configuration/schedule.md) - Game timeline and phases

### Appendix
- [Probability Tables](appendix/probability-tables.md) - News event probabilities
- [Formulas](appendix/formulas.md) - Mathematical formulas
- [Glossary](appendix/glossary.md) - Trading terms definitions
