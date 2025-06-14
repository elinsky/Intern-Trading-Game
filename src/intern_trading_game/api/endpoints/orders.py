"""Order management endpoints."""

import threading
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ...constants.errors import ErrorCodes
from ...domain.exchange.core.order import Order, OrderSide, OrderType
from ...infrastructure.api.auth import TeamInfo, get_current_team
from ...infrastructure.api.models import ApiError, ApiResponse, OrderRequest

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_queue():
    """Get the order queue dependency."""
    from ..main import order_queue

    return order_queue


def get_pending_orders():
    """Get the pending orders dict dependency."""
    from ..main import pending_orders

    return pending_orders


def get_order_responses():
    """Get the order responses dict dependency."""
    from ..main import order_responses

    return order_responses


def get_orders_lock():
    """Get the orders lock dependency."""
    from ..main import orders_lock

    return orders_lock


def get_orders_this_second():
    """Get the orders this second dict dependency."""
    from ..main import orders_this_second

    return orders_this_second


def get_exchange():
    """Get the exchange dependency."""
    from ..main import exchange

    return exchange


@router.post("", response_model=ApiResponse)
async def submit_order(
    request: OrderRequest,
    team: TeamInfo = Depends(get_current_team),
    order_queue=Depends(get_order_queue),
    pending_orders: Dict = Depends(get_pending_orders),
    order_responses: Dict = Depends(get_order_responses),
):
    """Submit a new order.

    Parameters
    ----------
    request : OrderRequest
        Order details including instrument, type, side, quantity, and price
    team : TeamInfo
        Authenticated team information from API key

    Returns
    -------
    ApiResponse
        Unified response with success status and order_id if accepted

    Raises
    ------
    HTTPException
        400 Bad Request for invalid order parameters
        504 Gateway Timeout if processing exceeds 5 seconds
    """
    # Generate request ID for tracking
    request_id = f"req_{datetime.now().timestamp()}"

    # Convert request to Order
    try:
        order_type = OrderType[request.order_type.upper()]
    except KeyError:
        return ApiResponse(
            success=False,
            request_id=request_id,
            error=ApiError(
                code=ErrorCodes.INVALID_ORDER_TYPE,
                message=f"Invalid order type: {request.order_type}",
            ),
            timestamp=datetime.now(),
        )

    # Validate price for limit orders
    if order_type == OrderType.LIMIT and request.price is None:
        return ApiResponse(
            success=False,
            request_id=request_id,
            error=ApiError(
                code=ErrorCodes.MISSING_PRICE,
                message="Price required for limit orders",
            ),
            timestamp=datetime.now(),
        )

    # Convert side to enum
    try:
        side = OrderSide(request.side)
    except ValueError:
        return ApiResponse(
            success=False,
            request_id=request_id,
            error=ApiError(
                code=ErrorCodes.INVALID_SIDE,
                message=f"Invalid side: {request.side}. Must be 'buy' or 'sell'",
            ),
            timestamp=datetime.now(),
        )

    # Create order
    order = Order(
        trader_id=team.team_id,
        instrument_id=request.instrument_id,
        order_type=order_type,
        side=side,
        quantity=request.quantity,
        price=request.price,
        client_order_id=request.client_order_id,
    )

    # Create response event
    response_event = threading.Event()
    response_key = f"{order.order_id}:{request_id}"
    pending_orders[response_key] = response_event

    # Submit to queue with 5-tuple format
    order_queue.put(("new_order", order, team, response_event, request_id))

    # Wait for response (with timeout)
    if response_event.wait(timeout=5.0):
        # Get response
        response = order_responses.pop(response_key)
        pending_orders.pop(response_key)
        return response
    else:
        # Timeout
        pending_orders.pop(response_key, None)
        raise HTTPException(status_code=504, detail="Order processing timeout")


@router.delete("/{order_id}", response_model=ApiResponse)
async def cancel_order(
    order_id: str,
    team: TeamInfo = Depends(get_current_team),
    order_queue=Depends(get_order_queue),
    pending_orders: Dict = Depends(get_pending_orders),
    order_responses: Dict = Depends(get_order_responses),
):
    """Cancel an existing order.

    Cancels are processed in FIFO order with all other order messages
    to ensure temporal fairness in the market.

    Parameters
    ----------
    order_id : str
        The exchange-assigned order ID to cancel
    team : TeamInfo
        Authenticated team information from API key

    Returns
    -------
    ApiResponse
        Unified response with success status

    Raises
    ------
    HTTPException
        504 Gateway Timeout if processing exceeds 5 seconds
    """
    # Generate request ID
    request_id = f"req_{datetime.now().timestamp()}"

    # Create response event for async processing
    response_event = threading.Event()
    response_key = f"{order_id}:{request_id}"
    pending_orders[response_key] = response_event

    # Submit cancel request to queue
    order_queue.put(
        ("cancel_order", order_id, team, response_event, request_id)
    )

    # Wait for response with timeout
    if response_event.wait(timeout=5.0):
        # Get response
        response = order_responses.pop(response_key)
        pending_orders.pop(response_key)
        return response
    else:
        # Timeout
        pending_orders.pop(response_key, None)
        raise HTTPException(status_code=504, detail="Cancel request timeout")


@router.get("", response_model=ApiResponse)
async def get_open_orders(
    team: TeamInfo = Depends(get_current_team),
    exchange=Depends(get_exchange),
):
    """Get all open (resting) orders for the authenticated team.

    Parameters
    ----------
    team : TeamInfo
        Authenticated team information from API key

    Returns
    -------
    ApiResponse
        Success response with list of open orders
    """
    # Generate request ID
    request_id = f"req_{datetime.now().timestamp()}"

    # Get all resting orders from exchange
    all_orders = exchange.get_all_resting_orders()

    # Filter for team's orders
    team_orders = []
    for instrument_orders in all_orders.values():
        for order in instrument_orders:
            if order.trader_id == team.team_id:
                team_orders.append(
                    {
                        "order_id": order.order_id,
                        "client_order_id": order.client_order_id,
                        "instrument_id": order.instrument_id,
                        "side": order.side.value,
                        "order_type": order.order_type.value.lower(),
                        "quantity": order.quantity,
                        "filled_quantity": order.filled_quantity,
                        "remaining_quantity": order.quantity
                        - order.filled_quantity,
                        "price": order.price,
                        "timestamp": order.timestamp.isoformat(),
                    }
                )

    return ApiResponse(
        success=True,
        request_id=request_id,
        data={
            "team_id": team.team_id,
            "orders": team_orders,
            "count": len(team_orders),
        },
        timestamp=datetime.now(),
    )
