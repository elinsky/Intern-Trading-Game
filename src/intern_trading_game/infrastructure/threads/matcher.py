"""Thread 3: Matching Engine - processes validated orders."""

import threading
from datetime import datetime
from queue import Queue
from typing import Dict

from ...infrastructure.api.models import OrderResponse
from ...services.order_matching import OrderMatchingService


def matching_thread(
    match_queue: Queue,
    trade_queue: Queue,
    websocket_queue: Queue,
    exchange,
    pending_orders: Dict[str, threading.Event],
    order_responses: Dict[str, OrderResponse],
):
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
                                "price": order.price,
                                "status": result.status,
                            },
                        )
                    )

                # Send to trade publisher
                trade_queue.put((result, order, team_info))

            except Exception as e:
                # Handle exchange errors using service
                result = matching_service.handle_exchange_error(e, order)

                # Create response from error result
                response = OrderResponse(
                    order_id=result.order_id,
                    status=result.status,
                    timestamp=datetime.now(),
                    error_code=result.error_code,
                    error_message=result.error_message,
                )

                # Find the response event
                if order.order_id in pending_orders:
                    order_responses[order.order_id] = response
                    pending_orders[order.order_id].set()

        except Exception as e:
            print(f"Matching thread error: {e}")
