"""Order validation service implementation.

This module provides the concrete implementation of order validation
business logic for the trading system.
"""

import threading
from typing import Dict, Optional, Tuple

from ..constants.errors import ErrorMessages
from ..domain.exchange.core.order import Order
from ..domain.exchange.order_result import OrderResult
from ..domain.exchange.validation.interfaces import ValidationContext
from ..domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
)
from ..domain.exchange.venue import ExchangeVenue
from ..infrastructure.api.models import TeamInfo
from .interfaces import OrderValidationServiceInterface


class OrderValidationService(OrderValidationServiceInterface):
    """Service for validating trading orders and cancellation requests.

    This service handles all order validation logic including constraint
    checking for new orders and ownership verification for cancellations.
    It owns and manages rate limiting state internally, providing thread-safe
    order rate tracking for the multi-threaded architecture.

    The service enforces trading rules such as position limits, order
    rate limits, and role-specific constraints to ensure fair and
    orderly market operations.

    Parameters
    ----------
    validator : ConstraintBasedOrderValidator
        The order validator configured with role-specific constraints
    exchange : ExchangeVenue
        The exchange venue for executing cancellation operations
    get_positions_func : callable
        Function to retrieve current positions for a team
        Signature: (team_id: str) -> Dict[str, int]

    Attributes
    ----------
    validator : ConstraintBasedOrderValidator
        The order validator instance
    exchange : ExchangeVenue
        The exchange venue instance
    _get_positions : callable
        Position retrieval function
    orders_this_second : Dict[str, int]
        Internal order count tracking per team (thread-safe)
    orders_lock : threading.RLock
        Lock for thread-safe access to order counts

    Notes
    -----
    The service owns rate limiting state internally while accessing
    position state through injected functions. This design enables:

    1. Thread-safe operation with internal locking for rate limits
    2. Service ownership of validation-related state
    3. Clear separation of concerns between services

    The validation process builds a complete context including current
    positions and order counts before applying configured constraints.

    TradingContext
    --------------
    Order validation enforces critical trading constraints:

    - Position limits: Prevent excessive risk exposure (e.g., ±50)
    - Order rate limits: Prevent system abuse and ensure fairness
    - Price validation: Ensure limit orders have reasonable prices
    - Role restrictions: Enforce role-specific trading rules

    Cancellation requests require ownership verification to prevent
    market manipulation through unauthorized cancellations.

    Examples
    --------
    >>> # Create service with state access functions
    >>> service = OrderValidationService(
    ...     validator=constraint_validator,
    ...     exchange=exchange_venue,
    ...     get_positions_func=lambda team_id: positions.get(team_id, {}),
    ...     get_order_count_func=lambda team_id: order_counts.get(team_id, 0)
    ... )
    >>>
    >>> # Validate a new order
    >>> order = Order(
    ...     instrument_id="SPX-20240315-4500C",
    ...     side="buy",
    ...     quantity=10,
    ...     order_type="limit",
    ...     price=125.50
    ... )
    >>> result = service.validate_new_order(order, team_info)
    >>> if result.status == "accepted":
    ...     print("Order validated successfully")
    ... else:
    ...     print(f"Validation failed: {result.error_message}")
    >>>
    >>> # Process a cancellation request
    >>> success, reason = service.validate_cancellation("ORD123", "TEAM001")
    >>> if success:
    ...     print("Order cancelled")
    >>> else:
    ...     print(f"Cancellation failed: {reason}")
    """

    def __init__(
        self,
        validator: ConstraintBasedOrderValidator,
        exchange: ExchangeVenue,
        get_positions_func,
    ):
        """Initialize the order validation service.

        Parameters
        ----------
        validator : ConstraintBasedOrderValidator
            Configured validator with role-specific constraints
        exchange : ExchangeVenue
            Exchange venue for cancellation operations
        get_positions_func : callable
            Thread-safe function to get team positions
        """
        self.validator = validator
        self.exchange = exchange
        self._get_positions = get_positions_func

        # Initialize internal rate limiting state
        self.orders_this_second: Dict[str, int] = {}
        self.orders_lock = threading.RLock()

    def get_order_count(self, team_id: str) -> int:
        """Get current order count for a team (thread-safe).

        Parameters
        ----------
        team_id : str
            The team ID to get order count for

        Returns
        -------
        int
            Number of orders submitted by the team this second

        Notes
        -----
        This method provides thread-safe access to the internal order
        count state using the service's internal lock.
        """
        with self.orders_lock:
            return self.orders_this_second.get(team_id, 0)

    def increment_order_count(self, team_id: str) -> None:
        """Increment order count for a team after successful validation.

        Parameters
        ----------
        team_id : str
            The team ID to increment order count for

        Notes
        -----
        This method should be called by the validator thread after
        successful order validation to update the rate limiting state.
        It provides thread-safe increment using the service's
        internal lock.
        """
        with self.orders_lock:
            current_count = self.orders_this_second.get(team_id, 0)
            self.orders_this_second[team_id] = current_count + 1

    def validate_new_order(self, order: Order, team: TeamInfo) -> OrderResult:
        """Validate a new order against all configured constraints.

        Performs comprehensive validation including position limits,
        order rate limits, price reasonability, and role-specific
        constraints. The validation occurs within the context of
        the team's current positions and order activity.

        Parameters
        ----------
        order : Order
            The order to validate, containing instrument, side,
            quantity, and price information
        team : TeamInfo
            Team information including role and authentication

        Returns
        -------
        OrderResult
            Result containing:
            - status: str ("accepted" or "rejected")
            - order_id: str identifying the order
            - error_code: Optional[str] for rejections
            - error_message: Optional[str] with constraint violation details

        Notes
        -----
        The validation process:
        1. Retrieves current team positions and order count
        2. Builds a ValidationContext with complete state
        3. Applies all configured constraints via the validator
        4. Returns detailed result for further processing

        The method is stateless and thread-safe, retrieving all
        required state through the injected functions.

        TradingContext
        --------------
        Validation must complete quickly (<1ms) to maintain low
        latency order processing. Common validation scenarios:

        - Market makers hitting position limits during active quoting
        - Teams exceeding order rate limits during volatile markets
        - Invalid prices outside reasonable bands for limit orders
        - Role-specific restrictions on certain instruments

        The validation result includes detailed error messages to
        help trading algorithms adjust their behavior appropriately.
        """
        # Get current state using injected functions and internal state
        team_positions = self._get_positions(team.team_id)
        team_orders = self.get_order_count(team.team_id)

        # Build validation context with complete state
        context = ValidationContext(
            order=order,
            trader_id=team.team_id,
            trader_role=team.role,
            current_positions=team_positions,
            orders_this_second=team_orders,
        )

        # Run validation through configured constraints
        result = self.validator.validate_order(context)

        return result

    def validate_cancellation(
        self, order_id: str, team_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate and process an order cancellation request.

        Verifies ownership and attempts to cancel the specified order
        at the exchange. Only orders owned by the requesting team can
        be cancelled, preventing unauthorized market manipulation.

        Parameters
        ----------
        order_id : str
            The exchange-assigned order ID to cancel
        team_id : str
            The ID of the team requesting cancellation

        Returns
        -------
        Tuple[bool, Optional[str]]
            A tuple containing:
            - success: bool indicating if cancellation succeeded
            - reason: Optional[str] with failure reason if applicable

        Notes
        -----
        The cancellation process delegates to the exchange, which:
        1. Verifies the order exists and is cancellable
        2. Confirms ownership matches the requesting team
        3. Removes the order from the order book if valid
        4. Returns success/failure indication

        Failure reasons include:
        - Order not found (never existed or already filled)
        - Unauthorized (order belongs to different team)
        - Order already filled or partially filled

        TradingContext
        --------------
        Cancellation timing is critical in fast-moving markets:

        - Orders may fill between submission and cancellation
        - Partial fills may occur, leaving residual quantities
        - Race conditions are inherent and must be handled gracefully

        Teams should implement robust error handling for failed
        cancellations and track their outstanding orders carefully
        to avoid confusion about order states.
        """
        # Attempt cancellation at exchange with ownership check
        try:
            success = self.exchange.cancel_order(order_id, team_id)
            if success:
                return (True, None)
            else:
                # Generic failure reason for security - don't reveal specific details
                return (False, ErrorMessages.ORDER_NOT_FOUND)
        except ValueError:
            # Exchange throws ValueError for ownership violations
            # Return generic message for security - don't reveal ownership details
            return (False, ErrorMessages.ORDER_NOT_FOUND)
