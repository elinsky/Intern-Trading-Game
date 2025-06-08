"""Order validation system for the Intern Trading Game.

This module implements a constraint-based order validation system that
enforces trading rules without any hardcoded role-specific logic. All
validation rules are expressed as configurable constraints.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..exchange.order_result import OrderResult
from ..interfaces import OrderValidator as OrderValidatorInterface
from ..interfaces import ValidationContext
from ..models import TickPhase


class ConstraintType(Enum):
    """Types of constraints that can be applied to orders."""

    POSITION_LIMIT = "position_limit"
    PORTFOLIO_LIMIT = "portfolio_limit"
    ORDER_SIZE = "order_size"
    ORDER_RATE = "order_rate"
    ORDER_TYPE_ALLOWED = "order_type_allowed"
    TRADING_WINDOW = "trading_window"
    INSTRUMENT_ALLOWED = "instrument_allowed"
    PRICE_RANGE = "price_range"


@dataclass
class ConstraintConfig:
    """Configuration for a single constraint.

    Parameters
    ----------
    constraint_type : ConstraintType
        The type of constraint to apply
    parameters : Dict[str, Any]
        Parameters specific to this constraint type
    error_code : str
        Error code to return if constraint is violated
    error_message : str
        Human-readable error message for constraint violations
    """

    constraint_type: ConstraintType
    parameters: Dict[str, Any]
    error_code: str
    error_message: str


@dataclass
class ValidationResult:
    """Result of a constraint check.

    Parameters
    ----------
    is_valid : bool
        Whether the constraint was satisfied
    error_detail : Optional[str]
        Additional detail about the violation (if any)
    """

    is_valid: bool
    error_detail: Optional[str] = None


class Constraint(ABC):
    """Base class for all constraint implementations."""

    @abstractmethod
    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check if the constraint is satisfied.

        Parameters
        ----------
        context : ValidationContext
            Current validation context with order and state
        config : ConstraintConfig
            Configuration for this specific constraint

        Returns
        -------
        ValidationResult
            Result indicating if constraint is satisfied
        """
        pass


class PositionLimitConstraint(Constraint):
    """Validates position limits per instrument.

    Checks that the order would not cause the trader's position
    in a specific instrument to exceed configured limits.

    Notes
    -----
    Supports both symmetric limits (±N) and absolute limits.
    """

    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check position limit constraint."""
        max_position = config.parameters.get("max_position", float("inf"))
        symmetric = config.parameters.get("symmetric", False)

        current = context.current_positions.get(context.order.instrument_id, 0)
        delta = (
            context.order.quantity
            if context.order.is_buy
            else -context.order.quantity
        )
        new_position = current + delta

        if symmetric:
            if -max_position <= new_position <= max_position:
                return ValidationResult(True)
            return ValidationResult(
                False, f"Position {new_position} outside ±{max_position}"
            )
        else:
            if abs(new_position) <= max_position:
                return ValidationResult(True)
            return ValidationResult(
                False, f"Position {abs(new_position)} exceeds {max_position}"
            )


class PortfolioLimitConstraint(Constraint):
    """Validates total portfolio position limits.

    Ensures the total absolute position across all instruments
    does not exceed the configured maximum.
    """

    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check portfolio limit constraint."""
        max_total = config.parameters.get("max_total_position", float("inf"))

        # Calculate total position after this order
        current_total = sum(
            abs(pos) for pos in context.current_positions.values()
        )
        current_instrument = abs(
            context.current_positions.get(context.order.instrument_id, 0)
        )
        delta = (
            context.order.quantity
            if context.order.is_buy
            else -context.order.quantity
        )
        new_instrument_pos = abs(
            context.current_positions.get(context.order.instrument_id, 0)
            + delta
        )

        new_total = current_total - current_instrument + new_instrument_pos

        if new_total <= max_total:
            return ValidationResult(True)
        return ValidationResult(
            False, f"Total position {new_total} would exceed {max_total}"
        )


class OrderSizeConstraint(Constraint):
    """Validates order size is within allowed bounds."""

    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check order size constraint."""
        min_size = config.parameters.get("min_size", 0)
        max_size = config.parameters.get("max_size", float("inf"))

        if min_size <= context.order.quantity <= max_size:
            return ValidationResult(True)
        return ValidationResult(
            False,
            f"Order size {context.order.quantity} not in [{min_size}, {max_size}]",
        )


class OrderRateConstraint(Constraint):
    """Validates order submission rate limits."""

    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check order rate constraint."""
        max_orders = config.parameters.get("max_orders_per_tick", float("inf"))

        if context.orders_this_tick < max_orders:
            return ValidationResult(True)
        return ValidationResult(
            False,
            f"Already submitted {context.orders_this_tick} orders this tick",
        )


