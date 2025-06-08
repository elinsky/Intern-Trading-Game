"""API-level integration test fixtures.

Provides fixtures for testing the REST and WebSocket APIs with all
threads running but using in-memory components.
"""

import pytest
from fastapi.testclient import TestClient

from intern_trading_game.api.main import (
    app,
    exchange,
    matching_t,
    orders_this_tick,
    positions,
    publisher_t,
    team_registry,
    validator_t,
    websocket_t,
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
    orders_this_tick.clear()
    team_registry.teams.clear()
    team_registry.api_key_to_team.clear()
    team_registry._team_counter = 0

    # Check thread states and restart if needed
    threads = {
        "validator": validator_t,
        "matching": matching_t,
        "publisher": publisher_t,
        "websocket": websocket_t,
    }

    # TestClient will handle startup/shutdown events
    with TestClient(app) as client:
        yield {
            "client": client,
            "exchange": exchange,
            "positions": positions,
            "orders_this_tick": orders_this_tick,
            "team_registry": team_registry,
            "threads": threads,
        }


@pytest.fixture
def client(api_context):
    """Provide just the test client for simple tests."""
    return api_context["client"]


@pytest.fixture
def registered_team(client):
    """Register a test team and return its info."""
    response = client.post(
        "/auth/register", json={"team_name": "TestBot", "role": "market_maker"}
    )
    assert response.status_code == 200
    return response.json()
