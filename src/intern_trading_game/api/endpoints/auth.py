"""Authentication and team registration endpoints."""

import threading
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends

from ...infrastructure.api.auth import team_registry
from ...infrastructure.api.models import (
    ApiError,
    ApiResponse,
    TeamRegistration,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_positions():
    """Get the positions dict dependency."""
    from ..main import positions

    return positions


def get_positions_lock():
    """Get the positions lock dependency."""
    from ..main import positions_lock

    return positions_lock


def get_orders_lock():
    """Get the orders lock dependency."""
    from ..main import orders_lock

    return orders_lock


def get_orders_this_second():
    """Get the orders this second dict dependency."""
    from ..main import orders_this_second

    return orders_this_second


@router.post("/register", response_model=ApiResponse)
async def register_team(
    registration: TeamRegistration,
    positions: Dict = Depends(get_positions),
    positions_lock: threading.RLock = Depends(get_positions_lock),
    orders_lock: threading.RLock = Depends(get_orders_lock),
    orders_this_second: Dict = Depends(get_orders_this_second),
):
    """Register a new trading team.

    Parameters
    ----------
    registration : TeamRegistration
        Team name and role selection

    Returns
    -------
    ApiResponse
        Success response with team details and API key

    Raises
    ------
    HTTPException
        400 Bad Request if role not supported
    """
    # Generate request ID
    request_id = f"req_{datetime.now().timestamp()}"

    # For MVP, only support market_maker
    if registration.role != "market_maker":
        return ApiResponse(
            success=False,
            request_id=request_id,
            order_id=None,
            data=None,
            error=ApiError(
                code="UNSUPPORTED_ROLE",
                message="Only market_maker role supported in MVP",
                details={"requested_role": registration.role},
            ),
            timestamp=datetime.now(),
        )

    team_info = team_registry.register_team(
        team_name=registration.team_name, role=registration.role
    )

    # Initialize tracking
    with positions_lock:
        positions[team_info.team_id] = {}

    with orders_lock:
        orders_this_second[team_info.team_id] = 0

    return ApiResponse(
        success=True,
        request_id=request_id,
        data={
            "team_id": team_info.team_id,
            "team_name": team_info.team_name,
            "role": team_info.role,
            "api_key": team_info.api_key,
            "created_at": team_info.created_at.isoformat(),
        },
        timestamp=datetime.now(),
    )
