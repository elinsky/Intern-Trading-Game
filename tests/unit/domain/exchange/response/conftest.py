"""Pytest fixtures for order response coordination tests.

This module provides reusable test fixtures for testing the order response
coordination system. Fixtures include mock services, test data generators,
and coordination scenarios commonly needed across test modules.

The fixtures follow the trading system's business patterns and enable
realistic testing of coordination behaviors under various market conditions.
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.response.interfaces import (
    OrderResponseCoordinatorInterface,
    ResponseRegistration,
    ResponseResult,
)
from intern_trading_game.domain.exchange.response.models import (
    CoordinationConfig,
    ResponseStatus,
)
from intern_trading_game.infrastructure.api.models import ApiError, ApiResponse


class MockPipelineThreads:
    """Mock pipeline threads for integration testing."""

    def __init__(self):
        self.validator_queue = asyncio.Queue()
        self.matcher_queue = asyncio.Queue()
        self.publisher_queue = asyncio.Queue()
        self.coordinator = None
        self._running = False
        self._threads = []

    def start(self, coordinator):
        """Start mock pipeline threads."""
        self.coordinator = coordinator
        self._running = True

        # Start all threads
        thread_configs = [
            ("validator", self._validator_thread),
            ("matcher", self._matcher_thread),
            ("publisher", self._publisher_thread),
        ]

        for name, target in thread_configs:
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self):
        """Stop mock pipeline threads."""
        self._running = False

    def submit_order(self, order, team_info, request_id):
        """Submit order to validator queue."""
        self.validator_queue.put_nowait((order, team_info, request_id))

    def _validator_thread(self):
        """Mock validator thread."""
        while self._running:
            try:
                item = self.validator_queue.get(timeout=0.1)
                self._process_validation(item)
            except Exception:
                continue

    def _process_validation(self, item):
        """Process validation for an order item."""
        order, team_info, request_id = item

        # Update status
        self.coordinator.update_status(request_id, ResponseStatus.VALIDATING)

        # Simulate validation timing
        time.sleep(0.02)

        # Process validation result
        if self._should_reject_order(order, team_info):
            self._handle_validation_failure(order, request_id)
        else:
            self._handle_validation_success(order, team_info, request_id)

    def _handle_validation_failure(self, order, request_id):
        """Handle validation failure."""
        self.coordinator.notify_completion(
            request_id=request_id,
            api_response=self._create_validation_error(order),
        )

    def _handle_validation_success(self, order, team_info, request_id):
        """Handle validation success."""
        self.coordinator.update_status(request_id, ResponseStatus.MATCHING)
        self.matcher_queue.put_nowait((order, team_info, request_id))

    def _matcher_thread(self):
        """Mock matcher thread."""
        while self._running:
            try:
                item = self.matcher_queue.get(timeout=0.1)
                self._process_matching(item)
            except Exception:
                continue

    def _process_matching(self, item):
        """Process matching for an order item."""
        order, team_info, request_id = item

        # Simulate matching timing
        time.sleep(0.05)

        # Forward to publisher
        self.coordinator.update_status(request_id, ResponseStatus.SETTLING)
        self.publisher_queue.put_nowait((order, team_info, request_id))

    def _publisher_thread(self):
        """Mock publisher thread."""
        while self._running:
            try:
                item = self.publisher_queue.get(timeout=0.1)
                self._process_publishing(item)
            except Exception:
                continue

    def _process_publishing(self, item):
        """Process publishing for an order item."""
        order, team_info, request_id = item

        # Simulate settlement timing
        time.sleep(0.03)

        # Complete successfully
        self.coordinator.notify_completion(
            request_id=request_id,
            api_response=self._create_success_response(order),
            order_id=f"ORD_{request_id[-6:]}",
        )

    def _should_reject_order(self, order, team_info):
        """Mock validation logic."""
        return order.get("quantity", 0) > 100

    def _create_validation_error(self, order):
        """Create validation error response."""
        return ApiResponse(
            success=False,
            request_id="mock_request",
            order_id=None,
            data=None,
            error=ApiError(
                code="VALIDATION_ERROR",
                message=f"Order quantity {order.get('quantity')} exceeds limit",
                details={"max_quantity": 100},
            ),
        )

    def _create_success_response(self, order):
        """Create successful order response."""
        is_market_order = order.get("order_type") == "market"
        return ApiResponse(
            success=True,
            request_id="mock_request",
            order_id="ORD_MOCK",
            data={
                "order_id": "ORD_MOCK",
                "status": "filled" if is_market_order else "new",
                "filled_quantity": order.get("quantity")
                if is_market_order
                else 0,
                "average_price": order.get("price", 128.50),
                "fees": -0.50,
                "liquidity_type": "taker" if is_market_order else None,
            },
            error=None,
        )


@pytest.fixture
def coordination_config():
    """Default coordination configuration for testing."""
    return CoordinationConfig(
        default_timeout_seconds=2.0,  # Shorter for faster tests
        max_pending_requests=100,
        cleanup_interval_seconds=1,
        enable_metrics=True,
        enable_detailed_logging=True,
        request_id_prefix="test_req",
    )


@pytest.fixture
def mock_coordinator():
    """Mock coordinator for unit testing API endpoints."""
    coordinator = Mock(spec=OrderResponseCoordinatorInterface)

    # Default successful registration
    coordinator.register_request.return_value = ResponseRegistration(
        request_id="test_req_123",
        team_id="TEAM_001",
        timeout_at=datetime.now() + timedelta(seconds=5),
        status=ResponseStatus.PENDING,
    )

    # Default successful completion
    coordinator.wait_for_completion.return_value = ResponseResult(
        request_id="test_req_123",
        success=True,
        api_response=ApiResponse(
            success=True,
            request_id="test_req_123",
            order_id="ORD_456",
            data={"status": "filled", "quantity": 10},
            error=None,
        ),
        processing_time_ms=50.0,
        final_status=ResponseStatus.COMPLETED,
        order_id="ORD_456",
    )

    return coordinator


@pytest.fixture
def sample_team_info():
    """Sample team information for testing."""
    return {
        "team_id": "TEAM_001",
        "team_name": "TestBot",
        "role": "market_maker",
        "api_key": "test_api_key_123",
    }


@pytest.fixture
def sample_order_request():
    """Sample order request for testing."""
    return {
        "instrument_id": "SPX_4500_CALL",
        "order_type": "limit",
        "side": "buy",
        "quantity": 10,
        "price": 128.50,
        "client_order_id": "client_123",
    }


@pytest.fixture
def sample_order_response():
    """Sample successful order response for testing."""
    return {
        "order_id": "ORD_456",
        "status": "filled",
        "timestamp": datetime.now(),
        "filled_quantity": 10,
        "average_price": 128.50,
        "fees": -0.50,
        "liquidity_type": "taker",
    }


@pytest.fixture
def market_maker_scenario():
    """Market maker trading scenario data."""
    return {
        "team_info": {
            "team_id": "TEAM_MM1",
            "role": "market_maker",
            "position_limit": 50,
            "current_position": 0,
        },
        "bid_order": {
            "instrument_id": "SPX_4500_CALL",
            "order_type": "limit",
            "side": "buy",
            "quantity": 10,
            "price": 127.50,
        },
        "ask_order": {
            "instrument_id": "SPX_4500_CALL",
            "order_type": "limit",
            "side": "sell",
            "quantity": 10,
            "price": 128.50,
        },
    }


@pytest.fixture
def hedge_fund_scenario():
    """Hedge fund trading scenario data."""
    return {
        "team_info": {
            "team_id": "TEAM_HF1",
            "role": "hedge_fund",
            "delta_limit": 50,
            "current_delta": 0,
        },
        "market_order": {
            "instrument_id": "SPX_4500_CALL",
            "order_type": "market",
            "side": "buy",
            "quantity": 20,
        },
        "hedge_order": {
            "instrument_id": "SPX_4500_PUT",
            "order_type": "market",
            "side": "sell",
            "quantity": 20,
        },
    }


@pytest.fixture
def validation_failure_scenarios():
    """Common validation failure scenarios."""
    return {
        "position_limit_exceeded": {
            "error_code": "POSITION_LIMIT_EXCEEDED",
            "error_message": "Order would exceed position limit of ±50",
            "http_status": 400,
            "details": {
                "current_position": 45,
                "order_quantity": 10,
                "position_limit": 50,
            },
        },
        "invalid_instrument": {
            "error_code": "INVALID_INSTRUMENT",
            "error_message": "Unknown instrument: INVALID_SYMBOL",
            "http_status": 400,
            "details": {
                "requested_instrument": "INVALID_SYMBOL",
                "available_instruments": ["SPX_4500_CALL", "SPX_4500_PUT"],
            },
        },
        "insufficient_balance": {
            "error_code": "INSUFFICIENT_BALANCE",
            "error_message": "Insufficient balance for order",
            "http_status": 400,
            "details": {
                "required_margin": 12850.0,
                "available_balance": 10000.0,
            },
        },
    }


@pytest.fixture
def system_error_scenarios():
    """Common system error scenarios."""
    return {
        "exchange_error": {
            "error_code": "EXCHANGE_ERROR",
            "error_message": "Exchange matching engine error",
            "http_status": 500,
            "details": {
                "support_reference": "ERR_20240115_103045_789",
                "stage": "matching",
            },
        },
        "settlement_error": {
            "error_code": "SETTLEMENT_ERROR",
            "error_message": "Trade settlement failed",
            "http_status": 500,
            "details": {
                "support_reference": "ERR_20240115_103046_790",
                "stage": "settlement",
            },
        },
        "timeout_error": {
            "error_code": "PROCESSING_TIMEOUT",
            "error_message": "Order processing exceeded time limit",
            "http_status": 504,
            "details": {
                "timeout_ms": 5000,
                "stage": "matching",
            },
        },
    }


@pytest.fixture
def mock_pipeline_threads():
    """Mock pipeline threads for integration testing."""
    return MockPipelineThreads()


@pytest.fixture
def concurrent_orders():
    """Generate multiple orders for concurrency testing."""
    orders = []
    for i in range(10):
        orders.append(
            {
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy" if i % 2 == 0 else "sell",
                "quantity": 10 + i,
                "price": 128.00 + (i * 0.25),
                "client_order_id": f"client_order_{i}",
            }
        )
    return orders


class PerformanceMonitor:
    """Performance monitoring helper for tests."""

    def __init__(self):
        self.metrics = {}
        self.start_times = {}

    def start_timer(self, operation: str):
        """Start timing an operation."""
        self.start_times[operation] = time.perf_counter()

    def end_timer(self, operation: str) -> float:
        """End timing and return duration in milliseconds."""
        if operation not in self.start_times:
            return 0.0

        duration_ms = (
            time.perf_counter() - self.start_times[operation]
        ) * 1000
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration_ms)
        del self.start_times[operation]
        return duration_ms

    def get_average_time(self, operation: str) -> float:
        """Get average time for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return 0.0
        return sum(self.metrics[operation]) / len(self.metrics[operation])

    def get_max_time(self, operation: str) -> float:
        """Get maximum time for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return 0.0
        return max(self.metrics[operation])

    def assert_performance(
        self, operation: str, max_avg_ms: float, max_single_ms: float
    ):
        """Assert performance requirements are met."""
        avg_time = self.get_average_time(operation)
        max_time = self.get_max_time(operation)

        assert (
            avg_time <= max_avg_ms
        ), f"Average {operation} time {avg_time:.1f}ms exceeds limit {max_avg_ms}ms"
        assert (
            max_time <= max_single_ms
        ), f"Maximum {operation} time {max_time:.1f}ms exceeds limit {max_single_ms}ms"


@pytest.fixture
def performance_monitor():
    """Performance monitoring helper for tests."""
    return PerformanceMonitor()
