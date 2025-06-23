"""Trade processing service implementation.

This module provides the concrete implementation of trade processing
business logic for the trading system, handling fee calculations,
position updates, and response generation.
"""

from datetime import datetime
from queue import Queue
from typing import Dict, List, Optional, Tuple

from ...infrastructure.api.models import OrderResponse, TeamInfo
from ...services.interfaces import TradeProcessingServiceInterface
from ..exchange.components.core.models import Order, OrderResult, Trade
from .fee_service import TradingFeeService
from .position_service import PositionManagementService


class TradeProcessingService(TradeProcessingServiceInterface):
    """Service for processing trade execution results.

    This service handles all aspects of trade processing including fee
    calculation, position updates, and order response generation. It
    coordinates multiple concerns internally while presenting a simple
    interface to the thread controller.

    The service processes trades atomically, ensuring consistency between
    fee calculations, position updates, and response generation. It supports
    complex scenarios including partial fills, multiple fills with mixed
    liquidity types, and role-specific fee structures.

    Parameters
    ----------
    fee_service : TradingFeeService
        Service for calculating trading fees based on role and liquidity
    position_service : PositionManagementService
        Service for thread-safe position updates
    websocket_queue : Queue
        Queue for sending execution reports to WebSocket thread

    Attributes
    ----------
    fee_service : TradingFeeService
        The fee calculation service
    position_service : PositionManagementService
        The position management service
    websocket_queue : Queue
        Queue for WebSocket messages

    Notes
    -----
    This service extracts business logic from trade_publisher_thread()
    lines 323-427, consolidating the complex trade processing workflow
    into a testable, reusable component.

    The service maintains the exact behavior of the original implementation
    including:
    - Fee calculation per trade with role-specific rules
    - Position updates only when fills occur
    - Execution report generation for each fill
    - Volume-weighted average price calculation

    TradingContext
    --------------
    Trade processing is a critical path in the trading system that must:
    - Complete quickly to maintain real-time position updates
    - Ensure atomic position updates for risk management
    - Calculate accurate fees for P&L tracking
    - Generate detailed execution reports for client notifications

    Market makers receive rebates for providing liquidity, creating an
    incentive to maintain tight spreads and deep order books.

    Examples
    --------
    >>> # Create service with dependencies
    >>> trade_service = TradeProcessingService(
    ...     fee_service=fee_service,
    ...     position_service=position_service,
    ...     websocket_queue=ws_queue
    ... )
    >>>
    >>> # Process a filled order
    >>> result = OrderResult(
    ...     order_id="ORD123",
    ...     status="filled",
    ...     fills=[Trade(...), Trade(...)],
    ...     remaining_quantity=0
    ... )
    >>> response = trade_service.process_trade_result(result, order, team)
    >>>
    >>> # Response contains aggregated information
    >>> print(f"Filled: {response.filled_quantity}")
    >>> print(f"Avg Price: {response.average_price}")
    >>> print(f"Total Fees: {response.fees}")
    """

    def __init__(
        self,
        fee_service: TradingFeeService,
        position_service: PositionManagementService,
        websocket_queue: Queue,
    ):
        """Initialize the trade processing service.

        Parameters
        ----------
        fee_service : TradingFeeService
            Service for fee calculations
        position_service : PositionManagementService
            Service for position updates
        websocket_queue : Queue
            Queue for WebSocket messages
        """
        self.fee_service = fee_service
        self.position_service = position_service
        self.websocket_queue = websocket_queue

    def process_trade_result(
        self, result: OrderResult, order: Order, team: TeamInfo
    ) -> OrderResponse:
        """Process trade execution result into complete order response.

        Coordinates all aspects of trade processing including fee
        calculation, position updates, and response generation.

        Parameters
        ----------
        result : OrderResult
            The result from the matching engine containing order status
            and any fill information
        order : Order
            The original order that was matched
        team : TeamInfo
            Team information including role for fee calculation

        Returns
        -------
        OrderResponse
            Complete response containing:
            - order_id: str
            - status: str matching the OrderResult status
            - timestamp: datetime of processing
            - filled_quantity: int total quantity filled
            - average_price: Optional[float] volume-weighted average
            - fees: float total fees (negative for rebates)
            - liquidity_type: Optional[str] "maker", "taker", or "mixed"

        Notes
        -----
        The processing follows this sequence:
        1. Calculate total fill quantity
        2. For each fill:
           - Determine liquidity type
           - Calculate fees
           - Send execution report
        3. Update positions if any fills occurred
        4. Calculate volume-weighted average price
        5. Create final response with aggregated data

        Side effects include:
        - Position updates via PositionManagementService
        - Execution reports sent to websocket_queue

        TradingContext
        --------------
        Trade processing must handle various scenarios:
        - Single fill: Order completely filled by one counterparty
        - Multiple fills: Order matched against multiple counterparties
        - Mixed liquidity: Some fills as maker, others as taker
        - No fills: Order rejected or resting in book

        Fee calculation depends on both role and liquidity type,
        with market makers receiving rebates for providing liquidity.

        Examples
        --------
        >>> # Process a partially filled order
        >>> result = OrderResult(
        ...     order_id="ORD123",
        ...     status="partially_filled",
        ...     fills=[Trade(quantity=50, price=100.0, ...)],
        ...     remaining_quantity=50
        ... )
        >>> response = service.process_trade_result(result, order, team)
        >>> assert response.filled_quantity == 50
        >>> assert response.status == "partially_filled"
        """
        # Initialize aggregation variables
        total_fees = 0.0
        liquidity_types = set()
        # TODO: Remove int() cast when exchange models are updated to use int for quantity
        fill_quantity = int(sum(trade.quantity for trade in result.fills))

        # Process each fill
        if fill_quantity > 0:
            for trade in result.fills:
                # Process individual trade
                fees, liquidity_type = self._process_single_fill(
                    trade, order, team
                )
                total_fees += fees
                liquidity_types.add(liquidity_type)

            # Update positions after all fills processed
            position_delta = self._calculate_position_delta(
                fill_quantity, order.side
            )
            self.position_service.update_position(
                team.team_id, order.instrument_id, position_delta
            )

            # Update counterparty positions for all fills
            self._update_counterparty_positions(
                result.fills, order, team.team_id
            )

        # Calculate average price if there were fills
        average_price = None
        if fill_quantity > 0:
            average_price = self._calculate_average_price(result.fills)

        # Determine overall liquidity type
        overall_liquidity_type = self._determine_overall_liquidity_type(
            liquidity_types
        )

        # Create response with aggregated data
        response = OrderResponse(
            order_id=order.order_id,
            status=result.status,
            timestamp=datetime.now(),
            filled_quantity=fill_quantity,
            average_price=average_price,
            fees=total_fees,
            liquidity_type=overall_liquidity_type,
        )

        return response

    def _process_single_fill(
        self, trade: Trade, order: Order, team: TeamInfo
    ) -> Tuple[float, str]:
        """Process a single trade fill.

        Calculates fees and sends execution report for one trade.

        Parameters
        ----------
        trade : Trade
            The individual trade to process
        order : Order
            The original order
        team : TeamInfo
            Team information for fee calculation

        Returns
        -------
        Tuple[float, str]
            A tuple of (fees, liquidity_type) where:
            - fees: float, positive for rebates, negative for charges
            - liquidity_type: str, either "maker" or "taker"

        Notes
        -----
        This method encapsulates the per-trade processing logic,
        including fee calculation and execution report generation.

        The execution report sent via WebSocket includes all trade
        details needed for client-side position tracking and P&L
        calculations.
        """
        # Determine liquidity type
        liquidity_type = self.fee_service.determine_liquidity_type(
            trade.aggressor_side, order.side
        )

        # Calculate fees
        # TODO: Remove int() cast when Trade.quantity is changed to int
        fees = self.fee_service.calculate_fee(
            int(trade.quantity), team.role, liquidity_type
        )

        # Create execution report data
        report_data = self._create_execution_report_data(
            trade, order, liquidity_type, fees
        )

        # Send execution report via WebSocket
        self.websocket_queue.put(
            ("execution_report", team.team_id, report_data)
        )

        return fees, liquidity_type

    def _calculate_position_delta(self, quantity: int, side: str) -> int:
        """Calculate the position change from filled quantity.

        Parameters
        ----------
        quantity : int
            The filled quantity
        side : str
            The order side ("buy" or "sell")

        Returns
        -------
        int
            Position delta: positive for buys, negative for sells

        Notes
        -----
        Buy orders increase position (positive delta) while sell
        orders decrease position (negative delta).
        """
        if side == "buy":
            return quantity
        else:
            return -quantity

    def _calculate_average_price(self, trades: List[Trade]) -> float:
        """Calculate volume-weighted average price from trades.

        Parameters
        ----------
        trades : List[Trade]
            List of trades to average

        Returns
        -------
        float
            Volume-weighted average price

        Notes
        -----
        The formula used is:

        $$\\text{VWAP} = \\frac{\\sum_{i=1}^{n} \\text{price}_i \\times \\text{quantity}_i}{\\sum_{i=1}^{n} \\text{quantity}_i}$$

        This ensures larger trades have proportionally more impact
        on the average price, accurately reflecting execution quality.
        """
        # TODO: Remove int() casts when Trade.quantity is changed to int
        total_value = sum(trade.price * trade.quantity for trade in trades)
        total_quantity = sum(trade.quantity for trade in trades)
        return total_value / total_quantity

    def _determine_overall_liquidity_type(
        self, liquidity_types: set
    ) -> Optional[str]:
        """Determine the overall liquidity type from individual fills.

        Parameters
        ----------
        liquidity_types : set
            Set of liquidity types from individual fills

        Returns
        -------
        Optional[str]
            "maker" if all fills were maker
            "taker" if all fills were taker
            "mixed" if both types present
            None if no fills

        Notes
        -----
        This aggregation helps clients understand their overall
        liquidity provision/removal for fee analysis.
        """
        if not liquidity_types:
            return None
        elif len(liquidity_types) == 1:
            return liquidity_types.pop()
        else:
            return "mixed"

    def _create_execution_report_data(
        self, trade: Trade, order: Order, liquidity_type: str, fees: float
    ) -> Dict:
        """Create execution report data for WebSocket broadcast.

        Parameters
        ----------
        trade : Trade
            The executed trade
        order : Order
            The original order
        liquidity_type : str
            Whether this fill was maker or taker
        fees : float
            Fees for this trade

        Returns
        -------
        Dict
            Execution report data matching the expected WebSocket format

        Notes
        -----
        The format must match exactly what the WebSocket thread expects
        to maintain compatibility with existing client implementations.
        """
        return {
            "trade": trade,
            "buyer_order_id": trade.buyer_order_id,
            "seller_order_id": trade.seller_order_id,
            "client_order_id": order.client_order_id
            if order.order_id in [trade.buyer_order_id, trade.seller_order_id]
            else None,
            "liquidity_type": liquidity_type,
            "fees": fees,
        }

    def _update_counterparty_positions(
        self, trades: List[Trade], order: Order, aggressor_team_id: str
    ) -> None:
        """Update positions for counterparties in all trades.

        For each trade, updates the position of the counterparty (the side
        that didn't initiate the order). This ensures both sides of every
        trade have their positions properly updated.

        Parameters
        ----------
        trades : List[Trade]
            List of trades to process counterparty updates for
        order : Order
            The aggressor order that initiated the trades
        aggressor_team_id : str
            Team ID of the order initiator (already updated)

        Notes
        -----
        This method implements proper trade settlement by ensuring both
        counterparties have their positions updated:
        - Aggressor: Already updated in main flow
        - Counterparty: Updated here

        The position delta for the counterparty is always opposite to
        the aggressor's delta to maintain position conservation.

        Examples
        --------
        For a buy order that trades against sell orders:
        - Aggressor (buyer): +quantity position
        - Counterparty (seller): -quantity position

        For a sell order that trades against buy orders:
        - Aggressor (seller): -quantity position
        - Counterparty (buyer): +quantity position
        """
        for trade in trades:
            # Get counterparty team ID and position delta
            counterparty_team_id, counterparty_delta = (
                self._get_counterparty_info(trade, order, aggressor_team_id)
            )

            # Skip if counterparty is the same as aggressor (self-trading)
            if counterparty_team_id == aggressor_team_id:
                continue

            # Update counterparty position
            # TODO: Remove int() cast when Trade.quantity is changed to int
            self.position_service.update_position(
                counterparty_team_id,
                order.instrument_id,
                counterparty_delta * int(trade.quantity),
            )

    def _get_counterparty_info(
        self, trade: Trade, order: Order, aggressor_team_id: str
    ) -> Tuple[str, int]:
        """Get counterparty team ID and position delta for a trade.

        Determines which side of the trade is the counterparty and
        calculates the appropriate position delta.

        Parameters
        ----------
        trade : Trade
            The trade to analyze
        order : Order
            The aggressor order
        aggressor_team_id : str
            Team ID of the order initiator

        Returns
        -------
        Tuple[str, int]
            A tuple of (counterparty_team_id, position_delta_sign) where:
            - counterparty_team_id: Team ID of the counterparty
            - position_delta_sign: +1 for buys, -1 for sells

        Notes
        -----
        The counterparty is determined by comparing the aggressor's order ID
        with the buyer_order_id and seller_order_id in the trade.

        Position deltas are:
        - +1 for buyers (position increases)
        - -1 for sellers (position decreases)
        """
        # Determine if aggressor is buyer or seller in this trade
        if order.order_id == trade.buyer_order_id:
            # Aggressor is buyer, counterparty is seller
            counterparty_team_id = trade.seller_id
            counterparty_delta = -1  # Seller decreases position
        else:
            # Aggressor is seller, counterparty is buyer
            counterparty_team_id = trade.buyer_id
            counterparty_delta = +1  # Buyer increases position

        return counterparty_team_id, counterparty_delta
