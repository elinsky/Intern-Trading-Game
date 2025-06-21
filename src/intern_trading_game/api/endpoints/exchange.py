"""Exchange API endpoints with response coordinator.

This module contains updated exchange endpoints that use the OrderResponseCoordinator
instead of global dictionaries for managing order responses.
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ...constants.errors import ErrorCodes
from ...domain.exchange.response.interfaces import (
    OrderResponseCoordinatorInterface,
)
from ...infrastructure.api.auth import TeamInfo, get_current_team
from ...infrastructure.api.models import (
    ApiError,
    ApiResponse,
    OrderRequest,
)
from ..dependencies import get_exchange

router = APIRouter(prefix="/exchange", tags=["exchange"])


def get_order_queue():
    """Get the global order queue."""
    from ..main import order_queue

    return order_queue


def get_response_coordinator() -> OrderResponseCoordinatorInterface:
    """Get the response coordinator from app state."""
    from ..main import app

    coordinator = getattr(app.state, "response_coordinator", None)
    if not coordinator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Response coordinator not initialized",
        )
    return coordinator


def validate_order_type(order_request: OrderRequest):
    """Validate and convert order type."""
    from ...domain.exchange.models.order import OrderType

    try:
        return OrderType[order_request.order_type.upper()]
    except KeyError:
        return None


def validate_order_side(order_request: OrderRequest):
    """Validate and convert order side."""
    from ...domain.exchange.models.order import OrderSide

    try:
        return OrderSide(order_request.side)
    except ValueError:
        return None


def create_validation_error_response(code: str, message: str) -> ApiResponse:
    """Create a validation error response."""
    return ApiResponse(
        success=False,
        request_id="",  # Empty string for errors before registration
        error=ApiError(
            code=code,
            message=message,
        ),
        timestamp=datetime.now(),
    )


async def process_order_submission(
    order, team_info, order_queue, coordinator, request_id
):
    """Process the order submission after validation."""
    # Create event for backward compatibility with current thread design
    response_event = asyncio.Event()

    # Submit to order queue with request_id
    order_queue.put(
        (
            "new_order",
            order,
            team_info,
            response_event,  # Not used by v2 threads
            request_id,
        )
    )

    # Wait for response using coordinator (async)
    def wait_for_completion():
        return coordinator.wait_for_completion(request_id)

    # Run synchronous wait in thread pool
    result = await asyncio.to_thread(wait_for_completion)

    if result is None or result.api_response is None:
        # Timeout occurred
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Order processing timeout",
        )

    return result.api_response


@router.post("/orders", response_model=ApiResponse)
async def submit_order(
    order_request: OrderRequest,
    team_info: TeamInfo = Depends(get_current_team),
    order_queue=Depends(get_order_queue),
    coordinator: OrderResponseCoordinatorInterface = Depends(
        get_response_coordinator
    ),
) -> ApiResponse:
    """Submit a new order to the exchange.

    This endpoint validates the order request and submits it to the
    order processing pipeline. It uses the OrderResponseCoordinator
    to manage the asynchronous response flow.

    Parameters
    ----------
    order_request : OrderRequest
        The order details from the client
    team_info : TeamInfo
        Authenticated team information
    order_queue : Queue
        The order processing queue
    coordinator : OrderResponseCoordinatorInterface
        The response coordinator for managing async responses

    Returns
    -------
    ApiResponse
        The order submission response

    Raises
    ------
    HTTPException
        If order submission fails or times out
    """
    try:
        # Convert request to domain order
        from ...domain.exchange.models.order import Order, OrderType

        # Validate order type
        order_type = validate_order_type(order_request)
        if order_type is None:
            return create_validation_error_response(
                ErrorCodes.INVALID_ORDER_TYPE,
                f"Invalid order type: {order_request.order_type}",
            )

        # Validate side
        side = validate_order_side(order_request)
        if side is None:
            return create_validation_error_response(
                ErrorCodes.INVALID_SIDE,
                f"Invalid side: {order_request.side}. Must be 'buy' or 'sell'",
            )

        # Validate price for limit orders
        if order_type == OrderType.LIMIT and order_request.price is None:
            return create_validation_error_response(
                ErrorCodes.MISSING_PRICE, "Price required for limit orders"
            )

        # Create order
        order = Order(
            trader_id=team_info.team_id,
            instrument_id=order_request.instrument_id,
            order_type=order_type,
            side=side,
            quantity=order_request.quantity,
            price=order_request.price,
            client_order_id=order_request.client_order_id,
        )

        # Register request with coordinator
        registration = coordinator.register_request(
            team_id=team_info.team_id,
            timeout_seconds=5.0,  # Could come from config
        )
        request_id = registration.request_id

        # Process the order submission
        return await process_order_submission(
            order, team_info, order_queue, coordinator, request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        return ApiResponse(
            success=False,
            request_id=request_id if "request_id" in locals() else "",
            order_id=None,
            data=None,
            error=ApiError(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"Failed to submit order: {str(e)}",
                details=None,
            ),
            timestamp=datetime.now(),
        )


@router.delete("/orders/{order_id}", response_model=ApiResponse)
async def cancel_order(
    order_id: str,
    team_info: TeamInfo = Depends(get_current_team),
    order_queue=Depends(get_order_queue),
    coordinator: OrderResponseCoordinatorInterface = Depends(
        get_response_coordinator
    ),
) -> ApiResponse:
    """Cancel an existing order.

    This endpoint attempts to cancel an order that has been previously
    submitted. It uses the OrderResponseCoordinator to manage the
    asynchronous cancellation response.

    Parameters
    ----------
    order_id : str
        The ID of the order to cancel
    team_info : TeamInfo
        Authenticated team information
    order_queue : Queue
        The order processing queue
    coordinator : OrderResponseCoordinatorInterface
        The response coordinator for managing async responses

    Returns
    -------
    ApiResponse
        The cancellation response

    Raises
    ------
    HTTPException
        If cancellation fails or times out
    """
    try:
        # Register cancellation request with coordinator
        registration = coordinator.register_request(
            team_id=team_info.team_id,
            timeout_seconds=3.0,  # Shorter timeout for cancellations
        )
        request_id = registration.request_id

        # Create event for backward compatibility
        response_event = asyncio.Event()

        # Submit cancellation to order queue
        order_queue.put(
            (
                "cancel_order",
                order_id,
                team_info,
                response_event,  # Not used by v2 threads
                request_id,
            )
        )

        # Wait for response using coordinator
        def wait_for_completion():
            return coordinator.wait_for_completion(request_id)

        # Run synchronous wait in thread pool
        result = await asyncio.to_thread(wait_for_completion)

        if result is None or result.api_response is None:
            # Timeout occurred
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Order cancellation timeout",
            )

        return result.api_response

    except HTTPException:
        raise
    except Exception as e:
        return ApiResponse(
            success=False,
            request_id=request_id if "request_id" in locals() else "",
            order_id=order_id,
            data=None,
            error=ApiError(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"Failed to cancel order: {str(e)}",
                details=None,
            ),
            timestamp=datetime.now(),
        )


@router.get("/orders", response_model=ApiResponse)
async def get_orders(
    team_info: TeamInfo = Depends(get_current_team),
    exchange=Depends(get_exchange),
) -> ApiResponse:
    """Get all orders for the authenticated team.

    This endpoint retrieves all orders (open and filled) for the
    current team from the exchange.

    Parameters
    ----------
    team_info : TeamInfo
        Authenticated team information
    exchange : ExchangeVenue
        The exchange instance

    Returns
    -------
    ApiResponse
        Response containing list of orders
    """
    try:
        # Get orders from exchange
        orders = exchange.get_orders_by_trader(team_info.team_id)

        # Convert to API format
        order_data = [
            {
                "order_id": order.order_id,
                "client_order_id": order.client_order_id,
                "instrument_id": order.instrument_id,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "filled_quantity": order.filled_quantity,
                "price": order.price,
                "status": order.status.value,
                "timestamp": order.timestamp.isoformat(),
            }
            for order in orders
        ]

        return ApiResponse(
            success=True,
            request_id="",
            order_id=None,
            data={"orders": order_data},
            error=None,
            timestamp=datetime.now(),
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            request_id="",
            order_id=None,
            data=None,
            error=ApiError(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"Failed to get orders: {str(e)}",
                details=None,
            ),
            timestamp=datetime.now(),
        )
