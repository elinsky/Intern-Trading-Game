"""Protocols for phase transition handling.

This module defines the protocols needed for handling phase transitions
in the exchange domain, following SOLID principles.
"""

from typing import Protocol


class ExchangeOperations(Protocol):
    """Protocol defining operations needed by phase transition handler.

    This protocol defines the minimal interface required from ExchangeVenue
    for handling phase transitions. Using a protocol ensures loose coupling
    and makes testing easier.

    Notes
    -----
    This follows the Interface Segregation Principle - the handler only
    needs these two methods, not the entire ExchangeVenue interface.
    """

    def execute_opening_auction(self) -> None:
        """Execute the opening auction batch match.

        This method should process all orders collected during pre-open
        using batch matching to establish fair opening prices.
        """
        ...

    def cancel_all_orders(self) -> None:
        """Cancel all resting orders across all instruments.

        This method should cancel every resting order in all order books,
        typically called when the market closes.
        """
        ...
