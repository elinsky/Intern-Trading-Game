"""Game service endpoints.

This module provides REST API endpoints for game operations including
team registration and management.
"""

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

router = APIRouter(prefix="/game", tags=["game"])


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


@router.post("/teams/register", response_model=ApiResponse)
async def register_team(
    registration: TeamRegistration,
    positions: Dict = Depends(get_positions),
    positions_lock: threading.RLock = Depends(get_positions_lock),
    orders_lock: threading.RLock = Depends(get_orders_lock),
    orders_this_second: Dict = Depends(get_orders_this_second),
):
    """Register a new team for the trading game.

    Creates a new team with the specified name and role, generating
    a unique team ID and API key for authentication.

    Parameters
    ----------
    registration : TeamRegistration
        Team name and role selection

    Returns
    -------
    ApiResponse
        Success response with team credentials or error

    Notes
    -----
    Team names must be unique. Roles include:
    - market_maker: Enhanced rebates, position limits
    - hedge_fund: Delta neutrality, volatility signals
    - arbitrage: SPX/SPY ratio constraints
    - retail: Standard fees, no special constraints
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

    # Check for duplicate team name
    existing_team = team_registry.get_team_by_name(registration.team_name)
    if existing_team is not None:
        return ApiResponse(
            success=False,
            request_id=request_id,
            error=ApiError(
                code="DUPLICATE_TEAM_NAME",
                message=f"Team name '{registration.team_name}' already exists",
            ),
            timestamp=datetime.now(),
        )

    # Register the team
    team_info = team_registry.register_team(
        team_name=registration.team_name, role=registration.role
    )

    # Initialize team positions with thread safety
    with positions_lock:
        positions[team_info.team_id] = {}

    # Initialize rate limiting
    with orders_lock:
        orders_this_second[team_info.team_id] = 0

    # Return success response
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


@router.get("/teams/{team_id}", response_model=ApiResponse)
async def get_team_info(
    team_id: str,
):
    """Get information about a specific team.

    Parameters
    ----------
    team_id : str
        The team ID to query

    Returns
    -------
    ApiResponse
        Success response with team information or error
    """
    # Generate request ID
    request_id = f"req_{datetime.now().timestamp()}"

    # Look up team
    team_info = team_registry.get_team_by_id(team_id)

    if team_info is None:
        return ApiResponse(
            success=False,
            request_id=request_id,
            error=ApiError(
                code="TEAM_NOT_FOUND",
                message=f"Team {team_id} not found",
            ),
            timestamp=datetime.now(),
        )

    # Return team information (excluding sensitive API key)
    return ApiResponse(
        success=True,
        request_id=request_id,
        data={
            "team_id": team_info.team_id,
            "team_name": team_info.team_name,
            "role": team_info.role,
            "created_at": team_info.created_at.isoformat(),
        },
        timestamp=datetime.now(),
    )
