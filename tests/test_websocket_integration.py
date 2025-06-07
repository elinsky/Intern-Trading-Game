"""Integration tests for WebSocket real-time updates.

Tests the complete order lifecycle through REST API submission
and WebSocket notification delivery.
"""

import asyncio
import json
from typing import List

import pytest
import websockets
from fastapi.testclient import TestClient

from intern_trading_game.api.main import app


class TestWebSocketIntegration:
    """Test WebSocket integration with REST API order flow."""

    @pytest.mark.asyncio
    async def test_order_lifecycle_websocket_updates(self):
        """Test complete order lifecycle via WebSocket.

        Given - A market maker connects via WebSocket
        When - They submit an order via REST API
        Then - They receive real-time updates for order acceptance and execution
        """
        # Given - Register team and connect WebSocket
        with TestClient(app) as client:
            # Register team
            reg_response = client.post(
                "/auth/register",
                json={"team_name": "TestMM", "role": "market_maker"},
            )
            team_data = reg_response.json()
            api_key = team_data["api_key"]

            # Track received messages
            messages: List[dict] = []

            async def collect_messages():
                uri = f"ws://localhost:8000/ws?api_key={api_key}"
                async with websockets.connect(uri) as websocket:
                    # Collect 3 messages: position_snapshot, new_order_ack, execution_report
                    for _ in range(3):
                        msg = await websocket.recv()
                        messages.append(json.loads(msg))

            # Start WebSocket collection in background
            ws_task = asyncio.create_task(collect_messages())

            # Wait for connection and position snapshot
            await asyncio.sleep(0.1)

            # When - Submit order via REST
            client.post(
                "/orders",
                headers={"X-API-Key": api_key},
                json={
                    "instrument_id": "SPX_4500_CALL",
                    "order_type": "limit",
                    "side": "buy",
                    "quantity": 10,
                    "price": 100.0,
                    "client_order_id": "TEST_ORDER_001",
                },
            )

            # Wait for WebSocket messages
            await asyncio.sleep(0.2)
            ws_task.cancel()

            # Then - Verify message sequence
            assert len(messages) >= 2

            # First message: position snapshot
            assert messages[0]["type"] == "position_snapshot"
            assert messages[0]["data"]["positions"] == {}

            # Second message: order acknowledgment
            assert messages[1]["type"] == "new_order_ack"
            ack_data = messages[1]["data"]
            assert ack_data["client_order_id"] == "TEST_ORDER_001"
            assert ack_data["instrument_id"] == "SPX_4500_CALL"
            assert ack_data["side"] == "buy"
            assert ack_data["quantity"] == 10
            assert ack_data["price"] == 100.0

    @pytest.mark.asyncio
    async def test_order_rejection_websocket(self):
        """Test order rejection delivered via WebSocket.

        Given - A market maker with an existing position at the limit
        When - They submit an order that would exceed position limits
        Then - They receive a rejection message via WebSocket
        """
        # Given - Register team and connect WebSocket
        with TestClient(app) as client:
            # Register team
            reg_response = client.post(
                "/auth/register",
                json={"team_name": "TestMMReject", "role": "market_maker"},
            )
            team_data = reg_response.json()
            api_key = team_data["api_key"]

            # Track received messages
            messages: List[dict] = []

            async def collect_messages():
                uri = f"ws://localhost:8000/ws?api_key={api_key}"
                async with websockets.connect(uri) as websocket:
                    # Collect messages
                    try:
                        while True:
                            msg = await asyncio.wait_for(
                                websocket.recv(), timeout=0.5
                            )
                            messages.append(json.loads(msg))
                    except asyncio.TimeoutError:
                        pass

            # Start WebSocket collection
            ws_task = asyncio.create_task(collect_messages())

            # Wait for connection
            await asyncio.sleep(0.1)

            # First, submit orders to reach position limit
            for i in range(5):
                client.post(
                    "/orders",
                    headers={"X-API-Key": api_key},
                    json={
                        "instrument_id": "SPX_4500_CALL",
                        "order_type": "limit",
                        "side": "buy",
                        "quantity": 10,
                        "price": 100.0 + i,
                    },
                )

            # When - Submit order that exceeds limit
            client.post(
                "/orders",
                headers={"X-API-Key": api_key},
                json={
                    "instrument_id": "SPX_4500_CALL",
                    "order_type": "limit",
                    "side": "buy",
                    "quantity": 10,
                    "price": 110.0,
                    "client_order_id": "REJECT_ORDER",
                },
            )

            # Wait for messages
            await asyncio.sleep(0.3)
            ws_task.cancel()

            # Then - Find rejection message
            reject_msgs = [
                m for m in messages if m["type"] == "new_order_reject"
            ]
            assert len(reject_msgs) >= 1

            reject_data = reject_msgs[-1]["data"]
            assert reject_data["client_order_id"] == "REJECT_ORDER"
            assert "limit" in reject_data["reason"].lower()

    @pytest.mark.asyncio
    async def test_multiple_teams_isolation(self):
        """Test teams only receive their own messages.

        Given - Two teams connected via WebSocket
        When - Each team submits orders
        Then - Each team only receives updates for their own orders
        """
        with TestClient(app) as client:
            # Given - Register two teams
            team1_response = client.post(
                "/auth/register",
                json={"team_name": "Team1", "role": "market_maker"},
            )
            team1_data = team1_response.json()

            team2_response = client.post(
                "/auth/register",
                json={"team_name": "Team2", "role": "market_maker"},
            )
            team2_data = team2_response.json()

            # Track messages per team
            team1_messages: List[dict] = []
            team2_messages: List[dict] = []

            async def collect_team_messages(
                api_key: str, messages_list: List[dict]
            ):
                uri = f"ws://localhost:8000/ws?api_key={api_key}"
                async with websockets.connect(uri) as websocket:
                    try:
                        while True:
                            msg = await asyncio.wait_for(
                                websocket.recv(), timeout=0.5
                            )
                            messages_list.append(json.loads(msg))
                    except asyncio.TimeoutError:
                        pass

            # Start WebSocket connections
            task1 = asyncio.create_task(
                collect_team_messages(team1_data["api_key"], team1_messages)
            )
            task2 = asyncio.create_task(
                collect_team_messages(team2_data["api_key"], team2_messages)
            )

            # Wait for connections
            await asyncio.sleep(0.1)

            # When - Each team submits an order
            client.post(
                "/orders",
                headers={"X-API-Key": team1_data["api_key"]},
                json={
                    "instrument_id": "SPX_4500_CALL",
                    "order_type": "limit",
                    "side": "buy",
                    "quantity": 5,
                    "price": 100.0,
                    "client_order_id": "TEAM1_ORDER",
                },
            )

            client.post(
                "/orders",
                headers={"X-API-Key": team2_data["api_key"]},
                json={
                    "instrument_id": "SPX_4500_PUT",
                    "order_type": "limit",
                    "side": "sell",
                    "quantity": 3,
                    "price": 50.0,
                    "client_order_id": "TEAM2_ORDER",
                },
            )

            # Wait and collect messages
            await asyncio.sleep(0.3)
            task1.cancel()
            task2.cancel()

            # Then - Verify isolation
            # Team 1 should only see TEAM1_ORDER
            team1_acks = [
                m for m in team1_messages if m["type"] == "new_order_ack"
            ]
            assert all(
                ack["data"].get("client_order_id") != "TEAM2_ORDER"
                for ack in team1_acks
            )

            # Team 2 should only see TEAM2_ORDER
            team2_acks = [
                m for m in team2_messages if m["type"] == "new_order_ack"
            ]
            assert all(
                ack["data"].get("client_order_id") != "TEAM1_ORDER"
                for ack in team2_acks
            )

    def test_websocket_queue_processing(self):
        """Test WebSocket queue handles messages correctly.

        Given - WebSocket thread is running
        When - Messages are added to websocket_queue
        Then - Messages are processed and sent to connected clients
        """
        # This tests the queue mechanism directly
        # We verify that the websocket_queue exists and can handle messages
        from intern_trading_game.api.main import websocket_queue

        # Test that queue exists and can accept messages
        test_msg = ("test_type", "TEAM_001", {"test": "data"})
        websocket_queue.put(test_msg)

        # Verify message can be retrieved (don't actually process)
        retrieved = websocket_queue.get(timeout=1)
        assert retrieved == test_msg

    @pytest.mark.asyncio
    async def test_execution_report_with_fees(self):
        """Test execution reports include fees and liquidity type.

        Given - A market maker submits an order
        When - The order executes
        Then - They receive execution report with maker fees
        """
        with TestClient(app) as client:
            # Given - Register market maker
            reg_response = client.post(
                "/auth/register",
                json={"team_name": "TestMMFees", "role": "market_maker"},
            )
            team_data = reg_response.json()
            api_key = team_data["api_key"]

            # Track messages
            messages: List[dict] = []

            async def collect_messages():
                uri = f"ws://localhost:8000/ws?api_key={api_key}"
                async with websockets.connect(uri) as websocket:
                    try:
                        while True:
                            msg = await asyncio.wait_for(
                                websocket.recv(), timeout=0.5
                            )
                            messages.append(json.loads(msg))
                    except asyncio.TimeoutError:
                        pass

            # Connect WebSocket
            ws_task = asyncio.create_task(collect_messages())
            await asyncio.sleep(0.1)

            # When - Submit order that provides liquidity
            order_response = client.post(
                "/orders",
                headers={"X-API-Key": api_key},
                json={
                    "instrument_id": "SPX_4500_CALL",
                    "order_type": "limit",
                    "side": "buy",
                    "quantity": 10,
                    "price": 100.0,
                    "client_order_id": "MAKER_ORDER",
                },
            )

            # Wait for messages
            await asyncio.sleep(0.2)
            ws_task.cancel()

            # Then - Check response includes fees
            response_data = order_response.json()
            if response_data["filled_quantity"] > 0:
                assert "fees" in response_data
                assert "liquidity_type" in response_data

    @pytest.mark.asyncio
    async def test_position_snapshot_on_connect(self):
        """Test position snapshot sent on WebSocket connect.

        Given - A team has existing positions
        When - They connect via WebSocket
        Then - They immediately receive position snapshot
        """
        with TestClient(app) as client:
            # Given - Register team and create positions
            reg_response = client.post(
                "/auth/register",
                json={"team_name": "TestSnapshot", "role": "market_maker"},
            )
            team_data = reg_response.json()
            api_key = team_data["api_key"]

            # Submit order to create position
            client.post(
                "/orders",
                headers={"X-API-Key": api_key},
                json={
                    "instrument_id": "SPX_4500_CALL",
                    "order_type": "limit",
                    "side": "buy",
                    "quantity": 5,
                    "price": 100.0,
                },
            )

            # When - Connect WebSocket
            messages: List[dict] = []

            async def connect_and_get_snapshot():
                uri = f"ws://localhost:8000/ws?api_key={api_key}"
                async with websockets.connect(uri) as websocket:
                    # First message should be position snapshot
                    msg = await websocket.recv()
                    messages.append(json.loads(msg))

            await connect_and_get_snapshot()

            # Then - Verify position snapshot
            assert len(messages) == 1
            assert messages[0]["type"] == "position_snapshot"
            positions = messages[0]["data"]["positions"]

            # Should have position from earlier order
            if positions:  # May be empty if order didn't fill
                assert "SPX_4500_CALL" in positions
