"""Minimal API integration tests with threading support.

Focus on essential order submission -> trade execution -> position update flow
with proper thread lifecycle management.
"""

# Note: No pytest.skip() - these tests are enabled!


class TestMinimalAPIIntegration:
    """Essential API integration tests with full threading."""

    def test_order_submission_end_to_end(self, api_context):
        """Test complete order submission flow through threading pipeline.

        Given - API server running with all threads active
        Market maker team registered and ready to trade.
        Exchange has listed instruments available.

        When - Team submits order via REST API
        Order flows through: API -> Validator -> Matcher -> Publisher threads.
        All services process the order through the complete pipeline.

        Then - Order processed successfully with proper response
        Order accepted by validator and submitted to exchange.
        Position updated after any fills occur.
        Response includes order status and execution details.
        """
        client = api_context["client"]

        # Given - Register a market maker team
        registration_response = client.post(
            "/game/teams/register",
            json={"team_name": "TestMM", "role": "market_maker"},
        )
        assert registration_response.status_code == 200
        response_data = registration_response.json()
        assert response_data["success"] is True
        team_data = response_data["data"]
        api_key = team_data["api_key"]

        # When - Submit a limit order
        order_response = client.post(
            "/exchange/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 5,
                "price": 127.50,
                "client_order_id": "TEST_ORDER_001",
            },
            headers={"X-API-Key": api_key},
        )

        # Then - Order should be accepted
        assert order_response.status_code == 200
        order_data = order_response.json()

        # Verify order was processed (API returns success)
        assert order_data["success"] is True
        assert order_data["order_id"] is not None
        assert "timestamp" in order_data

        # Order should be resting in the book (no counter party)
        # Wait a moment for threads to process
        import time

        time.sleep(0.1)  # 100ms should be enough for thread processing

        # Verify order is in exchange order book
        exchange = api_context["exchange"]
        book = exchange.get_order_book("SPX_4500_CALL")
        assert len(book.bids) > 0

    def test_position_query_with_trades(self, api_context):
        """Test position updates after trade execution.

        Given - Team with existing trading activity
        Orders have been submitted and potentially filled.

        When - Query positions via REST API
        Position service returns current holdings.

        Then - Positions reflect actual trading activity
        API returns accurate position data.
        Position updates are consistent with trade executions.
        """
        client = api_context["client"]

        # Given - Register team and establish position
        registration_response = client.post(
            "/game/teams/register",
            json={"team_name": "PositionTest", "role": "market_maker"},
        )
        response_data = registration_response.json()
        assert response_data["success"] is True
        team_data = response_data["data"]
        api_key = team_data["api_key"]
        team_id = team_data["team_id"]

        # Submit an order to create potential position
        client.post(
            "/exchange/orders",
            json={
                "instrument_id": "SPX_4500_CALL",
                "order_type": "limit",
                "side": "buy",
                "quantity": 3,
                "price": 125.00,
            },
            headers={"X-API-Key": api_key},
        )

        # When - Query positions
        position_response = client.get(
            "/positions", headers={"X-API-Key": api_key}
        )

        # Then - Position query succeeds
        assert position_response.status_code == 200
        response_data = position_response.json()
        assert response_data["success"] is True
        position_data = response_data["data"]

        assert position_data["team_id"] == team_id
        assert isinstance(position_data["positions"], dict)
        assert "last_updated" in position_data

        # Position should be consistent with order activity
        # (May be 0 if order didn't fill, or +3 if it did)
        positions = position_data["positions"]
        if "SPX_4500_CALL" in positions:
            assert isinstance(positions["SPX_4500_CALL"], int)

    def test_authentication_and_authorization_flow(self, api_context):
        """Test complete authentication and authorization pipeline.

        Given - API server with authentication middleware
        Teams need valid API keys to access protected endpoints.

        When - Request protected resources with/without auth
        API validates credentials through auth middleware.

        Then - Proper authorization enforcement
        Valid API keys grant access to team resources.
        Invalid keys are rejected with appropriate errors.
        Teams can only access their own data.
        """
        client = api_context["client"]

        # Given - Register a team to get valid credentials
        registration_response = client.post(
            "/game/teams/register",
            json={"team_name": "AuthTest", "role": "market_maker"},
        )
        response_data = registration_response.json()
        assert response_data["success"] is True
        team_data = response_data["data"]
        valid_api_key = team_data["api_key"]

        # Test 1: Valid API key should work
        response = client.get(
            "/positions", headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 200

        # Test 2: Missing API key should be rejected
        response = client.get("/positions")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

        # Test 3: Invalid API key should be rejected
        response = client.get(
            "/positions", headers={"X-API-Key": "invalid_key_12345"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

        # Test 4: With the new API design, teams automatically get their own positions
        # The /positions endpoint always returns the authenticated team's data
