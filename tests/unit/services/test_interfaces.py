"""Unit tests for service interface contracts.

This module tests that the service interfaces properly enforce
abstract method implementation and maintain correct type signatures.
The tests use mock implementations to verify interface contracts
without requiring actual business logic.
"""

from typing import Dict, Optional, Tuple
from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.models.order import Order
from intern_trading_game.domain.exchange.order_result import OrderResult
from intern_trading_game.domain.exchange.validation.order_validator import (
    ValidationResult,
)
from intern_trading_game.infrastructure.api.models import (
    OrderResponse,
    TeamInfo,
)
from intern_trading_game.services import (
    OrderMatchingServiceInterface,
    OrderValidationServiceInterface,
    TradeProcessingServiceInterface,
    WebSocketMessagingServiceInterface,
)


class TestOrderValidationServiceInterface:
    """Test OrderValidationServiceInterface contract enforcement."""

    def test_cannot_instantiate_abstract_interface(self):
        """Test that abstract interface cannot be instantiated directly."""
        with pytest.raises(
            TypeError, match="Can't instantiate abstract class"
        ):
            OrderValidationServiceInterface()

    def test_concrete_class_must_implement_all_methods(self):
        """Test that concrete implementations must define all methods."""

        # Create incomplete implementation missing validate_cancellation
        class IncompleteValidationService(OrderValidationServiceInterface):
            def validate_new_order(
                self, order: Order, team: TeamInfo
            ) -> ValidationResult:
                return ValidationResult(is_valid=True)

        with pytest.raises(
            TypeError, match="Can't instantiate abstract class"
        ):
            IncompleteValidationService()

    def test_validate_new_order_signature(self):
        """Test validate_new_order method signature and return type."""

        # Create complete implementation
        class ConcreteValidationService(OrderValidationServiceInterface):
            def validate_new_order(
                self, order: Order, team: TeamInfo
            ) -> ValidationResult:
                return ValidationResult(is_valid=True)

            def validate_cancellation(
                self, order_id: str, team_id: str
            ) -> Tuple[bool, Optional[str]]:
                return True, None

        service = ConcreteValidationService()

        # Test with mock objects
        mock_order = Mock(spec=Order)
        mock_team = Mock(spec=TeamInfo)

        result = service.validate_new_order(mock_order, mock_team)

        assert isinstance(result, ValidationResult)
        assert hasattr(result, "is_valid")
        assert hasattr(result, "error_detail")

    def test_validate_cancellation_signature(self):
        """Test validate_cancellation method signature and return type."""

        class ConcreteValidationService(OrderValidationServiceInterface):
            def validate_new_order(
                self, order: Order, team: TeamInfo
            ) -> ValidationResult:
                return ValidationResult(is_valid=True)

            def validate_cancellation(
                self, order_id: str, team_id: str
            ) -> Tuple[bool, Optional[str]]:
                return False, "Order not found"

        service = ConcreteValidationService()

        success, reason = service.validate_cancellation("ORD_123", "TEAM_001")

        assert isinstance(success, bool)
        assert reason is None or isinstance(reason, str)


class TestOrderMatchingServiceInterface:
    """Test OrderMatchingServiceInterface contract enforcement."""

    def test_cannot_instantiate_abstract_interface(self):
        """Test that abstract interface cannot be instantiated directly."""
        with pytest.raises(
            TypeError, match="Can't instantiate abstract class"
        ):
            OrderMatchingServiceInterface()

    def test_concrete_class_must_implement_all_methods(self):
        """Test that concrete implementations must define all methods."""

        # Create incomplete implementation missing handle_exchange_error
        class IncompleteMatchingService(OrderMatchingServiceInterface):
            def submit_order_to_exchange(self, order: Order) -> OrderResult:
                return OrderResult(order_id="123", status="new")

        with pytest.raises(
            TypeError, match="Can't instantiate abstract class"
        ):
            IncompleteMatchingService()

    def test_submit_order_to_exchange_signature(self):
        """Test submit_order_to_exchange method signature."""

        class ConcreteMatchingService(OrderMatchingServiceInterface):
            def submit_order_to_exchange(self, order: Order) -> OrderResult:
                return OrderResult(
                    order_id="ORD_123", status="new", remaining_quantity=10
                )

            def handle_exchange_error(
                self, error: Exception, order: Order
            ) -> OrderResult:
                return OrderResult(
                    order_id=order.order_id,
                    status="rejected",
                    error_message=str(error),
                )

        service = ConcreteMatchingService()
        mock_order = Mock(spec=Order)
        mock_order.order_id = "ORD_123"

        result = service.submit_order_to_exchange(mock_order)

        assert isinstance(result, OrderResult)
        assert hasattr(result, "order_id")
        assert hasattr(result, "status")

    def test_handle_exchange_error_signature(self):
        """Test handle_exchange_error method signature."""

        class ConcreteMatchingService(OrderMatchingServiceInterface):
            def submit_order_to_exchange(self, order: Order) -> OrderResult:
                return OrderResult(order_id="123", status="new")

            def handle_exchange_error(
                self, error: Exception, order: Order
            ) -> OrderResult:
                return OrderResult(
                    order_id="ORD_123",
                    status="error",
                    error_message=str(error),
                )

        service = ConcreteMatchingService()
        mock_order = Mock(spec=Order)
        mock_error = ValueError("Test error")

        result = service.handle_exchange_error(mock_error, mock_order)

        assert isinstance(result, OrderResult)
        assert result.status == "error"


