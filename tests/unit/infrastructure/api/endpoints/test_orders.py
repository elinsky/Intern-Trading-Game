"""Unit tests for order endpoints."""

import threading
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from intern_trading_game.infrastructure.api.auth import TeamInfo
from intern_trading_game.infrastructure.api.models import ApiResponse


class TestOrderEndpoints:
    """Test order submission and cancellation endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        # Import here to avoid circular imports
        from intern_trading_game.api.main import app

        return TestClient(app)

    @pytest.fixture
    def team_info(self):
        """Create test team info."""
        return TeamInfo(
            team_id="TEAM_001",
            team_name="TestBot",
            role="market_maker",
            api_key="test_key_123",
            created_at=datetime.now(),
        )

    @pytest.fixture
    def mock_auth(self, team_info):
        """Mock authentication to return test team."""
        # Need to patch at the FastAPI dependency level
        from intern_trading_game.api.endpoints.exchange import get_current_team

        async def mock_get_current_team():
            return team_info

        from intern_trading_game.api.main import app

        app.dependency_overrides[get_current_team] = mock_get_current_team
        yield
        app.dependency_overrides.clear()

    def test_submit_valid_limit_order_queue_message(
        self, client, team_info, mock_auth
    ):
        """Test submitting a valid limit order creates correct queue message.

        Given - A market maker wants to submit a limit order
        When - They send a properly formatted order request
        Then - The correct 5-tuple message is put on the queue
        """
        # Given - A market maker submitting a buy order
        order_data = {
            "instrument_id": "SPX_4500_CALL",
            "order_type": "limit",
            "side": "buy",
            "quantity": 10,
            "price": 25.50,
            "client_order_id": "client_123",
        }

        # Mock dependencies using FastAPI's dependency override
        from intern_trading_game.api.endpoints.exchange import (
            get_order_queue,
            get_order_responses,
            get_pending_orders,
        )
        from intern_trading_game.api.main import app

        # Track what gets put on queue
        captured_messages = []
        mock_queue = MagicMock()
        mock_queue.put = lambda x: captured_messages.append(x)

        # Create mock dependency functions
        def mock_get_queue():
            return mock_queue

        def mock_get_pending():
            return {}

        def mock_get_responses():
            return {}

        # Override dependencies
        app.dependency_overrides[get_order_queue] = mock_get_queue
        app.dependency_overrides[get_pending_orders] = mock_get_pending
        app.dependency_overrides[get_order_responses] = mock_get_responses

        try:
            # When - Submit the order (will timeout, but that's OK)
            response = client.post(
                "/orders",
                json=order_data,
                headers={"X-API-Key": "test_key_123"},
            )

            # Then - Verify the queue message structure
            assert len(captured_messages) == 1
            msg_type, order, team, event, request_id = captured_messages[0]

            assert msg_type == "new_order"
            assert order.instrument_id == "SPX_4500_CALL"
            assert order.order_type.value == "limit"
            assert order.side.value == "buy"
            assert order.quantity == 10
            assert order.price == 25.50
            assert order.client_order_id == "client_123"
            assert order.trader_id == "TEAM_001"
            assert team.team_id == "TEAM_001"
            assert isinstance(event, threading.Event)
            assert request_id.startswith("req_")

            # Response will timeout since we don't simulate validator
            assert response.status_code == 504

        finally:
            # Clean up overrides
            del app.dependency_overrides[get_order_queue]
            del app.dependency_overrides[get_pending_orders]
            del app.dependency_overrides[get_order_responses]

    def test_submit_valid_limit_order_with_response(
        self, client, team_info, mock_auth
    ):
        """Test submitting a valid limit order with simulated validator response.

        Given - A market maker wants to submit a limit order
        When - They send a properly formatted order request
        Then - They receive an ApiResponse with success=true
        """
        # Given - A market maker submitting a buy order
        order_data = {
            "instrument_id": "SPX_4500_CALL",
            "order_type": "limit",
            "side": "buy",
            "quantity": 10,
            "price": 25.50,
            "client_order_id": "client_123",
        }

        # Mock dependencies
        from intern_trading_game.api.endpoints.exchange import (
            get_order_queue,
            get_order_responses,
            get_pending_orders,
        )
        from intern_trading_game.api.main import app

        # Create shared state
        pending_dict = {}
        responses_dict = {}

        # Mock queue that simulates validator behavior
        def mock_put(msg_tuple):
            msg_type, order, team, event, request_id = msg_tuple
            response_key = f"{order.order_id}:{request_id}"

            # Simulate validator creating response
            responses_dict[response_key] = ApiResponse(
                success=True,
                request_id=request_id,
                order_id=order.order_id,
                timestamp=datetime.now(),
            )
            # Signal the event
            event.set()

        mock_queue = MagicMock()
        mock_queue.put = mock_put

        # Override dependencies
        app.dependency_overrides[get_order_queue] = lambda: mock_queue
        app.dependency_overrides[get_pending_orders] = lambda: pending_dict
        app.dependency_overrides[get_order_responses] = lambda: responses_dict

        try:
            # When - Submit the order
            response = client.post(
                "/orders",
                json=order_data,
                headers={"X-API-Key": "test_key_123"},
            )

            # Then - Response indicates success
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["request_id"] is not None
            assert data["order_id"] is not None
            assert data["error"] is None

        finally:
            # Clean up
            del app.dependency_overrides[get_order_queue]
            del app.dependency_overrides[get_pending_orders]
            del app.dependency_overrides[get_order_responses]

    def test_submit_order_missing_price(self, client, team_info, mock_auth):
        """Test limit order without price returns error.

        Given - A bot submits a limit order without price
        When - The API validates the request
        Then - An ApiResponse with error is returned immediately
        """
        # Given - Incomplete order data (missing price for limit order)
        order_data = {
            "instrument_id": "SPX_4500_CALL",
            "order_type": "limit",
            "side": "buy",
            "quantity": 10,
            # price is missing
        }

        # No need to mock queues - validation happens before queuing

        # When - Submit the invalid order
        response = client.post(
            "/orders", json=order_data, headers={"X-API-Key": "test_key_123"}
        )

        # Then - Error response returned
        assert response.status_code == 200  # Still 200, but success=false
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None
        assert data["error"]["code"] == "MISSING_PRICE"
        assert "Price required" in data["error"]["message"]

    def test_cancel_order_success(self, client, team_info, mock_auth):
        """Test successful order cancellation.

        Given - A bot wants to cancel an existing order
        When - They send a cancel request
        Then - ApiResponse confirms the cancellation
        """
        # Given - An existing order that needs cancellation
        order_id = "ORD_123456"

        # Mock dependencies
        from intern_trading_game.api.endpoints.exchange import (
            get_order_queue,
            get_order_responses,
            get_pending_orders,
        )
        from intern_trading_game.api.main import app

        # Create shared state
        pending_dict = {}
        responses_dict = {}

        # Mock queue that simulates validator behavior
        def mock_put(msg_tuple):
            msg_type, cancel_order_id, team, event, request_id = msg_tuple
            response_key = f"{cancel_order_id}:{request_id}"

            # Simulate validator creating response
            responses_dict[response_key] = ApiResponse(
                success=True,
                request_id=request_id,
                order_id=cancel_order_id,
                timestamp=datetime.now(),
            )
            # Signal the event
            event.set()

        mock_queue = MagicMock()
        mock_queue.put = mock_put

        # Override dependencies
        app.dependency_overrides[get_order_queue] = lambda: mock_queue
        app.dependency_overrides[get_pending_orders] = lambda: pending_dict
        app.dependency_overrides[get_order_responses] = lambda: responses_dict

        try:
            # When - Cancel the order
            response = client.delete(
                f"/orders/{order_id}", headers={"X-API-Key": "test_key_123"}
            )

            # Then - Cancellation confirmed
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["order_id"] == order_id

        finally:
            # Clean up
            del app.dependency_overrides[get_order_queue]
            del app.dependency_overrides[get_pending_orders]
            del app.dependency_overrides[get_order_responses]

    def test_order_timeout_handling(self, client, team_info, mock_auth):
        """Test timeout handling for order submission.

        Given - A slow validator thread
        When - Order processing exceeds timeout
        Then - 504 Gateway Timeout is returned
        """
        # Given - Order that will timeout
        order_data = {
            "instrument_id": "SPX_4500_CALL",
            "order_type": "limit",
            "side": "buy",
            "quantity": 10,
            "price": 25.50,
        }

        with (
            patch(
                "intern_trading_game.api.endpoints.exchange.get_order_queue"
            ) as mock_queue,
            patch(
                "intern_trading_game.api.endpoints.exchange.get_pending_orders"
            ) as mock_pending,
            patch(
                "intern_trading_game.api.endpoints.exchange.get_order_responses"
            ) as mock_responses,
        ):
            # Setup mocks
            queue_instance = MagicMock()
            mock_queue.return_value = queue_instance
            mock_pending.return_value = {}
            mock_responses.return_value = {}

            # Don't set the event - simulate timeout
            queue_instance.put.side_effect = lambda x: None

            # When - Submit order that times out
            response = client.post(
                "/orders",
                json=order_data,
                headers={"X-API-Key": "test_key_123"},
            )

            # Then - Timeout error returned
            assert response.status_code == 504
            assert "timeout" in response.json()["detail"].lower()
