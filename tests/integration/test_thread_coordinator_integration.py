"""Integration tests for threads with OrderResponseCoordinator.

These tests verify that the pipeline threads correctly integrate with
the OrderResponseCoordinator for managing order responses.
"""

import threading
import time
from datetime import datetime
from queue import Queue
from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.components.core.models import (
    Order,
    OrderResult,
    OrderSide,
    OrderType,
)
from intern_trading_game.domain.exchange.response.coordinator import (
    OrderResponseCoordinator,
)
from intern_trading_game.domain.exchange.response.models import (
    CoordinationConfig,
)
from intern_trading_game.domain.exchange.threads_v2 import (
    matching_thread_v2,
    validator_thread_v2,
)
from intern_trading_game.infrastructure.api.models import (
    TeamInfo,
)


class TestValidatorThreadIntegration:
    """Test validator thread integration with coordinator."""

    @pytest.fixture
    def setup_validator_thread(self):
        """Set up validator thread test environment."""
        # Create queues
        order_queue = Queue()
        match_queue = Queue()
        websocket_queue = Queue()

        # Create mock validation service
        validation_service = Mock()

        # Create coordinator with test config
        config = CoordinationConfig(
            default_timeout_seconds=1.0,
            max_pending_requests=10,
            cleanup_interval_seconds=60,
            enable_metrics=False,
            enable_detailed_logging=True,
            request_id_prefix="test",
        )
        coordinator = OrderResponseCoordinator(config)

        # Create and start thread
        thread = threading.Thread(
            target=validator_thread_v2,
            args=(
                order_queue,
                match_queue,
                websocket_queue,
                validation_service,
                coordinator,
            ),
            daemon=True,
        )
        thread.start()

        yield {
            "order_queue": order_queue,
            "match_queue": match_queue,
            "websocket_queue": websocket_queue,
            "validation_service": validation_service,
            "coordinator": coordinator,
            "thread": thread,
        }

        # Cleanup
        order_queue.put(None)  # Shutdown signal
        thread.join(timeout=1.0)
        coordinator.shutdown()

    def test_successful_order_validation(self, setup_validator_thread):
        """Test successful order validation flow.

        Given - Validator thread running with coordinator
        When - Valid order submitted
        Then - Response returned via coordinator
        """
        # Given - Setup from fixture
        env = setup_validator_thread

        # Configure validation service to accept order
        env[
            "validation_service"
        ].validate_new_order.return_value = OrderResult(
            order_id="ORD_001",
            status="accepted",
            error_code=None,
            error_message=None,
            remaining_quantity=10,
        )

        # Create test order
        order = Order(
            order_id="ORD_001",
            client_order_id="CLIENT_001",
            trader_id="TEAM_001",
            instrument_id="SPX_4500_CALL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=100.0,
            timestamp=datetime.now(),
        )

        team_info = TeamInfo(
            team_id="TEAM_001",
            team_name="Test Team",
            role="market_maker",
            api_key="test_key_001",
            created_at=datetime.now(),
        )

        # Register request with coordinator
        registration = env["coordinator"].register_request(
            team_id=team_info.team_id,
            timeout_seconds=2.0,
        )
        request_id = registration.request_id

        # When - Submit order to validator
        env["order_queue"].put(
            (
                "new_order",
                order,
                team_info,
                None,  # event not used
                request_id,
            )
        )

        # Then - Response available via coordinator
        result = env["coordinator"].wait_for_completion(request_id)
        response = result.api_response
        assert response is not None
        assert response.success is True
        assert response.order_id == "ORD_001"
        assert response.error is None

        # Verify order sent to matching queue
        assert not env["match_queue"].empty()
        match_data = env["match_queue"].get()
        assert match_data[0].order_id == "ORD_001"

    def test_order_rejection_flow(self, setup_validator_thread):
        """Test order rejection flow.

        Given - Validator thread with coordinator
        When - Invalid order submitted
        Then - Rejection response returned with error details
        """
        # Given - Setup from fixture
        env = setup_validator_thread

        # Configure validation service to reject order
        env[
            "validation_service"
        ].validate_new_order.return_value = OrderResult(
            order_id="ORD_002",
            status="rejected",
            error_code="POSITION_LIMIT",
            error_message="Position limit exceeded",
        )

        # Create test order
        order = Order(
            order_id="ORD_002",
            client_order_id="CLIENT_002",
            trader_id="TEAM_001",
            instrument_id="SPX_4500_CALL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,  # Too large
            price=100.0,
            timestamp=datetime.now(),
        )

        team_info = TeamInfo(
            team_id="TEAM_001",
            team_name="Test Team",
            role="market_maker",
            api_key="test_key_001",
            created_at=datetime.now(),
        )

        # Register request
        registration = env["coordinator"].register_request(
            team_id=team_info.team_id,
            timeout_seconds=2.0,
        )
        request_id = registration.request_id

        # When - Submit order
        env["order_queue"].put(
            (
                "new_order",
                order,
                team_info,
                None,
                request_id,
            )
        )

        # Then - Rejection response received
        result = env["coordinator"].wait_for_completion(request_id)
        response = result.api_response
        assert response is not None
        assert response.success is False
        assert response.order_id is None
        assert response.error is not None
        assert response.error.code == "POSITION_LIMIT"
        assert response.error.message == "Position limit exceeded"

        # Verify rejection sent via WebSocket
        assert not env["websocket_queue"].empty()
        ws_msg = env["websocket_queue"].get()
        assert ws_msg[0] == "new_order_reject"
        assert ws_msg[2]["error_code"] == "POSITION_LIMIT"

        # Verify order NOT sent to matching
        assert env["match_queue"].empty()

    def test_order_cancellation_flow(self, setup_validator_thread):
        """Test order cancellation flow.

        Given - Validator thread with existing order
        When - Cancellation requested
        Then - Cancellation response returned
        """
        # Given - Setup from fixture
        env = setup_validator_thread

        # Configure validation service to accept cancellation
        env["validation_service"].validate_cancellation.return_value = (
            True,  # success
            None,  # reason
        )

        team_info = TeamInfo(
            team_id="TEAM_001",
            team_name="Test Team",
            role="market_maker",
            api_key="test_key_001",
            created_at=datetime.now(),
        )

        # Register cancellation request
        order_id = "ORD_003"
        registration = env["coordinator"].register_request(
            team_id=team_info.team_id,
            timeout_seconds=2.0,
        )
        request_id = registration.request_id

        # When - Submit cancellation
        env["order_queue"].put(
            (
                "cancel_order",
                order_id,
                team_info,
                None,
                request_id,
            )
        )

        # Then - Success response received
        result = env["coordinator"].wait_for_completion(request_id)
        response = result.api_response
        assert response is not None
        assert response.success is True
        assert response.order_id == order_id
        assert response.error is None

        # Verify cancel ACK sent via WebSocket
        assert not env["websocket_queue"].empty()
        ws_msg = env["websocket_queue"].get()
        assert ws_msg[0] == "cancel_ack"
        assert ws_msg[2]["order_id"] == order_id

    def test_concurrent_order_processing(self, setup_validator_thread):
        """Test concurrent order processing.

        Given - Multiple orders submitted simultaneously
        When - Validator processes them
        Then - All responses returned correctly
        """
        # Given - Setup from fixture
        env = setup_validator_thread

        # Configure validation to alternate accept/reject
        results = [
            OrderResult(
                order_id="ORD_000",
                status="accepted",
                remaining_quantity=10,
            ),
            OrderResult(
                order_id="ORD_001",
                status="rejected",
                error_code="RATE_LIMIT",
                error_message="Rate limit exceeded",
            ),
            OrderResult(
                order_id="ORD_002",
                status="accepted",
                remaining_quantity=10,
            ),
        ]
        env["validation_service"].validate_new_order.side_effect = results

        team_info = TeamInfo(
            team_id="TEAM_001",
            team_name="Test Team",
            role="market_maker",
            api_key="test_key_001",
            created_at=datetime.now(),
        )

        # Submit multiple orders
        orders = []
        request_ids = []

        for i in range(3):
            order = Order(
                order_id=f"ORD_{i:03d}",
                client_order_id=f"CLIENT_{i:03d}",
                trader_id="TEAM_001",
                instrument_id="SPX_4500_CALL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=10,
                price=100.0 + i,
                timestamp=datetime.now(),
            )
            orders.append(order)

            # Register request
            registration = env["coordinator"].register_request(
                team_id=team_info.team_id,
                timeout_seconds=2.0,
            )
            request_ids.append(registration.request_id)

            # Submit order
            env["order_queue"].put(
                (
                    "new_order",
                    order,
                    team_info,
                    None,
                    registration.request_id,
                )
            )

        # Wait for all responses
        responses = []
        for request_id in request_ids:
            result = env["coordinator"].wait_for_completion(request_id)
            responses.append(result.api_response)

        # Verify responses
        assert responses[0].success is True
        assert responses[0].order_id == "ORD_000"

        assert responses[1].success is False
        assert responses[1].error.code == "RATE_LIMIT"

        assert responses[2].success is True
        assert responses[2].order_id == "ORD_002"

        # Verify only accepted orders sent to matching
        matched_orders = []
        while not env["match_queue"].empty():
            matched_orders.append(env["match_queue"].get()[0])

        assert len(matched_orders) == 2
        assert matched_orders[0].order_id == "ORD_000"
        assert matched_orders[1].order_id == "ORD_002"


