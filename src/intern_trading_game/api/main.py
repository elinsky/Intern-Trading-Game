"""REST API for the Intern Trading Game with queue-based architecture."""

import threading
from contextlib import asynccontextmanager
from queue import Queue
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..domain.exchange.book.matching_engine import ContinuousMatchingEngine
from ..domain.exchange.core.instrument import Instrument
from ..domain.exchange.threads import matching_thread, validator_thread
from ..domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintConfig,
    ConstraintType,
)
from ..domain.exchange.venue import ExchangeVenue
from ..domain.positions import (
    PositionManagementService,
)
from ..domain.positions.threads import position_tracker_thread
from ..infrastructure.api.auth import team_registry
from ..infrastructure.api.websocket import ws_manager
from ..infrastructure.communication.threads import (
    trade_publisher_thread,
    websocket_thread,
)
from ..services import OrderValidationService
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
position_queue: Queue = Queue()  # Publisher -> Position Tracker

# Game components
exchange = ExchangeVenue(ContinuousMatchingEngine())
validator = ConstraintBasedOrderValidator()

# Service instances
validation_service: Optional[OrderValidationService] = None
position_service = PositionManagementService()

# Global order tracking removed - now owned by OrderValidationService
# Global position tracking removed - now owned by PositionManagementService

# Pending orders waiting for response
pending_orders: Dict[str, threading.Event] = {}
order_responses: Dict[
    str, Dict
] = {}  # Now stores ApiResponse objects with order_id:request_id keys


def validator_thread_wrapper():
    """Wrapper for Exchange Service validator thread.

    Calls the Exchange domain validator thread with all required parameters.
    Rate limiting state is now owned by the validation service.
    """
    validator_thread(
        order_queue=order_queue,
        match_queue=match_queue,
        websocket_queue=websocket_queue,
        validation_service=validation_service,
        pending_orders=pending_orders,
        order_responses=order_responses,
    )


def matching_thread_wrapper():
    """Wrapper for Exchange Service matching thread.

    Calls the Exchange domain matching thread with all required parameters.
    """
    matching_thread(
        match_queue=match_queue,
        trade_queue=trade_queue,
        websocket_queue=websocket_queue,
        exchange=exchange,
        pending_orders=pending_orders,
        order_responses=order_responses,
    )


def trade_publisher_thread_wrapper():
    """Wrapper for Communication Infrastructure trade publisher thread.

    Calls the Communication infrastructure trade publisher thread.
    The thread function accesses global queues via runtime imports
    to avoid circular dependencies.
    """
    trade_publisher_thread()


def position_tracker_thread_wrapper():
    """Thread 5: Position Tracker - updates positions based on executed trades.

    This thread is owned by the Position Service and handles all position
    tracking logic. It consumes trades from the position queue and updates
    the position state accordingly.
    """
    # Run the position tracker thread with the global service instance
    position_tracker_thread(position_queue, position_service)


def websocket_thread_wrapper():
    """Wrapper for Communication Infrastructure websocket thread.

    Calls the Communication infrastructure websocket thread.
    The thread function accesses global queues via runtime imports
    to avoid circular dependencies.
    """
    websocket_thread()


# Create threads but don't start them yet
validator_t = threading.Thread(target=validator_thread_wrapper, daemon=True)
matching_t = threading.Thread(target=matching_thread_wrapper, daemon=True)
publisher_t = threading.Thread(
    target=trade_publisher_thread_wrapper, daemon=True
)
position_t = threading.Thread(
    target=position_tracker_thread_wrapper, daemon=True
)
websocket_t = threading.Thread(target=websocket_thread_wrapper, daemon=True)


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
        position_service=position_service,
    )

    # Start processing threads
    validator_t.start()
    matching_t.start()
    publisher_t.start()
    position_t.start()
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
        f"✓ API started with {len(instruments)} instruments and 5 processing threads"
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
    position_queue.put(None)
    websocket_queue.put(None)

    # Wait for threads to finish
    validator_t.join(timeout=1)
    matching_t.join(timeout=1)
    publisher_t.join(timeout=1)
    position_t.join(timeout=1)
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
            "position_tracker": position_t.is_alive() if position_t else False,
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
    team_positions = position_service.get_positions(team.team_id)

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
