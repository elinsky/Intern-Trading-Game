"""Authentication module for the REST API.

This module provides team registration and API key authentication for
the Intern Trading Game REST API. It implements a simple in-memory
registry suitable for development and testing."""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from ...domain.game.game_service import GameService
from .models import TeamInfo

# Global game service instance (will be replaced with dependency injection)
team_registry = GameService()

# FastAPI dependency
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_team(
    api_key: str = Security(api_key_header),
) -> TeamInfo:
    """FastAPI dependency to validate API key and return team info."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
        )

    team = team_registry.get_team_by_api_key(api_key)
    if not team:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return team
