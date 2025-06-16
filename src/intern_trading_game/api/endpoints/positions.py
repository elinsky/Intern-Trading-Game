"""Position and open orders query endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends

from ...infrastructure.api.auth import TeamInfo, get_current_team
from ...infrastructure.api.models import ApiResponse

router = APIRouter(tags=["positions"])


def get_position_service():
    """Get the position service dependency."""
    from ..main import position_service

    return position_service


@router.get("/positions", response_model=ApiResponse)
async def get_positions(
    team: TeamInfo = Depends(get_current_team),
    position_service=Depends(get_position_service),
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

    # Get positions from service
    team_positions = position_service.get_positions(team.team_id)

    return ApiResponse(
        success=True,
        request_id=request_id,
        data={
            "team_id": team.team_id,
            "positions": team_positions,
            "last_updated": datetime.now().isoformat(),
        },
        timestamp=datetime.now(),
    )
