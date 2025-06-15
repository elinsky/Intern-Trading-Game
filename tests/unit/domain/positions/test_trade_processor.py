"""Unit tests for TradeProcessingService."""

from datetime import datetime
from queue import Queue
from unittest.mock import call, create_autospec

import pytest

from intern_trading_game.domain.exchange.core.order import (
    Order,
    OrderSide,
    OrderType,
)
from intern_trading_game.domain.exchange.core.trade import Trade
from intern_trading_game.domain.exchange.order_result import OrderResult
from intern_trading_game.domain.positions import (
    PositionManagementService,
    TradeProcessingService,
    TradingFeeService,
)
from intern_trading_game.infrastructure.api.models import TeamInfo


class TestTradeProcessingService:
    """Test suite for TradeProcessingService."""

    @pytest.fixture
    def mock_fee_service(self):
        """Create a mock TradingFeeService."""
        return create_autospec(TradingFeeService, instance=True)

    @pytest.fixture
    def mock_position_service(self):
        """Create a mock PositionManagementService."""
        return create_autospec(PositionManagementService, instance=True)

    @pytest.fixture
    def websocket_queue(self):
        """Create a test queue for WebSocket messages."""
        return Queue()

    @pytest.fixture
    def service(
        self, mock_fee_service, mock_position_service, websocket_queue
    ):
        """Create a TradeProcessingService instance with mocks."""
        return TradeProcessingService(
            fee_service=mock_fee_service,
            position_service=mock_position_service,
            websocket_queue=websocket_queue,
        )

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
            client_order_id="MY_ORDER_1",
        )

    @pytest.fixture
    def sample_team(self):
        """Create a sample team info for testing."""
        return TeamInfo(
            team_id="TEAM001",
            team_name="Test Team",
            role="market_maker",
            api_key="test-api-key",
            created_at=datetime.now(),
        )

    @pytest.fixture
    def sample_trade(self):
        """Create a sample trade for testing."""
        return Trade(
            instrument_id="SPX-20240315-4500C",
            buyer_id="TEAM001",
            seller_id="TEAM002",
            price=125.50,
            quantity=50,
            buyer_order_id="ORD123",
            seller_order_id="ORD456",
            aggressor_side="buy",
        )

    def test_process_trade_result_no_fills(
        self, service, sample_order, sample_team
    ):
        """Test processing result with no fills (rejected or resting order).

        Given - Order with no fills
        When - Processing trade result
        Then - Response shows no fills, no fees, no position update
        """
        # Given - Order result with no fills
        result = OrderResult(
            order_id=sample_order.order_id,
            status="new",
            fills=[],
            remaining_quantity=sample_order.quantity,
        )

        # When - Process the result
        response = service.process_trade_result(
            result, sample_order, sample_team
        )

        # Then - Response reflects no activity
        assert response.order_id == sample_order.order_id
        assert response.status == "new"
        assert response.filled_quantity == 0
        assert response.average_price is None
        assert response.fees == 0.0
        assert response.liquidity_type is None

        # No position update should occur
        service.position_service.update_position.assert_not_called()

        # No WebSocket messages sent
        assert service.websocket_queue.empty()

    def test_process_trade_result_single_fill_as_taker(
        self,
        service,
        sample_order,
        sample_team,
        sample_trade,
        mock_fee_service,
        mock_position_service,
        websocket_queue,
    ):
        """Test processing single fill where order was the taker.

        Given - Fully filled order as taker
        When - Processing trade result
        Then - Fees charged, position updated, execution report sent
        """
        # Given - Configure mocks
        mock_fee_service.determine_liquidity_type.return_value = "taker"
        mock_fee_service.calculate_fee.return_value = -5.00  # $5 fee

        result = OrderResult(
            order_id=sample_order.order_id,
            status="filled",
            fills=[sample_trade],
            remaining_quantity=0,
        )

        # When - Process the result
        response = service.process_trade_result(
            result, sample_order, sample_team
        )

        # Then - Response shows complete fill
        assert response.order_id == sample_order.order_id
        assert response.status == "filled"
        assert response.filled_quantity == 50
        assert response.average_price == 125.50
        assert response.fees == -5.00  # Negative = fee paid
        assert response.liquidity_type == "taker"

        # Verify fee calculation
        mock_fee_service.determine_liquidity_type.assert_called_once_with(
            "buy",
            "buy",  # aggressor_side, order_side
        )
        mock_fee_service.calculate_fee.assert_called_once_with(
            50, "market_maker", "taker"
        )

        # Verify position update
        mock_position_service.update_position.assert_called_once_with(
            "TEAM001",
            "SPX-20240315-4500C",
            50,  # Buy increases position
        )

        # Verify WebSocket message
        assert websocket_queue.qsize() == 1
        msg_type, team_id, data = websocket_queue.get()
        assert msg_type == "execution_report"
        assert team_id == "TEAM001"
        assert data["trade"] == sample_trade
        assert data["liquidity_type"] == "taker"
        assert data["fees"] == -5.00

    def test_process_trade_result_single_fill_as_maker(
        self,
        service,
        sample_order,
        sample_team,
        sample_trade,
        mock_fee_service,
    ):
        """Test processing single fill where order was the maker.

        Given - Market maker order filled as maker
        When - Processing trade result
        Then - Rebate received
        """
        # Given - Order was maker (not aggressor)
        mock_fee_service.determine_liquidity_type.return_value = "maker"
        mock_fee_service.calculate_fee.return_value = 1.00  # $1 rebate

        result = OrderResult(
            order_id=sample_order.order_id,
            status="filled",
            fills=[sample_trade],
            remaining_quantity=0,
        )

        # When - Process the result
        response = service.process_trade_result(
            result, sample_order, sample_team
        )

        # Then - Response shows rebate
        assert response.fees == 1.00  # Positive = rebate received
        assert response.liquidity_type == "maker"

    def test_process_trade_result_multiple_fills_same_liquidity(
        self, service, sample_order, sample_team, mock_fee_service
    ):
        """Test processing multiple fills with same liquidity type.

        Given - Order filled by multiple counterparties, all as taker
        When - Processing trade result
        Then - Fees aggregated, average price calculated correctly
        """
        # Given - Two trades at different prices
        trade1 = Trade(
            instrument_id="SPX-20240315-4500C",
            buyer_id="TEAM001",
            seller_id="TEAM002",
            price=125.40,
            quantity=30,
            buyer_order_id="ORD123",
            seller_order_id="ORD456",
            aggressor_side="buy",
        )
        trade2 = Trade(
            instrument_id="SPX-20240315-4500C",
            buyer_id="TEAM001",
            seller_id="TEAM003",
            price=125.60,
            quantity=70,
            buyer_order_id="ORD123",
            seller_order_id="ORD789",
            aggressor_side="buy",
        )

        mock_fee_service.determine_liquidity_type.return_value = "taker"
        mock_fee_service.calculate_fee.side_effect = [-1.50, -3.50]  # Fees

        result = OrderResult(
            order_id=sample_order.order_id,
            status="filled",
            fills=[trade1, trade2],
            remaining_quantity=0,
        )

        # When - Process the result
        response = service.process_trade_result(
            result, sample_order, sample_team
        )

        # Then - Aggregated results
        assert response.filled_quantity == 100  # 30 + 70
        assert response.fees == -5.00  # -1.50 + -3.50
        assert response.liquidity_type == "taker"

        # Average price calculation: (30*125.40 + 70*125.60) / 100
        expected_avg = (30 * 125.40 + 70 * 125.60) / 100
        assert response.average_price == pytest.approx(expected_avg)

    def test_process_trade_result_mixed_liquidity(
        self, service, sample_order, sample_team, mock_fee_service
    ):
        """Test processing fills with mixed liquidity types.

        Given - Some fills as maker, others as taker
        When - Processing trade result
        Then - Liquidity type is "mixed"
        """
        # Given - Two trades with different liquidity
        trades = [
            Trade(
                instrument_id="SPX-20240315-4500C",
                buyer_id="TEAM001",
                seller_id="TEAM002",
                price=125.50,
                quantity=50,
                buyer_order_id="ORD123",
                seller_order_id="ORD456",
                aggressor_side="sell",  # Order is maker
            ),
            Trade(
                instrument_id="SPX-20240315-4500C",
                buyer_id="TEAM001",
                seller_id="TEAM003",
                price=125.50,
                quantity=50,
                buyer_order_id="ORD123",
                seller_order_id="ORD789",
                aggressor_side="buy",  # Order is taker
            ),
        ]

        mock_fee_service.determine_liquidity_type.side_effect = [
            "maker",
            "taker",
        ]
        mock_fee_service.calculate_fee.side_effect = [1.00, -2.50]

        result = OrderResult(
            order_id=sample_order.order_id,
            status="filled",
            fills=trades,
            remaining_quantity=0,
        )

        # When - Process the result
        response = service.process_trade_result(
            result, sample_order, sample_team
        )

        # Then - Mixed liquidity type
        assert response.liquidity_type == "mixed"
        assert response.fees == -1.50  # 1.00 - 2.50

    def test_process_trade_result_partial_fill(
        self,
        service,
        sample_order,
        sample_team,
        sample_trade,
        mock_fee_service,
    ):
        """Test processing partially filled order.

        Given - Order partially filled
        When - Processing trade result
        Then - Status remains partially_filled
        """
        # Given - Partial fill
        mock_fee_service.determine_liquidity_type.return_value = "taker"
        mock_fee_service.calculate_fee.return_value = -2.50

        result = OrderResult(
            order_id=sample_order.order_id,
            status="partially_filled",
            fills=[sample_trade],  # 50 out of 100
            remaining_quantity=50,
        )

        # When - Process the result
        response = service.process_trade_result(
            result, sample_order, sample_team
        )

        # Then - Status preserved
        assert response.status == "partially_filled"
        assert response.filled_quantity == 50

    def test_process_sell_order_position_update(
        self, service, sample_team, mock_position_service, mock_fee_service
    ):
        """Test that sell orders decrease position.

        Given - Sell order that fills
        When - Processing trade result
        Then - Position decreases
        """
        # Given - Sell order
        mock_fee_service.determine_liquidity_type.return_value = "maker"
        mock_fee_service.calculate_fee.return_value = 1.00

        sell_order = Order(
            instrument_id="SPX-20240315-4500C",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.LIMIT,
            price=125.50,
            trader_id="TEAM001",
        )

        trade = Trade(
            instrument_id="SPX-20240315-4500C",
            buyer_id="TEAM002",
            seller_id="TEAM001",
            price=125.50,
            quantity=50,
            buyer_order_id="ORD456",
            seller_order_id=sell_order.order_id,
            aggressor_side="buy",
        )

        result = OrderResult(
            order_id=sell_order.order_id,
            status="filled",
            fills=[trade],
            remaining_quantity=0,
        )

        # When - Process the result
        service.process_trade_result(result, sell_order, sample_team)

        # Then - Positions updated for both counterparties
        # Now expect two calls: one for aggressor, one for counterparty
        expected_calls = [
            call(
                "TEAM001", "SPX-20240315-4500C", -50
            ),  # Seller (aggressor): -50
            call(
                "TEAM002", "SPX-20240315-4500C", 50
            ),  # Buyer (counterparty): +50
        ]
        mock_position_service.update_position.assert_has_calls(
            expected_calls, any_order=False
        )

    def test_websocket_messages_for_multiple_fills(
        self,
        service,
        sample_order,
        sample_team,
        websocket_queue,
        mock_fee_service,
    ):
        """Test that each fill generates a separate WebSocket message.

        Given - Order with multiple fills
        When - Processing trade result
        Then - Each fill gets its own execution report
        """
        # Given - Three fills
        mock_fee_service.determine_liquidity_type.return_value = "taker"
        mock_fee_service.calculate_fee.side_effect = [-1.50, -1.75, -2.00]

        trades = []
        for i in range(3):
            trades.append(
                Trade(
                    instrument_id="SPX-20240315-4500C",
                    buyer_id="TEAM001",
                    seller_id=f"TEAM00{i+2}",
                    price=125.50 + i * 0.10,
                    quantity=30 + i * 5,
                    buyer_order_id="ORD123",
                    seller_order_id=f"ORD{i+456}",
                    aggressor_side="buy",
                )
            )

        result = OrderResult(
            order_id=sample_order.order_id,
            status="filled",
            fills=trades,
            remaining_quantity=0,
        )

        # When - Process the result
        service.process_trade_result(result, sample_order, sample_team)

        # Then - Three WebSocket messages sent
        assert websocket_queue.qsize() == 3

        # Verify each message
        for i in range(3):
            msg_type, team_id, data = websocket_queue.get()
            assert msg_type == "execution_report"
            assert team_id == "TEAM001"
            assert data["trade"] == trades[i]

    def test_client_order_id_included_when_applicable(
        self,
        service,
        sample_order,
        sample_team,
        websocket_queue,
        mock_fee_service,
    ):
        """Test client_order_id is included in execution report when order matches.

        Given - Trade where our order is the buyer
        When - Creating execution report
        Then - client_order_id is included
        """
        # Given - Trade where our order is buyer
        mock_fee_service.determine_liquidity_type.return_value = "taker"
        mock_fee_service.calculate_fee.return_value = -2.50

        trade = Trade(
            instrument_id="SPX-20240315-4500C",
            buyer_id="TEAM001",
            seller_id="TEAM002",
            price=125.50,
            quantity=50,
            buyer_order_id=sample_order.order_id,  # Our order
            seller_order_id="OTHER_ORDER",
            aggressor_side="buy",
        )

        result = OrderResult(
            order_id=sample_order.order_id,
            status="filled",
            fills=[trade],
            remaining_quantity=0,
        )

        # When - Process the result
        service.process_trade_result(result, sample_order, sample_team)

        # Then - client_order_id included
        msg_type, team_id, data = websocket_queue.get()
        assert data["client_order_id"] == "MY_ORDER_1"

    def test_zero_quantity_edge_case(self, service, sample_order, sample_team):
        """Test handling of edge case with zero total quantity.

        Given - Result with empty fills list
        When - Processing
        Then - No errors, sensible defaults
        """
        # Given - No fills
        result = OrderResult(
            order_id=sample_order.order_id,
            status="rejected",
            fills=[],
            remaining_quantity=sample_order.quantity,
        )

        # When - Process the result
        response = service.process_trade_result(
            result, sample_order, sample_team
        )

        # Then - Sensible response
        assert response.filled_quantity == 0
        assert response.average_price is None
        assert response.fees == 0.0
        assert response.liquidity_type is None

    @pytest.mark.parametrize(
        "role,liquidity,expected_fee",
        [
            ("market_maker", "maker", 1.00),  # Rebate
            ("market_maker", "taker", -0.50),  # Small fee
            ("retail", "maker", -0.50),  # Fee even as maker
            ("retail", "taker", -1.50),  # Larger fee
            ("hedge_fund", "maker", 0.50),  # Small rebate
            ("hedge_fund", "taker", -1.00),  # Standard fee
        ],
    )
    def test_role_specific_fees(
        self,
        service,
        sample_order,
        sample_trade,
        mock_fee_service,
        role,
        liquidity,
        expected_fee,
    ):
        """Test fee calculation for different roles and liquidity types."""
        # Given - Team with specific role
        team = TeamInfo(
            team_id="TEAM001",
            team_name="Test Team",
            role=role,
            api_key="test-api-key",
            created_at=datetime.now(),
        )

        mock_fee_service.determine_liquidity_type.return_value = liquidity
        mock_fee_service.calculate_fee.return_value = expected_fee

        result = OrderResult(
            order_id=sample_order.order_id,
            status="filled",
            fills=[sample_trade],
            remaining_quantity=0,
        )

        # When - Process the result
        response = service.process_trade_result(result, sample_order, team)

        # Then - Correct fee applied
        assert response.fees == expected_fee
        mock_fee_service.calculate_fee.assert_called_with(50, role, liquidity)
