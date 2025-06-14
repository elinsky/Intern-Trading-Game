"""Unit tests for OrderMatchingService."""

from unittest.mock import create_autospec

import pytest

from intern_trading_game.domain.exchange.core.order import (
    Order,
    OrderSide,
    OrderType,
)
from intern_trading_game.domain.exchange.core.trade import Trade
from intern_trading_game.domain.exchange.order_result import OrderResult
from intern_trading_game.domain.exchange.venue import ExchangeVenue
from intern_trading_game.services.order_matching import (
    OrderMatchingService,
)


class TestOrderMatchingService:
    """Test suite for OrderMatchingService."""

    @pytest.fixture
    def mock_exchange(self):
        """Create a mock ExchangeVenue."""
        return create_autospec(ExchangeVenue, instance=True)

    @pytest.fixture
    def service(self, mock_exchange):
        """Create an OrderMatchingService instance with mocked exchange."""
        return OrderMatchingService(mock_exchange)

    @pytest.fixture
    def sample_order(self):
        """Create a sample order for testing."""
        return Order(
            instrument_id="SPX-20240315-4500C",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=125.50,
            trader_id="TEAM001",
            client_order_id="CLIENT_001",
        )

    def test_submit_order_success_new(
        self, service, mock_exchange, sample_order
    ):
        """Test successful order submission that rests in book.

        Given - Limit order below best ask
        When - Submitting to exchange
        Then - Order accepted and resting with status "new"
        """
        # Given - Exchange returns new order result
        expected_result = OrderResult(
            order_id=sample_order.order_id,
            status="new",
            fills=[],
            remaining_quantity=sample_order.quantity,
        )
        mock_exchange.submit_order.return_value = expected_result

        # When - Submit order
        result = service.submit_order_to_exchange(sample_order)

        # Then - Order submitted and result returned
        assert result == expected_result
        assert result.status == "new"
        assert len(result.fills) == 0
        assert result.remaining_quantity == 100
        mock_exchange.submit_order.assert_called_once_with(sample_order)

    def test_submit_order_immediate_fill(
        self, service, mock_exchange, sample_order
    ):
        """Test order submission with immediate fill.

        Given - Market order or aggressive limit order
        When - Submitting to exchange
        Then - Order filled immediately with trades
        """
        # Given - Order crosses spread and fills
        trade = Trade(
            instrument_id="SPX-20240315-4500C",
            buyer_id="TEAM001",
            seller_id="TEAM002",
            price=125.50,
            quantity=100,
            buyer_order_id=sample_order.order_id,
            seller_order_id="OTHER_ORDER",
            aggressor_side="buy",
        )

        expected_result = OrderResult(
            order_id=sample_order.order_id,
            status="filled",
            fills=[trade],
            remaining_quantity=0,
        )
        mock_exchange.submit_order.return_value = expected_result

        # When - Submit order
        result = service.submit_order_to_exchange(sample_order)

        # Then - Order filled
        assert result.status == "filled"
        assert len(result.fills) == 1
        assert result.fills[0] == trade
        assert result.remaining_quantity == 0

    def test_submit_order_partial_fill(
        self, service, mock_exchange, sample_order
    ):
        """Test order submission with partial fill.

        Given - Order larger than available liquidity
        When - Submitting to exchange
        Then - Order partially filled
        """
        # Given - Partial fill
        trade = Trade(
            instrument_id="SPX-20240315-4500C",
            buyer_id="TEAM001",
            seller_id="TEAM002",
            price=125.50,
            quantity=60,
            buyer_order_id=sample_order.order_id,
            seller_order_id="OTHER_ORDER",
            aggressor_side="buy",
        )

        expected_result = OrderResult(
            order_id=sample_order.order_id,
            status="partially_filled",
            fills=[trade],
            remaining_quantity=40,
        )
        mock_exchange.submit_order.return_value = expected_result

        # When - Submit order
        result = service.submit_order_to_exchange(sample_order)

        # Then - Order partially filled
        assert result.status == "partially_filled"
        assert len(result.fills) == 1
        assert result.fills[0].quantity == 60
        assert result.remaining_quantity == 40

    def test_submit_order_rejected_by_exchange(
        self, service, mock_exchange, sample_order
    ):
        """Test order rejected by exchange validation.

        Given - Order violates exchange rules
        When - Submitting to exchange
        Then - Order rejected with error details
        """
        # Given - Exchange rejects order
        expected_result = OrderResult(
            order_id=sample_order.order_id,
            status="rejected",
            fills=[],
            remaining_quantity=sample_order.quantity,
            error_code="PRICE_INVALID",
            error_message="Price must be positive",
        )
        mock_exchange.submit_order.return_value = expected_result

        # When - Submit order
        result = service.submit_order_to_exchange(sample_order)

        # Then - Rejection returned
        assert result.status == "rejected"
        assert result.error_code == "PRICE_INVALID"
        assert result.error_message == "Price must be positive"
        assert len(result.fills) == 0

    def test_handle_exchange_error_value_error(self, service, sample_order):
        """Test handling ValueError from exchange.

        Given - Exchange raises ValueError
        When - Handling the error
        Then - Returns standardized error response
        """
        # Given - ValueError from exchange
        error = ValueError("Quantity must be positive")

        # When - Handle error
        result = service.handle_exchange_error(error, sample_order)

        # Then - Error response created
        assert result.order_id == sample_order.order_id
        assert result.status == "error"
        assert result.error_code == "INVALID_ORDER"
        assert "Invalid order parameters" in result.error_message
        assert "Quantity must be positive" in result.error_message
        assert result.remaining_quantity == sample_order.quantity

    def test_handle_exchange_error_key_error(self, service, sample_order):
        """Test handling KeyError for unknown instrument.

        Given - Exchange raises KeyError
        When - Handling the error
        Then - Returns instrument not found error
        """
        # Given - KeyError from exchange
        error = KeyError("SPX-20240315-4500C")

        # When - Handle error
        result = service.handle_exchange_error(error, sample_order)

        # Then - Instrument error response
        assert result.status == "error"
        assert result.error_code == "UNKNOWN_INSTRUMENT"
        assert "Instrument not found" in result.error_message
        assert sample_order.instrument_id in result.error_message

    def test_handle_exchange_error_runtime_error(self, service, sample_order):
        """Test handling RuntimeError from exchange.

        Given - Exchange raises RuntimeError
        When - Handling the error
        Then - Returns exchange error response
        """
        # Given - RuntimeError from exchange
        error = RuntimeError("Matching engine halted")

        # When - Handle error
        result = service.handle_exchange_error(error, sample_order)

        # Then - Exchange error response
        assert result.status == "error"
        assert result.error_code == "EXCHANGE_ERROR"
        assert "Exchange error" in result.error_message
        assert "Matching engine halted" in result.error_message

    def test_handle_exchange_error_unexpected(self, service, sample_order):
        """Test handling unexpected exception types.

        Given - Exchange raises unexpected exception
        When - Handling the error
        Then - Returns internal error response
        """
        # Given - Unexpected exception type
        error = TypeError("Unexpected type issue")

        # When - Handle error
        result = service.handle_exchange_error(error, sample_order)

        # Then - Internal error response
        assert result.status == "error"
        assert result.error_code == "INTERNAL_ERROR"
        assert "Unexpected error" in result.error_message

    def test_submit_market_order(self, service, mock_exchange):
        """Test submitting market order.

        Given - Market order
        When - Submitting to exchange
        Then - Order processed correctly
        """
        # Given - Market order
        market_order = Order(
            instrument_id="SPX-20240315-4500C",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.MARKET,
            price=None,
            trader_id="TEAM001",
        )

        expected_result = OrderResult(
            order_id=market_order.order_id,
            status="filled",
            fills=[
                Trade(
                    instrument_id="SPX-20240315-4500C",
                    buyer_id="TEAM002",
                    seller_id="TEAM001",
                    price=125.25,
                    quantity=50,
                    buyer_order_id="OTHER_ORDER",
                    seller_order_id=market_order.order_id,
                    aggressor_side="sell",
                )
            ],
            remaining_quantity=0,
        )
        mock_exchange.submit_order.return_value = expected_result

        # When - Submit market order
        result = service.submit_order_to_exchange(market_order)

        # Then - Market order filled
        assert result.status == "filled"
        assert result.remaining_quantity == 0

    def test_submit_order_multiple_fills(self, service, mock_exchange):
        """Test order with multiple fills.

        Given - Large order matched against multiple counterparties
        When - Submitting to exchange
        Then - All fills included in result
        """
        # Given - Order with multiple fills
        order = Order(
            instrument_id="SPX-20240315-4500C",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=125.60,
            trader_id="TEAM001",
        )

        trades = [
            Trade(
                instrument_id="SPX-20240315-4500C",
                buyer_id="TEAM001",
                seller_id="TEAM002",
                price=125.50,
                quantity=30,
                buyer_order_id=order.order_id,
                seller_order_id="ORDER1",
                aggressor_side="buy",
            ),
            Trade(
                instrument_id="SPX-20240315-4500C",
                buyer_id="TEAM001",
                seller_id="TEAM003",
                price=125.55,
                quantity=40,
                buyer_order_id=order.order_id,
                seller_order_id="ORDER2",
                aggressor_side="buy",
            ),
            Trade(
                instrument_id="SPX-20240315-4500C",
                buyer_id="TEAM001",
                seller_id="TEAM004",
                price=125.60,
                quantity=30,
                buyer_order_id=order.order_id,
                seller_order_id="ORDER3",
                aggressor_side="buy",
            ),
        ]

        expected_result = OrderResult(
            order_id=order.order_id,
            status="filled",
            fills=trades,
            remaining_quantity=0,
        )
        mock_exchange.submit_order.return_value = expected_result

        # When - Submit order
        result = service.submit_order_to_exchange(order)

        # Then - All fills included
        assert result.status == "filled"
        assert len(result.fills) == 3
        assert sum(trade.quantity for trade in result.fills) == 100

    @pytest.mark.parametrize(
        "status,expected_ack",
        [
            ("new", True),
            ("partially_filled", True),
            ("filled", True),
            ("rejected", False),
            ("error", False),
        ],
    )
    def test_order_acknowledgment_logic(
        self, service, mock_exchange, sample_order, status, expected_ack
    ):
        """Test which order statuses should trigger acknowledgments.

        This helps thread controllers decide when to send WebSocket ACKs.
        """
        # Given - Order with specific status
        result = OrderResult(
            order_id=sample_order.order_id,
            status=status,
            fills=[],
            remaining_quantity=sample_order.quantity
            if status != "filled"
            else 0,
        )
        mock_exchange.submit_order.return_value = result

        # When - Submit order
        actual_result = service.submit_order_to_exchange(sample_order)

        # Then - Status determines ACK eligibility
        assert actual_result.status == status
        # Thread controller would check:
        # should_send_ack = actual_result.status in ["new", "partially_filled", "filled"]
        assert (
            actual_result.status in ["new", "partially_filled", "filled"]
        ) == expected_ack
