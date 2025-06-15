"""API-level integration test fixtures.

Provides fixtures for testing the REST and WebSocket APIs with all
threads running but using in-memory components.
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
def api_context():
    """Full API context with all threads running.

    This fixture provides a complete API environment with:
    - All processing threads running
    - In-memory exchange
    - TestClient for HTTP/WebSocket testing

    Note: This fixture manages thread lifecycle and cleanup.
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
        matching_thread,
        trade_publisher_thread,
        validator_thread,
        websocket_thread,
    )

    # Create fresh threads for this test
    fresh_validator_t = threading.Thread(target=validator_thread, daemon=True)
    fresh_matching_t = threading.Thread(target=matching_thread, daemon=True)
    fresh_publisher_t = threading.Thread(
        target=trade_publisher_thread, daemon=True
    )
    fresh_websocket_t = threading.Thread(target=websocket_thread, daemon=True)

    # Temporarily replace the global thread references
    import intern_trading_game.api.main as main_module

    original_threads = (
        main_module.validator_t,
        main_module.matching_t,
        main_module.publisher_t,
        main_module.websocket_t,
    )

    # Replace with fresh threads
    main_module.validator_t = fresh_validator_t
    main_module.matching_t = fresh_matching_t
    main_module.publisher_t = fresh_publisher_t
    main_module.websocket_t = fresh_websocket_t

    # Test instruments will be added by the app startup

    # Load constraints for validator
    from intern_trading_game.api.main import validator
    from intern_trading_game.domain.exchange.validation.order_validator import (
        ConstraintConfig,
        ConstraintType,
    )

    mm_position_constraint = ConstraintConfig(
        constraint_type=ConstraintType.POSITION_LIMIT,
        parameters={"max_position": 50, "symmetric": True},
        error_code="MM_POS_LIMIT",
        error_message="Market maker position limit",
    )
    mm_instrument_constraint = ConstraintConfig(
        constraint_type=ConstraintType.INSTRUMENT_ALLOWED,
        parameters={"allowed_instruments": ["SPX_4500_CALL", "SPX_4500_PUT"]},
        error_code="INVALID_INSTRUMENT",
        error_message="Instrument not found",
    )
    validator.load_constraints(
        "market_maker", [mm_position_constraint, mm_instrument_constraint]
    )

    try:
        # TestClient will handle startup/shutdown events with fresh threads
        with TestClient(app) as client:
            threads = {
                "validator": fresh_validator_t,
                "matching": fresh_matching_t,
                "publisher": fresh_publisher_t,
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
        main_module.websocket_t = original_threads[3]


@pytest.fixture
def client(api_context):
    """Provide just the test client for simple tests."""
    return api_context["client"]


@pytest.fixture
def registered_team(client):
    """Register a test team and return its info."""
    response = client.post(
        "/game/teams/register",
        json={"team_name": "TestBot", "role": "market_maker"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    return data["data"]  # Return just the team data, not the full ApiResponse
