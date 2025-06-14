"""Position and open orders query endpoints."""

import threading
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ...infrastructure.api.auth import TeamInfo, get_current_team
from ...infrastructure.api.models import ApiResponse

router = APIRouter(tags=["positions"])


def get_positions_dict():
    """Get the positions dict dependency."""
    from ..main import positions
    return positions


def get_positions_lock():
    """Get the positions lock dependency."""
    from ..main import positions_lock
    return positions_lock




@router.get("/positions", response_model=ApiResponse)
async def get_positions(
    team: TeamInfo = Depends(get_current_team),
    positions: Dict = Depends(get_positions_dict),
    positions_lock: threading.RLock = Depends(get_positions_lock),
):
    """Get current positions for the authenticated team.
    
    Parameters
    ----------
    team : TeamInfo
        Authenticated team information from API key
        
    Returns
    -------
    ApiResponse
        Success response with positions data
    """
    # Generate request ID
    request_id = f"req_{datetime.now().timestamp()}"
    
    with positions_lock:
        team_positions = positions.get(team.team_id, {}).copy()
    
    return ApiResponse(
        success=True,
        request_id=request_id,
        data={
            "team_id": team.team_id,
            "positions": team_positions,
            "last_updated": datetime.now().isoformat()
        },
        timestamp=datetime.now()
    )


