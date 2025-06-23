"""Position service API protocol definitions.

This module defines the protocol (interface) for position services,
establishing a contract for position tracking as required by the REST API.

The protocol maps to REST operation:
- Get Positions (GET /positions)

Internal operations for trade processing are included but should
be moved to a separate internal interface in future refactoring.

Notes
-----
This protocol focuses on the REST API requirements while maintaining
compatibility with the current implementation.
"""

from typing import Dict, Protocol

from ...infrastructure.api.models import OrderResponse, TeamInfo
from ..exchange.components.core.models import Order, OrderResult


class PositionServiceProtocol(Protocol):
    """Protocol defining the position service interface for REST operations.

    This protocol establishes the contract for position queries required
    by the REST API, plus internal operations that will be refactored later.
    """

    def get_positions(self, team_id: str) -> Dict[str, int]:
        """Get current positions for a team.

        Parameters
        ----------
        team_id : str
            The team identifier

        Returns
        -------
        Dict[str, int]
            Mapping of instrument_id to position quantity.
            Positive values are long positions, negative are short.

        Notes
        -----
        Maps to GET /positions endpoint.
        Returns a copy of positions to prevent external modification.
        Empty dict returned for teams with no positions.
        """
        ...


class PositionInternalProtocol(Protocol):
    """Protocol for internal position operations.

    These methods are used by the threading infrastructure but are not
    exposed through the REST API. They will be moved to a separate
    service implementation in future refactoring.
    """

    def get_position_for_instrument(
        self, team_id: str, instrument_id: str
    ) -> int:
        """Get position for a specific instrument.

        Used internally for validation and risk checks.
        """
        ...

    def update_position(
        self, team_id: str, instrument_id: str, delta: int
    ) -> None:
        """Update a team's position in an instrument.

        Used internally after trade execution.
        """
        ...

    def get_total_absolute_position(self, team_id: str) -> int:
        """Calculate total absolute position across all instruments.

        Used internally for portfolio-level position limit validation.
        """
        ...

    def process_trade_result(
        self, result: OrderResult, order: Order, team_info: TeamInfo
    ) -> OrderResponse:
        """Process a trade result and update positions.

        Used internally by the trade publisher thread.
        """
        ...

    def initialize_team(self, team_id: str) -> None:
        """Initialize position tracking for a new team.

        Used internally during team registration.
        """
        ...


class PositionEventType:
    """Enumeration of position service event types.

    These events are published for real-time position updates.
    """

    POSITION_UPDATE = "position_update"
    EXECUTION_REPORT = "execution_report"
