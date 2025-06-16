"""Order validation service implementation.

This module provides the concrete implementation of order validation
business logic for the trading system.
"""

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..constants.errors import ErrorMessages
from ..domain.exchange.models.order import Order
from ..domain.exchange.order_result import OrderResult
from ..domain.exchange.validation.interfaces import ValidationContext
from ..domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
)
from ..domain.exchange.venue import ExchangeVenue
from ..infrastructure.api.models import TeamInfo
from .interfaces import OrderValidationServiceInterface


@dataclass
class RateLimitWindow:
    """Represents a rate limiting window for tracking orders per second.

    This data structure tracks the count of orders within a specific
    time window (one second) along with the window start timestamp.

    Attributes
    ----------
    count : int
        Number of orders submitted within this window
    window_start : float
        Unix timestamp (in seconds) when this window started

    Notes
    -----
    Windows are based on integer second boundaries. For example,
    timestamps 1000.1, 1000.5, and 1000.9 all belong to the same
    window (second 1000), while 1001.0 starts a new window.
    """

    count: int
    window_start: float

    def is_current_window(self, current_time: float) -> bool:
        """Check if given time is within the same second window.

        Parameters
        ----------
        current_time : float
            Unix timestamp to check

        Returns
        -------
        bool
            True if current_time is in same second as window_start

        Notes
        -----
        Uses integer comparison of timestamps to determine if times
        fall within the same one-second window boundary.

        Examples
        --------
        >>> window = RateLimitWindow(count=5, window_start=1000.3)
        >>> window.is_current_window(1000.9)  # Same second
        True
        >>> window.is_current_window(1001.0)  # Next second
        False
        """
        return int(current_time) == int(self.window_start)


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
    rate_limit_windows : Dict[str, RateLimitWindow]
        Internal rate limiting windows per team (thread-safe)
    orders_lock : threading.RLock
        Lock for thread-safe access to rate limit windows

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
        position_service,
    ):
        """Initialize the order validation service.

        Parameters
        ----------
        validator : ConstraintBasedOrderValidator
            Configured validator with role-specific constraints
        exchange : ExchangeVenue
            Exchange venue for cancellation operations
        position_service : PositionManagementService
            Service for managing position state
        """
        self.validator = validator
        self.exchange = exchange
        self.position_service = position_service

        # Initialize internal rate limiting state
        self.rate_limit_windows: Dict[str, RateLimitWindow] = {}
        self.orders_lock = threading.RLock()

    def get_order_count(
        self, team_id: str, current_time: Optional[float] = None
    ) -> int:
        """Get current order count for a team within specified second window.

        Parameters
        ----------
        team_id : str
            The team ID to get order count for
        current_time : float, optional
            Unix timestamp for current time. If None, uses time.time()

        Returns
        -------
        int
            Number of orders submitted by the team in specified second window

        Notes
        -----
        This method implements proper per-second rate limiting by:
        1. Checking if team has an existing rate limit window
        2. If window exists and matches requested time, returns count
        3. If no window or time doesn't match, returns 0 (no orders in that window)

        The method does NOT modify the existing window when checking
        different time periods - it only reports what's in that window.

        The method is thread-safe and uses integer second boundaries
        for window comparison (e.g., 1000.1 and 1000.9 are same window).
        """
        if current_time is None:
            current_time = time.time()

        with self.orders_lock:
            window = self.rate_limit_windows.get(team_id)

            if window is None:
                # No window exists - return 0 for any time
                return 0

            if window.is_current_window(current_time):
                # Requested time matches existing window
                return window.count
            else:
                # Requested time is different window - return 0
                return 0

    def increment_order_count(
        self, team_id: str, current_time: Optional[float] = None
    ) -> None:
        """Increment order count for a team after successful validation.

        Parameters
        ----------
        team_id : str
            The team ID to increment order count for
        current_time : float, optional
            Unix timestamp for current time. If None, uses time.time()

        Notes
        -----
        This method should be called by the validator thread after
        successful order validation to update the rate limiting state.
        It handles window creation and rollover when entering a new second.

        The method is thread-safe and automatically manages window
        transitions and count accumulation.
        """
        if current_time is None:
            current_time = time.time()

        with self.orders_lock:
            window = self.rate_limit_windows.get(team_id)

            if window is None or not window.is_current_window(current_time):
                # New team or new second - start fresh window with count 1
                self.rate_limit_windows[team_id] = RateLimitWindow(
                    1, current_time
                )
            else:
                # Same window - increment count
                self.rate_limit_windows[team_id] = RateLimitWindow(
                    count=window.count + 1, window_start=window.window_start
                )

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
        # Get current state using services
        team_positions = self.position_service.get_positions(team.team_id)
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
