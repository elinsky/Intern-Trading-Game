"""Authentication module for the REST API.

This module provides API key authentication for the Intern Trading Game
REST API through FastAPI dependency injection. It eliminates global state
by accepting service dependencies as parameters, enabling testable and
modular authentication workflows.

The authentication system validates API keys against the GameService
team registry and provides secure access control for trading operations.
All authentication dependencies follow the dependency injection pattern
established in the application architecture.

Examples
--------
>>> # In an endpoint
>>> @app.get("/orders")
>>> async def get_orders(
...     team: TeamInfo = Depends(get_current_team)
... ) -> List[Order]:
...     return get_team_orders(team.team_id)
"""

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from ...api.dependencies import get_game_service
from ...domain.game.game_service import GameService
from .models import TeamInfo

# FastAPI dependency
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_team(
    api_key: str = Security(api_key_header),
    game_service: GameService = Depends(get_game_service),
) -> TeamInfo:
    """FastAPI dependency to validate API key and return team information.

    This dependency function provides secure authentication for trading
    endpoints by validating API keys against the team registry. It uses
    dependency injection to access the GameService rather than global
    state, enabling testable and modular authentication workflows.

    The function validates the presence and authenticity of API keys,
    returning complete team information for authenticated requests and
    raising HTTP exceptions for authentication failures.

    Parameters
    ----------
    api_key : str
        The API key provided in the X-API-Key header. This key is
        generated during team registration and must match a registered
        team's authentication credentials.
    game_service : GameService
        The GameService instance containing team registry and
        authentication state. Injected via FastAPI dependency system
        to eliminate global state access.

    Returns
    -------
    TeamInfo
        Complete team information including:
        - team_id: Unique team identifier
        - team_name: Display name for the team
        - role: Trading role (market_maker, hedge_fund, etc.)
        - api_key: Authentication key (for reference)
        - created_at: Team registration timestamp

    Raises
    ------
    HTTPException
        401 Unauthorized if:
        - No API key provided in request headers
        - API key does not match any registered team
        - API key format is invalid

    Notes
    -----
    This dependency eliminates global state access by accepting the
    GameService as an injected parameter. This pattern enables:
    - Easy mocking for unit tests
    - Service isolation and testing
    - Clear dependency relationships
    - Compliance with SOLID principles

    The dependency uses FastAPI's Security() function to automatically
    extract the API key from request headers, providing a clean
    interface for endpoint authentication.

    TradingContext
    --------------
    API key authentication is critical for trading system security:
    - Prevents unauthorized order submission
    - Enables proper position tracking per team
    - Supports audit trails for regulatory compliance
    - Ensures fair access to trading resources

    Each team receives a unique API key with 256 bits of entropy,
    providing strong security against brute force attacks. Keys are
    transmitted via secure headers and validated on each request.

    Examples
    --------
    >>> # Endpoint with authentication
    >>> @app.post("/exchange/orders")
    >>> async def submit_order(
    ...     order: OrderRequest,
    ...     team: TeamInfo = Depends(get_current_team)
    ... ) -> OrderResponse:
    ...     # team.team_id is now available for order processing
    ...     return process_order(order, team.team_id)
    >>>
    >>> # Testing with mocked authentication
    >>> async def test_authenticated_endpoint():
    ...     mock_team = TeamInfo(team_id="TEST_001", ...)
    ...     with patch("auth.get_current_team", return_value=mock_team):
    ...         response = await client.post("/orders", json=order_data)
    ...         assert response.status_code == 200
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
        )

    team = game_service.get_team_by_api_key(api_key)
    if not team:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return team
