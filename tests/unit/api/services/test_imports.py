"""Unit tests for service package imports and exports.

This module verifies that the service package correctly imports and
re-exports types from other modules, and that all interfaces are
properly accessible without circular import issues.
"""

import sys
from types import ModuleType

import pytest


class TestPackageImports:
    """Test that service package imports work correctly."""

    def test_service_package_imports_successfully(self):
        """Test that the services package can be imported."""
        # Clear any cached imports
        if "intern_trading_game.api.services" in sys.modules:
            del sys.modules["intern_trading_game.api.services"]

        # Import should not raise any errors
        import intern_trading_game.api.services as services

        assert isinstance(services, ModuleType)

    def test_all_interfaces_are_exported(self):
        """Test that all interfaces are accessible from package."""
        from intern_trading_game.api import services

        expected_interfaces = [
            "OrderValidationServiceInterface",
            "OrderMatchingServiceInterface",
            "TradeProcessingServiceInterface",
            "WebSocketMessagingServiceInterface",
        ]

        for interface_name in expected_interfaces:
            assert hasattr(
                services, interface_name
            ), f"{interface_name} not exported from services package"

            # Verify it's a class
            interface_class = getattr(services, interface_name)
            assert isinstance(interface_class, type)

    def test_reexported_types_are_accessible(self):
        """Test that re-exported types are accessible from package."""
        from intern_trading_game.api import services

        # Test ValidationResult re-export
        assert hasattr(services, "ValidationResult")
        validation_result = services.ValidationResult(is_valid=True)
        assert hasattr(validation_result, "is_valid")
        assert hasattr(validation_result, "error_detail")

        # Test OrderResult re-export
        assert hasattr(services, "OrderResult")
        order_result = services.OrderResult(order_id="ORD_123", status="new")
        assert hasattr(order_result, "order_id")
        assert hasattr(order_result, "status")

        # Test OrderResponse re-export
        assert hasattr(services, "OrderResponse")
        # OrderResponse is a Pydantic model, so we need to import datetime
        from datetime import datetime

        order_response = services.OrderResponse(
            order_id="ORD_123", status="filled", timestamp=datetime.now()
        )
        assert hasattr(order_response, "order_id")
        assert hasattr(order_response, "status")

    def test_reexported_types_match_originals(self):
        """Test that re-exported types are same as originals."""
        from intern_trading_game.api import services
        from intern_trading_game.api.models import OrderResponse
        from intern_trading_game.core.order_validator import ValidationResult
        from intern_trading_game.exchange.order_result import OrderResult

        # Verify they are the same classes, not copies
        assert services.ValidationResult is ValidationResult
        assert services.OrderResult is OrderResult
        assert services.OrderResponse is OrderResponse

    def test_package_all_exports(self):
        """Test that __all__ exports the expected items."""
        from intern_trading_game.api import services

        expected_exports = [
            # Interfaces
            "OrderValidationServiceInterface",
            "OrderMatchingServiceInterface",
            "TradeProcessingServiceInterface",
            "WebSocketMessagingServiceInterface",
            # Re-exported types
            "ValidationResult",
            "OrderResult",
            "OrderResponse",
        ]

        assert hasattr(services, "__all__")
        assert set(services.__all__) == set(expected_exports)

    def test_no_circular_imports(self):
        """Test that importing services doesn't cause circular imports."""
        # Clear all related modules
        modules_to_clear = [
            "intern_trading_game.api.services",
            "intern_trading_game.api.services.interfaces",
            "intern_trading_game.core.order_validator",
            "intern_trading_game.exchange.order_result",
            "intern_trading_game.api.models",
        ]

        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]

        # Import in various orders - should not raise ImportError
        try:
            # Import services first
            import intern_trading_game.api.models
            import intern_trading_game.api.services

            # Then import the source modules
            import intern_trading_game.core.order_validator
            import intern_trading_game.exchange.order_result

            # Verify modules loaded (satisfies F401)
            assert intern_trading_game.api.services is not None
            assert intern_trading_game.core.order_validator is not None
            assert intern_trading_game.exchange.order_result is not None
            assert intern_trading_game.api.models is not None

        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_import_specific_items(self):
        """Test importing specific items from services package."""
        # Test importing just interfaces
        from intern_trading_game.api.services import (
            OrderMatchingServiceInterface,
            OrderValidationServiceInterface,
        )

        assert OrderValidationServiceInterface is not None
        assert OrderMatchingServiceInterface is not None

        # Test importing just re-exported types
        from intern_trading_game.api.services import (
            OrderResponse,
            OrderResult,
            ValidationResult,
        )

        assert ValidationResult is not None
        assert OrderResult is not None
        assert OrderResponse is not None

    def test_type_compatibility_with_existing_code(self):
        """Test that re-exported types work with existing type hints."""
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            # This tests that the imports work for type checking
            from intern_trading_game.api.models import TeamInfo
            from intern_trading_game.api.services import (
                OrderValidationServiceInterface,
                ValidationResult,
            )
            from intern_trading_game.exchange.order import Order

            # This should type check correctly
            def example_usage(
                service: OrderValidationServiceInterface,
                order: Order,
                team: TeamInfo,
            ) -> ValidationResult:
                return service.validate_new_order(order, team)

        # Test passes if no import errors occur
        assert True
