"""Game service API protocol definitions.

This module defines the protocol (interface) for game services,
establishing a contract for team registration and game management.

The protocol maps to REST operation:
- Register Team (POST /auth/register)

Notes
-----
This protocol focuses on the team registration requirement from
the 5 core REST operations.
"""

from typing import Protocol

from ...infrastructure.api.models import TeamInfo


class GameServiceProtocol(Protocol):
    """Protocol defining the game service interface for REST operations.

    This protocol establishes the contract for team registration
    as required by the REST API.
    """

    def register_team(self, team_name: str, role: str) -> TeamInfo:
        """Register a new team for the game.

        Parameters
        ----------
        team_name : str
            The desired team name
        role : str
            The team's role (market_maker, hedge_fund, arbitrage, retail)

        Returns
        -------
        TeamInfo
            Team information including generated team_id and api_key

        Raises
        ------
        ValueError
            If team_name is already taken or role is invalid

        Notes
        -----
        Maps to POST /auth/register endpoint.
        Generates unique team_id and api_key for authentication.
        """
        ...
