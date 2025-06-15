"""Authentication module for the REST API.

This module provides team registration and API key authentication for
the Intern Trading Game REST API. It implements a simple in-memory
registry suitable for development and testing."""

import secrets
from datetime import datetime
from typing import Dict, Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from .models import TeamInfo


class TeamRegistry:
    """In-memory registry for trading team authentication.

    This class manages team registration and API key validation for
    the trading game. It provides a simple authentication mechanism
    where each team receives a unique API key upon registration.

    In production deployments, this would typically be backed by
    a persistent database rather than in-memory storage.

    Attributes
    ----------
    teams : Dict[str, TeamInfo]
        Mapping of team IDs to team information objects.
    api_key_to_team : Dict[str, str]
        Mapping of API keys to team IDs for fast lookup.

    Notes
    -----
    API keys are generated using cryptographically secure random
    tokens with 32 bytes of entropy (256 bits), providing
    sufficient security for the trading simulation.

    The registry assigns sequential team IDs (TEAM_001, TEAM_002,
    etc.) to maintain ordering and simplify debugging.

    Examples
    --------
    >>> registry = TeamRegistry()
    >>> team = registry.register_team("AlphaBot", "market_maker")
    >>> print(team.team_id)
    TEAM_001
    >>> print(team.api_key.startswith("itg_"))
    True

    >>> # Lookup by API key
    >>> retrieved = registry.get_team_by_api_key(team.api_key)
    >>> print(retrieved.team_name)
    AlphaBot
    """

    def __init__(self):
        self.teams: Dict[str, TeamInfo] = {}
        self.api_key_to_team: Dict[str, str] = {}
        self._team_counter = 0

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
        >>> registry = TeamRegistry()
        >>> team = registry.register_team("QuantFund", "hedge_fund")
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
        """Look up team by API key."""
        team_id = self.api_key_to_team.get(api_key)
        if team_id:
            return self.teams.get(team_id)
        return None

    def get_team_by_id(self, team_id: str) -> Optional[TeamInfo]:
        """Look up team by ID."""
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


# Global registry instance
team_registry = TeamRegistry()

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
