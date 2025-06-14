"""Unit tests for API models.

Tests the Pydantic models used for API requests and responses,
focusing on the unified ApiResponse format that enables fast
validation feedback to trading bots.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from intern_trading_game.infrastructure.api.models import (
    ApiError,
    ApiResponse,
    OrderRequest,
)


class TestApiError:
    """Test ApiError model used for communicating failures to bots."""

    def test_create_api_error(self):
        """Test creating ApiError for validation failures.

        Given - A bot's order fails validation
        When - The system creates an error response
        Then - The error should contain code and message
        """
        # Given - A bot submits an order that would exceed position limits
        # The system needs to communicate this clearly

        # When - We create an ApiError for the rejection
        error = ApiError(
            code="POSITION_LIMIT_EXCEEDED",
            message="Order would exceed position limit of 50",
            details={
                "current_position": 45,
                "order_quantity": 10,
                "limit": 50,
            },
        )

        # Then - The error contains all necessary information
        # for the bot to understand and handle the rejection
        assert error.code == "POSITION_LIMIT_EXCEEDED"
        assert error.message == "Order would exceed position limit of 50"
        assert error.details["current_position"] == 45

    def test_api_error_serialization(self):
        """Test ApiError serializes correctly for API responses.

        Given - An error that needs to be sent to a bot
        When - We serialize it to JSON
        Then - It should match the expected API format
        """
        # Given - An error object representing an invalid order
        error = ApiError(
            code="INVALID_QUANTITY", message="Quantity must be positive"
        )

        # When - We serialize to dict (for FastAPI response)
        error_dict = error.model_dump()

        # Then - The format matches what bots expect
        assert error_dict == {
            "code": "INVALID_QUANTITY",
            "message": "Quantity must be positive",
            "details": None,
        }


class TestApiResponse:
    """Test unified ApiResponse format for all API operations."""

    def test_successful_order_response(self):
        """Test ApiResponse for successful order submission.

        Given - A bot submits a valid order
        When - The validator accepts it
        Then - ApiResponse returns with order_id
        """
        # Given - A market maker's order passes validation
        # The bot needs immediate confirmation with order_id

        # When - We create the success response
        response = ApiResponse(
            success=True,
            request_id="req_12345",
            order_id="ORD_67890",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
        )

        # Then - The response confirms success with order tracking info
        assert response.success is True
        assert response.request_id == "req_12345"  # Echo for correlation
        assert response.order_id == "ORD_67890"  # For order tracking
        assert response.data is None  # No data for order ops
        assert response.error is None  # No error on success

    def test_successful_query_response(self):
        """Test ApiResponse for data queries.

        Given - A bot queries its positions
        When - The system returns position data
        Then - ApiResponse includes data field
        """
        # Given - A bot needs to check positions before trading
        positions_data = {
            "positions": {
                "SPX_CALL_4500_20240315": 10,
                "SPX_PUT_4500_20240315": -5,
            }
        }

        # When - We create the query response
        response = ApiResponse(
            success=True,
            request_id="req_12346",
            data=positions_data,
            timestamp=datetime(2024, 1, 15, 10, 0, 1),
        )

        # Then - The response contains the requested data
        assert response.success is True
        assert response.order_id is None  # No order_id for queries
        assert response.data["positions"]["SPX_CALL_4500_20240315"] == 10

    def test_failure_response(self):
        """Test ApiResponse for validation failures.

        Given - A bot's order fails validation
        When - The system rejects it
        Then - ApiResponse includes error details
        """
        # Given - A hedge fund tries to exceed position limits
        # They need detailed error info to adjust their strategy

        # When - We create the failure response
        error = ApiError(
            code="POSITION_LIMIT_EXCEEDED",
            message="Order would exceed position limit of 50",
            details={"current_position": 45, "order_quantity": 10},
        )
        response = ApiResponse(
            success=False,
            request_id="req_12347",
            error=error,
            timestamp=datetime(2024, 1, 15, 10, 0, 2),
        )

        # Then - The response clearly indicates failure with details
        assert response.success is False
        assert response.error.code == "POSITION_LIMIT_EXCEEDED"
        assert response.order_id is None  # No order_id on failure
        assert response.data is None  # No data on failure

    def test_timestamp_auto_generation(self):
        """Test timestamp is auto-generated.

        Given - An API response is created
        When - No timestamp is provided
        Then - Current time is used automatically
        """
        # Given - Quick response generation without explicit timestamp

        # When - We create a response
        response = ApiResponse(success=True, request_id="req_12348")

        # Then - Timestamp is set to current time
        assert response.timestamp is not None
        time_diff = datetime.now() - response.timestamp
        assert time_diff.total_seconds() < 1.0  # Within last second


class TestOrderRequest:
    """Test OrderRequest model for order submission."""

    def test_limit_order_request(self):
        """Test creating a limit order request.

        Given - A bot wants to submit a limit order
        When - It creates an OrderRequest
        Then - All order details are validated
        """
        # Given - A market maker posting liquidity
        # Needs to specify exact price for the limit order

        # When - Creating the order request
        request = OrderRequest(
            instrument_id="SPX_CALL_4500_20240315",
            order_type="limit",
            side="buy",
            quantity=10,
            price=100.0,
            client_order_id="MM_001",
        )

        # Then - Request contains all necessary order information
        assert request.instrument_id == "SPX_CALL_4500_20240315"
        assert request.order_type == "limit"
        assert request.price == 100.0  # Required for limit orders

    def test_market_order_request(self):
        """Test creating a market order request.

        Given - A bot wants immediate execution
        When - It creates a market order
        Then - No price is required
        """
        # Given - An arbitrage bot needs immediate fill
        # Market orders execute at best available price

        # When - Creating market order (no price)
        request = OrderRequest(
            instrument_id="SPX_PUT_4500_20240315",
            order_type="market",
            side="sell",
            quantity=5,
        )

        # Then - Order is valid without price
        assert request.order_type == "market"
        assert request.price is None
        assert request.client_order_id is None  # Optional

    def test_invalid_quantity(self):
        """Test quantity validation.

        Given - Invalid order parameters
        When - Creating an order with zero quantity
        Then - Validation should fail
        """
        # Given - Erroneous order with invalid quantity

        # When/Then - Pydantic validates quantity > 0
        with pytest.raises(ValidationError) as exc_info:
            OrderRequest(
                instrument_id="SPX_CALL_4500_20240315",
                order_type="limit",
                side="buy",
                quantity=0,  # Invalid
                price=100.0,
            )
        assert "greater than 0" in str(exc_info.value)
