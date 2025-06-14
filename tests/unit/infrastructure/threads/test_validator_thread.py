"""Unit tests for validator thread.

Tests the order validation thread's behavior with the new ApiResponse
format, ensuring immediate responses for both accepted and rejected orders.

Note: These tests follow TDD principles - they define the expected behavior
for the new ApiResponse format. The validator thread implementation needs
to be updated to support:
1. 5-tuple message format with request_id
2. Creating ApiResponse for both accepted and rejected orders
3. Response key format: order_id:request_id
"""

import threading
from datetime import datetime
from queue import Queue
from unittest.mock import MagicMock

import pytest

from intern_trading_game.domain.exchange.core.order import Order
from intern_trading_game.domain.exchange.order_result import OrderResult
from intern_trading_game.infrastructure.api.auth import TeamInfo
from intern_trading_game.infrastructure.api.models import ApiResponse
from intern_trading_game.infrastructure.threads.validator import (
    validator_thread,
)
from intern_trading_game.services.order_validation import (
    OrderValidationService,
)


class TestValidatorThread:
    """Test validator thread behavior with ApiResponse format."""

    @pytest.fixture
    def queues(self):
        """Create test queues for thread communication."""
        return {
            "order_queue": Queue(),
            "match_queue": Queue(),
            "websocket_queue": Queue(),
        }

    @pytest.fixture
    def shared_state(self):
        """Create shared state dictionaries."""
        return {
            "orders_this_tick": {},
            "orders_lock": threading.RLock(),
            "pending_orders": {},
            "order_responses": {},
        }

    @pytest.fixture
    def mock_validation_service(self):
        """Create mock validation service."""
        return MagicMock(spec=OrderValidationService)

    @pytest.fixture
    def sample_order(self):
        """Create a test order."""
        return Order(
            order_id="ORD_123",
            trader_id="TEAM_001",
            instrument_id="SPX_CALL_4500_20240315",
            order_type="limit",
            side="buy",
            quantity=10,
            price=100.0,
            client_order_id="client_123",
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_team(self):
        """Create a test team."""
        return TeamInfo(
            team_id="TEAM_001",
            team_name="TestBot",
            role="market_maker",
            api_key="test_key",
            created_at=datetime.now(),
        )

    def test_accepted_order_creates_api_response(
        self,
        queues,
        shared_state,
        mock_validation_service,
        sample_order,
        sample_team,
    ):
        """Test accepted orders create immediate ApiResponse.

        Given - A valid order is submitted to the validator
        When - The validation service accepts the order
        Then - An ApiResponse is created and order forwarded to matching
        """
        # Given - A market maker submits a valid order
        # The validator needs to provide immediate feedback
        mock_validation_service.validate_new_order.return_value = OrderResult(
            status="accepted",
            order_id=sample_order.order_id,
        )

        response_event = threading.Event()
        request_id = "req_12345"

        # Start validator thread
        thread = threading.Thread(
            target=validator_thread,
            args=(
                queues["order_queue"],
                queues["match_queue"],
                queues["websocket_queue"],
                mock_validation_service,
                shared_state["orders_this_tick"],
                shared_state["orders_lock"],
                shared_state["pending_orders"],
                shared_state["order_responses"],
            ),
        )
        thread.daemon = True
        thread.start()

        # When - Submit order with request_id (5-tuple format)
        queues["order_queue"].put(
            (
                "new_order",
                sample_order,
                sample_team,
                response_event,
                request_id,
            )
        )

        # Wait for response
        assert response_event.wait(timeout=1.0), "Response not received"

        # Then - ApiResponse is created with success=true
        response_key = f"{sample_order.order_id}:{request_id}"
        assert response_key in shared_state["order_responses"]

        api_response = shared_state["order_responses"][response_key]
        assert isinstance(api_response, ApiResponse)
        assert api_response.success is True
        assert api_response.request_id == request_id
        assert api_response.order_id == sample_order.order_id
        assert api_response.error is None

        # And - Order is forwarded to match queue
        assert not queues["match_queue"].empty()
        match_data = queues["match_queue"].get()
        assert match_data == (sample_order, sample_team)

        # And - NO WebSocket message for accepted orders
        assert queues["websocket_queue"].empty()

        # Cleanup
        queues["order_queue"].put(None)
        thread.join(timeout=1.0)

    def test_rejected_order_creates_api_response_with_error(
        self,
        queues,
        shared_state,
        mock_validation_service,
        sample_order,
        sample_team,
    ):
        """Test rejected orders create ApiResponse with error details.

        Given - An invalid order is submitted
        When - The validation service rejects it
        Then - ApiResponse includes error and WebSocket gets rejection
        """
        # Given - A hedge fund exceeds position limits
        # They need detailed error information
        mock_validation_service.validate_new_order.return_value = OrderResult(
            status="rejected",
            order_id=sample_order.order_id,
            error_code="POSITION_LIMIT_EXCEEDED",
            error_message="Order would exceed position limit of 50",
        )

        response_event = threading.Event()
        request_id = "req_12346"

        # Start thread
        thread = threading.Thread(
            target=validator_thread,
            args=(
                queues["order_queue"],
                queues["match_queue"],
                queues["websocket_queue"],
                mock_validation_service,
                shared_state["orders_this_tick"],
                shared_state["orders_lock"],
                shared_state["pending_orders"],
                shared_state["order_responses"],
            ),
        )
        thread.daemon = True
        thread.start()

        # When - Submit invalid order
        queues["order_queue"].put(
            (
                "new_order",
                sample_order,
                sample_team,
                response_event,
                request_id,
            )
        )

        assert response_event.wait(timeout=1.0)

        # Then - ApiResponse has error details
        response_key = f"{sample_order.order_id}:{request_id}"
        api_response = shared_state["order_responses"][response_key]

        assert isinstance(api_response, ApiResponse)
        assert api_response.success is False
        assert api_response.request_id == request_id
        assert api_response.order_id is None  # No order_id on failure
        assert api_response.error is not None
        assert api_response.error.code == "POSITION_LIMIT_EXCEEDED"

        # And - WebSocket gets rejection message
        assert not queues["websocket_queue"].empty()
        ws_msg = queues["websocket_queue"].get()
        assert ws_msg[0] == "new_order_reject"
        assert ws_msg[1] == sample_team.team_id

        # And - Order NOT forwarded to matching
        assert queues["match_queue"].empty()

        # Cleanup
        queues["order_queue"].put(None)
        thread.join(timeout=1.0)

    def test_cancel_order_success_returns_api_response(
        self, queues, shared_state, mock_validation_service, sample_team
    ):
        """Test successful cancellation returns ApiResponse.

        Given - A cancel request for an existing order
        When - The cancellation succeeds
        Then - ApiResponse confirms success
        """
        # Given - A bot wants to cancel its resting order
        mock_validation_service.validate_cancellation.return_value = (
            True,
            None,
        )

        response_event = threading.Event()
        request_id = "req_12347"
        order_id = "ORD_123"

        # Start thread
        thread = threading.Thread(
            target=validator_thread,
            args=(
                queues["order_queue"],
                queues["match_queue"],
                queues["websocket_queue"],
                mock_validation_service,
                shared_state["orders_this_tick"],
                shared_state["orders_lock"],
                shared_state["pending_orders"],
                shared_state["order_responses"],
            ),
        )
        thread.daemon = True
        thread.start()

        # When - Submit cancel request
        queues["order_queue"].put(
            ("cancel_order", order_id, sample_team, response_event, request_id)
        )

        assert response_event.wait(timeout=1.0)

        # Then - ApiResponse confirms cancellation
        response_key = f"{order_id}:{request_id}"
        api_response = shared_state["order_responses"][response_key]

        assert isinstance(api_response, ApiResponse)
        assert api_response.success is True
        assert api_response.request_id == request_id
        assert api_response.order_id == order_id
        assert api_response.error is None

        # And - WebSocket notified of cancellation
        assert not queues["websocket_queue"].empty()
        ws_msg = queues["websocket_queue"].get()
        assert ws_msg[0] == "cancel_ack"

        # Cleanup
        queues["order_queue"].put(None)
        thread.join(timeout=1.0)

    def test_response_key_format(
        self,
        queues,
        shared_state,
        mock_validation_service,
        sample_order,
        sample_team,
    ):
        """Test response storage uses correct key format.

        Given - Orders with different request_ids
        When - They are processed
        Then - Responses are stored with order_id:request_id keys
        """
        # Given - Multiple orders with same order_id but different request_ids
        # This tests request correlation
        mock_validation_service.validate_new_order.return_value = OrderResult(
            status="accepted", order_id=sample_order.order_id
        )

        thread = threading.Thread(
            target=validator_thread,
            args=(
                queues["order_queue"],
                queues["match_queue"],
                queues["websocket_queue"],
                mock_validation_service,
                shared_state["orders_this_tick"],
                shared_state["orders_lock"],
                shared_state["pending_orders"],
                shared_state["order_responses"],
            ),
        )
        thread.daemon = True
        thread.start()

        # When - Submit same order with different request_ids
        request_ids = ["req_001", "req_002", "req_003"]
        events = []

        for req_id in request_ids:
            event = threading.Event()
            events.append(event)
            queues["order_queue"].put(
                ("new_order", sample_order, sample_team, event, req_id)
            )

        # Wait for all responses
        for event in events:
            assert event.wait(timeout=1.0)

        # Then - Each has unique storage key
        for req_id in request_ids:
            key = f"{sample_order.order_id}:{req_id}"
            assert key in shared_state["order_responses"]
            response = shared_state["order_responses"][key]
            assert response.request_id == req_id

        # Cleanup
        queues["order_queue"].put(None)
        thread.join(timeout=1.0)
