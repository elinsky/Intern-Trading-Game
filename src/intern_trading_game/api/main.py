"""REST API for the Intern Trading Game with queue-based architecture."""

import threading
from contextlib import asynccontextmanager
from queue import Queue
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..domain.exchange.response.coordinator import OrderResponseCoordinator
from ..domain.exchange.threads_v2 import (
    matching_thread_v2,
    validator_thread_v2,
)
from ..domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
)
from ..domain.exchange.venue import ExchangeVenue
from ..domain.game.game_service import GameService
from ..domain.positions import (
    PositionManagementService,
    TradingFeeService,
)
from ..domain.positions.threads import position_tracker_thread
from ..infrastructure.communication.threads import (
    trade_publisher_thread,
    websocket_thread,
)
from ..infrastructure.messaging.websocket_manager import ws_manager
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

# Exchange instance - set during startup from config
_exchange: Optional[ExchangeVenue] = None

# Validator instance - set during startup from config
_validator: Optional[ConstraintBasedOrderValidator] = None

# Service instances
validation_service: Optional[OrderValidationService] = None
position_service = PositionManagementService()
fee_service: Optional[TradingFeeService] = None
game_service: Optional[GameService] = None

# Response coordinator - replaces global dictionaries
response_coordinator: Optional[OrderResponseCoordinator] = None


def validator_thread_wrapper():
    """Wrapper for Exchange Service validator thread.

    Calls the Exchange domain validator thread with all required parameters.
    Now uses the OrderResponseCoordinator instead of global dictionaries.
    """
    validator_thread_v2(
        order_queue=order_queue,
        match_queue=match_queue,
        websocket_queue=websocket_queue,
        validation_service=validation_service,
        response_coordinator=response_coordinator,
    )


def matching_thread_wrapper():
    """Wrapper for Exchange Service matching thread.

    Calls the Exchange domain matching thread with all required parameters.
    Now optionally uses the OrderResponseCoordinator for error cases.
    """
    matching_thread_v2(
        match_queue=match_queue,
        trade_queue=trade_queue,
        websocket_queue=websocket_queue,
        exchange=_exchange,
        response_coordinator=response_coordinator,
    )


def trade_publisher_thread_wrapper():
    """Wrapper for Communication Infrastructure trade publisher thread.

    Calls the Communication infrastructure trade publisher thread.
    The thread function accesses global queues via runtime imports
    to avoid circular dependencies.
    """
    trade_publisher_thread(fee_service)


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
    - Loading configuration
    - Creating exchange from config
    - Creating validator from config
    - Initializing services (including GameService)
    - Starting processing threads
    - Loading instruments from config

    The startup process establishes proper dependency injection by storing
    service instances in app.state for access throughout the application
    lifecycle. This eliminates global state access and enables testable
    service interactions.

    Notes
    -----
    Service initialization follows dependency injection patterns where
    services receive their dependencies through constructor parameters
    rather than accessing global state directly. The GameService is
    created fresh for each application startup, ensuring clean state
    for testing and production deployments.

    All service instances are stored in app.state to enable FastAPI
    dependency injection throughout the request/response cycle.

    TradingContext
    --------------
    The startup process establishes the foundational services required
    for trading operations:
    - GameService: Team management and authentication
    - ExchangeVenue: Order matching and trade execution
    - PositionService: Position tracking and risk management
    - ValidationService: Order constraint validation

    Proper initialization order ensures that all service dependencies
    are satisfied before processing begins.

    Examples
    --------
    >>> # Services are accessible via dependency injection
    >>> @app.post("/teams/register")
    >>> async def register_team(
    ...     request: TeamRegistration,
    ...     game_service: GameService = Depends(get_game_service)
    ... ) -> TeamInfo:
    ...     return game_service.register_team(request.name, request.role)
    """
    global validation_service, _exchange, _validator, fee_service, game_service
    global response_coordinator

    # Load configuration
    from ..infrastructure.config import ConfigLoader
    from ..infrastructure.factories.exchange_factory import ExchangeFactory
    from ..infrastructure.factories.fee_service_factory import (
        FeeServiceFactory,
    )
    from ..infrastructure.factories.validator_factory import ValidatorFactory

    config_loader = ConfigLoader()

    # Create response coordinator from config
    try:
        coord_config = config_loader.get_response_coordinator_config()
        response_coordinator = OrderResponseCoordinator(coord_config)
        print(f"Response coordinator started with config: {coord_config}")
    except ValueError as e:
        print(f"Failed to load response coordinator config: {e}")
        raise

    # Store coordinator in app state for endpoint access
    app.state.response_coordinator = response_coordinator

    # Create exchange from config
    exchange_config = config_loader.get_exchange_config()
    exchange = ExchangeFactory.create_from_config(exchange_config)

    # Store exchange for thread access and dependency injection
    _exchange = exchange
    app.state.exchange = exchange

    # Create validator from config
    validator = ValidatorFactory.create_from_config(config_loader)
    _validator = validator

    # Create fee service from config
    fee_service = FeeServiceFactory.create_from_config(config_loader)

    # Create game service for team management
    game_service = GameService()

    # Initialize services
    validation_service = OrderValidationService(
        validator=validator,
        exchange=exchange,
        position_service=position_service,
    )

    # Store services in app state for dependency injection
    app.state.game_service = game_service

    # Start processing threads
    validator_t.start()
    matching_t.start()
    publisher_t.start()
    position_t.start()
    websocket_t.start()

    # Load instruments from config
    instruments = config_loader.get_instruments()
    for instrument in instruments:
        exchange.list_instrument(instrument)

    print(
        f"API started with {len(instruments)} instruments and 5 processing threads"
    )


async def shutdown():
    """Cleanup resources on shutdown.

    This function handles all cleanup logic including:
    - Stopping the response coordinator
    - Sending shutdown signals to threads
    - Waiting for threads to complete

    Follows Single Responsibility Principle by focusing only on cleanup tasks.
    """
    # Stop response coordinator
    if response_coordinator:
        response_coordinator.shutdown()
        print("Response coordinator stopped")

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
        "version": "2.0.0",
        "threads": {
            "validator": validator_t.is_alive() if validator_t else False,
            "matching": matching_t.is_alive() if matching_t else False,
            "publisher": publisher_t.is_alive() if publisher_t else False,
            "position_tracker": position_t.is_alive() if position_t else False,
            "websocket": websocket_t.is_alive() if websocket_t else False,
        },
        "coordinator_active": response_coordinator is not None,
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
    # Validate API key using game service
    if game_service:
        team = game_service.get_team_by_api_key(api_key)
        if not team:
            await websocket.close(code=1008, reason="Invalid API key")
            return
    else:
        await websocket.close(code=1008, reason="Service not available")
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
