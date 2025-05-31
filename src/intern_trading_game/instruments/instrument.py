"""
Instrument module for the Intern Trading Game.

This module defines the Instrument class, which represents a tradeable asset.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Instrument:
    """
    Represents a tradeable instrument in the exchange.

    Attributes:
        symbol (str): The unique identifier for the instrument.
        strike (Optional[float]): The strike price for options, None for other
            instruments.
        expiry (Optional[str]): The expiration date for options in ISO format
            (YYYY-MM-DD).
        option_type (Optional[str]): The type of option ('call' or 'put'), None
            for other instruments.
        underlying (Optional[str]): The underlying asset symbol for
            derivatives.
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

        Returns:
            str: The instrument's symbol, which serves as its unique ID.
        """
        return self.symbol
