# Order Validation API Reference

## Overview

The Order Validation system provides constraint-based validation for all orders before they reach the exchange. It's designed to be role-agnostic, with all role-specific rules defined in configuration.

## Core Components

### ValidationContext

Contains all information needed to validate an order:

```python
@dataclass
class ValidationContext:
    order: Order                          # The order being validated
    trader_id: str                        # ID of the trader
    trader_role: str                      # Role (for loading constraints)
    tick_phase: TickPhase                 # Current market phase
    current_positions: Dict[str, int]     # Current positions by instrument
    orders_this_tick: int                 # Orders already submitted
    metadata: Dict[str, Any]              # Additional context
```

### ConstraintConfig

Defines a single validation constraint:

```python
@dataclass
class ConstraintConfig:
    constraint_type: ConstraintType       # Type of constraint
    parameters: Dict[str, Any]            # Constraint-specific parameters
    error_code: str                       # Error code if violated
    error_message: str                    # Human-readable error message
```

## Constraint Types

### POSITION_LIMIT
Validates position limits per instrument.

Parameters:
- `max_position`: Maximum absolute position allowed
- `symmetric`: If true, enforces ±max_position

### PORTFOLIO_LIMIT
Validates total portfolio position across all instruments.

Parameters:
- `max_total_position`: Maximum total absolute position

### ORDER_SIZE
Validates order size is within bounds.

Parameters:
- `min_size`: Minimum order size (default: 0)
- `max_size`: Maximum order size (default: infinity)

### ORDER_RATE
Validates order submission rate.

Parameters:
- `max_orders_per_tick`: Maximum orders allowed per tick

### ORDER_TYPE_ALLOWED
Validates order type is permitted for the role.

Parameters:

- `allowed_types`: List of allowed order types (e.g., ["limit", "market", "quote"])

### TRADING_WINDOW
Validates orders are submitted during allowed phases.

Parameters:

- `allowed_phases`: List of phase names (e.g., ["PRE_OPEN"])

## Configuration Format

Constraints are configured per role in YAML:

```yaml
roles:
  market_maker:
    constraints:
      - type: position_limit
        max_position: 50
        symmetric: true
        error_code: "MM_POS_LIMIT"
        error_message: "Position exceeds ±50"

      - type: order_size
        min_size: 1
        max_size: 1000
        error_code: "MM_SIZE"
        error_message: "Order size must be between 1 and 1000"
```

## Usage Example

```python
# Create validator
validator = ConstraintBasedOrderValidator()

# Load constraints from config
role_constraints = load_constraints_from_dict(config)
for role, constraints in role_constraints.items():
    validator.load_constraints(role, constraints)

# Validate an order
context = ValidationContext(
    order=order,
    trader_id="TRADER1",
    trader_role="market_maker",
    tick_phase=TickPhase.PRE_OPEN,
    current_positions={"SPX_CALL_4500": 40},
    orders_this_tick=5
)

result = validator.validate_order(context)

if result.status == "rejected":
    print(f"Order rejected: {result.error_code} - {result.error_message}")
```

## Error Handling

Rejected orders include:
- `error_code`: Machine-readable error identifier
- `error_message`: Human-readable explanation

The validator uses a fail-fast approach, returning the first constraint violation encountered.

## Universal Constraints

Some constraints apply to all roles automatically:
- Trading window enforcement (orders only during PRE_OPEN phase)

Additional universal constraints can be defined in the configuration.
