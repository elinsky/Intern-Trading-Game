"""REST API for the Intern Trading Game with queue-based architecture."""

import asyncio
import threading
from contextlib import asynccontextmanager
from queue import Queue
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..domain.exchange.book.matching_engine import ContinuousMatchingEngine
from ..domain.exchange.core.instrument import Instrument
from ..domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintConfig,
    ConstraintType,
)
from ..domain.exchange.venue import ExchangeVenue
from ..domain.positions import (
    PositionManagementService,
    TradeProcessingService,
    TradingFeeService,
)
from ..infrastructure.api.auth import team_registry
from ..infrastructure.api.websocket import ws_manager
from ..infrastructure.config.fee_config import get_hardcoded_fee_schedules
from ..infrastructure.threads.validator import (
    validator_thread as validator_thread_impl,
)
from ..services import OrderValidationService
from ..services.order_matching import OrderMatchingService
from .endpoints import exchange as exchange_endpoints
from .endpoints import game as game_endpoints
from .endpoints import positions as positions_endpoints

# Thread-safe queues
order_queue: Queue = Queue()  # API -> Validator
validation_queue: Queue = Queue()  # Validator → Matcher
match_queue: Queue = Queue()  # For matching engine
trade_queue: Queue = Queue()  # Matcher -> Publisher
response_queue: Queue = Queue()  # For order responses back to API
websocket_queue: Queue = Queue()  # Threads -> WebSocket

# Game components
exchange = ExchangeVenue(ContinuousMatchingEngine())
validator = ConstraintBasedOrderValidator()

# Service instances
validation_service: Optional[OrderValidationService] = None


# Position tracking (thread-safe)
positions: Dict[str, Dict[str, int]] = {}
positions_lock = threading.RLock()

# Track orders per second
# TODO: Implement proper per-second rate limiting with timestamp tracking
# See https://github.com/Elinsky/Intern-Trading-Game/issues/1
# Current implementation only increments counter without resetting each second
# Should store (count, last_reset_timestamp) and reset when second changes
orders_this_second: Dict[str, int] = {}
orders_lock = threading.RLock()

# Pending orders waiting for response
pending_orders: Dict[str, threading.Event] = {}
order_responses: Dict[
    str, Dict
] = {}  # Now stores ApiResponse objects with order_id:request_id keys


# Helper functions for service dependency injection
def get_team_positions(team_id: str) -> Dict[str, int]:
    """Thread-safe retrieval of team positions."""
    with positions_lock:
        return positions.get(team_id, {}).copy()


def get_team_order_count(team_id: str) -> int:
    """Thread-safe retrieval of team order count for current second.

    WARNING: Current implementation does not reset counter each second.
    This is a known limitation - the counter will continuously increment
    until the system is restarted. See GitHub issue #1 and TODO above.

    Returns
    -------
    int
        Number of orders submitted (never resets in current implementation)
    """
    with orders_lock:
        return orders_this_second.get(team_id, 0)


def validator_thread():
    """Wrapper for validator thread implementation.

    Calls the imported validator thread with all required parameters.
    """
    validator_thread_impl(
        order_queue=order_queue,
        match_queue=match_queue,
        websocket_queue=websocket_queue,
        validation_service=validation_service,
        orders_this_second=orders_this_second,
        orders_lock=orders_lock,
        pending_orders=pending_orders,
        order_responses=order_responses,
    )


def matching_thread():
    """Thread 3: Matching Engine - processes validated orders."""
    print("Matching engine thread started")

    # Initialize service once at thread startup
    matching_service = OrderMatchingService(exchange)

    while True:
        try:
            # Get validated order
            order_data = match_queue.get()
            if order_data is None:  # Shutdown signal
                break

            order, team_info = order_data

            # Submit to exchange using service
            try:
                result = matching_service.submit_order_to_exchange(order)

                # Send ACK if order accepted by exchange
                if result.status in ["new", "partially_filled", "filled"]:
                    websocket_queue.put(
                        (
                            "new_order_ack",
                            team_info.team_id,
                            {
                                "order_id": order.order_id,
                                "client_order_id": order.client_order_id,
                                "instrument_id": order.instrument_id,
                                "side": order.side,
                                "quantity": order.quantity,
                                "order_type": order.order_type,
                                "price": order.price,
                            },
                        )
                    )

                # Send to trade publisher
                trade_queue.put((result, order, team_info))

            except Exception as e:
                # Log exchange errors - validator already sent response
                print(f"Exchange error for order {order.order_id}: {e}")
                # Note: The validator has already responded to the API
                # so we just log the error here

        except Exception as e:
            print(f"Matching thread error: {e}")


def trade_publisher_thread():
    """Thread 4: Trade Publisher - updates positions and sends responses."""
    print("Trade publisher thread started")

    # Initialize services once at thread startup
    role_fees = get_hardcoded_fee_schedules()
    fee_service = TradingFeeService(role_fees)
    position_service = PositionManagementService(positions, positions_lock)
    trade_service = TradeProcessingService(
        fee_service, position_service, websocket_queue
    )

    while True:
        try:
            # Get trade result
            trade_data = trade_queue.get()
            if trade_data is None:  # Shutdown signal
                break

            result, order, team_info = trade_data

            # Use service for all business logic
            # Note: No API response needed - validator already responded
            trade_service.process_trade_result(result, order, team_info)

        except Exception as e:
            print(f"Trade publisher thread error: {e}")


def websocket_thread():
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


