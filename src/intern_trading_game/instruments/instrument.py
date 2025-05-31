"""
Instrument module for the Intern Trading Game.

This module defines the Instrument class, which represents a tradeable asset.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Instrument:
    r"""
    Represents a tradeable instrument in the exchange.

    This class models financial instruments that can be traded on the exchange.
    It supports various types of instruments including stocks, futures, and
    options. For options, additional fields like strike price, expiration date,
    and option type (call/put) are provided.

    The instrument serves as the fundamental unit of trading in the system and
    is referenced by orders, trades, and market data.

    Parameters
    ----------
    symbol : str
        The unique identifier for the instrument.
    strike : Optional[float], default=None
        The strike price for options. None for non-option instruments.
    expiry : Optional[str], default=None
        The expiration date for options in ISO format (YYYY-MM-DD).
        None for non-expiring instruments.
    option_type : Optional[str], default=None
        The type of option ('call' or 'put'). None for non-option instruments.
    underlying : Optional[str], default=None
        The underlying asset symbol for derivatives. None for non-derivative
        instruments.

    Attributes
    ----------
    symbol : str
        The unique identifier for the instrument.
    strike : Optional[float]
        The strike price for options. None for non-option instruments.
    expiry : Optional[str]
        The expiration date for options in ISO format (YYYY-MM-DD).
        None for non-expiring instruments.
    option_type : Optional[str]
        The type of option ('call' or 'put'). None for non-option instruments.
    underlying : Optional[str]
        The underlying asset symbol for derivatives. None for non-derivative
        instruments.

    Notes
    -----
    Financial instruments are the building blocks of any trading system. They
    represent the assets that can be bought and sold on the exchange.

    For options, the Black-Scholes model is commonly used for pricing:

    $$C = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)$$

    where:

    $$d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$$

    $$d_2 = d_1 - \sigma\sqrt{T}$$

    The instrument ID is derived from the symbol, which must be unique across
    the exchange. This simplifies instrument lookup and reference.

    TradingContext
    -------------
    This implementation assumes:
    - Instruments are uniquely identified by their symbol
    - Options require strike, expiry, and option_type
    - Expiry dates follow ISO format (YYYY-MM-DD)
    - Option types are limited to 'call' and 'put'
    - No support for complex derivatives like swaps or structured products
    - No handling of corporate actions (splits, dividends, etc.)
    - No support for different settlement types or delivery methods

    Examples
    --------
    Creating a stock instrument:

    >>> apple_stock = Instrument(symbol="AAPL", underlying="AAPL")
    >>> apple_stock.id
    'AAPL'
    >>> apple_stock.option_type is None
    True

    Creating an option instrument:

    >>> apple_call = Instrument(
    ...     symbol="AAPL_C_150_20230621",
    ...     underlying="AAPL",
    ...     strike=150.0,
    ...     expiry="2023-06-21",
    ...     option_type="call"
    ... )
    >>> apple_call.id
    'AAPL_C_150_20230621'
    >>> apple_call.option_type
    'call'
    """

    symbol: str
    strike: Optional[float] = None
    expiry: Optional[str] = None
    option_type: Optional[str] = None
    underlying: Optional[str] = None

    def __post_init__(self):
        """Validate the instrument attributes after initialization."""
        if self.option_type and self.option_type.lower() not in [
            "call",
            "put",
        ]:
            raise ValueError("Option type must be 'call' or 'put'")

        if self.expiry:
            try:
                # Validate expiry date format
                year, month, day = map(int, self.expiry.split("-"))
                date(year, month, day)
            except (ValueError, TypeError):
                raise ValueError("Expiry must be in ISO format (YYYY-MM-DD)")

    @property
    def id(self) -> str:
        """
        Get the unique identifier for this instrument.

        Returns
        -------
        str
            The instrument's symbol, which serves as its unique ID.
        """
        return self.symbol