class TestTradeProcessingServiceInterface:
    """Test TradeProcessingServiceInterface contract enforcement."""

    def test_cannot_instantiate_abstract_interface(self):
        """Test that abstract interface cannot be instantiated directly."""
        with pytest.raises(
            TypeError, match="Can't instantiate abstract class"
        ):
            TradeProcessingServiceInterface()

    def test_process_trade_result_signature(self):
        """Test process_trade_result method signature and return type."""
        from datetime import datetime

        class ConcreteTradeService(TradeProcessingServiceInterface):
            def process_trade_result(
                self, result: OrderResult, order: Order, team: TeamInfo
            ) -> OrderResponse:
                return OrderResponse(
                    order_id=result.order_id,
                    status=result.status,
                    timestamp=datetime.now(),
                    filled_quantity=10,
                    average_price=100.5,
                )

        service = ConcreteTradeService()

        mock_result = Mock(spec=OrderResult)
        mock_result.order_id = "ORD_123"
        mock_result.status = "filled"
        mock_order = Mock(spec=Order)
        mock_team = Mock(spec=TeamInfo)

        response = service.process_trade_result(
            mock_result, mock_order, mock_team
        )

        assert isinstance(response, OrderResponse)
        assert hasattr(response, "order_id")
        assert hasattr(response, "status")
        assert hasattr(response, "filled_quantity")


class TestWebSocketMessagingServiceInterface:
    """Test WebSocketMessagingServiceInterface contract enforcement."""

    def test_cannot_instantiate_abstract_interface(self):
        """Test that abstract interface cannot be instantiated directly."""
        with pytest.raises(
            TypeError, match="Can't instantiate abstract class"
        ):
            WebSocketMessagingServiceInterface()

    def test_concrete_class_must_implement_all_methods(self):
        """Test that concrete implementations must define all methods."""

        # Create incomplete implementation missing format_order_ack
        class IncompleteMessagingService(WebSocketMessagingServiceInterface):
            async def route_message(
                self, msg_type: str, team_id: str, data: Dict
            ) -> None:
                pass

        with pytest.raises(
            TypeError, match="Can't instantiate abstract class"
        ):
            IncompleteMessagingService()

    @pytest.mark.asyncio
    async def test_route_message_signature(self):
        """Test route_message async method signature."""

        class ConcreteMessagingService(WebSocketMessagingServiceInterface):
            async def route_message(
                self, msg_type: str, team_id: str, data: Dict
            ) -> None:
                # Fire-and-forget pattern
                return None

            def format_order_ack(self, order: Order, status: str) -> Dict:
                return {"order_id": order.order_id, "status": status}

        service = ConcreteMessagingService()

        # Test async method returns None
        result = await service.route_message(
            "new_order_ack", "TEAM_001", {"order_id": "123"}
        )

        assert result is None

    def test_format_order_ack_signature(self):
        """Test format_order_ack method signature and return type."""

        class ConcreteMessagingService(WebSocketMessagingServiceInterface):
            async def route_message(
                self, msg_type: str, team_id: str, data: Dict
            ) -> None:
                pass

            def format_order_ack(self, order: Order, status: str) -> Dict:
                return {
                    "order_id": order.order_id,
                    "status": status,
                    "timestamp": "2024-01-01T00:00:00",
                }

        service = ConcreteMessagingService()
        mock_order = Mock(spec=Order)
        mock_order.order_id = "ORD_123"

        result = service.format_order_ack(mock_order, "new")

        assert isinstance(result, dict)
        assert "order_id" in result
        assert "status" in result


class TestInterfaceTypeAnnotations:
    """Test that all interfaces have proper type annotations."""

    def test_all_methods_have_type_hints(self):
        """Verify all interface methods have complete type annotations."""
        interfaces = [
            OrderValidationServiceInterface,
            OrderMatchingServiceInterface,
            TradeProcessingServiceInterface,
            WebSocketMessagingServiceInterface,
        ]

        for interface in interfaces:
            for method_name in dir(interface):
                if method_name.startswith("_"):
                    continue

                method = getattr(interface, method_name)
                if not callable(method):
                    continue

                # Check that abstract methods have annotations
                if hasattr(method, "__isabstractmethod__"):
                    annotations = getattr(method, "__annotations__", {})
                    # All abstract methods should have return type annotation
                    assert (
                        "return" in annotations
                    ), f"{interface.__name__}.{method_name} missing return type"
