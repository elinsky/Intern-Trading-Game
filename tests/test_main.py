"""
Tests for the main module.
"""

from intern_trading_game.main import main


def test_main_returns_zero():
    """Test that the main function returns 0."""
    assert main() == 0
