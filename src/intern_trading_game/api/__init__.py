"""REST API module for the Intern Trading Game."""

from ..infrastructure.api.app import create_app
from ..infrastructure.api.auth import team_registry
from ..infrastructure.api.models import (
    OrderRequest,
    OrderResponse,
    PositionResponse,
    TeamInfo,
)

# Create the app instance for backwards compatibility
app = create_app()

__all__ = [
    "app",
    "OrderRequest",
    "OrderResponse",
    "TeamInfo",
    "PositionResponse",
    "team_registry",
]
