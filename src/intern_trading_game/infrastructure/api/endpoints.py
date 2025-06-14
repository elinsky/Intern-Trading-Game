"""FastAPI endpoints for the trading system."""

import threading
from datetime import datetime
from queue import Queue
from typing import Dict

from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect

from ...domain.exchange.core.order import Order, OrderSide, OrderType
from .auth import get_current_team, team_registry
from .models import (
    OrderRequest,
    OrderResponse,
    PositionResponse,
    TeamInfo,
    TeamRegistration,
)
from .websocket import ws_manager


def create_endpoints(
    app,
    order_queue: Queue,
    positions: Dict[str, Dict[str, int]],
    positions_lock: threading.RLock,
    orders_this_tick: Dict[str, int],
    orders_lock: threading.RLock,
    pending_orders: Dict[str, threading.Event],
    order_responses: Dict[str, OrderResponse],
    websocket_queue: Queue,
):
    """Create and register all FastAPI endpoints.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance
    order_queue : Queue
        Queue for order submissions
    positions : Dict[str, Dict[str, int]]
        Shared position state
    positions_lock : threading.RLock
        Lock for position access
    orders_this_tick : Dict[str, int]
        Order count tracking
    orders_lock : threading.RLock
        Lock for order count access
    pending_orders : Dict[str, threading.Event]
        Pending order events
    order_responses : Dict[str, OrderResponse]
        Order response storage
    websocket_queue : Queue
        WebSocket message queue
    """

    @app.get("/")
    async def root():
        """Health check endpoint."""
        return {
            "status": "ok",
            "service": "Intern Trading Game API",
            "threads": {
                "validator": True,  # TODO: get actual thread status
                "matching": True,
                "publisher": True,
                "websocket": True,
            },
        }

    @app.post("/auth/register", response_model=TeamInfo)
    async def register_team(registration: TeamRegistration):
        """Register a new trading team."""
        # For MVP, only support market_maker
        if registration.role != "market_maker":
            raise HTTPException(
                status_code=400,
                detail="Only market_maker role supported in MVP",
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
                status_code=400,
                detail=f"Invalid order type: {request.order_type}",
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

        # Submit to queue with message type
        order_queue.put(("new_order", order, team, response_event))

        # Wait for response (with timeout)
        if response_event.wait(timeout=5.0):
            # Get response
            response = order_responses.pop(order.order_id)
            pending_orders.pop(order.order_id)
            return response
        else:
            # Timeout
            pending_orders.pop(order.order_id, None)
            raise HTTPException(
                status_code=504, detail="Order processing timeout"
            )

    @app.delete("/orders/{order_id}", response_model=OrderResponse)
    async def cancel_order(
        order_id: str, team: TeamInfo = Depends(get_current_team)
    ):
        """Cancel an existing order (FIX MsgType=F).

        Implements standard exchange order cancellation following
        FIX protocol semantics. Cancels are processed in FIFO
        order with all other order messages to ensure temporal
        fairness in the market.

        Parameters
        ----------
        order_id : str
            The exchange-assigned order ID to cancel (FIX Tag 37)
        team : TeamInfo
            Authenticated team information from API key

        Returns
        -------
        OrderResponse
            Status will be 'cancelled' on success or 'rejected'
            with error details on failure

        Raises
        ------
        HTTPException
            504 Gateway Timeout if processing exceeds 5 seconds

        Notes
        -----
        Cancel requests enter the same queue as new orders,
        maintaining strict FIFO processing. This ensures a
        cancel submitted at T+1ms cannot jump ahead of a
        new order submitted at T+0ms.

        The validator thread verifies ownership before
        cancelling to prevent market manipulation.

        TradingContext
        --------------
        In fast markets, cancellation may fail if the order
        has already been matched by an earlier message in
        the queue. This race condition is inherent to all
        exchanges and traders must handle cancel rejections.

        Real exchanges often provide more detailed reject
        reasons (e.g., ALREADY_FILLED vs NOT_FOUND). Future
        enhancement could add this granularity.

        Examples
        --------
        >>> # Cancel a resting limit order
        >>> response = await client.delete(
        ...     "/orders/ORD_12345",
        ...     headers={"X-API-Key": api_key}
        ... )
        >>> if response.json()["status"] == "cancelled":
        ...     print("Order successfully cancelled")
        """
        # Create response event for async processing
        response_event = threading.Event()
        pending_orders[order_id] = response_event

        # Submit cancel request to queue
        order_queue.put(("cancel_order", order_id, team, response_event))

        # Wait for response with timeout
        if response_event.wait(timeout=5.0):
            # Get response
            response = order_responses.pop(order_id)
            pending_orders.pop(order_id)
            return response
        else:
            # Timeout
            pending_orders.pop(order_id, None)
            raise HTTPException(
                status_code=504, detail="Cancel request timeout"
            )

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
            team_id=team_id,
            positions=team_positions,
            last_updated=datetime.now(),
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