class TestMatchingThreadIntegration:
    """Test matching thread integration with coordinator."""

    @pytest.fixture
    def setup_matching_thread(self):
        """Set up matching thread test environment."""
        # Create queues
        match_queue = Queue()
        trade_queue = Queue()
        websocket_queue = Queue()

        # Create mock exchange
        exchange = Mock()

        # Create coordinator (optional for matching thread)
        config = CoordinationConfig(
            default_timeout_seconds=1.0,
            max_pending_requests=10,
            cleanup_interval_seconds=60,
            enable_metrics=False,
            enable_detailed_logging=True,
            request_id_prefix="test",
        )
        coordinator = OrderResponseCoordinator(config)

        # Create and start thread
        thread = threading.Thread(
            target=matching_thread_v2,
            args=(
                match_queue,
                trade_queue,
                websocket_queue,
                exchange,
                coordinator,
            ),
            daemon=True,
        )
        thread.start()

        yield {
            "match_queue": match_queue,
            "trade_queue": trade_queue,
            "websocket_queue": websocket_queue,
            "exchange": exchange,
            "coordinator": coordinator,
            "thread": thread,
        }

        # Cleanup
        match_queue.put(None)  # Shutdown signal
        thread.join(timeout=1.0)
        coordinator.shutdown()

    def test_successful_order_matching(self, setup_matching_thread):
        """Test successful order matching flow.

        Given - Matching thread with mock exchange
        When - Valid order submitted
        Then - Order matched and results forwarded
        """
        # Given - Setup from fixture
        env = setup_matching_thread

        # Configure exchange to accept order
        from intern_trading_game.domain.exchange.components.core.models import (
            OrderResult,
        )

        result = OrderResult(
            order_id="ORD_001",
            status="new",
            fills=[],
            remaining_quantity=10,
            error_code=None,
            error_message=None,
        )
        env["exchange"].submit_order.return_value = result

        # Create test order
        order = Order(
            order_id="ORD_001",
            client_order_id="CLIENT_001",
            trader_id="TEAM_001",
            instrument_id="SPX_4500_CALL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=100.0,
            timestamp=datetime.now(),
        )

        team_info = TeamInfo(
            team_id="TEAM_001",
            team_name="Test Team",
            role="market_maker",
            api_key="test_key",
            created_at=datetime.now(),
        )

        # When - Submit order to matching
        env["match_queue"].put((order, team_info))

        # Give thread time to process
        time.sleep(0.1)

        # Then - Order submitted to exchange
        env["exchange"].submit_order.assert_called_once_with(order)

        # Verify ACK sent via WebSocket
        assert not env["websocket_queue"].empty()
        ws_msg = env["websocket_queue"].get()
        assert ws_msg[0] == "new_order_ack"
        assert ws_msg[2]["order_id"] == "ORD_001"
        assert ws_msg[2]["status"] == "new"

        # Verify result forwarded to trade publisher
        assert not env["trade_queue"].empty()
        trade_data = env["trade_queue"].get()
        assert trade_data[0].order_id == "ORD_001"
        assert trade_data[1].order_id == "ORD_001"
        assert trade_data[2].team_id == "TEAM_001"
