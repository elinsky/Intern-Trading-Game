"""REST API for the Intern Trading Game with queue-based architecture."""

import asyncio
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from queue import Queue
from typing import Dict

import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from ..core.interfaces import ValidationContext
from ..core.models import TickPhase
from ..core.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintConfig,
    ConstraintType,
)
from ..exchange.matching_engine import ContinuousMatchingEngine
from ..exchange.order import Order, OrderSide, OrderType
from ..exchange.venue import ExchangeVenue
from ..instruments.instrument import Instrument
from .auth import get_current_team, team_registry
from .models import (
    OrderRequest,
    OrderResponse,
    PositionResponse,
    TeamInfo,
    TeamRegistration,
)
from .websocket import ws_manager

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

# Position tracking (thread-safe)
positions: Dict[str, Dict[str, int]] = {}
positions_lock = threading.RLock()

# Track orders per tick
orders_this_tick: Dict[str, int] = {}
orders_lock = threading.RLock()

# Pending orders waiting for response
pending_orders: Dict[str, threading.Event] = {}
order_responses: Dict[str, OrderResponse] = {}


def validator_thread():
    """Thread 2: Order Validator - validates orders from queue.

    This thread implements the order validation pipeline, continuously
    processing orders from the order queue and applying role-based
    constraints before forwarding valid orders to the matching engine.

    The validator thread acts as a gatekeeper, ensuring that only
    orders meeting all constraints (position limits, order size, etc.)
    proceed to execution. Rejected orders receive immediate feedback.

    Notes
    -----
    The thread uses a blocking get() on the order queue, which means
    it sleeps when no orders are available, minimizing CPU usage.

    A None value in the queue signals thread shutdown, allowing for
    graceful termination during API shutdown.

    The validation context includes current positions and order counts,
    which are retrieved thread-safely using locks to prevent race
    conditions with the trade publisher thread.

    TradingContext
    --------------
    In production, this thread would also:
    - Track order rates per tick for rate limiting
    - Validate against real-time market conditions
    - Check margin requirements
    - Enforce trading session rules

    Examples
    --------
    The thread processes orders in this sequence:
    1. Receive (order, team_info, response_event) from queue
    2. Build ValidationContext with current state
    3. Run constraint validation
    4. If valid: forward to match_queue
    5. If invalid: send rejection via response_event
    """
    print("Validator thread started")

    while True:
        try:
            # Get order from queue
            order_data = order_queue.get()
            if order_data is None:  # Shutdown signal
                break

            order, team_info, response_event = order_data

            # Get current positions safely
            with positions_lock:
                team_positions = positions.get(team_info.team_id, {}).copy()

            with orders_lock:
                team_orders = orders_this_tick.get(team_info.team_id, 0)

            # Build validation context
            context = ValidationContext(
                order=order,
                trader_id=team_info.team_id,
                trader_role=team_info.role,
                tick_phase=TickPhase.TRADING,
                current_positions=team_positions,
                orders_this_tick=team_orders,
            )

            # Validate order
            result = validator.validate_order(context)

            if result.status == "accepted":
                # Send to matching engine
                match_queue.put((order, team_info))

                # Update order count
                with orders_lock:
                    orders_this_tick[team_info.team_id] = team_orders + 1
            else:
                # Send rejection via WebSocket
                websocket_queue.put(
                    (
                        "new_order_reject",
                        team_info.team_id,
                        {
                            "order_id": order.order_id,
                            "client_order_id": order.client_order_id,
                            "reason": result.error_message,
                            "error_code": result.error_code,
                        },
                    )
                )

                # Send rejection response
                response = OrderResponse(
                    order_id=order.order_id,
                    status="rejected",
                    timestamp=datetime.now(),
                    error_code=result.error_code,
                    error_message=result.error_message,
                )
                order_responses[order.order_id] = response
                response_event.set()

        except Exception as e:
            print(f"Validator thread error: {e}")


def matching_thread():
    """Thread 3: Matching Engine - processes validated orders."""
    print("Matching engine thread started")

    while True:
        try:
            # Get validated order
            order_data = match_queue.get()
            if order_data is None:  # Shutdown signal
                break

            order, team_info = order_data

            # Submit to exchange
            try:
                result = exchange.submit_order(order)

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
                                "price": order.price,
                                "status": result.status,
                            },
                        )
                    )

                # Send to trade publisher
                trade_queue.put((result, order, team_info))

            except Exception as e:
                # Handle exchange errors
                response = OrderResponse(
                    order_id=order.order_id,
                    status="error",
                    timestamp=datetime.now(),
                    error_message=str(e),
                )

                # Find the response event
                if order.order_id in pending_orders:
                    order_responses[order.order_id] = response
                    pending_orders[order.order_id].set()

        except Exception as e:
            print(f"Matching thread error: {e}")


