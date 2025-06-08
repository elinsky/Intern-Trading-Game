"""Service-level integration tests for complete order lifecycle.

Tests the integration between services without threading complexity.
Focuses on the core business flow: validation -> matching -> position updates.
"""

from datetime import datetime

from intern_trading_game.domain.exchange.order import (
    Order,
    OrderSide,
    OrderType,
)
from intern_trading_game.infrastructure.api.models import TeamInfo


class TestOrderLifecycleIntegration:
    """Test complete order processing flow through all services."""

    def test_successful_order_validation_to_matching(self, service_context):
        """Test order flows from validation through matching successfully.

        Given - A market maker with clean position state
        The MM has no existing positions or pending orders.
        They have standard ±50 position limits configured.
        The exchange has liquid instruments available.

        When - They submit a valid limit order
        The order meets all validation constraints.
        The exchange can accept the order for matching.

        Then - Order flows through validation to matching successfully
        ValidationService accepts the order.
        MatchingService submits to exchange successfully.
        No errors occur in the integration boundary.
        """
        # Given - Clean market maker setup
        team = TeamInfo(
            team_id="MM_TEST_001",
            team_name="Test Market Maker",
            role="market_maker",
            api_key="test_key_123",
            created_at=datetime.now(),
        )

        # Create order that should pass validation
        order = Order(
            trader_id=team.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=10,
            price=127.50,
        )

        # When - Validate the order
        validation_result = service_context[
            "validation_service"
        ].validate_new_order(order, team)

        # Then - Validation should pass
        assert validation_result.status == "accepted"
        assert validation_result.error_code is None
        assert validation_result.error_message is None

        # When - Submit to matching service
        matching_result = service_context[
            "matching_service"
        ].submit_order_to_exchange(order)

        # Then - Matching should accept
        assert matching_result.status == "new"
        assert matching_result.order_id == order.order_id
        assert matching_result.fills == []  # No immediate fills

        # Verify order is in exchange
        exchange = service_context["exchange"]
        book = exchange.get_order_book("SPX_4500_CALL")
        assert len(book.bids) == 1
        assert book.best_bid() == (127.50, 10)

    def test_position_limit_validation_blocks_matching(self, service_context):
        """Test validation properly blocks orders that exceed position limits.

        Given - Market maker at position limit boundary
        MM already has 45 long position in SPX_4500_CALL.
        Their ±50 position limit allows only 5 more contracts.

        When - They attempt to buy 10 contracts (would exceed limit)
        This would result in 55 long position, violating constraints.

        Then - Validation rejects, order never reaches matching
        ValidationService returns rejected status.
        MatchingService never sees the order.
        Position management maintains integrity.
        """
        # Given - Market maker with position near limit
        team = TeamInfo(
            team_id="MM_TEST_002",
            team_name="Near Limit MM",
            role="market_maker",
            api_key="test_key_456",
            created_at=datetime.now(),
        )

        # Set up existing position near limit
        positions = service_context["positions"]
        positions[team.team_id] = {"SPX_4500_CALL": 45}

        # Create order that would exceed limit
        order = Order(
            trader_id=team.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=10,  # 45 + 10 = 55 > 50 limit
            price=128.00,
        )

        # When - Validate the order
        validation_result = service_context[
            "validation_service"
        ].validate_new_order(order, team)

        # Then - Validation should reject
        assert validation_result.status == "rejected"
        assert validation_result.error_code == "MM_POS_LIMIT"
        assert "Position exceeds ±50" in validation_result.error_message

        # Verify order never reached exchange
        exchange = service_context["exchange"]
        book = exchange.get_order_book("SPX_4500_CALL")
        assert len(book.bids) == 0  # No orders in book

    def test_order_matching_to_trade_processing_integration(
        self, service_context
    ):
        """Test order matching integrates with trade processing and fees.

        Given - Market maker placing order that executes immediately
        MM submits a market buy order that hits existing liquidity.
        Exchange generates a trade result with fills.

        When - TradeProcessingService processes the result
        Service calculates fees based on liquidity type and role.
        Position updated based on filled quantity.

        Then - Complete trade processing occurs
        Order shows filled status with correct price.
        Position updated correctly for the trader.
        Fees calculated per role (market taker fee).
        """
        # Given - Market maker team (buyer) and counterparty (seller)
        mm_buyer = TeamInfo(
            team_id="MM_BUYER",
            team_name="Buyer MM",
            role="market_maker",
            api_key="buyer_key",
            created_at=datetime.now(),
        )

        # Initialize positions for both counterparties
        positions = service_context["positions"]
        positions[mm_buyer.team_id] = {}
        positions["MM_SELLER"] = {}  # Initialize seller position

        # Create order for testing
        buy_order = Order(
            trader_id=mm_buyer.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=5,
        )

        # When - Simulate a filled order result (would come from exchange)
        # Create a Trade object to simulate a fill
        from intern_trading_game.domain.exchange.order_result import (
            OrderResult,
        )
        from intern_trading_game.domain.exchange.trade import Trade

        trade = Trade(
            instrument_id="SPX_4500_CALL",
            buyer_id=mm_buyer.team_id,
            seller_id="MM_SELLER",  # Use actual seller ID for counterparty testing
            buyer_order_id=buy_order.order_id,
            seller_order_id="OTHER_ORDER_ID",
            quantity=5,
            price=128.50,
            aggressor_side="buy",  # Buy order was the aggressor
        )

        filled_result = OrderResult(
            order_id=buy_order.order_id,
            status="filled",
            fills=[trade],
            remaining_quantity=0,
        )

        # Process the trade through TradeProcessingService
        response = service_context["trade_service"].process_trade_result(
            filled_result, buy_order, mm_buyer
        )

        # Then - Verify trade processing results
        assert response.status == "filled"
        assert response.filled_quantity == 5
        assert response.average_price == 128.50

        # Verify positions updated correctly for both counterparties
        assert positions[mm_buyer.team_id]["SPX_4500_CALL"] == 5  # Buyer: +5
        assert positions["MM_SELLER"]["SPX_4500_CALL"] == -5  # Seller: -5

        # Verify position conservation (no contracts created/destroyed)
        total_position = (
            positions[mm_buyer.team_id]["SPX_4500_CALL"]
            + positions["MM_SELLER"]["SPX_4500_CALL"]
        )
        assert total_position == 0

        # Verify fees were calculated
        assert response.fees is not None
        assert (
            response.liquidity_type == "taker"
        )  # Market order takes liquidity

        # Market maker taking liquidity should pay taker fee
        expected_taker_fee = -0.05 * 5  # -$0.25
        assert response.fees == expected_taker_fee

    def test_websocket_message_generation_integration(self, service_context):
        """Test WebSocket message generation without actual WebSocket threading.

        Given - Trade processing service with WebSocket queue
        TradeProcessingService will process a trade with fills.
        WebSocket queue should receive execution reports.

        When - TradeProcessingService processes trade with fills
        Service generates execution reports for each fill.

        Then - Proper messages queued for WebSocket delivery
        Messages contain correct trade information.
        Team-specific routing information included.
        Message format matches WebSocket expectations.
        """
        # Given - Team and trade setup
        team = TeamInfo(
            team_id="MM_WEBSOCKET",
            team_name="WebSocket Test MM",
            role="market_maker",
            api_key="ws_test_key",
            created_at=datetime.now(),
        )

        # Create order
        order = Order(
            trader_id=team.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=3,
            price=127.75,
        )

        # Create a filled result with trade
        from intern_trading_game.domain.exchange.order_result import (
            OrderResult,
        )
        from intern_trading_game.domain.exchange.trade import Trade

        trade = Trade(
            instrument_id="SPX_4500_CALL",
            buyer_id=team.team_id,
            seller_id="OTHER_TRADER",
            buyer_order_id=order.order_id,
            seller_order_id="OTHER_ORDER",
            quantity=3,
            price=127.75,
            aggressor_side="buy",
        )

        filled_result = OrderResult(
            order_id=order.order_id,
            status="filled",
            fills=[trade],
            remaining_quantity=0,
        )

        # Clear any existing messages in queue
        websocket_queue = service_context["trade_service"].websocket_queue
        while not websocket_queue.empty():
            websocket_queue.get()

        # When - Process through trade service
        service_context["trade_service"].process_trade_result(
            filled_result, order, team
        )

        # Then - WebSocket message should be queued
        assert not websocket_queue.empty()

        # Verify message content
        msg_type, team_id, data = websocket_queue.get()
        assert msg_type == "execution_report"
        assert team_id == team.team_id
        # The data contains the trade object and related info
        assert "trade" in data
        assert data["trade"] == trade

    def test_cancellation_service_integration(self, service_context):
        """Test order cancellation flows through validation service.

        Given - Market maker with resting order
        MM has placed a limit order that's sitting in the book.
        Order hasn't been filled yet.

        When - MM requests cancellation
        ValidationService processes the cancel request.
        Ownership verification occurs.

        Then - Cancellation processed correctly
        ValidationService verifies ownership.
        Exchange removes order from book.
        Appropriate success/failure response generated.
        """
        # Given - Market maker with resting order
        team = TeamInfo(
            team_id="MM_CANCEL_TEST",
            team_name="Cancel Test MM",
            role="market_maker",
            api_key="cancel_key",
            created_at=datetime.now(),
        )

        # Place order first
        order = Order(
            trader_id=team.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=8,
            price=127.25,
        )

        # Submit to exchange
        result = service_context["matching_service"].submit_order_to_exchange(
            order
        )
        assert result.status == "new"

        # Verify order in book
        exchange = service_context["exchange"]
        book = exchange.get_order_book("SPX_4500_CALL")
        assert len(book.bids) == 1

        # When - Request cancellation
        success, reason = service_context[
            "validation_service"
        ].validate_cancellation(order.order_id, team.team_id)

        # Then - Cancellation should succeed
        assert success is True
        assert reason is None

        # Verify order removed from book
        book = exchange.get_order_book("SPX_4500_CALL")
        assert len(book.bids) == 0

    def test_unauthorized_cancellation_blocked(self, service_context):
        """Test cancellation blocked for orders owned by other teams.

        Given - Two market makers, one with resting order
        MM1 has placed an order.
        MM2 attempts to cancel MM1's order.

        When - MM2 requests cancellation of MM1's order
        ValidationService catches the ownership exception.

        Then - Cancellation rejected due to ownership
        ValidationService returns failure with error message.
        Exchange order remains untouched.
        Clear error message about ownership.
        """
        # Given - Two market makers
        mm1 = TeamInfo(
            team_id="MM_OWNER",
            team_name="Order Owner",
            role="market_maker",
            api_key="owner_key",
            created_at=datetime.now(),
        )

        mm2 = TeamInfo(
            team_id="MM_ATTACKER",
            team_name="Unauthorized Team",
            role="market_maker",
            api_key="attacker_key",
            created_at=datetime.now(),
        )

        # MM1 places order
        order = Order(
            trader_id=mm1.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=12,
            price=129.00,
        )

        service_context["matching_service"].submit_order_to_exchange(order)

        # When - MM2 tries to cancel MM1's order
        # Note: The ValidationService should catch the ValueError from exchange
        success, reason = service_context[
            "validation_service"
        ].validate_cancellation(order.order_id, mm2.team_id)

        # Then - Should be rejected
        assert success is False
        assert "does not own" in reason

        # Verify order still in book
        exchange = service_context["exchange"]
        book = exchange.get_order_book("SPX_4500_CALL")
        assert len(book.asks) == 1
