"""WebSocket infrastructure for real-time data streaming.

This module implements the WebSocket server for the Intern Trading Game,
providing real-time updates for trades, orders, market data, and signals
to connected bots.

The WebSocket system integrates with the existing multi-threaded architecture,
receiving data from the trade publisher and other threads via queues, then
broadcasting relevant information to connected teams based on their roles.

Key features:
- Single connection per team (enforced)
- Role-based data filtering
- Message sequencing for order guarantees
- Automatic position snapshot on connect
- Graceful disconnection handling

Notes
-----
The WebSocket manager maintains a registry of active connections and handles
all broadcasting logic. Messages are JSON-formatted with sequence numbers
to ensure clients can detect missed messages.

Each team can only have one active WebSocket connection at a time. If a team
attempts to connect while already connected, the old connection is terminated.

TradingContext
--------------
In a production trading system, WebSocket connections would typically include:
- Heartbeat mechanisms for connection health
- Message compression for bandwidth efficiency
- Binary protocols for lower latency
- Persistent message queues for guaranteed delivery

For this educational game, we prioritize simplicity and debuggability with
JSON messages and straightforward connection management.

Examples
--------
Typical WebSocket message flow:

1. Bot connects with API key
2. Server sends position snapshot
3. Bot receives real-time updates:
   - Trade executions
   - Order status changes
   - Market data updates
   - Role-specific signals
4. Bot disconnects or is disconnected
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional, Set

from fastapi import WebSocket

from ...domain.exchange.types import LiquidityType
from ..api.models import TeamInfo
from .websocket_messages import (
    MessageType,
    build_cancel_ack,
    build_cancel_reject,
    build_connection_status,
    build_execution_report,
    build_market_data,
    build_new_order_ack,
    build_new_order_reject,
    build_position_snapshot,
    build_quote_ack,
    build_quote_reject,
)


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting.

    This class handles all WebSocket connection lifecycle events and provides
    methods for broadcasting different types of messages to connected clients.
    It ensures that each team has only one active connection and tracks
    sequence numbers for message ordering guarantees.

    The manager integrates with the game's role-based access control, ensuring
    teams only receive data they are authorized to see based on their trading
    role (market maker, hedge fund, arbitrage desk, or retail).

    Attributes
    ----------
    active_connections : Dict[str, WebSocket]
        Maps team_id to their active WebSocket connection
    sequence_numbers : Dict[str, int]
        Tracks the last sequence number sent to each team
    team_info : Dict[str, TeamInfo]
        Stores team information for each connected client
    _lock : asyncio.Lock
        Ensures thread-safe operations on connection state

    Notes
    -----
    The manager uses asyncio for all I/O operations, making it compatible
    with FastAPI's async request handling. All public methods are async
    and should be awaited.

    Message Format:
    All messages follow this JSON structure:
    {
        "seq": <int>,              # Sequence number
        "type": <str>,             # Message type
        "timestamp": <ISO-8601>,   # Server timestamp
        "data": <dict>             # Message payload
    }

    TradingContext
    --------------
    WebSocket connections in trading systems require careful handling of:
    - Network failures and reconnections
    - Message ordering and delivery guarantees
    - Bandwidth management during high-volume periods
    - Security considerations for sensitive data

    This implementation provides basic reliability features suitable for
    an educational trading game environment.
    """

    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.sequence_numbers: Dict[str, int] = {}
        self.team_info: Dict[str, TeamInfo] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, team_info: TeamInfo) -> bool:
        """Accept a new WebSocket connection for a team.

        If the team already has an active connection, the old connection
        is closed before accepting the new one. This ensures each team
        has exactly one WebSocket connection.

        Parameters
        ----------
        websocket : WebSocket
            The new WebSocket connection to accept
        team_info : TeamInfo
            Information about the connecting team

        Returns
        -------
        bool
            True if connection was successful, False otherwise

        Notes
        -----
        Connection establishment includes:
        1. Closing any existing connection for the team
        2. Accepting the new WebSocket connection
        3. Initializing sequence numbering
        4. Storing team information

        The method is atomic - either all steps succeed or the connection
        is rejected entirely.
        """
        async with self._lock:
            team_id = team_info.team_id

            # Disconnect existing connection if any
            if team_id in self.active_connections:
                old_ws = self.active_connections[team_id]
                try:
                    await old_ws.close(
                        code=1000, reason="New connection established"
                    )
                except Exception:
                    # Connection might already be closed, which is fine
                    pass  # nosec B110

            # Accept new connection
            try:
                await websocket.accept()
                self.active_connections[team_id] = websocket
                self.sequence_numbers[team_id] = 0
                self.team_info[team_id] = team_info
                return True
            except Exception as e:
                print(f"Failed to accept WebSocket for {team_id}: {e}")
                return False

    async def disconnect(self, team_id: str):
        """Remove a team's WebSocket connection.

        Cleans up all connection-related state for the team, including
        the connection itself, sequence numbers, and team information.

        Parameters
        ----------
        team_id : str
            The ID of the team to disconnect

        Notes
        -----
        This method is idempotent - calling it multiple times for the
        same team_id is safe and will not raise errors.
        """
        async with self._lock:
            self.active_connections.pop(team_id, None)
            self.sequence_numbers.pop(team_id, None)
            self.team_info.pop(team_id, None)

    async def send_to_team(
        self, team_id: str, message_type: MessageType, data: dict
    ):
        """Send a message to a specific team.

        Constructs a properly formatted message with sequence number and
        timestamp, then sends it to the team if they have an active
        connection.

        Parameters
        ----------
        team_id : str
            The ID of the team to send to
        message_type : str
            The type of message (e.g., "trade_execution", "order_update")
        data : dict
            The message payload

        Notes
        -----
        Messages are automatically assigned:
        - Incrementing sequence numbers for ordering
        - Server timestamps for synchronization
        - Proper JSON formatting

        If the send fails (e.g., connection closed), the team is
        automatically disconnected.
        """
        async with self._lock:
            if team_id not in self.active_connections:
                return

            # Increment sequence number
            self.sequence_numbers[team_id] += 1
            seq = self.sequence_numbers[team_id]

            # Build message
            message = {
                "seq": seq,
                "type": message_type.value,
                "timestamp": datetime.now().isoformat(),
                "data": data,
            }

            # Send message
            websocket = self.active_connections[team_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Failed to send to {team_id}: {e}")
                await self.disconnect(team_id)

    async def broadcast_trade_execution(
        self,
        trade,  # Trade object
        buyer_order_id: str,
        seller_order_id: str,
        buyer_client_order_id: Optional[str],
        seller_client_order_id: Optional[str],
        buyer_remaining: int,
        seller_remaining: int,
        buyer_status: str,
        seller_status: str,
        buyer_fees: float,
        seller_fees: float,
    ):
        """Broadcast trade execution to both parties.

        Sends execution reports to both the buyer and seller with
        appropriate liquidity types and fees based on the aggressor side.
        This method handles the complexity of determining maker/taker status
        and ensures both parties receive accurate execution information.

        The aggressor side determines liquidity classification:
        - If buy order aggressed: buyer is taker, seller is maker
        - If sell order aggressed: seller is taker, buyer is maker

        This classification affects fee structures where makers typically
        receive rebates and takers pay fees.

        Parameters
        ----------
        trade : Trade
            The executed trade object containing price, quantity, and
            aggressor side information
        buyer_order_id : str
            Exchange-assigned order ID for the buy side
        seller_order_id : str
            Exchange-assigned order ID for the sell side
        buyer_client_order_id : Optional[str]
            Client's reference ID for the buy order, used for order
            reconciliation by the bot
        seller_client_order_id : Optional[str]
            Client's reference ID for the sell order
        buyer_remaining : int
            Quantity remaining on the buy order after this fill
        seller_remaining : int
            Quantity remaining on the sell order after this fill
        buyer_status : str
            Updated order status for buyer ('filled' or 'partially_filled')
        seller_status : str
            Updated order status for seller ('filled' or 'partially_filled')
        buyer_fees : float
            Transaction fees charged to the buyer (negative for rebates)
        seller_fees : float
            Transaction fees charged to the seller (negative for rebates)

        Notes
        -----
        This method sends two separate execution reports, one to each
        party involved in the trade. Each report contains:
        - Trade identification (trade_id, order_id, client_order_id)
        - Execution details (price, quantity, remaining)
        - Fee information based on maker/taker status
        - Updated order status

        The execution reports follow FIX protocol conventions where each
        fill generates a separate report with cumulative information.

        TradingContext
        --------------
        Market Assumptions
            - Aggressor always pays taker fees
            - Passive side receives maker rebates
            - Fees are calculated externally and passed in

        Trading Rules
            - Both parties must receive execution reports
            - Reports must indicate correct liquidity type
            - Fee structures incentivize liquidity provision

        Examples
        --------
        >>> # Buy order crosses the spread (buy aggressor)
        >>> await manager.broadcast_trade_execution(
        ...     trade=trade,  # aggressor_side="buy"
        ...     buyer_order_id="ORD-123",
        ...     seller_order_id="ORD-456",
        ...     buyer_client_order_id="CLIENT-1",
        ...     seller_client_order_id="CLIENT-2",
        ...     buyer_remaining=0,
        ...     seller_remaining=5,
        ...     buyer_status="filled",
        ...     seller_status="partially_filled",
        ...     buyer_fees=0.20,    # Taker fee
        ...     seller_fees=-0.10,  # Maker rebate
        ... )
        """
        # Determine liquidity types based on aggressor side
        if trade.aggressor_side == "buy":
            buyer_liquidity = LiquidityType.TAKER
            seller_liquidity = LiquidityType.MAKER
        else:
            buyer_liquidity = LiquidityType.MAKER
            seller_liquidity = LiquidityType.TAKER

        # Send to buyer
        await self.broadcast_execution_report(
            team_id=trade.buyer_id,
            order_id=buyer_order_id,
            client_order_id=buyer_client_order_id,
            trade_id=trade.trade_id,
            instrument_id=trade.instrument_id,
            side="buy",
            executed_quantity=trade.quantity,
            executed_price=trade.price,
            remaining_quantity=buyer_remaining,
            order_status=buyer_status,
            liquidity_type=buyer_liquidity,
            fees=buyer_fees,
        )

        # Send to seller
        await self.broadcast_execution_report(
            team_id=trade.seller_id,
            order_id=seller_order_id,
            client_order_id=seller_client_order_id,
            trade_id=trade.trade_id,
            instrument_id=trade.instrument_id,
            side="sell",
            executed_quantity=trade.quantity,
            executed_price=trade.price,
            remaining_quantity=seller_remaining,
            order_status=seller_status,
            liquidity_type=seller_liquidity,
            fees=seller_fees,
        )

    async def broadcast_new_order_ack(
        self,
        team_id: str,
        order_id: str,
        client_order_id: Optional[str],
        instrument_id: str,
        side: str,
        quantity: int,
        order_type: str,
        price: Optional[float],
    ):
        """Broadcast order acceptance to the order owner.

        Sends a new order acknowledgment message to confirm that an order
        has been validated and accepted by the exchange. This message
        indicates the order is now active and eligible for matching.

        For limit orders, acceptance means the order has been placed in
        the order book at the specified price level. For market orders,
        acceptance means the order is ready for immediate execution at
        the best available price.

        Parameters
        ----------
        team_id : str
            Team identifier that submitted the order
        order_id : str
            Exchange-assigned unique order identifier used for all
            subsequent order-related operations
        client_order_id : Optional[str]
            Client's reference identifier for order tracking and
            reconciliation. Bots use this to match responses to their
            internal order records
        instrument_id : str
            Identifier of the instrument being traded (e.g., "SPX_4500_CALL")
        side : str
            Order side, either "buy" or "sell"
        quantity : int
            Number of contracts in the order
        order_type : str
            Type of order, either "limit" or "market"
        price : Optional[float]
            Limit price for the order. None for market orders which
            execute at the best available price

        Notes
        -----
        Order acknowledgment is the first message a bot receives after
        submitting an order, confirming the order passed all validations:
        - Instrument is valid and tradeable
        - Quantity is within allowed limits
        - Price is valid (for limit orders)
        - Position limits won't be exceeded
        - Bot has appropriate permissions

        The order_id returned in this message must be used for all
        subsequent operations (cancellation, modification, etc.).

        TradingContext
        --------------
        Market Assumptions
            - Orders are processed in submission order
            - Acknowledgment doesn't guarantee execution
            - Market conditions may change before execution

        Trading Rules
            - Only acknowledged orders can be cancelled
            - Order priority is established at acknowledgment time
            - Late orders may be rejected after market close

        Examples
        --------
        >>> # Acknowledge a limit buy order
        >>> await manager.broadcast_new_order_ack(
        ...     team_id="TEAM-001",
        ...     order_id="ORD-12345",
        ...     client_order_id="CLIENT-001",
        ...     instrument_id="SPX_4500_CALL",
        ...     side="buy",
        ...     quantity=10,
        ...     order_type="limit",
        ...     price=128.50
        ... )
        """
        data = build_new_order_ack(
            order_id=order_id,
            client_order_id=client_order_id,
            instrument_id=instrument_id,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
        )
        await self.send_to_team(team_id, MessageType.NEW_ORDER_ACK, data)

    async def broadcast_new_order_reject(
        self,
        team_id: str,
        order_id: str,
        client_order_id: Optional[str],
        reason: str,
        error_code: Optional[str] = None,
    ):
        """Broadcast order rejection to the order owner.

        Parameters
        ----------
        team_id : str
            Team that submitted the order
        order_id : str
            Exchange-assigned order ID
        client_order_id : Optional[str]
            Client's order reference
        reason : str
            Human-readable rejection reason
        error_code : Optional[str]
            Machine-readable error code
        """
        data = build_new_order_reject(
            order_id=order_id,
            client_order_id=client_order_id,
            reason=reason,
            error_code=error_code,
        )
        await self.send_to_team(team_id, MessageType.NEW_ORDER_REJECT, data)

    async def broadcast_execution_report(
        self,
        team_id: str,
        order_id: str,
        client_order_id: Optional[str],
        trade_id: str,
        instrument_id: str,
        side: str,
        executed_quantity: int,
        executed_price: float,
        remaining_quantity: int,
        order_status: str,
        liquidity_type: LiquidityType,
        fees: float,
    ):
        """Broadcast trade execution report to the order owner.

        Parameters
        ----------
        team_id : str
            Team that owns the order
        order_id : str
            Exchange-assigned order ID
        client_order_id : Optional[str]
            Client's order reference
        trade_id : str
            Unique trade identifier
        instrument_id : str
            Instrument that was traded
        side : str
            Order side ("buy" or "sell")
        executed_quantity : int
            Quantity filled in this execution
        executed_price : float
            Price at which the trade occurred
        remaining_quantity : int
            Quantity still open on the order
        order_status : str
            Updated order status
        liquidity_type : LiquidityType
            Whether this was maker or taker
        fees : float
            Fees charged for this execution
        """
        data = build_execution_report(
            order_id=order_id,
            client_order_id=client_order_id,
            trade_id=trade_id,
            instrument_id=instrument_id,
            side=side,
            executed_quantity=executed_quantity,
            executed_price=executed_price,
            remaining_quantity=remaining_quantity,
            order_status=order_status,
            liquidity_type=liquidity_type,
            fees=fees,
        )
        await self.send_to_team(team_id, MessageType.EXECUTION_REPORT, data)

    async def broadcast_cancel_ack(
        self,
        team_id: str,
        order_id: str,
        client_order_id: Optional[str],
        cancelled_quantity: int,
        reason: str = "user_requested",
    ):
        """Broadcast order cancellation acknowledgment.

        Sends a cancellation confirmation message to the team that
        successfully cancelled their order. This message indicates
        that the order has been removed from the order book and
        cannot be matched.

        Parameters
        ----------
        team_id : str
            Team identifier that owns the cancelled order
        order_id : str
            Exchange-assigned order ID that was cancelled
        client_order_id : Optional[str]
            Client's order reference for reconciliation. None if
            the client didn't provide one with the original order
        cancelled_quantity : int
            Number of contracts that were cancelled. For partially
            filled orders, this is the unfilled remainder
        reason : str, default="user_requested"
            Reason for cancellation. Common values:

            - "user_requested": Client initiated cancellation
            - "tick_end": Automatic end-of-tick cancellation
            - "session_end": Trading session closed

        Notes
        -----
        Cancellation acknowledgments are only sent to the order owner.
        Other market participants do not receive notifications about
        cancelled orders to prevent information leakage.

        The cancelled_quantity may be less than the original order
        quantity if partial fills occurred before cancellation.

        TradingContext
        --------------
        Successful cancellation means:

        - The order is no longer visible in the order book
        - No further matches can occur against this order
        - Any unfilled quantity is permanently removed
        - Position limits are updated to reflect the cancellation

        Examples
        --------
        >>> # Cancel acknowledgment for fully cancelled order
        >>> await ws_manager.broadcast_cancel_ack(
        ...     team_id="TEAM_001",
        ...     order_id="ORD_12345",
        ...     client_order_id="CLIENT_001",
        ...     cancelled_quantity=10,
        ...     reason="user_requested"
        ... )

        >>> # Cancel acknowledgment for partially filled order
        >>> await ws_manager.broadcast_cancel_ack(
        ...     team_id="TEAM_001",
        ...     order_id="ORD_12346",
        ...     client_order_id=None,
        ...     cancelled_quantity=7,  # 3 were already filled
        ...     reason="user_requested"
        ... )
        """
        data = build_cancel_ack(
            order_id=order_id,
            client_order_id=client_order_id,
            cancelled_quantity=cancelled_quantity,
            reason=reason,
        )
        await self.send_to_team(team_id, MessageType.CANCEL_ACK, data)

    async def broadcast_cancel_reject(
        self,
        team_id: str,
        order_id: str,
        client_order_id: Optional[str],
        reason: str,
    ):
        """Broadcast order cancellation rejection.

        Sends a cancellation failure message to the team that
        attempted to cancel an order. This indicates the order
        could not be cancelled and remains active or was already
        processed.

        Parameters
        ----------
        team_id : str
            Team identifier that requested the cancellation
        order_id : str
            Exchange-assigned order ID that could not be cancelled
        client_order_id : Optional[str]
            Client's order reference for reconciliation. None if
            the client didn't provide one with the original order
        reason : str
            Human-readable explanation of why cancellation failed.
            Common reasons include:

            - "Order not found": Order ID doesn't exist
            - "Order already filled": Too late, order executed
            - "Unauthorized": Not the order owner
            - "Order already cancelled": Duplicate cancel request

        Notes
        -----
        Cancel rejections help bots understand the current state
        of their orders and adjust their strategies accordingly.
        The reason field should be specific enough for automated
        handling by trading algorithms.

        TradingContext
        --------------
        Cancel rejections occur in several scenarios:

        - Racing with fills: Order matched before cancel processed
        - Invalid order ID: Typo or stale reference
        - Permission issues: Attempting to cancel another's order
        - Duplicate requests: Order already cancelled

        The FIFO queue ensures temporal fairness - a fill that
        arrives before a cancel will always execute first.

        Examples
        --------
        >>> # Rejection due to order already filled
        >>> await ws_manager.broadcast_cancel_reject(
        ...     team_id="TEAM_001",
        ...     order_id="ORD_12345",
        ...     client_order_id="CLIENT_001",
        ...     reason="Order already filled"
        ... )

        >>> # Rejection due to invalid order ID
        >>> await ws_manager.broadcast_cancel_reject(
        ...     team_id="TEAM_001",
        ...     order_id="ORD_INVALID",
        ...     client_order_id=None,
        ...     reason="Order not found"
        ... )
        """
        data = build_cancel_reject(
            order_id=order_id,
            client_order_id=client_order_id,
            reason=reason,
        )
        await self.send_to_team(team_id, MessageType.CANCEL_REJECT, data)

    async def broadcast_market_data(
        self,
        instrument_id: str,
        bid: Optional[float],
        ask: Optional[float],
        last: Optional[float],
        bid_size: Optional[int] = None,
        ask_size: Optional[int] = None,
    ):
        """Broadcast market data update to all connected teams.

        Sends current market prices for an instrument to all teams that
        are authorized to receive market data based on their role.

        Parameters
        ----------
        instrument_id : str
            Instrument with updated prices
        bid : Optional[float]
            Best bid price (None if no bids)
        ask : Optional[float]
            Best ask price (None if no asks)
        last : Optional[float]
            Last traded price (None if no trades)
        bid_size : Optional[int]
            Size at best bid
        ask_size : Optional[int]
            Size at best ask

        Notes
        -----
        Market data access may be restricted by role in future versions.
        Currently, all connected teams receive all market data updates.
        """
        data = build_market_data(
            instrument_id=instrument_id,
            bid=bid,
            ask=ask,
            last=last,
            bid_size=bid_size,
            ask_size=ask_size,
        )

        # Send to all connected teams
        # In future: filter by role permissions
        team_ids = list(self.active_connections.keys())
        for team_id in team_ids:
            await self.send_to_team(team_id, MessageType.MARKET_DATA, data)

    async def send_position_snapshot(
        self, team_id: str, positions: Dict[str, int]
    ):
        """Send current position snapshot to a team.

        Typically called when a team first connects to provide them with
        their current position state.

        Parameters
        ----------
        team_id : str
            Team to send snapshot to
        positions : Dict[str, int]
            Current positions by instrument
        """
        data = build_position_snapshot(positions)
        await self.send_to_team(team_id, MessageType.POSITION_SNAPSHOT, data)

    async def broadcast_signal(
        self,
        signal_type: str,
        data: dict,
        allowed_roles: Set[str],
    ):
        """Broadcast a trading signal to teams with appropriate access.

        Sends role-specific signals (e.g., volatility forecasts for hedge
        funds, tracking error for arbitrage desks) only to teams with the
        correct role permissions.

        Parameters
        ----------
        signal_type : str
            Type of signal (e.g., "volatility_forecast", "tracking_error")
        data : dict
            Signal data payload
        allowed_roles : Set[str]
            Roles that should receive this signal

        Notes
        -----
        This implements the role-based signal access control that gives
        different teams different advantages based on their trading role.
        """
        signal_data = {"signal_type": signal_type, **data}

        # Send only to teams with allowed roles
        team_ids = list(self.active_connections.keys())
        for team_id in team_ids:
            if team_id in self.team_info:
                team_role = self.team_info[team_id].role
                if team_role in allowed_roles:
                    await self.send_to_team(
                        team_id, MessageType.SIGNAL, signal_data
                    )

    async def broadcast_event(self, event_type: str, event_data: dict):
        """Broadcast a market event to all connected teams.

        Sends news events, market announcements, or game state changes
        to all connected teams simultaneously.

        Parameters
        ----------
        event_type : str
            Type of event (e.g., "news", "tick_start", "game_end")
        event_data : dict
            Event details and parameters
        """
        data = {"event_type": event_type, **event_data}

        # Send to all teams
        team_ids = list(self.active_connections.keys())
        for team_id in team_ids:
            await self.send_to_team(team_id, MessageType.EVENT, data)

    async def send_connection_status(
        self, team_id: str, status: str, message: str
    ):
        """Send connection status to a specific team.

        Parameters
        ----------
        team_id : str
            Team to notify
        status : str
            Connection status (e.g., "connected", "authenticated", "ready")
        message : str
            Human-readable status message
        """
        data = build_connection_status(status=status, message=message)
        await self.send_to_team(team_id, MessageType.CONNECTION_STATUS, data)

    async def broadcast_quote_ack(
        self,
        team_id: str,
        instrument_id: str,
        bid_price: float,
        ask_price: float,
        size: int,
    ):
        """Acknowledge quote submission for market makers.

        Parameters
        ----------
        team_id : str
            Market maker team
        instrument_id : str
            Instrument being quoted
        bid_price : float
            Bid price level
        ask_price : float
            Ask price level
        size : int
            Size at both levels
        """
        data = build_quote_ack(
            instrument_id=instrument_id,
            bid_price=bid_price,
            ask_price=ask_price,
            size=size,
        )
        await self.send_to_team(team_id, MessageType.QUOTE_ACK, data)

    async def broadcast_quote_reject(
        self, team_id: str, instrument_id: str, reason: str
    ):
        """Reject quote submission for market makers.

        Parameters
        ----------
        team_id : str
            Market maker team
        instrument_id : str
            Instrument quote was for
        reason : str
            Why quote was rejected
        """
        data = build_quote_reject(instrument_id=instrument_id, reason=reason)
        await self.send_to_team(team_id, MessageType.QUOTE_REJECT, data)

    def get_connection_count(self) -> int:
        """Get the number of active connections.

        Returns
        -------
        int
            Number of teams currently connected
        """
        return len(self.active_connections)

    def is_connected(self, team_id: str) -> bool:
        """Check if a team is currently connected.

        Parameters
        ----------
        team_id : str
            Team ID to check

        Returns
        -------
        bool
            True if team has active WebSocket connection
        """
        return team_id in self.active_connections


# Global WebSocket manager instance
ws_manager = WebSocketManager()
