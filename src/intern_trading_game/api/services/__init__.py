"""Service layer for API thread business logic extraction.

This package contains abstract interfaces for the service-oriented
architecture that extracts business logic from the monolithic thread
functions in main.py.

The service layer follows SOLID principles with clear separation of concerns:
- Each service interface represents a single responsibility
- Services depend on abstractions, not concrete implementations
- All data types are reused from existing modules (no new DTOs!)

Architecture Overview
--------------------
The services correspond to the threading model defined in architecture-v2.md:

- OrderValidationService: Thread 2 business logic (order validation)
- OrderMatchingService: Thread 3 business logic (exchange interaction)
- TradeProcessingService: Thread 4 business logic (trade processing)
- WebSocketMessagingService: Thread 8 business logic (message routing)

Each service extracts pure business logic while thread functions remain
as thin infrastructure controllers managing queues and coordination.

Type Reuse Strategy
------------------
This package creates NO new data transfer objects. Instead, it reuses:
- OrderResult from exchange.order_result
- OrderResponse from api.models

This approach follows DRY principle and leverages well-tested existing types.

Examples
--------
>>> from intern_trading_game.api.services import (
...     OrderValidationServiceInterface,
...     OrderResult,       # Re-exported from exchange
...     OrderResponse      # Re-exported from api
... )
>>>
>>> # Services will be injected into thread functions
>>> validation_service: OrderValidationServiceInterface = get_validation_service()
>>> result: OrderResult = validation_service.validate_new_order(order, team)
"""

# Re-export existing types for convenience
from ...exchange.order_result import OrderResult
from ..models import OrderResponse

# Import supporting services and configs
from .fee_config import FeeConfig, FeeSchedule

# Import interfaces
from .interfaces import (
    OrderMatchingServiceInterface,
    OrderValidationServiceInterface,
    TradeProcessingServiceInterface,
    WebSocketMessagingServiceInterface,
)

# Import concrete implementations
from .order_matching_service import OrderMatchingService
from .order_validation_service import OrderValidationService
from .position_management_service import PositionManagementService
from .trade_processing_service import TradeProcessingService
from .trading_fee_service import TradingFeeService

__all__ = [
    # Interfaces
    "OrderValidationServiceInterface",
    "OrderMatchingServiceInterface",
    "TradeProcessingServiceInterface",
    "WebSocketMessagingServiceInterface",
    # Concrete implementations
    "OrderValidationService",
    "OrderMatchingService",
    "TradeProcessingService",
    # Supporting services
    "TradingFeeService",
    "PositionManagementService",
    # Configuration models
    "FeeConfig",
    "FeeSchedule",
    # Re-exported existing types
    "OrderResult",  # From exchange.order_result
    "OrderResponse",  # From api.models
]
