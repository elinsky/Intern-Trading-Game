# Technical Explanations

In-depth explanations of how the Intern Trading Game works under the hood. These guides explain concepts, algorithms, and design decisions.

## Core Concepts

### Order Processing

- **[Order Matching](order-matching.md)** - How the matching engine pairs buy and sell orders
- **[Batch Matching](batch-matching.md)** - The batch processing algorithm used during tick execution
- **[Order Validator Design](order-validator-design.md)** - Architecture and patterns for order validation

### Game Mechanics

- **[Trading Phases](trading-phases.md)** - Detailed explanation of the tick lifecycle and trading phases

## Key Topics

### The Matching Engine

The heart of the exchange is the matching engine. It processes orders according to price-time priority:

- **[Order Matching](order-matching.md)** explains the continuous matching process
- **[Batch Matching](batch-matching.md)** explains the batch matching process

### Validation Framework

Order validation ensures market integrity:

- **[Order Validator Design](order-validator-design.md)** details the validation architecture
- Role-specific constraints are enforced through the validation pipeline

### Trading Phases

- **[Trading Phases](trading-phases.md)** breaks down different market phases the game supports
- Order windows, matching times, and settlement explained

## Related Resources

- **[Architecture Overview](../architecture-v3.md)** - System design and components
- **[API Reference](../reference/index.md)** - Detailed API specifications
- **[How-To Guides](../how-to/index.md)** - Practical implementation guides

## Navigation

← Back to [Technical Docs](../index.md) | [Tutorials](../tutorials/market-maker-tutorial.md) →
