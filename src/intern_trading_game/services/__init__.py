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
>>> from intern_trading_game.services import (
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
from ..domain.exchange.components.core.models import OrderResult
from ..infrastructure.api.models import OrderResponse

# Import supporting services and configs
# (fee configuration is now handled directly in infrastructure layer)
# Import interfaces
from .interfaces import (
    OrderMatchingServiceInterface,
    OrderValidationServiceInterface,
    TradeProcessingServiceInterface,
    WebSocketMessagingServiceInterface,
)

# Import concrete implementations
from .order_matching import OrderMatchingService
from .order_validation import OrderValidationService

__all__ = [
    # Interfaces
    "OrderValidationServiceInterface",
    "OrderMatchingServiceInterface",
    "TradeProcessingServiceInterface",
    "WebSocketMessagingServiceInterface",
    # Concrete implementations
    "OrderValidationService",
    "OrderMatchingService",
    # Re-exported existing types
    "OrderResult",  # From exchange.order_result
    "OrderResponse",  # From api.models
]
