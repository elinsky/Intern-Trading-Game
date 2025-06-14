"""Core interfaces for the Intern Trading Game.

This module defines the abstract base classes for order validation
and related data structures used throughout the trading system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

from .exchange.order import Order
from .exchange.order_result import OrderResult


@dataclass
class ValidationContext:
    """Context information needed for order validation.

    Contains all the state and metadata required to validate an order
    against the configured constraints. This allows validators to make
    decisions based on current positions, order rates, and other factors.

    Parameters
    ----------
    order : Order
        The order being validated
    trader_id : str
        ID of the trader submitting the order
    trader_role : str
        Role of the trader (determines which constraints apply)
    current_positions : Dict[str, int]
        Current positions by instrument_id (positive=long, negative=short)
    orders_this_second : int
        Number of orders already submitted by this trader in current second
    metadata : Dict[str, Any]
        Additional context that may be needed by custom constraints

    Notes
    -----
    This context object is passed to all constraint validators, allowing
    them to make decisions based on the full trading state without
    needing direct access to services.

    The positions dictionary only includes instruments with non-zero
    positions to minimize memory usage.
    """

    order: Order
    trader_id: str
    trader_role: str
    current_positions: Dict[str, int] = field(default_factory=dict)
    orders_this_second: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderValidator(ABC):
    """Abstract interface for order validation.

    The OrderValidator is responsible for checking all orders against
    configurable constraints before they reach the exchange. It enforces
    trading rules without any hardcoded role-specific logic.

    All validation rules are expressed as generic constraints that can
    be configured differently per role through configuration files.

    Notes
    -----
    The validator is designed to be role-agnostic. It understands
    constraint types (position limits, order sizes) but has no
    knowledge of specific roles (market maker, hedge fund).

    Validation follows a fail-fast approach where the first constraint
    violation immediately rejects the order with a specific error.

    TradingContext
    --------------
    Market Assumptions
        - Orders must be validated before exchange submission
        - Validation rules can vary by role but use same constraint types
        - Position limits are enforced pre-trade

    Trading Rules
        - Trading window constraints apply to all roles
        - Each role may have different position and order limits
        - Validation errors provide clear feedback
    """

    @abstractmethod
    def validate_order(self, context: ValidationContext) -> "OrderResult":
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
        Validation is performed sequentially with early exit on first
        failure. The order of constraint checking may affect performance
        but not correctness.

        The context contains all necessary information including:
        - The order to validate
        - Current trader positions
        - Orders submitted this tick
        - Current tick phase
        - Trader role for loading constraints
        """
        pass
