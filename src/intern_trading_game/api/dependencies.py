"""FastAPI dependency injection functions for service layer access.

This module provides dependency injection functions that enable FastAPI
endpoints to access service layer components in a testable and modular
way. Dependencies follow the SOLID principles by depending on abstractions
rather than concrete implementations.

The dependency injection pattern eliminates global state access from
endpoints while enabling easy mocking and testing of service interactions.
All dependencies are configured during application startup and accessed
through FastAPI's dependency injection system.

Examples
--------
>>> # In an endpoint
>>> @app.post("/game/teams/register")
>>> async def register_team(
...     team_data: TeamRegistration,
...     game_service: GameService = Depends(get_game_service)
... ) -> TeamInfo:
...     return game_service.register_team(team_data.name, team_data.role)
"""

from fastapi import Request

from ..domain.exchange.venue import ExchangeVenue
from ..domain.game.game_service import GameService


def get_exchange(request: Request) -> ExchangeVenue:
    """Dependency to get exchange from app state.

    Retrieves the configured exchange instance from the FastAPI
    application state. This allows endpoints to access the exchange
    without importing global variables.

    Parameters
    ----------
    request : Request
        FastAPI request object containing app reference

    Returns
    -------
    ExchangeVenue
        The exchange instance from app state

    Raises
    ------
    AttributeError
        If exchange is not found in app state
    """
    return request.app.state.exchange


def get_game_service(request: Request) -> GameService:
    """FastAPI dependency to retrieve the GameService instance.

    This dependency function provides access to the centralized GameService
    instance that owns team management state and operations. The service
    is initialized during application startup and stored in app.state for
    dependency injection throughout the request lifecycle.

    The GameService handles team registration, API key management, role
    assignment, and team lookup operations. It maintains consistency of
    team state across all trading operations and ensures proper
    authentication for API access.

    Parameters
    ----------
    request : Request
        FastAPI request object containing application state from which
        the GameService instance is retrieved. The service is stored
        in request.app.state.game_service during application startup.

    Returns
    -------
    GameService
        The initialized GameService instance containing team registry
        and authentication state. This service provides methods for:
        - register_team(): Create new trading teams
        - get_team_by_api_key(): Authenticate API requests
        - get_team_by_id(): Retrieve team information
        - get_team_by_name(): Lookup teams by display name

    Notes
    -----
    This dependency function eliminates global state access by providing
    controlled access to the GameService through FastAPI's dependency
    injection system. The service instance is created once during
    application startup and reused across all requests.

    The dependency follows the Dependency Inversion Principle by allowing
    endpoints to depend on the GameService abstraction rather than
    concrete global variables or direct instantiation.

    TradingContext
    --------------
    The GameService manages critical trading infrastructure state:
    - Team authentication keys for secure API access
    - Role assignments that determine trading constraints
    - Team registration timing for audit and compliance
    - API key rotation and security management

    All trading operations depend on proper team authentication, making
    this service a critical component of the trading infrastructure.

    Examples
    --------
    >>> # Basic endpoint usage
    >>> @app.post("/teams/register")
    >>> async def register_team(
    ...     request: TeamRegistration,
    ...     game_service: GameService = Depends(get_game_service)
    ... ) -> TeamInfo:
    ...     return game_service.register_team(request.name, request.role)
    >>>
    >>> # Authentication dependency usage
    >>> async def get_current_team(
    ...     api_key: str = Security(api_key_header),
    ...     game_service: GameService = Depends(get_game_service)
    ... ) -> TeamInfo:
    ...     team = game_service.get_team_by_api_key(api_key)
    ...     if not team:
    ...         raise HTTPException(401, "Invalid API key")
    ...     return team
    """
    return request.app.state.game_service
