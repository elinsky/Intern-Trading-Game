"""Test fixtures for the Intern Trading Game.

This module provides reusable test data creators for orders, instruments,
and common trading scenarios. All fixtures follow a consistent pattern:
- Sensible defaults that can be overridden
- Common test scenarios as helper functions
- Test data constants for typical values

Example usage:
    >>> from tests.fixtures import create_test_order, create_spx_option
    >>> from tests.fixtures import create_test_spread, TEST_PRICES
    >>>
    >>> # Simple order with defaults
    >>> order = create_test_order()
    >>>
    >>> # Order with custom price
    >>> order = create_test_order(price=TEST_PRICES["in_the_money"])
    >>>
    >>> # Create a bid/ask spread
    >>> spread = create_test_spread(spread_width=1.0)
"""

from .market_data import (
    TEST_PRICES,
    TEST_QUANTITIES,
    TEST_SPREADS,
    create_ladder_orders,
    create_matched_orders,
    create_order_book_scenario,
    create_spx_option,
    create_spy_option,
    create_test_order,
    create_test_spread,
    create_test_trade,
)

__all__ = [
    # Constants
    "TEST_PRICES",
    "TEST_QUANTITIES",
    "TEST_SPREADS",
    # Order creators
    "create_test_order",
    # Instrument creators
    "create_spx_option",
    "create_spy_option",
    # Scenario creators
    "create_test_spread",
    "create_ladder_orders",
    "create_order_book_scenario",
    "create_matched_orders",
    "create_test_trade",
]
