"""Unit tests for game endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


class TestGameEndpoints:
    """Test game management endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        # Import here to avoid circular imports
        from intern_trading_game.api.main import app

        return TestClient(app)

    def test_register_team_success(self, client):
        """Test successful team registration.

        Given - A user wants to register a new trading team
        When - They submit valid registration data
        Then - Team is created with unique ID and API key
        """
        # Given - Valid registration data
        registration_data = {
            "team_name": "TestMarketMaker",
            "role": "market_maker",
        }

        # When - Register the team
        response = client.post("/game/teams/register", json=registration_data)

        # Then - Registration succeeds
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["team_name"] == "TestMarketMaker"
        assert data["data"]["role"] == "market_maker"
        assert "team_id" in data["data"]
        assert "api_key" in data["data"]
        assert "created_at" in data["data"]

    def test_register_team_unsupported_role(self, client):
        """Test registration with unsupported role.

        Given - MVP only supports market_maker role
        When - User tries to register with different role
        Then - Registration fails with appropriate error
        """
        # Given - Registration with unsupported role
        registration_data = {
            "team_name": "TestHedgeFund",
            "role": "hedge_fund",
        }

        # When - Try to register
        response = client.post("/game/teams/register", json=registration_data)

        # Then - Registration fails
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_ROLE"
        assert "market_maker" in data["error"]["message"]

    def test_register_team_duplicate_name(self, client):
        """Test registration with duplicate team name.

        Given - A team already exists with a specific name
        When - Another user tries to register with same name
        Then - Registration fails with duplicate error
        """
        # Given - Register first team
        first_registration = {
            "team_name": "DuplicateTest",
            "role": "market_maker",
        }
        response1 = client.post(
            "/game/teams/register", json=first_registration
        )
        assert response1.status_code == 200
        assert response1.json()["success"] is True

        # When - Try to register with same name
        response2 = client.post(
            "/game/teams/register", json=first_registration
        )

        # Then - Registration fails
        assert response2.status_code == 200
        data = response2.json()
        assert data["success"] is False
        assert data["error"]["code"] == "DUPLICATE_TEAM_NAME"
        assert "already exists" in data["error"]["message"]

    def test_get_team_info_success(self, client):
        """Test retrieving team information.

        Given - A registered team exists
        When - Query team info by ID
        Then - Team details returned (excluding API key)
        """
        # Given - Register a team first
        registration_data = {
            "team_name": "InfoTest",
            "role": "market_maker",
        }
        reg_response = client.post(
            "/game/teams/register", json=registration_data
        )
        reg_data = reg_response.json()
        team_id = reg_data["data"]["team_id"]

        # When - Query team info
        response = client.get(f"/game/teams/{team_id}")

        # Then - Team info returned
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["team_id"] == team_id
        assert data["data"]["team_name"] == "InfoTest"
        assert data["data"]["role"] == "market_maker"
        assert "created_at" in data["data"]
        # API key should NOT be included for security
        assert "api_key" not in data["data"]

    def test_get_team_info_not_found(self, client):
        """Test querying non-existent team.

        Given - No team exists with given ID
        When - Query team info
        Then - Error response returned
        """
        # When - Query non-existent team
        response = client.get("/game/teams/FAKE_TEAM_ID")

        # Then - Not found error
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "TEAM_NOT_FOUND"
        assert "not found" in data["error"]["message"]

    def test_team_initialization_with_positions(self, client):
        """Test that team registration initializes positions.

        Given - New team registration
        When - Team is created
        Then - Positions are properly initialized through PositionManagementService

        Note: Both positions and rate limiting are now handled internally by services
        """
        # Mock the position service
        from intern_trading_game.api.endpoints.game import get_position_service
        from intern_trading_game.api.main import app
        from intern_trading_game.domain.positions import (
            PositionManagementService,
        )

        mock_position_service = MagicMock(spec=PositionManagementService)

        # Override dependency
        app.dependency_overrides[get_position_service] = (
            lambda: mock_position_service
        )

        try:
            # Register team
            registration_data = {
                "team_name": "InitTest",
                "role": "market_maker",
            }
            response = client.post(
                "/game/teams/register", json=registration_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            team_id = data["data"]["team_id"]

            # Verify position service was called to initialize team
            mock_position_service.initialize_team.assert_called_once_with(
                team_id
            )

        finally:
            # Clean up
            del app.dependency_overrides[get_position_service]
