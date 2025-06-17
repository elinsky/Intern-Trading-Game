"""API-level integration test fixtures.

Provides fixtures for testing the REST and WebSocket APIs with all
threads running but using in-memory components.
"""

import pytest
from fastapi.testclient import TestClient

from intern_trading_game.api.main import app


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
    # Exchange will be created fresh during startup
    # Position service state will be created fresh during app startup
    # Rate limiting state now owned by OrderValidationService
    # GameService state will be created fresh during app startup

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

    # Test instruments and constraints will be loaded from config by app startup

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

            # Get services from app state after startup
            exchange = client.app.state.exchange
            game_service = client.app.state.game_service

            yield {
                "client": client,
                "exchange": exchange,
                # Position service is now internal to the app
                "game_service": game_service,
                "threads": threads,
            }
    finally:
        # Restore original threads
        main_module.validator_t = original_threads[0]
        main_module.matching_t = original_threads[1]
        main_module.publisher_t = original_threads[2]
        main_module.position_t = original_threads[3]
        main_module.websocket_t = original_threads[4]


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
