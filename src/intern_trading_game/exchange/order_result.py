"""Order result data structure for the Intern Trading Game.

This module defines the OrderResult dataclass that represents the outcome
of submitting an order to the exchange. It's separated into its own module
to avoid circular imports between venue.py and matching_engine.py.
"""

from dataclasses import dataclass, field
from typing import List

from intern_trading_game.exchange.trade import Trade


@dataclass
class OrderResult:
    """Represents the result of submitting an order.

    This class encapsulates all information about what happened when an order
    was submitted to the exchange, including its status, any trades that were
    generated, and the remaining unfilled quantity.

    Attributes
    ----------
    order_id : str
        The ID of the submitted order.
    status : str
        The status of the order. Possible values:
        - 'pending_new': Order is queued for batch matching (batch mode only)
        - 'new': Order acknowledged and resting in the order book
        - 'partially_filled': Order partially executed, remainder in book
        - 'filled': Order was completely filled
        - 'rejected': Order was rejected (future use for validation failures)
        - 'cancelled': Order was cancelled (future use)
    fills : List[Trade]
        Any trades that were generated. Empty for pending orders.
    remaining_quantity : float
        The unfilled quantity of the order. Equal to original quantity
        for pending orders, 0 for fully filled orders.

    Notes
    -----
    In continuous mode, orders will have status 'new', 'partially_filled',
    or 'filled' immediately upon submission. In batch mode, orders start
    as 'pending_new' and transition to 'new', 'partially_filled', or 'filled'
    after batch execution.

    The status progression follows standard FIX protocol conventions where
    possible, adapted for our game's requirements.
    """

    order_id: str
    status: str
    fills: List[Trade] = field(default_factory=list)
    remaining_quantity: float = 0
