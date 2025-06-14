"""Pydantic models for REST API requests and responses."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    """Error details for failed API requests."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error context"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "POSITION_LIMIT_EXCEEDED",
                "message": "Order would exceed position limit of 50",
                "details": {
                    "current_position": 45,
                    "order_quantity": 10,
                    "limit": 50,
                },
            }
        }
    }


class ApiResponse(BaseModel):
    """Generic API response for all operations.

    This unified response structure is used for both successful and failed
    operations, providing a consistent interface for clients.
    """

    success: bool = Field(..., description="Whether the request succeeded")
    request_id: str = Field(..., description="Echo of client's request ID")
    order_id: Optional[str] = Field(
        default=None, description="Order ID for successful order operations"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Response data for query operations"
    )
    error: Optional[ApiError] = Field(
        default=None, description="Error details if failed"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Server timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "examples": {
                "success": {
                    "value": {
                        "success": True,
                        "request_id": "req_abc123",
                        "order_id": "ORD_123456",
                        "error": None,
                        "timestamp": "2024-01-15T10:00:01.001Z",
                    }
                },
                "failure": {
                    "value": {
                        "success": False,
                        "request_id": "req_abc123",
                        "order_id": None,
                        "error": {
                            "code": "POSITION_LIMIT_EXCEEDED",
                            "message": "Order would exceed position limit of 50",
                            "details": {
                                "current_position": 45,
                                "order_quantity": 10,
                                "limit": 50,
                            },
                        },
                        "timestamp": "2024-01-15T10:00:01.001Z",
                    }
                },
            }
        }
    }


class OrderRequest(BaseModel):
    """Request model for order submission."""

    instrument_id: str = Field(..., description="Instrument to trade")
    order_type: str = Field(..., description="Order type: limit or market")
    side: str = Field(..., description="Order side: buy or sell")
    quantity: int = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(
        None, gt=0, description="Limit price (required for limit orders)"
    )
    client_order_id: Optional[str] = Field(
        None, description="Client's order reference ID"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 10,
                "price": 25.50,
            }
        }
    }


class OrderResponse(BaseModel):
    """Response model for order submission."""

    order_id: str
    status: str
    timestamp: datetime
    filled_quantity: int = 0
    average_price: Optional[float] = None
    fees: float = 0.0
    liquidity_type: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class TeamRegistration(BaseModel):
    """Request model for team registration."""

    team_name: str = Field(..., min_length=1, max_length=50)
    role: str = Field(
        ..., description="Role: market_maker, hedge_fund, arbitrage, retail"
    )

    model_config = {
        "json_schema_extra": {
            "example": {"team_name": "AlphaBot", "role": "hedge_fund"}
        }
    }


class TeamInfo(BaseModel):
    """Response model for team registration."""

    team_id: str
    team_name: str
    role: str
    api_key: str
    created_at: datetime


class PositionResponse(BaseModel):
    """Response model for position queries."""

    team_id: str
    positions: Dict[str, int]
    last_updated: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "team_id": "TEAM_123",
                "positions": {"SPX_4500_CALL": 10, "SPX_4500_PUT": -5},
                "last_updated": "2024-01-15T10:30:00Z",
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
