"""Order validation service implementation.

This module provides the concrete implementation of order validation
business logic for the trading system.
"""

from typing import Optional, Tuple

from ...core.interfaces import ValidationContext
from ...core.models import TickPhase
from ...core.order_validator import ConstraintBasedOrderValidator
from ...exchange.order import Order
from ...exchange.order_result import OrderResult
from ...exchange.venue import ExchangeVenue
from ..models import TeamInfo
from .interfaces import OrderValidationServiceInterface


class OrderValidationService(OrderValidationServiceInterface):
    """Service for validating trading orders and cancellation requests.

    This service handles all order validation logic including constraint
    checking for new orders and ownership verification for cancellations.
    It operates statelessly, retrieving required state through injected
    functions to maintain thread safety in the multi-threaded architecture.

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
    get_order_count_func : callable
        Function to retrieve order count for current tick
        Signature: (team_id: str) -> int

    Attributes
    ----------
    validator : ConstraintBasedOrderValidator
        The order validator instance
    exchange : ExchangeVenue
        The exchange venue instance
    _get_positions : callable
        Position retrieval function
    _get_order_count : callable
        Order count retrieval function

    Notes
    -----
    The service is designed to be stateless, with all required state
    accessed through injected functions. This design enables:

    1. Thread-safe operation in multi-threaded environments
    2. Easy unit testing with mock state providers
    3. Clear separation of validation logic from state management

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
        get_order_count_func,
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
        get_order_count_func : callable
            Thread-safe function to get order count
        """
        self.validator = validator
        self.exchange = exchange
        self._get_positions = get_positions_func
        self._get_order_count = get_order_count_func

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
        # Get current state using injected functions
        team_positions = self._get_positions(team.team_id)
        team_orders = self._get_order_count(team.team_id)

        # Build validation context with complete state
        context = ValidationContext(
            order=order,
            trader_id=team.team_id,
            trader_role=team.role,
            tick_phase=TickPhase.TRADING,
            current_positions=team_positions,
            orders_this_tick=team_orders,
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
        success = self.exchange.cancel_order(order_id, team_id)

        if success:
            return (True, None)
        else:
            # Generic failure reason - future enhancement could
            # provide more detailed failure codes from exchange
            return (False, "Order not found or unauthorized")
