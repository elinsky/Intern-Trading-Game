"""Thread 4: Trade Publisher - updates positions and sends responses."""

import threading
from queue import Queue
from typing import Dict

from ...infrastructure.api.models import OrderResponse
from ...infrastructure.config.fee_config import FeeConfig
from ...services.position_management import PositionManagementService
from ...services.trade_processing import TradeProcessingService
from ...services.trading_fees import TradingFeeService


def trade_publisher_thread(
    trade_queue: Queue,
    websocket_queue: Queue,
    fee_config_dict: Dict,
    positions: Dict[str, Dict[str, int]],
    positions_lock: threading.RLock,
    pending_orders: Dict[str, threading.Event],
    order_responses: Dict[str, OrderResponse],
):
    """Thread 4: Trade Publisher - updates positions and sends responses."""
    print("Trade publisher thread started")

    # Initialize services once at thread startup
    fee_config = FeeConfig.from_config_dict(fee_config_dict)
    fee_service = TradingFeeService(fee_config)
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
            response = trade_service.process_trade_result(
                result, order, team_info
            )

            # Send response back (infrastructure concern)
            if order.order_id in pending_orders:
                order_responses[order.order_id] = response
                pending_orders[order.order_id].set()

        except Exception as e:
            print(f"Trade publisher thread error: {e}")
