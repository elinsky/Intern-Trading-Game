# OrderValidator Design

## Overview

The OrderValidator is a constraint-based validation system that checks all orders before they reach the Exchange. It's designed to be completely role-agnostic - it understands types of constraints (like position limits) but has no knowledge of specific roles (like market maker or hedge fund).

## Core Design Principles

### 1. Role-Agnostic
The validator doesn't contain any role-specific logic. It only knows about generic constraint types that can be applied to any role.

### 2. Configuration-Driven
All validation rules are defined in configuration files, not hardcoded. This allows game parameters to be adjusted without changing code.

### 3. Composable Constraints
Complex validation rules are built by combining simple, reusable constraint types.

## How It Works

When an order is submitted:

1. **Context Building**: The system gathers the current state needed for validation:
   - Current positions for the trader
   - Number of orders submitted this tick
   - Current tick phase
   - Any other relevant metadata

2. **Constraint Loading**: The validator retrieves the list of constraints configured for the trader's role

3. **Sequential Validation**: Each constraint is checked in order. The first failure immediately rejects the order with a specific error message.

4. **Result**: If all constraints pass, the order is accepted and forwarded to the exchange.

## Constraint Types

The system supports these generic constraint types:

- **Position Limits**: Maximum position per instrument (can be symmetric ±N or absolute)
- **Portfolio Limits**: Maximum total position across all instruments
- **Order Size**: Minimum and maximum order quantities
- **Order Rate**: Maximum orders allowed per tick
- **Order Types**: Which order types (limit, market, quote) are permitted
- **Trading Window**: Which tick phases allow order submission
- **Price Bounds**: Valid price ranges for limit orders

## Configuration Structure

Constraints are configured per role in YAML:

```yaml
roles:
  [role_name]:
    constraints:
      - type: [constraint_type]
        parameters:
          [param1]: [value1]
          [param2]: [value2]
        error_code: "SPECIFIC_ERROR"
        error_message: "Human-readable explanation"
```

## Integration Points

### With Game Loop
- Provides current tick phase for trading window validation
- Tracks order counts per tick

### With Position Service
- Queries current positions for limit checking
- Calculates portfolio totals

### With Exchange
- Validates orders before submission
- Returns detailed rejection reasons

## Advantages

1. **Flexibility**: New constraint types can be added without modifying existing code
2. **Maintainability**: Role rules are data, not code, making them easier to adjust
3. **Testability**: Each constraint type can be tested independently
4. **Performance**: Constraints are cached per role to avoid repeated parsing
5. **Clarity**: Validation logic is centralized and consistent

## Trade-offs

### Pros
- Clean separation between validation logic and role definitions
- Easy to add new roles or modify existing ones
- Configuration changes don't require code changes
- Validation rules are transparent and auditable

### Cons
- Less type safety for constraint parameters (they're configuration data)
- Need to maintain registry of constraint types
- Slightly more complex than hardcoded validation
- Requires careful configuration management

## Error Handling

Each constraint provides:
- **Error Code**: Machine-readable identifier for the specific violation
- **Error Message**: Human-readable explanation for the trader
- **Context**: Which constraint failed and why

This enables both automated handling and clear feedback to users.

## Future Extensibility

The design supports several extension points:

1. **Custom Constraints**: New constraint types can be added by implementing the Constraint interface
2. **Dynamic Rules**: Constraints could be modified during gameplay based on market conditions
3. **Composite Constraints**: Complex rules can be built by combining existing constraints
4. **Performance Optimization**: Frequently-used constraint combinations can be cached

## Example: Market Maker Configuration

```yaml
market_maker:
  constraints:
    # Symmetric position limits
    - type: position_limit
      parameters:
        max_position: 50
        symmetric: true

    # Total portfolio limit
    - type: portfolio_limit
      parameters:
        max_total: 200

    # Order size bounds
    - type: order_size
      parameters:
        min: 1
        max: 1000

    # Can submit quotes
    - type: order_type_allowed
      parameters:
        allowed: ["limit", "market", "quote"]
```

This configuration enforces all market maker rules without any market-maker-specific code in the validator.
