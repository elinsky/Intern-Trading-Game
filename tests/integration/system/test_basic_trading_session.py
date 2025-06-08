"""System-level integration test for complete trading session.

Tests the entire system end-to-end with minimal scenario:
Two market makers trade one contract through the complete pipeline.
"""


class TestBasicTradingSession:
    """System-level test proving complete trading system functionality."""

    def test_minimal_trading_session(self, api_context):
        """Test complete trading session: Two market makers trade one contract.

        Given - Clean trading system with two market maker teams
        System has all threads running and exchange ready.
        Teams are registered and authenticated with API keys.

        When - Market makers engage in basic trading activity
        MM1 posts a resting sell order providing liquidity.
        MM2 submits a buy order that crosses and executes.
        Complete trade lifecycle occurs through all system components.

        Then - Trade executed successfully with proper settlement
        Orders flow through: API -> Validator -> Matcher -> Publisher.
        Trade occurs at expected price with correct quantities.
        Positions updated for both counterparties (+1/-1).
        Fees calculated correctly (maker rebate vs taker fee).
        Both teams can query their updated positions via API.
        """
        client = api_context["client"]

        # Given - Register two market maker teams
        mm1_response = client.post(
            "/auth/register",
            json={"team_name": "MarketMaker1", "role": "market_maker"},
        )
        assert mm1_response.status_code == 200
        mm1_data = mm1_response.json()
        mm1_api_key = mm1_data["api_key"]
        mm1_team_id = mm1_data["team_id"]

        mm2_response = client.post(
            "/auth/register",
            json={"team_name": "MarketMaker2", "role": "market_maker"},
        )
        assert mm2_response.status_code == 200
        mm2_data = mm2_response.json()
        mm2_api_key = mm2_data["api_key"]
        mm2_team_id = mm2_data["team_id"]

        # Verify both teams start with zero positions
        mm1_positions = client.get(
            f"/positions/{mm1_team_id}", headers={"X-API-Key": mm1_api_key}
        ).json()
        mm2_positions = client.get(
            f"/positions/{mm2_team_id}", headers={"X-API-Key": mm2_api_key}
        ).json()

        assert mm1_positions["positions"] == {}
        assert mm2_positions["positions"] == {}

        # When - MM1 posts resting sell order (provides liquidity)
        mm1_sell_response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "sell",
                "quantity": 1,
                "price": 128.50,
                "client_order_id": "MM1_SELL_001",
            },
            headers={"X-API-Key": mm1_api_key},
        )

        assert mm1_sell_response.status_code == 200
        mm1_order_data = mm1_sell_response.json()
        assert mm1_order_data["status"] in ["new", "accepted"]  # Resting order

        # Verify order is in the book
        exchange = api_context["exchange"]
        book = exchange.get_order_book("SPX_4500_CALL")
        assert len(book.asks) == 1
        assert book.best_ask() == (128.50, 1)

        # When - MM2 submits crossing buy order (takes liquidity)
        mm2_buy_response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 1,
                "price": 128.50,  # Crosses the spread
                "client_order_id": "MM2_BUY_001",
            },
            headers={"X-API-Key": mm2_api_key},
        )

        assert mm2_buy_response.status_code == 200
        mm2_order_data = mm2_buy_response.json()

        # Then - Trade should have occurred
        assert mm2_order_data["status"] == "filled"
        assert mm2_order_data["filled_quantity"] == 1
        assert mm2_order_data["average_price"] == 128.50

        # Verify fees were calculated
        assert "fees" in mm2_order_data
        assert "liquidity_type" in mm2_order_data
        assert mm2_order_data["liquidity_type"] == "taker"

        # MM2 should pay taker fee
        expected_taker_fee = -0.05 * 1  # -$0.05
        assert mm2_order_data["fees"] == expected_taker_fee

        # Verify order book is now empty (orders matched)
        book = exchange.get_order_book("SPX_4500_CALL")
        assert len(book.asks) == 0
        assert len(book.bids) == 0

        # Verify positions were updated correctly for both counterparties
        mm1_final_positions = client.get(
            f"/positions/{mm1_team_id}", headers={"X-API-Key": mm1_api_key}
        ).json()
        mm2_final_positions = client.get(
            f"/positions/{mm2_team_id}", headers={"X-API-Key": mm2_api_key}
        ).json()

        # MM1 sold 1 contract (short position) - counterparty update
        assert mm1_final_positions["positions"]["SPX_4500_CALL"] == -1

        # MM2 bought 1 contract (long position) - aggressor update
        assert mm2_final_positions["positions"]["SPX_4500_CALL"] == 1

        # Verify system consistency: positions sum to zero (conservation of contracts)
        total_position = (
            mm1_final_positions["positions"]["SPX_4500_CALL"]
            + mm2_final_positions["positions"]["SPX_4500_CALL"]
        )
        assert total_position == 0  # No contracts created or destroyed

    def test_system_health_and_thread_status(self, api_context):
        """Test system health verification and thread monitoring.

        Given - Trading system running with all components
        API server, exchange, validation, matching, and publishing threads.

        When - Query system health endpoint
        Health check reports on all system components.

        Then - All threads operational and system ready
        Health endpoint returns 200 OK.
        All critical threads report as alive and running.
        System ready to process trading requests.
        """
        client = api_context["client"]

        # When - Check system health
        health_response = client.get("/")

        # Then - System should be healthy
        assert health_response.status_code == 200
        health_data = health_response.json()

        assert health_data["status"] == "ok"
        assert "service" in health_data
        assert "threads" in health_data

        # Verify all critical threads are running
        threads = health_data["threads"]
        assert threads["validator"] is True
        assert threads["matching"] is True
        assert threads["publisher"] is True
        assert threads["websocket"] is True

    def test_system_error_handling_and_recovery(self, api_context):
        """Test system handles errors gracefully without crashing.

        Given - Trading system under normal operation
        All components functioning correctly.

        When - Invalid requests submitted to various endpoints
        Malformed orders, unauthorized access, invalid instruments.

        Then - System handles errors gracefully
        Appropriate error responses returned.
        System remains stable and continues processing.
        No thread crashes or system failures.
        """
        client = api_context["client"]

        # Register valid team for comparison
        team_response = client.post(
            "/auth/register",
            json={"team_name": "ErrorTest", "role": "market_maker"},
        )
        team_data = team_response.json()
        api_key = team_data["api_key"]
        team_id = team_data["team_id"]

        # Test 1: Invalid instrument causes business validation rejection
        # Business rule violations return HTTP 200 with rejected order
        response = client.post(
            "/orders",
            json={
                "instrument_id": "INVALID_INSTRUMENT",
                "order_type": "limit",
                "side": "buy",
                "quantity": 1,
                "price": 100.0,
            },
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200  # API call succeeds
        order_data = response.json()
        assert (
            order_data["status"] == "rejected"
        )  # Business rule validation failed
        assert order_data["error_code"] == "INVALID_INSTRUMENT"
        assert "not in allowed list" in order_data["error_message"]
        # Note: Trading bot also receives new_order_reject via WebSocket

        # Test 2: Malformed order should be rejected
        response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 1,
                # Missing required price for limit order
            },
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 400
        assert "Price required for limit orders" in response.json()["detail"]

        # Test 3: Unauthorized access should be rejected
        response = client.get(f"/positions/{team_id}")  # No API key
        assert response.status_code == 401

        # Test 4: System should still be healthy after errors
        health_response = client.get("/")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "ok"

        # Test 5: Valid requests should still work
        valid_response = client.post(
            "/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 1,
                "price": 125.0,
            },
            headers={"X-API-Key": api_key},
        )
        assert valid_response.status_code == 200
        assert valid_response.json()["status"] in ["new", "accepted", "filled"]
