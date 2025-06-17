"""Order response coordination module for the Exchange domain.

This module provides services and models for coordinating synchronous API
responses with asynchronous order processing pipelines. It eliminates global
state by providing proper service ownership of response coordination logic.

The module includes:
- OrderResponseCoordinator: Main service for response coordination
- Response data models: PendingRequest, ResponseResult, etc.
- Configuration models: CoordinationConfig
- Custom exceptions: CoordinationError types

Examples
--------
>>> # Basic usage in API endpoint
>>> coordinator = OrderResponseCoordinator(config)
>>> registration = coordinator.register_request(team_id="TEAM_001")
>>> # Submit order to pipeline...
>>> result = await coordinator.wait_for_completion(registration.request_id)
>>> return JSONResponse(result.http_status_code, result.api_response)
"""

from .coordinator import OrderResponseCoordinator
from .interfaces import (
    OrderResponseCoordinatorInterface,
    ResponseRegistration,
    ResponseResult,
)
from .models import (
    CoordinationConfig,
    PendingRequest,
    ResponseStatus,
)

__all__ = [
    "OrderResponseCoordinator",
    "OrderResponseCoordinatorInterface",
    "ResponseRegistration",
    "ResponseResult",
    "CoordinationConfig",
    "PendingRequest",
    "ResponseStatus",
]
