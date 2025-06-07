"""Pydantic models for REST API requests and responses."""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


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
