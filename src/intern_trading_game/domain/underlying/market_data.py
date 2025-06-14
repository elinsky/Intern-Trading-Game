"""Market data for underlying products.

This module defines data structures for underlying asset prices
used throughout the trading simulation.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UnderlyingMarketData:
    """Market data for a single underlying product.

    Represents the current market price for an underlying asset
    such as an index or ETF. This is product-agnostic and can
    be used for any underlying instrument.

    Parameters
    ----------
    symbol : str
        Underlying symbol (e.g., "SPX", "SPY", "NDX")
    timestamp : datetime
        Real-world timestamp of market data
    price : float
        Current price of the underlying

    Notes
    -----
    This class represents spot prices for underlying assets,
    not derivative prices. Options market data (bid/ask/last)
    should be handled separately.

    The design is intentionally simple and product-agnostic
    to support various underlying assets without modification.

    Examples
    --------
    >>> spx_data = UnderlyingMarketData(
    ...     symbol="SPX",
    ...     timestamp=datetime(2024, 3, 21, 10, 30, 0),
    ...     price=5234.50
    ... )
    >>> print(f"{spx_data.symbol}={spx_data.price}")
    SPX=5234.5

    >>> spy_data = UnderlyingMarketData(
    ...     symbol="SPY",
    ...     timestamp=datetime(2024, 3, 21, 10, 30, 0),
    ...     price=523.15
    ... )
    """

    symbol: str
    timestamp: datetime
    price: float