class OrderTypeConstraint(Constraint):
    """Validates order type is allowed for the role."""

    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check order type constraint."""
        allowed_types = config.parameters.get("allowed_types", [])

        # Handle QUOTE orders specially (they may not be in the OrderType enum yet)
        order_type_str = context.order.order_type.value
        if hasattr(context.order, "is_quote") and context.order.is_quote:
            order_type_str = "quote"

        if order_type_str in allowed_types:
            return ValidationResult(True)
        return ValidationResult(
            False, f"Order type {order_type_str} not in {allowed_types}"
        )


class TradingWindowConstraint(Constraint):
    """Validates orders are submitted during allowed tick phases."""

    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check trading window constraint."""
        allowed_phases = config.parameters.get("allowed_phases", [])

        # TickPhase.value is a tuple, but config has phase names
        # So compare using the enum name instead
        current_phase_name = context.tick_phase.name

        if current_phase_name in allowed_phases:
            return ValidationResult(True)
        return ValidationResult(
            False,
            f"Current phase {current_phase_name} not in {allowed_phases}",
        )


class InstrumentAllowedConstraint(Constraint):
    """Validates instrument is tradeable (placeholder for future use)."""

    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check instrument allowed constraint."""
        # For now, all instruments are allowed
        # Future: could restrict certain instruments by role
        return ValidationResult(True)


class PriceRangeConstraint(Constraint):
    """Validates limit order prices are within reasonable bounds."""

    def check(
        self, context: ValidationContext, config: ConstraintConfig
    ) -> ValidationResult:
        """Check price range constraint."""
        if context.order.is_market_order:
            return ValidationResult(True)

        min_price = config.parameters.get("min_price", 0)
        max_price = config.parameters.get("max_price", float("inf"))

        if min_price <= context.order.price <= max_price:
            return ValidationResult(True)
        return ValidationResult(
            False,
            f"Price {context.order.price} not in [{min_price}, {max_price}]",
        )


class ConstraintBasedOrderValidator(OrderValidatorInterface):
    """Implementation of OrderValidator using configurable constraints.

    This validator applies a series of constraints to each order based
    on the trader's role. All role-specific logic is encoded in the
    constraint configuration, not in the validator itself.

    Parameters
    ----------
    constraint_registry : Optional[Dict[ConstraintType, Constraint]]
        Custom constraint implementations. If None, uses defaults.

    Notes
    -----
    The validator maintains a registry of constraint implementations
    and applies them based on configuration. New constraint types can
    be added by extending the Constraint base class.

    TradingContext
    --------------
    The validator assumes:
    - Constraint configurations are loaded from external config
    - Position data is current as of order submission
    - Order counts are tracked externally per tick
    """

    def __init__(
        self,
        constraint_registry: Optional[Dict[ConstraintType, Constraint]] = None,
    ):
        """Initialize the order validator."""
        # Default constraint implementations
        self.constraints = constraint_registry or {
            ConstraintType.POSITION_LIMIT: PositionLimitConstraint(),
            ConstraintType.PORTFOLIO_LIMIT: PortfolioLimitConstraint(),
            ConstraintType.ORDER_SIZE: OrderSizeConstraint(),
            ConstraintType.ORDER_RATE: OrderRateConstraint(),
            ConstraintType.ORDER_TYPE_ALLOWED: OrderTypeConstraint(),
            ConstraintType.TRADING_WINDOW: TradingWindowConstraint(),
            ConstraintType.INSTRUMENT_ALLOWED: InstrumentAllowedConstraint(),
            ConstraintType.PRICE_RANGE: PriceRangeConstraint(),
        }

        # Cache for loaded constraints per role
        self._role_constraints_cache: Dict[str, List[ConstraintConfig]] = {}

    def validate_order(self, context: ValidationContext) -> OrderResult:
        """Validate an order against all configured constraints.

        Parameters
        ----------
        context : ValidationContext
            Context containing the order and all state needed for validation

        Returns
        -------
        OrderResult
            Result indicating acceptance or rejection with details

        Notes
        -----
        Applies constraints sequentially, returning immediately on the
        first violation. This fail-fast approach provides clear error
        messages and good performance.
        """
        # Get constraints for this role
        constraints = self._get_constraints_for_role(context.trader_role)

        # Apply each constraint
        for constraint_config in constraints:
            constraint_impl = self.constraints.get(
                constraint_config.constraint_type
            )
            if not constraint_impl:
                # Skip unknown constraint types
                continue

            result = constraint_impl.check(context, constraint_config)
            if not result.is_valid:
                # Return rejection with details
                error_msg = constraint_config.error_message
                if result.error_detail:
                    error_msg = f"{error_msg}: {result.error_detail}"

                return OrderResult(
                    order_id=context.order.order_id,
                    status="rejected",
                    error_code=constraint_config.error_code,
                    error_message=error_msg,
                )

        # All constraints passed
        return OrderResult(
            order_id=context.order.order_id,
            status="accepted",
            remaining_quantity=context.order.quantity,
        )

    def load_constraints(self, role: str, constraints: List[ConstraintConfig]):
        """Load constraints for a specific role.

        Parameters
        ----------
        role : str
            The role to configure
        constraints : List[ConstraintConfig]
            List of constraints to apply to this role
        """
        self._role_constraints_cache[role] = constraints

    def _get_constraints_for_role(self, role: str) -> List[ConstraintConfig]:
        """Get cached constraints for a role.

        Parameters
        ----------
        role : str
            The role to get constraints for

        Returns
        -------
        List[ConstraintConfig]
            Constraints configured for this role
        """
        # Return cached constraints or empty list
        return self._role_constraints_cache.get(role, [])


# Simple configuration helpers
def create_constraint(
    constraint_type: str,
    role_name: str,
    error_suffix: str,
    error_message: str,
    **parameters,
) -> ConstraintConfig:
    """Create a constraint configuration.

    Parameters
    ----------
    constraint_type : str
        Type of constraint (must match ConstraintType enum value)
    role_name : str
        Name of the role (used for error code)
    error_suffix : str
        Suffix for the error code
    error_message : str
        Human-readable error message
    **parameters : Any
        Parameters for the constraint

    Returns
    -------
    ConstraintConfig
        Configured constraint
    """
    return ConstraintConfig(
        constraint_type=ConstraintType(constraint_type),
        parameters=parameters,
        error_code=f"{role_name.upper()}_{error_suffix}",
        error_message=error_message,
    )


def get_universal_constraints() -> List[ConstraintConfig]:
    """Get constraints that apply to all roles."""
    return [
        ConstraintConfig(
            constraint_type=ConstraintType.TRADING_WINDOW,
            parameters={
                "allowed_phases": [
                    TickPhase.PRE_OPEN.name,
                ]
            },
            error_code="TRADING_WINDOW_CLOSED",
            error_message="Orders only accepted during pre-open phase",
        )
    ]


def load_constraints_from_dict(
    config: Dict[str, Any],
) -> Dict[str, List[ConstraintConfig]]:
    """Load role constraints from a configuration dictionary.

    This is a simplified loader that expects constraints to be
    explicitly defined in the configuration rather than inferring
    them from nested structures.

    Expected config format:
    ```yaml
    roles:
      market_maker:
        constraints:
          - type: position_limit
            max_position: 50
            symmetric: true
            error_code: MM_POS_LIMIT
            error_message: "Position exceeds ±50"
          - type: order_size
            min_size: 1
            max_size: 1000
            error_code: MM_SIZE
            error_message: "Order size out of range"
    ```

    Parameters
    ----------
    config : Dict[str, Any]
        Configuration dictionary

    Returns
    -------
    Dict[str, List[ConstraintConfig]]
        Constraints organized by role name
    """
    role_constraints = {}
    universal = get_universal_constraints()

    for role_name, role_config in config.get("roles", {}).items():
        constraints = []

        # Load explicitly defined constraints
        for constraint_data in role_config.get("constraints", []):
            constraint_type = ConstraintType(constraint_data["type"])

            # Extract parameters (everything except type, error_code, error_message)
            parameters = {
                k: v
                for k, v in constraint_data.items()
                if k not in ["type", "error_code", "error_message"]
            }

            constraints.append(
                ConstraintConfig(
                    constraint_type=constraint_type,
                    parameters=parameters,
                    error_code=constraint_data.get(
                        "error_code", f"{role_name.upper()}_CONSTRAINT"
                    ),
                    error_message=constraint_data.get(
                        "error_message", "Constraint violated"
                    ),
                )
            )

        # Add universal constraints
        constraints.extend(universal)
        role_constraints[role_name] = constraints

    return role_constraints