# Create threads but don't start them yet
validator_t = threading.Thread(target=validator_thread, daemon=True)
matching_t = threading.Thread(target=matching_thread, daemon=True)
publisher_t = threading.Thread(target=trade_publisher_thread, daemon=True)
websocket_t = threading.Thread(target=websocket_thread, daemon=True)


async def startup():
    """Initialize the game components on startup.

    This function handles all startup logic including:
    - Initializing services
    - Starting processing threads
    - Configuring market maker constraints
    - Listing trading instruments

    Follows Single Responsibility Principle by focusing only on startup tasks.
    """
    global validation_service

    # Initialize services
    validation_service = OrderValidationService(
        validator=validator,
        exchange=exchange,
        get_positions_func=get_team_positions,
        get_order_count_func=get_team_order_count,
    )

    # Start processing threads
    validator_t.start()
    matching_t.start()
    publisher_t.start()
    websocket_t.start()

    # Setup market maker constraints
    mm_position_constraint = ConstraintConfig(
        constraint_type=ConstraintType.POSITION_LIMIT,
        parameters={"max_position": 50, "symmetric": True},
        error_code="MM_POS_LIMIT",
        error_message="Position exceeds ±50",
    )

    mm_instrument_constraint = ConstraintConfig(
        constraint_type=ConstraintType.INSTRUMENT_ALLOWED,
        parameters={"allowed_instruments": ["SPX_4500_CALL", "SPX_4500_PUT"]},
        error_code="INVALID_INSTRUMENT",
        error_message="Instrument not found",
    )

    validator.load_constraints(
        "market_maker", [mm_position_constraint, mm_instrument_constraint]
    )

    # List instruments
    instruments = [
        Instrument(
            symbol="SPX_4500_CALL",
            strike=4500.0,
            option_type="call",
            underlying="SPX",
        ),
        Instrument(
            symbol="SPX_4500_PUT",
            strike=4500.0,
            option_type="put",
            underlying="SPX",
        ),
    ]

    for instrument in instruments:
        exchange.list_instrument(instrument)

    print(
        f"✓ API started with {len(instruments)} instruments and 4 processing threads"
    )


async def shutdown():
    """Cleanup resources on shutdown.

    This function handles all cleanup logic including:
    - Sending shutdown signals to threads
    - Waiting for threads to complete

    Follows Single Responsibility Principle by focusing only on cleanup tasks.
    """
    # Send shutdown signals to threads
    order_queue.put(None)
    match_queue.put(None)
    trade_queue.put(None)
    websocket_queue.put(None)

    # Wait for threads to finish
    validator_t.join(timeout=1)
    matching_t.join(timeout=1)
    publisher_t.join(timeout=1)
    websocket_t.join(timeout=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application lifecycle.

    This context manager handles startup and shutdown events for the FastAPI
    application, replacing the deprecated @app.on_event decorators.

    The lifespan pattern ensures proper resource management and follows
    SOLID principles by delegating to separate startup/shutdown functions.
    """
    await startup()
    yield
    await shutdown()


# Initialize FastAPI app with lifespan management
app = FastAPI(
    title="Intern Trading Game API",
    description="REST API for algorithmic trading simulation",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Intern Trading Game API",
        "threads": {
            "validator": validator_t.is_alive() if validator_t else False,
            "matching": matching_t.is_alive() if matching_t else False,
            "publisher": publisher_t.is_alive() if publisher_t else False,
            "websocket": websocket_t.is_alive() if websocket_t else False,
        },
    }


# Include routers
app.include_router(game_endpoints.router)
app.include_router(exchange_endpoints.router)
app.include_router(positions_endpoints.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, api_key: str):
    """WebSocket endpoint for real-time trading updates.

    Establishes a persistent WebSocket connection for a trading team,
    enabling real-time streaming of order updates, trade executions,
    and position changes.

    Parameters
    ----------
    websocket : WebSocket
        The WebSocket connection instance from FastAPI
    api_key : str
        Team's API key provided as query parameter (?api_key=...)

    Notes
    -----
    Connection lifecycle:
    1. Validate API key against team registry
    2. Register connection with WebSocketManager
    3. Send initial position snapshot
    4. Keep connection alive until disconnect

    Only one WebSocket connection is allowed per team. New connections
    will automatically close any existing connection for that team.

    The connection uses query parameter authentication because WebSocket
    headers are not consistently supported across all client libraries.

    TradingContext
    --------------
    Teams receive only their own order updates and trades. Market data
    and public events are broadcast to all connected teams.

    Message types sent to clients:
    - position_snapshot: Initial positions on connect
    - new_order_ack: Order accepted by exchange
    - new_order_reject: Order validation failed
    - execution_report: Trade executed

    Examples
    --------

    Connect using Python:
    >>> import websockets
    >>> async with websockets.connect('ws://localhost:8000/ws?api_key=YOUR_KEY') as ws:
    ...     async for message in ws:
    ...         msg = json.loads(message)
    ...         print(f"Received {msg['type']}")
    """
    # Validate API key
    team = team_registry.get_team_by_api_key(api_key)
    if not team:
        await websocket.close(code=1008, reason="Invalid API key")
        return

    # Connect
    await ws_manager.connect(websocket, team)

    # Send position snapshot via queue
    with positions_lock:
        team_positions = positions.get(team.team_id, {}).copy()

    websocket_queue.put(
        ("position_snapshot", team.team_id, {"positions": team_positions})
    )

    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(team.team_id)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)  # nosec B104
