"""System-level integration test fixtures.

Provides fixtures for complete end-to-end system testing with all
components running together including threads, API, and persistence.
"""

import pytest
from fastapi.testclient import TestClient

from intern_trading_game.api.main import (
    app,
    exchange,
    orders_this_second,
    positions,
    team_registry,
)


@pytest.fixture
def system_context():
    """Complete system context for end-to-end testing.

    This fixture provides the highest level of integration testing with:
    - Full API server with all threads running
    - Complete trading system functionality
    - Real threading pipeline
    - All services integrated

    Note: This is the same as api_context but semantically represents
    complete system testing rather than just API testing.
    """
    # Reset state before test
    exchange.order_books.clear()
    exchange.instruments.clear()
    exchange.all_order_ids.clear()
    positions.clear()
    orders_this_second.clear()
    team_registry.teams.clear()
    team_registry.api_key_to_team.clear()
    team_registry._team_counter = 0

    # Import the threading functions to create fresh threads
    import threading

    from intern_trading_game.api.main import (
        matching_thread_wrapper,
        position_tracker_thread_wrapper,
        trade_publisher_thread_wrapper,
        validator_thread_wrapper,
        websocket_thread_wrapper,
    )

    # Create fresh threads for this test
    fresh_validator_t = threading.Thread(
        target=validator_thread_wrapper, daemon=True
    )
    fresh_matching_t = threading.Thread(
        target=matching_thread_wrapper, daemon=True
    )
    fresh_publisher_t = threading.Thread(
        target=trade_publisher_thread_wrapper, daemon=True
    )
    fresh_position_t = threading.Thread(
        target=position_tracker_thread_wrapper, daemon=True
    )
    fresh_websocket_t = threading.Thread(
        target=websocket_thread_wrapper, daemon=True
    )

    # Temporarily replace the global thread references
    import intern_trading_game.api.main as main_module

    original_threads = (
        main_module.validator_t,
        main_module.matching_t,
        main_module.publisher_t,
        main_module.position_t,
        main_module.websocket_t,
    )

    # Replace with fresh threads
    main_module.validator_t = fresh_validator_t
    main_module.matching_t = fresh_matching_t
    main_module.publisher_t = fresh_publisher_t
    main_module.position_t = fresh_position_t
    main_module.websocket_t = fresh_websocket_t

    try:
        # TestClient will handle startup/shutdown events with fresh threads
        with TestClient(app) as client:
            threads = {
                "validator": fresh_validator_t,
                "matching": fresh_matching_t,
                "publisher": fresh_publisher_t,
                "position": fresh_position_t,
                "websocket": fresh_websocket_t,
            }

            yield {
                "client": client,
                "exchange": exchange,
                "positions": positions,
                "orders_this_second": orders_this_second,
                "team_registry": team_registry,
                "threads": threads,
            }
    finally:
        # Restore original threads
        main_module.validator_t = original_threads[0]
        main_module.matching_t = original_threads[1]
        main_module.publisher_t = original_threads[2]
        main_module.position_t = original_threads[3]
        main_module.websocket_t = original_threads[4]


# Alias for backwards compatibility and semantic clarity
@pytest.fixture
def api_context(system_context):
    """Alias for system_context to support tests that expect api_context."""
    return system_context
