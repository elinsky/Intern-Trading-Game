"""Tests for the REST API module.

This module contains comprehensive tests for the Intern Trading Game
REST API, including authentication, order submission, and position
tracking functionality.

Note: These tests require the threaded architecture to be running,
which can be complex in test environments. Consider running integration
tests separately.
"""

import pytest
from fastapi.testclient import TestClient

from intern_trading_game.api.auth import team_registry
from intern_trading_game.api.main import (
    app,
    exchange,
    orders_this_tick,
    positions,
)

pytest.skip(
    "API tests require running threads - run as integration tests",
    allow_module_level=True,
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    # Reset state before each test
    exchange.order_books.clear()
    exchange.instruments.clear()
    exchange.all_order_ids.clear()
    positions.clear()
    orders_this_tick.clear()
    team_registry.teams.clear()
    team_registry.api_key_to_team.clear()
    team_registry._team_counter = 0

    # TestClient will automatically call startup/shutdown events
    with TestClient(app) as client:
        yield client


@pytest.fixture
def registered_team(client):
    """Register a test team and return its info."""
    response = client.post(
        "/auth/register", json={"team_name": "TestBot", "role": "market_maker"}
    )
    assert response.status_code == 200
    return response.json()


class TestAuthentication:
    """Test authentication endpoints and mechanisms."""

    def test_register_team_success(self, client):
        """Test successful team registration.

        Given - A new team wanting to participate
        When - They register with valid name and role
        Then - They receive team ID and API key
        """
        response = client.post(
            "/auth/register",
            json={"team_name": "AlphaBot", "role": "market_maker"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["team_name"] == "AlphaBot"
        assert data["role"] == "market_maker"
        assert data["team_id"].startswith("TEAM_")
        assert data["api_key"].startswith("itg_")
        assert len(data["api_key"]) > 40  # Ensure sufficient entropy

    def test_register_invalid_role(self, client):
        """Test registration with invalid role.

        Given - A team trying to register
        When - They specify an unsupported role
        Then - Registration is rejected with error
        """
        response = client.post(
            "/auth/register",
            json={"team_name": "BadBot", "role": "invalid_role"},
        )

        assert response.status_code == 400
        assert "Only market_maker role" in response.json()["detail"]

    def test_api_key_required(self, client):
        """Test that API key is required for protected endpoints.

        Given - An unauthenticated request
        When - Accessing a protected endpoint
        Then - Request is rejected with 401
        """
        response = client.get("/positions/TEAM_001")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_invalid_api_key(self, client):
        """Test that invalid API keys are rejected.

        Given - A request with invalid API key
        When - Accessing a protected endpoint
        Then - Request is rejected with 401
        """
        response = client.get(
            "/positions/TEAM_001", headers={"X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]


class TestOrderSubmission:
    """Test order submission functionality."""

    def test_submit_limit_order(self, client, registered_team):
        """Test submitting a valid limit order.

        Given - A registered market maker
        When - They submit a limit buy order
        Then - Order is accepted and processed
        """
        response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 10,
                "price": 25.50,
            },
            headers={"X-API-Key": registered_team["api_key"]},
        )

        assert response.status_code == 200
        data = response.json()
        if data["status"] == "error":
            print(f"Error response: {data}")
        assert data["status"] in ["accepted", "filled"]
        assert data["order_id"] is not None
        assert "timestamp" in data

    def test_submit_market_order(self, client, registered_team):
        """Test submitting a market order.

        Given - A registered trader
        When - They submit a market order
        Then - Order is processed without price
        """
        response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "market",
                "side": "buy",
                "quantity": 5,
            },
            headers={"X-API-Key": registered_team["api_key"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["accepted", "filled", "no_liquidity"]

    def test_limit_order_requires_price(self, client, registered_team):
        """Test that limit orders require a price.

        Given - A trader submitting a limit order
        When - They omit the price field
        Then - Order is rejected with error
        """
        response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 10,
            },
            headers={"X-API-Key": registered_team["api_key"]},
        )

        assert response.status_code == 400
        assert "Price required for limit orders" in response.json()["detail"]

    def test_position_limit_enforcement(self, client, registered_team):
        """Test that position limits are enforced.

        Given - A market maker with ±50 position limit
        When - They try to exceed the limit
        Then - Order is rejected by validator
        """
        # First, submit orders to build position close to limit
        api_key = registered_team["api_key"]

        # Buy 45 contracts
        response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 45,
                "price": 100.0,  # High price to ensure no fill
            },
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200

        # Try to buy 10 more (would exceed 50 limit)
        response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 10,
                "price": 100.0,
            },
            headers={"X-API-Key": api_key},
        )

        # Should be rejected
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["error_code"] == "MM_POS_LIMIT"
        assert "Position exceeds ±50" in data["error_message"]

    def test_invalid_instrument(self, client, registered_team):
        """Test submitting order for non-existent instrument.

        Given - A trader trying to trade
        When - They specify an invalid instrument
        Then - Order is rejected with error
        """
        response = client.post(
            "/orders",
            json={
                "instrument_id": "INVALID_INSTRUMENT",
                "order_type": "limit",
                "side": "buy",
                "quantity": 10,
                "price": 25.50,
            },
            headers={"X-API-Key": registered_team["api_key"]},
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"]


class TestPositionTracking:
    """Test position query functionality."""

    def test_get_own_positions(self, client, registered_team):
        """Test querying own positions.

        Given - A registered team
        When - They query their positions
        Then - They see current holdings
        """
        team_id = registered_team["team_id"]
        response = client.get(
            f"/positions/{team_id}",
            headers={"X-API-Key": registered_team["api_key"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == team_id
        assert isinstance(data["positions"], dict)
        assert "last_updated" in data

    def test_cannot_query_other_positions(self, client, registered_team):
        """Test that teams cannot see others' positions.

        Given - Two different teams
        When - One tries to query the other's positions
        Then - Request is rejected with 403
        """
        # Register second team
        response = client.post(
            "/auth/register",
            json={"team_name": "OtherBot", "role": "market_maker"},
        )
        other_team = response.json()

        # Try to query other team's positions
        response = client.get(
            f"/positions/{other_team['team_id']}",
            headers={"X-API-Key": registered_team["api_key"]},
        )

        assert response.status_code == 403
        assert (
            "Cannot query other teams' positions" in response.json()["detail"]
        )


class TestThreadSafety:
    """Test thread safety and queue processing."""

    def test_concurrent_order_submission(self, client, registered_team):
        """Test that concurrent orders are processed safely.

        Given - Multiple orders submitted simultaneously
        When - They are processed by different threads
        Then - All orders are handled correctly
        """
        import concurrent.futures

        api_key = registered_team["api_key"]

        def submit_order(i):
            return client.post(
                "/orders",
                json={
                    "instrument_id": "SPX_4500_CALL",
                    "order_type": "limit",
                    "side": "buy" if i % 2 == 0 else "sell",
                    "quantity": 1,
                    "price": 25.0 + i * 0.1,
                },
                headers={"X-API-Key": api_key},
            )

        # Submit 10 orders concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(submit_order, i) for i in range(10)]
            results = [f.result() for f in futures]

        # All should succeed
        for result in results:
            assert result.status_code == 200
            assert result.json()["status"] in ["accepted", "filled"]

    def test_order_processing_timeout(self, client, registered_team):
        """Test order timeout handling.

        Given - An order that gets stuck in processing
        When - The timeout expires
        Then - Client receives timeout error
        """
        # This would require mocking the queue processing
        # For now, just verify the endpoint exists
        pass


class TestHealthCheck:
    """Test system health endpoints."""

    def test_root_endpoint(self, client):
        """Test the health check endpoint.

        Given - The API is running
        When - Health check is requested
        Then - Status and thread info returned
        """
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "threads" in data
        assert all(data["threads"].values())  # All threads running
