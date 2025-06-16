"""Communication infrastructure thread implementations.

This module contains thread functions that handle cross-domain communication
and technical infrastructure concerns like message routing and protocol bridging.
"""

import asyncio

from ...domain.positions import TradingFeeService
from ...infrastructure.config.fee_config import get_hardcoded_fee_schedules
from ..messaging.websocket_manager import ws_manager


def trade_publisher_thread():
    """Thread 4: Trade Publisher - routes trades and sends WebSocket messages.

    This thread acts as a message router, forwarding trades to the position
    tracker thread and sending execution reports via WebSocket. It handles
    cross-domain communication rather than domain-specific business logic.

    Infrastructure Role:
    - Routes messages between Exchange → Position → WebSocket domains
    - Handles communication coordination, not business logic
    - Serves as a message bus for trade-related events
    """
    print("Trade publisher thread started")

    # Initialize only the services needed for WebSocket messaging
    role_fees = get_hardcoded_fee_schedules()
    fee_service = TradingFeeService(role_fees)

    while True:
        try:
            # Import here to avoid circular imports
            from ...api.main import (
                position_queue,
                trade_queue,
                websocket_queue,
            )

            # Get trade result
            trade_data = trade_queue.get()
            if trade_data is None:  # Shutdown signal
                break

            result, order, team_info = trade_data

            # Forward to position tracker for position updates
            position_queue.put((result, order, team_info))

            # Send WebSocket messages for each fill
            if result.fills:
                for trade in result.fills:
                    # Calculate fee for this specific fill
                    liquidity_type = fee_service.determine_liquidity_type(
                        order.order_id, trade
                    )
                    fee = fee_service.calculate_fee(
                        quantity=trade.quantity,
                        role=team_info.role,
                        liquidity_type=liquidity_type,
                    )

                    # Determine counterparty order ID
                    if order.side.value == "buy":
                        counterparty_order_id = trade.seller_order_id
                    else:
                        counterparty_order_id = trade.buyer_order_id

                    # Send execution report
                    websocket_queue.put(
                        (
                            "execution_report",
                            team_info.team_id,
                            {
                                "order_id": order.order_id,
                                "client_order_id": order.client_order_id,
                                "side": order.side.value,
                                "quantity": trade.quantity,
                                "price": trade.price,
                                "liquidity": liquidity_type,
                                "fee": fee,
                                "timestamp": trade.timestamp.isoformat(),
                                "trade_id": trade.trade_id,
                                "counterparty": counterparty_order_id,
                                "team_id": team_info.team_id,
                            },
                        )
                    )

        except Exception as e:
            print(f"Trade publisher thread error: {e}")


def websocket_thread():
    """Thread 8: WebSocket Publisher - sends async messages to connected clients.

    This thread bridges the synchronous trading threads with the asynchronous
    WebSocket connections. It receives messages from other threads via a
    thread-safe queue and broadcasts them to connected clients based on
    team ID and message type.

    Infrastructure Role:
    - Bridges sync threads ↔ async WebSocket protocol (technical concern)
    - Serves ALL domains: Exchange updates, Position updates, Game events
    - Handles network communication infrastructure, not business logic

    The thread runs an asyncio event loop to handle WebSocket operations,
    using asyncio.to_thread to safely retrieve messages from the synchronous
    queue without blocking the event loop.

    Message flow:
    1. Trading threads put messages on websocket_queue
    2. This thread retrieves messages asynchronously
    3. Messages are routed to appropriate WebSocket broadcast methods
    4. Connected clients receive real-time updates

    Notes
    -----
    The thread uses a None sentinel value in the queue to signal shutdown,
    allowing graceful termination during API shutdown.

    Messages are only sent to connected clients - disconnected clients are
    silently skipped to prevent blocking the queue.

    The thread handles all WebSocket message types:
    - new_order_ack: Order accepted by exchange
    - new_order_reject: Order failed validation
    - execution_report: Trade executed
    - position_snapshot: Current positions on connect

    TradingContext
    --------------
    In production, this thread would also handle:
    - Market data updates (bid/ask changes)
    - News events and signals
    - System announcements
    - Heartbeat messages for connection health

    Examples
    --------
    Message format in queue:
    >>> websocket_queue.put((
    ...     'new_order_ack',  # message type
    ...     'TEAM_001',       # team_id
    ...     {                 # data dict
    ...         'order_id': 'ORD_123',
    ...         'client_order_id': 'MY_ORDER_1',
    ...         'status': 'new'
    ...     }
    ... ))
    """
    print("WebSocket thread started")
    asyncio.run(websocket_async_loop())


async def websocket_async_loop():
    """Async event loop for WebSocket operations.

    Continuously processes messages from the websocket_queue and sends
    them to connected clients via the WebSocketManager.

    This coroutine bridges the synchronous thread world with the async
    WebSocket world using asyncio.to_thread for non-blocking queue access.

    Notes
    -----
    The loop runs until a None message is received, signaling shutdown.
    All exceptions are caught and logged to prevent thread termination
    on individual message failures.
    """
    while True:
        try:
            # Import here to avoid circular imports
            from ...api.main import websocket_queue

            # Bridge sync to async - get from queue without blocking event loop
            msg = await asyncio.to_thread(websocket_queue.get)
            if msg is None:  # Shutdown signal
                break

            msg_type, team_id, data = msg

            # Route to appropriate WebSocket method
            if ws_manager.is_connected(team_id):
                if msg_type == "new_order_ack":
                    await ws_manager.broadcast_new_order_ack(team_id, **data)
                elif msg_type == "new_order_reject":
                    await ws_manager.broadcast_new_order_reject(
                        team_id, **data
                    )
                elif msg_type == "execution_report":
                    await ws_manager.broadcast_trade_execution(**data)
                elif msg_type == "position_snapshot":
                    await ws_manager.send_position_snapshot(
                        team_id, data["positions"]
                    )
                elif msg_type == "order_cancelled":
                    await ws_manager.broadcast_cancel_ack(team_id, **data)
                elif msg_type == "order_cancel_reject":
                    await ws_manager.broadcast_cancel_reject(team_id, **data)

        except Exception as e:
            print(f"WebSocket thread error: {e}")
