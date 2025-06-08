"""Thread 8: WebSocket Publisher - sends async messages to connected clients."""

import asyncio
from queue import Queue

from ...infrastructure.api.websocket import ws_manager


def websocket_thread(websocket_queue: Queue):
    """Thread 8: WebSocket Publisher - sends async messages to connected clients.

    This thread bridges the synchronous trading threads with the asynchronous
    WebSocket connections. It receives messages from other threads via a
    thread-safe queue and broadcasts them to connected clients based on
    team ID and message type.

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
    asyncio.run(websocket_async_loop(websocket_queue))


async def websocket_async_loop(websocket_queue: Queue):
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
                elif msg_type == "order_cancel_ack":
                    await ws_manager.broadcast_cancel_ack(team_id, **data)
                elif msg_type == "order_cancel_reject":
                    await ws_manager.broadcast_cancel_reject(team_id, **data)

        except Exception as e:
            print(f"WebSocket thread error: {e}")
