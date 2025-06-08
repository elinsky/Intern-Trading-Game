"""Common types and enums for the exchange module.

This module contains shared types used across the exchange components
to avoid circular imports.
"""

from enum import Enum


class LiquidityType(str, Enum):
    """Liquidity type for trade execution.

    Indicates whether an order added or removed liquidity from the
    order book, which affects fee calculations and rebates.

    Attributes
    ----------
    MAKER : str
        Order added liquidity (posted to book and waited)
    TAKER : str
        Order removed liquidity (crossed the spread immediately)

    Notes
    -----
    Liquidity classification follows standard exchange conventions:
    - Maker orders provide liquidity by posting limit orders
    - Taker orders consume liquidity by crossing the spread
    - Market orders are always takers
    - Limit orders can be either, depending on price

    Fee structures typically favor makers with rebates and charge
    takers fees to incentivize liquidity provision.

    TradingContext
    --------------
    Market Assumptions
        - Maker rebates incentivize tight spreads
        - Taker fees fund the rebate pool
        - Classification happens at execution time

    Trading Rules
        - Market orders always pay taker fees
        - Limit orders at marketable prices are takers
        - Limit orders that post to book are makers

    Examples
    --------
    >>> # Limit order that posts to book
    >>> order = Order(side="buy", price=127.50, ...)  # Below ask
    >>> # This becomes a MAKER when it rests in book

    >>> # Market order that executes immediately
    >>> order = Order(order_type="market", ...)
    >>> # This is always a TAKER
    """

    MAKER = "maker"
    TAKER = "taker"
