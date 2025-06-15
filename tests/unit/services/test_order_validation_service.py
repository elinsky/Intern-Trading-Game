"""Unit tests for OrderValidationService.

This module contains comprehensive tests for the order validation
service, verifying correct behavior for order validation and
cancellation scenarios.
"""

from unittest.mock import Mock, create_autospec

import pytest

from intern_trading_game.domain.exchange.core.order import (
    Order,
    OrderSide,
    OrderType,
)
from intern_trading_game.domain.exchange.order_result import OrderResult
from intern_trading_game.domain.exchange.validation.interfaces import (
    ValidationContext,
)
from intern_trading_game.domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
)
from intern_trading_game.domain.exchange.venue import ExchangeVenue
from intern_trading_game.infrastructure.api.models import TeamInfo
from intern_trading_game.services.interfaces import (
    OrderValidationServiceInterface,
)
from intern_trading_game.services.order_validation import (
    OrderValidationService,
)


class TestOrderValidationService:
    """Test suite for OrderValidationService."""

    @pytest.fixture
    def mock_validator(self):
        """Create a mock ConstraintBasedOrderValidator."""
        return create_autospec(ConstraintBasedOrderValidator, instance=True)

    @pytest.fixture
    def mock_exchange(self):
        """Create a mock ExchangeVenue."""
        return create_autospec(ExchangeVenue, instance=True)

    @pytest.fixture
    def mock_get_positions(self):
        """Create a mock position retrieval function."""
        return Mock(return_value={"SPX-20240315-4500C": 25})

    @pytest.fixture
    def service(
        self,
        mock_validator,
        mock_exchange,
        mock_get_positions,
    ):
        """Create an OrderValidationService instance with mocks.

        Rate limiting state is now owned internally by the service.
        """
        return OrderValidationService(
            validator=mock_validator,
            exchange=mock_exchange,
            get_positions_func=mock_get_positions,
        )

    @pytest.fixture
    def sample_order(self):
        """Create a sample order for testing."""
        return Order(
            instrument_id="SPX-20240315-4500C",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.LIMIT,
            price=125.50,
            trader_id="TEAM001",
        )

    @pytest.fixture
    def sample_team(self):
        """Create a sample team info for testing."""
        from datetime import datetime

        return TeamInfo(
            team_id="TEAM001",
            team_name="Test Team",
            role="market_maker",
            api_key="test-api-key",
            created_at=datetime.now(),
        )

    def test_service_implements_interface(self, service):
        """Test that service implements the interface correctly."""
        assert isinstance(service, OrderValidationServiceInterface)

    def test_validate_new_order_accepted(
        self,
        service,
        sample_order,
        sample_team,
        mock_validator,
        mock_get_positions,
    ):
        """Test successful order validation.

        Given - Valid order with team under position limits
        When - Order is validated
        Then - Validation passes with correct context
        """
        # Given - Configure mock to accept order
        mock_validator.validate_order.return_value = OrderResult(
            order_id=sample_order.order_id,
            status="accepted",
            remaining_quantity=sample_order.quantity,
        )

        # When - Validate the order
        result = service.validate_new_order(sample_order, sample_team)

        # Then - Validation should pass
        assert result.status == "accepted"
        assert result.error_message is None

        # Verify correct state retrieval
        mock_get_positions.assert_called_once_with("TEAM001")
        # Order count now managed internally by service

        # Verify validator called with correct context
        mock_validator.validate_order.assert_called_once()
        context = mock_validator.validate_order.call_args[0][0]
        assert isinstance(context, ValidationContext)
        assert context.order == sample_order
        assert context.trader_id == "TEAM001"
        assert context.trader_role == "market_maker"
        assert context.current_positions == {"SPX-20240315-4500C": 25}
        assert context.orders_this_second == 0  # Fresh service starts with 0

    def test_validate_new_order_rejected_position_limit(
        self,
        service,
        sample_order,
        sample_team,
        mock_validator,
        mock_get_positions,
    ):
        """Test order rejection due to position limit.

        Given - Team at position limit for instrument
        When - New order would exceed limit
        Then - Validation fails with position limit error
        """
        # Given - Configure positions at limit
        mock_get_positions.return_value = {"SPX-20240315-4500C": 45}
        mock_validator.validate_order.return_value = OrderResult(
            order_id=sample_order.order_id,
            status="rejected",
            error_code="POSITION_LIMIT",
            error_message="Position limit exceeded: current 45 + order 10 > limit 50",
        )

        # When - Validate order that would exceed limit
        result = service.validate_new_order(sample_order, sample_team)

        # Then - Validation should fail
        assert result.status == "rejected"
        assert "Position limit exceeded" in result.error_message

    def test_validate_new_order_rejected_rate_limit(
        self,
        service,
        sample_order,
        sample_team,
        mock_validator,
    ):
        """Test order rejection due to rate limit.

        Given - Team has submitted maximum orders this second
        When - Another order is submitted
        Then - Validation fails with rate limit error
        """
        # Given - Set high order count in service internal state
        service.orders_this_second[sample_team.team_id] = 10
        mock_validator.validate_order.return_value = OrderResult(
            order_id=sample_order.order_id,
            status="rejected",
            error_code="RATE_LIMIT",
            error_message="Order rate limit exceeded: 10 orders in current tick",
        )

        # When - Validate order
        result = service.validate_new_order(sample_order, sample_team)

        # Then - Validation should fail
        assert result.status == "rejected"
        assert "rate limit exceeded" in result.error_message

    def test_validate_cancellation_success(self, service, mock_exchange):
        """Test successful order cancellation.

        Given - Valid order owned by requesting team
        When - Cancellation is requested
        Then - Order is cancelled successfully
        """
        # Given - Configure exchange to accept cancellation
        mock_exchange.cancel_order.return_value = True

        # When - Request cancellation
        success, reason = service.validate_cancellation("ORD123", "TEAM001")

        # Then - Cancellation should succeed
        assert success is True
        assert reason is None
        mock_exchange.cancel_order.assert_called_once_with("ORD123", "TEAM001")

    def test_validate_cancellation_unauthorized(self, service, mock_exchange):
        """Test cancellation failure due to unauthorized access.

        Given - Order owned by different team
        When - Cancellation requested by non-owner
        Then - Cancellation fails with unauthorized error
        """
        # Given - Configure exchange to reject cancellation
        mock_exchange.cancel_order.return_value = False

        # When - Request cancellation
        success, reason = service.validate_cancellation("ORD123", "TEAM002")

        # Then - Cancellation should fail with generic error
        assert success is False
        assert reason == "Order not found"
        mock_exchange.cancel_order.assert_called_once_with("ORD123", "TEAM002")

    def test_validate_cancellation_order_not_found(
        self, service, mock_exchange
    ):
        """Test cancellation failure for non-existent order.

        Given - Order ID that doesn't exist
        When - Cancellation is requested
        Then - Cancellation fails with not found error
        """
        # Given - Configure exchange to reject cancellation
        mock_exchange.cancel_order.return_value = False

        # When - Request cancellation of non-existent order
        success, reason = service.validate_cancellation("BADORD", "TEAM001")

        # Then - Cancellation should fail with generic error
        assert success is False
        assert reason == "Order not found"

    @pytest.mark.parametrize(
        "positions,order_count,expected_positions,expected_count",
        [
            ({}, 0, {}, 0),  # Empty state
            ({"SPX-20240315-4500C": 10}, 5, {"SPX-20240315-4500C": 10}, 5),
            ({"SPX-20240315-4500C": -20}, 1, {"SPX-20240315-4500C": -20}, 1),
        ],
    )
    def test_state_retrieval_variations(
        self,
        service,
        sample_order,
        sample_team,
        mock_validator,
        positions,
        order_count,
        expected_positions,
        expected_count,
    ):
        """Test service handles various state configurations.

        Given - Different position and order count states
        When - Order validation occurs
        Then - Correct state is passed to validator
        """
        # Given - Configure state
        service._get_positions = Mock(return_value=positions)
        # Set internal order count state
        if order_count > 0:
            service.orders_this_second[sample_team.team_id] = order_count
        mock_validator.validate_order.return_value = OrderResult(
            order_id=sample_order.order_id,
            status="accepted",
            remaining_quantity=sample_order.quantity,
        )

        # When - Validate order
        service.validate_new_order(sample_order, sample_team)

        # Then - Verify correct state in context
        context = mock_validator.validate_order.call_args[0][0]
        assert context.current_positions == expected_positions
        assert context.orders_this_second == expected_count

    def test_validate_new_order_with_complex_positions(
        self,
        service,
        sample_order,
        sample_team,
        mock_validator,
    ):
        """Test validation with multiple instrument positions.

        Given - Team has positions in multiple instruments
        When - Validating order for one instrument
        Then - All positions are included in context
        """
        # Given - Multiple positions
        positions = {
            "SPX-20240315-4500C": 20,
            "SPX-20240315-4500P": -15,
            "SPY-20240315-450C": 30,
        }
        service._get_positions = Mock(return_value=positions)
        mock_validator.validate_order.return_value = OrderResult(
            order_id=sample_order.order_id,
            status="accepted",
            remaining_quantity=sample_order.quantity,
        )

        # When - Validate order
        service.validate_new_order(sample_order, sample_team)

        # Then - All positions in context
        context = mock_validator.validate_order.call_args[0][0]
        assert context.current_positions == positions
        assert len(context.current_positions) == 3

    def test_service_initialization(self):
        """Test service can be initialized with real dependencies."""
        # Given - Real (but minimal) dependencies
        validator = Mock(spec=ConstraintBasedOrderValidator)
        exchange = Mock(spec=ExchangeVenue)

        def get_pos(team_id):
            return {}

        # When - Create service (rate limiting handled internally)
        service = OrderValidationService(
            validator=validator,
            exchange=exchange,
            get_positions_func=get_pos,
        )

        # Then - Service is properly initialized
        assert service.validator is validator
        assert service.exchange is exchange
        assert service.orders_this_second == {}
        assert service.orders_lock is not None
        assert service._get_positions is get_pos
