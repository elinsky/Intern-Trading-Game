"""Tests for WebSocket infrastructure and message handling.

This module tests the WebSocket manager, message builders, and
connection lifecycle to ensure reliable real-time communication.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocket

from intern_trading_game.api.models import TeamInfo
from intern_trading_game.api.websocket import ws_manager
from intern_trading_game.api.websocket_messages import (
    build_execution_report,
    build_new_order_ack,
    build_new_order_reject,
    build_position_snapshot,
)
from intern_trading_game.exchange.types import (
    LiquidityType as CoreLiquidityType,
)


class TestWebSocketMessages:
    """Test message builders produce correct formats.

    Verifies that all message types contain required fields
    and follow the expected structure for client consumption.
    """

    def test_new_order_ack_message(self):
        """Test new order acknowledgment message format."""
        # Given - Order details for acknowledgment
        msg = build_new_order_ack(
            order_id="ORD-123",
            client_order_id="CLIENT-1",
            instrument_id="SPX_4500_CALL",
            side="buy",
            quantity=10,
            order_type="limit",
            price=128.50,
        )

        # Then - Message has all required fields
        assert msg["order_id"] == "ORD-123"
        assert msg["client_order_id"] == "CLIENT-1"
        assert msg["instrument_id"] == "SPX_4500_CALL"
        assert msg["side"] == "buy"
        assert msg["quantity"] == 10
        assert msg["order_type"] == "limit"
        assert msg["price"] == 128.50
        assert msg["status"] == "new"
        assert "timestamp" in msg

    def test_new_order_reject_message(self):
        """Test new order rejection message format."""
        # Given - Rejection details
        msg = build_new_order_reject(
            order_id="ORD-124",
            client_order_id="CLIENT-2",
            reason="Position limit exceeded",
            error_code="POS_LIMIT",
        )

        # Then - Message contains rejection info
        assert msg["order_id"] == "ORD-124"
        assert msg["client_order_id"] == "CLIENT-2"
        assert msg["status"] == "rejected"
        assert msg["reason"] == "Position limit exceeded"
        assert msg["error_code"] == "POS_LIMIT"
        assert "timestamp" in msg

    def test_execution_report_message(self):
        """Test execution report message format."""
        # Given - Trade execution details
        msg = build_execution_report(
            order_id="ORD-125",
            client_order_id="CLIENT-3",
            trade_id="TRD-001",
            instrument_id="SPX_4500_CALL",
            side="buy",
            executed_quantity=5,
            executed_price=128.75,
            remaining_quantity=5,
            order_status="partially_filled",
            liquidity_type=CoreLiquidityType.TAKER,
            fees=0.10,
        )

        # Then - Message contains all execution details
        assert msg["order_id"] == "ORD-125"
        assert msg["client_order_id"] == "CLIENT-3"
        assert msg["trade_id"] == "TRD-001"
        assert msg["executed_quantity"] == 5
        assert msg["executed_price"] == 128.75
        assert msg["remaining_quantity"] == 5
        assert msg["order_status"] == "partially_filled"
        assert msg["liquidity_type"] == "taker"
        assert msg["fees"] == 0.10

    def test_position_snapshot_message(self):
        """Test position snapshot message format."""
        # Given - Current positions
        positions = {"SPX_4500_CALL": 10, "SPX_4500_PUT": -5}
        msg = build_position_snapshot(positions)

        # Then - Message contains position data
        assert msg["positions"] == positions
        assert "timestamp" in msg

    def test_message_without_client_order_id(self):
        """Test messages handle missing client order ID."""
        # Given - Order without client ID
        msg = build_new_order_ack(
            order_id="ORD-126",
            client_order_id=None,
            instrument_id="SPX_4500_CALL",
            side="sell",
            quantity=20,
            order_type="market",
            price=None,
        )

        # Then - Message excludes client_order_id
        assert "client_order_id" not in msg
        assert msg["order_id"] == "ORD-126"
        assert "price" not in msg  # Market order has no price


class TestWebSocketManager:
    """Test WebSocket connection management and broadcasting.

    Verifies connection lifecycle, message routing, and proper
    cleanup of resources.
    """

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.fixture
    def team_info(self):
        """Create test team information."""
        return TeamInfo(
            team_id="TEAM-001",
            team_name="TestBot",
            role="market_maker",
            api_key="test-key",
            created_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, mock_websocket, team_info):
        """Test WebSocket connection and disconnection.

        Verifies that connections are properly established,
        tracked, and cleaned up.
        """
        # Given - WebSocket manager
        manager = ws_manager

        # When - Team connects
        connected = await manager.connect(mock_websocket, team_info)

        # Then - Connection is established
        assert connected is True
        assert manager.is_connected(team_info.team_id)
        assert manager.get_connection_count() == 1
        mock_websocket.accept.assert_called_once()

        # When - Team disconnects
        await manager.disconnect(team_info.team_id)

        # Then - Connection is cleaned up
        assert not manager.is_connected(team_info.team_id)
        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_single_connection_per_team(self, mock_websocket, team_info):
        """Test that only one connection per team is allowed.

        When a team connects again, the old connection should
        be closed before accepting the new one.
        """
        # Given - Existing connection
        manager = ws_manager
        ws1 = AsyncMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()
        await manager.connect(ws1, team_info)

        # When - Same team connects again
        ws2 = AsyncMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        await manager.connect(ws2, team_info)

        # Then - Old connection is closed
        ws1.close.assert_called_once()
        assert manager.is_connected(team_info.team_id)
        assert manager.get_connection_count() == 1

    @pytest.mark.asyncio
    async def test_message_sequence_numbers(self, mock_websocket, team_info):
        """Test that messages have incrementing sequence numbers.

        Each message sent to a team should have a unique,
        incrementing sequence number for ordering guarantees.
        """
        # Given - Connected team
        manager = ws_manager
        await manager.connect(mock_websocket, team_info)

        # When - Multiple messages sent
        await manager.broadcast_new_order_ack(
            team_id=team_info.team_id,
            order_id="ORD-1",
            client_order_id=None,
            instrument_id="SPX_4500_CALL",
            side="buy",
            quantity=10,
            order_type="limit",
            price=128.50,
        )

        await manager.broadcast_new_order_ack(
            team_id=team_info.team_id,
            order_id="ORD-2",
            client_order_id=None,
            instrument_id="SPX_4500_PUT",
            side="sell",
            quantity=5,
            order_type="limit",
            price=32.00,
        )

        # Then - Sequence numbers increment
        calls = mock_websocket.send_json.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0]["seq"] == 1
        assert calls[1][0][0]["seq"] == 2
        assert calls[0][0][0]["type"] == "new_order_ack"
        assert calls[1][0][0]["type"] == "new_order_ack"

    @pytest.mark.asyncio
    async def test_role_based_signal_filtering(self, mock_websocket):
        """Test that signals are only sent to authorized roles.

        Hedge funds should receive volatility signals,
        while market makers should not.
        """
        # Given - Teams with different roles
        manager = ws_manager

        # Market maker
        mm_team = TeamInfo(
            team_id="MM-001",
            team_name="MarketMaker",
            role="market_maker",
            api_key="mm-key",
            created_at=datetime.now(),
        )
        mm_ws = AsyncMock(spec=WebSocket)
        mm_ws.accept = AsyncMock()
        mm_ws.send_json = AsyncMock()
        await manager.connect(mm_ws, mm_team)

        # Hedge fund
        hf_team = TeamInfo(
            team_id="HF-001",
            team_name="HedgeFund",
            role="hedge_fund",
            api_key="hf-key",
            created_at=datetime.now(),
        )
        hf_ws = AsyncMock(spec=WebSocket)
        hf_ws.accept = AsyncMock()
        hf_ws.send_json = AsyncMock()
        await manager.connect(hf_ws, hf_team)

        # When - Volatility signal broadcast
        await manager.broadcast_signal(
            signal_type="volatility_forecast",
            data={"forecast": "high", "confidence": 0.75},
            allowed_roles={"hedge_fund"},
        )

        # Then - Only hedge fund receives signal
        hf_ws.send_json.assert_called_once()
        mm_ws.send_json.assert_not_called()

        # Verify signal content
        signal_msg = hf_ws.send_json.call_args[0][0]
        assert signal_msg["type"] == "signal"
        assert signal_msg["data"]["signal_type"] == "volatility_forecast"

    @pytest.mark.asyncio
    async def test_broadcast_to_all_teams(self, mock_websocket):
        """Test broadcasting to all connected teams.

        Market data and tick events should be sent to all
        connected teams regardless of role.
        """
        # Given - Multiple connected teams
        manager = ws_manager

        teams = []
        for i in range(3):
            team = TeamInfo(
                team_id=f"TEAM-{i}",
                team_name=f"Team{i}",
                role="market_maker",
                api_key=f"key-{i}",
                created_at=datetime.now(),
            )
            ws = AsyncMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await manager.connect(ws, team)
            teams.append((team, ws))

        # When - Tick start broadcast
        await manager.broadcast_tick_start(
            tick_number=42,
            tick_duration_seconds=300,
            order_window_open=datetime.now(),
            order_window_close=datetime.now(),
        )

        # Then - All teams receive message
        for team, ws in teams:
            ws.send_json.assert_called_once()
            msg = ws.send_json.call_args[0][0]
            assert msg["type"] == "tick_start"
            assert msg["data"]["tick_number"] == 42

    @pytest.mark.asyncio
    async def test_failed_send_disconnects_client(
        self, mock_websocket, team_info
    ):
        """Test that send failures result in disconnection.

        If a WebSocket send fails, the client should be
        automatically disconnected to maintain consistency.
        """
        # Given - Connected team with failing WebSocket
        manager = ws_manager
        await manager.connect(mock_websocket, team_info)
        mock_websocket.send_json.side_effect = Exception("Connection lost")

        # When - Send attempt fails
        await manager.broadcast_new_order_ack(
            team_id=team_info.team_id,
            order_id="ORD-1",
            client_order_id=None,
            instrument_id="SPX_4500_CALL",
            side="buy",
            quantity=10,
            order_type="limit",
            price=128.50,
        )

        # Then - Team is disconnected
        assert not manager.is_connected(team_info.team_id)
        assert manager.get_connection_count() == 0
