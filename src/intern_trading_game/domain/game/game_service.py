"""Game orchestration service owning team management and game state.

This module implements the Game Service as defined in Architecture v4,
which is responsible for team management, role assignment, scoring,
and overall game flow control.
"""

import secrets
from datetime import datetime
from typing import Dict, Optional

from ...infrastructure.api.models import TeamInfo


class GameService:
    """Game orchestration service owning team management and game state.

    Per Architecture v4, this service owns:
    - Team registration and authentication
    - Role assignment (via team registration)
    - Score calculation (future)
    - Game flow control (future)
    - Service configuration (future)

    This service provides centralized management of game-related state
    and operations, ensuring consistency across the trading simulation.

    Attributes
    ----------
    teams : Dict[str, TeamInfo]
        Mapping of team IDs to team information objects.
    api_key_to_team : Dict[str, str]
        Mapping of API keys to team IDs for fast lookup.
    _team_counter : int
        Counter for generating sequential team IDs.

    Notes
    -----
    In the current monolithic implementation, this service manages
    in-memory state. In the future microservices architecture, this
    would be backed by a persistent Game State DB.

    The service generates cryptographically secure API keys with
    256 bits of entropy for team authentication.

    Examples
    --------
    >>> game_service = GameService()
    >>> team = game_service.register_team("AlphaBot", "market_maker")
    >>> print(team.team_id)
    TEAM_001
    >>> retrieved = game_service.get_team_by_api_key(team.api_key)
    >>> print(retrieved.team_name)
    AlphaBot
    """

    def __init__(self):
        """Initialize the game service with empty state."""
        # Team management state
        self.teams: Dict[str, TeamInfo] = {}
        self.api_key_to_team: Dict[str, str] = {}
        self._team_counter = 0

        # Future: scoring state, game configuration, etc.

    def register_team(self, team_name: str, role: str) -> TeamInfo:
        """Register a new trading team and generate API key.

        Creates a new team entry with a unique ID and cryptographically
        secure API key. The team can then use this API key to authenticate
        all subsequent API requests.

        Parameters
        ----------
        team_name : str
            Display name for the team (e.g., "AlphaBot", "QuantTraders").
            Must be between 1 and 50 characters.
        role : str
            Trading role for the team. Valid values are:
            - "market_maker": Provides liquidity with bid/ask quotes
            - "hedge_fund": Trades on volatility signals
            - "arbitrage": Exploits price discrepancies
            - "retail": Individual trader with limited capital

        Returns
        -------
        TeamInfo
            Complete team information including generated team_id
            and api_key for authentication.

        Notes
        -----
        The generated API key format is "itg_" followed by 43 characters
        of URL-safe base64 encoding, providing 256 bits of entropy.

        Team IDs are assigned sequentially (TEAM_001, TEAM_002, etc.)
        to maintain chronological ordering of registrations.

        Examples
        --------
        >>> game_service = GameService()
        >>> team = game_service.register_team("QuantFund", "hedge_fund")
        >>> print(f"Team {team.team_id} registered")
        Team TEAM_001 registered
        >>> print(f"API key: {team.api_key[:12]}...")  # Show prefix only
        API key: itg_a1b2c3d4...
        """
        self._team_counter += 1
        team_id = f"TEAM_{self._team_counter:03d}"
        api_key = f"itg_{secrets.token_urlsafe(32)}"

        team_info = TeamInfo(
            team_id=team_id,
            team_name=team_name,
            role=role,
            api_key=api_key,
            created_at=datetime.now(),
        )

        self.teams[team_id] = team_info
        self.api_key_to_team[api_key] = team_id

        return team_info

    def get_team_by_api_key(self, api_key: str) -> Optional[TeamInfo]:
        """Look up team by API key.

        Parameters
        ----------
        api_key : str
            The API key to search for

        Returns
        -------
        Optional[TeamInfo]
            Team information if found, None otherwise
        """
        team_id = self.api_key_to_team.get(api_key)
        if team_id:
            return self.teams.get(team_id)
        return None

    def get_team_by_id(self, team_id: str) -> Optional[TeamInfo]:
        """Look up team by ID.

        Parameters
        ----------
        team_id : str
            The team ID to search for

        Returns
        -------
        Optional[TeamInfo]
            Team information if found, None otherwise
        """
        return self.teams.get(team_id)

    def get_team_by_name(self, team_name: str) -> Optional[TeamInfo]:
        """Look up team by name.

        Parameters
        ----------
        team_name : str
            The team name to search for

        Returns
        -------
        Optional[TeamInfo]
            Team information if found, None otherwise
        """
        for team_info in self.teams.values():
            if team_info.team_name == team_name:
                return team_info
        return None
