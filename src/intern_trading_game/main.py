"""
Intern Trading Game - Main Module

This module serves as the entry point for the Intern Trading Game application.
"""

# Order is imported but not used in this file
from intern_trading_game.domain.models.instrument import Instrument

from .domain.exchange.venue import ExchangeVenue


def main():
    """
    Main entry point for the application.
    """
    print("Welcome to the Intern Trading Game!")
    print("Initializing exchange...")

    # Create an exchange venue
    exchange = ExchangeVenue()

    # Create and list some sample instruments
    instruments = [
        Instrument(symbol="AAPL", underlying="AAPL"),
        Instrument(symbol="MSFT", underlying="MSFT"),
        Instrument(
            symbol="AAPL_150C_DEC",
            strike=150.0,
            expiry="2024-12-20",
            option_type="call",
            underlying="AAPL",
        ),
        Instrument(
            symbol="MSFT_300P_JUN",
            strike=300.0,
            expiry="2024-06-21",
            option_type="put",
            underlying="MSFT",
        ),
    ]

    for instrument in instruments:
        exchange.list_instrument(instrument)

    instruments_list = [i.symbol for i in exchange.get_all_instruments()]
    print(f"Listed instruments: {instruments_list}")
    print("\nExchange is ready for trading!")

    return 0


if __name__ == "__main__":
    exit(main())
