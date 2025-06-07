"""
Tests for the main module.
"""

from intern_trading_game.main import main


def test_main_returns_zero():
    """Test that the main function returns 0."""
    # Given - The main module of the application
    # The main function is the entry point for the application and should
    # initialize the exchange and list some sample instruments.

    # When - The main function is executed
    # We call the main function which should perform its initialization tasks
    # and return a status code.
    result = main()

    # Then - The function returns a success code
    # The main function should return 0, indicating successful execution.
    assert result == 0