def trade_publisher_thread():
    """Thread 4: Trade Publisher - updates positions and sends responses."""
    print("Trade publisher thread started")

    while True:
        try:
            # Get trade result
            trade_data = trade_queue.get()
            if trade_data is None:  # Shutdown signal
                break

            result, order, team_info = trade_data

            # Calculate fees and send execution reports
            total_fees = 0.0
            liquidity_type = None
            fill_quantity = sum(trade.quantity for trade in result.fills)

            # Update positions if filled
            if fill_quantity > 0:
                # Send execution reports for each fill
                for trade in result.fills:
                    # Determine liquidity type based on aggressor
                    if trade.aggressor_side == order.side:
                        liquidity_type = "taker"
                    else:
                        liquidity_type = "maker"

                    # Calculate fees
                    if (
                        team_info.role == "market_maker"
                        and liquidity_type == "maker"
                    ):
                        fees = -0.02 * trade.quantity  # Rebate
                    else:
                        fees = 0.05 * trade.quantity  # Taker fee

                    total_fees += fees

                    # Send execution report via WebSocket
                    websocket_queue.put(
                        (
                            "execution_report",
                            team_info.team_id,
                            {
                                "trade": trade,
                                "buyer_order_id": trade.buyer_order_id,
                                "seller_order_id": trade.seller_order_id,
                                "client_order_id": order.client_order_id
                                if order.order_id
                                in [
                                    trade.buyer_order_id,
                                    trade.seller_order_id,
                                ]
                                else None,
                                "liquidity_type": liquidity_type,
                                "fees": fees,
                            },
                        )
                    )

                # Update positions
                with positions_lock:
                    if team_info.team_id not in positions:
                        positions[team_info.team_id] = {}

                    instrument = order.instrument_id
                    if instrument not in positions[team_info.team_id]:
                        positions[team_info.team_id][instrument] = 0

                    position_delta = (
                        fill_quantity
                        if order.side == "buy"
                        else -fill_quantity
                    )
                    positions[team_info.team_id][instrument] += position_delta

            # Calculate average price from fills
            if fill_quantity > 0:
                total_value = sum(
                    trade.price * trade.quantity for trade in result.fills
                )
                average_price = total_value / fill_quantity
            else:
                average_price = None

            # Create response with fees and liquidity_type
            response = OrderResponse(
                order_id=order.order_id,
                status=result.status,
                timestamp=datetime.now(),
                filled_quantity=fill_quantity,
                average_price=average_price,
                fees=total_fees,
                liquidity_type=liquidity_type,
            )

            # Send response back
            if order.order_id in pending_orders:
                order_responses[order.order_id] = response
                pending_orders[order.order_id].set()

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
                    await ws_manager.broadcast_position_snapshot(
                        team_id, data["positions"]
                    )

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
    - Starting processing threads
    - Configuring market maker constraints
    - Listing trading instruments

    Follows Single Responsibility Principle by focusing only on startup tasks.
    """
    # Start processing threads
    validator_t.start()
    matching_t.start()
    publisher_t.start()
    websocket_t.start()

    # Setup market maker constraints
    mm_constraint = ConstraintConfig(
        constraint_type=ConstraintType.POSITION_LIMIT,
        parameters={"max_position": 50, "symmetric": True},
        error_code="MM_POS_LIMIT",
        error_message="Position exceeds ±50",
    )
    validator.load_constraints("market_maker", [mm_constraint])

    # List instruments
    instruments = [
        Instrument("SPX_4500_CALL", "SPX 4500 Call Option"),
        Instrument("SPX_4500_PUT", "SPX 4500 Put Option"),
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


@app.post("/auth/register", response_model=TeamInfo)
async def register_team(registration: TeamRegistration):
    """Register a new trading team."""
    # For MVP, only support market_maker
    if registration.role != "market_maker":
        raise HTTPException(
            status_code=400, detail="Only market_maker role supported in MVP"
        )

    team_info = team_registry.register_team(
        team_name=registration.team_name, role=registration.role
    )

    # Initialize tracking
    with positions_lock:
        positions[team_info.team_id] = {}

    with orders_lock:
        orders_this_tick[team_info.team_id] = 0

    return team_info


@app.post("/orders", response_model=OrderResponse)
async def submit_order(
    request: OrderRequest, team: TeamInfo = Depends(get_current_team)
):
    """Submit a new order through the queue system."""
    # Convert request to Order
    try:
        order_type = OrderType[request.order_type.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400, detail=f"Invalid order type: {request.order_type}"
        )

    # Validate price for limit orders
    if order_type == OrderType.LIMIT and request.price is None:
        raise HTTPException(
            status_code=400, detail="Price required for limit orders"
        )

    # Convert side to enum
    try:
        side = OrderSide(request.side)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid side: {request.side}. Must be 'buy' or 'sell'",
        )

    # Create order
    order = Order(
        trader_id=team.team_id,
        instrument_id=request.instrument_id,
        order_type=order_type,
        side=side,
        quantity=request.quantity,
        price=request.price,
        client_order_id=request.client_order_id,
    )

    # Create response event
    response_event = threading.Event()
    pending_orders[order.order_id] = response_event

    # Submit to queue
    order_queue.put((order, team, response_event))

    # Wait for response (with timeout)
    if response_event.wait(timeout=5.0):
        # Get response
        response = order_responses.pop(order.order_id)
        pending_orders.pop(order.order_id)
        return response
    else:
        # Timeout
        pending_orders.pop(order.order_id, None)
        raise HTTPException(status_code=504, detail="Order processing timeout")


@app.get("/positions/{team_id}", response_model=PositionResponse)
async def get_positions(
    team_id: str, current_team: TeamInfo = Depends(get_current_team)
):
    """Get positions for a team."""
    # Teams can only query their own positions
    if team_id != current_team.team_id:
        raise HTTPException(
            status_code=403, detail="Cannot query other teams' positions"
        )

    with positions_lock:
        team_positions = positions.get(team_id, {}).copy()

    return PositionResponse(
        team_id=team_id, positions=team_positions, last_updated=datetime.now()
    )


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
    Connect using JavaScript:
    >>> const ws = new WebSocket('ws://localhost:8000/ws?api_key=YOUR_KEY');
    >>> ws.onmessage = (event) => {
    ...     const msg = JSON.parse(event.data);
    ...     console.log(`Received ${msg.type}:`, msg.data);
    ... };

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
