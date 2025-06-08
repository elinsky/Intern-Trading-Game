"""Thread 2: Order Validator - validates orders from queue."""

import threading
from datetime import datetime
from queue import Queue
from typing import Dict

from ...infrastructure.api.models import OrderResponse
from ...services.order_validation import OrderValidationService


def validator_thread(
    order_queue: Queue,
    match_queue: Queue,
    websocket_queue: Queue,
    validation_service: OrderValidationService,
    orders_this_tick: Dict[str, int],
    orders_lock: threading.RLock,
    pending_orders: Dict[str, threading.Event],
    order_responses: Dict[str, OrderResponse],
):
    """Thread 2: Order Validator - validates orders from queue.

    This thread implements the order validation pipeline, continuously
    processing messages from the order queue. It handles both new order
    submissions and cancellation requests, maintaining strict FIFO
    processing order to ensure market fairness.

    The validator thread acts as a gatekeeper for new orders, ensuring
    that only orders meeting all constraints (position limits, order
    size, etc.) proceed to execution. For cancellations, it verifies
    ownership before forwarding to the exchange.

    Notes
    -----
    The thread uses a blocking get() on the order queue, which means
    it sleeps when no messages are available, minimizing CPU usage.

    Messages follow a 4-tuple format:
    (message_type, data, team_info, response_event)
    where message_type is either "new_order" or "cancel_order".

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
    - Provide detailed cancellation failure reasons

    Examples
    --------
    The thread processes messages in this sequence:

    For new orders:

    1. Receive ("new_order", order, team_info, response_event)
    2. Build ValidationContext with current state
    3. Run constraint validation
    4. If valid: forward to match_queue
    5. If invalid: send rejection via response_event

    For cancellations:

    1. Receive ("cancel_order", order_id, team_info, response_event)
    2. Call exchange.cancel_order() with ownership check
    3. Send cancel_ack or cancel_reject via WebSocket
    4. Return response via response_event
    """
    print("Validator thread started")

    while True:
        try:
            # Get message from queue (4-tuple format)
            queue_data = order_queue.get()
            if queue_data is None:  # Shutdown signal
                break

            # Unpack the consistent 4-tuple format
            message_type, data, team_info, response_event = queue_data

            if message_type == "new_order":
                # Handle new order submission
                order = data

                # Validate order using service
                result = validation_service.validate_new_order(
                    order, team_info
                )

                if result.status == "accepted":
                    # Send to matching engine
                    match_queue.put((order, team_info))

                    # Update order count
                    with orders_lock:
                        current_count = orders_this_tick.get(
                            team_info.team_id, 0
                        )
                        orders_this_tick[team_info.team_id] = current_count + 1
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

            elif message_type == "cancel_order":
                # Handle order cancellation
                order_id = data

                # Validate and attempt cancellation using service
                success, reason = validation_service.validate_cancellation(
                    order_id, team_info.team_id
                )

                if success:
                    # Send cancel acknowledgment via WebSocket
                    websocket_queue.put(
                        (
                            "order_cancel_ack",
                            team_info.team_id,
                            {
                                "order_id": order_id,
                                "client_order_id": None,  # TODO: track this
                                "cancelled_quantity": 0,  # TODO: get from exchange
                                "reason": "user_requested",
                            },
                        )
                    )

                    # Create success response
                    response = OrderResponse(
                        order_id=order_id,
                        status="cancelled",
                        timestamp=datetime.now(),
                    )
                else:
                    # Use failure reason from service
                    error_code = "CANCEL_FAILED"

                    # Send cancel rejection via WebSocket
                    websocket_queue.put(
                        (
                            "order_cancel_reject",
                            team_info.team_id,
                            {
                                "order_id": order_id,
                                "client_order_id": None,
                                "reason": reason,
                            },
                        )
                    )

                    # Create rejection response
                    response = OrderResponse(
                        order_id=order_id,
                        status="rejected",
                        timestamp=datetime.now(),
                        error_code=error_code,
                        error_message=f"Cancel failed: {reason}",
                    )

                # Send response back to API thread
                order_responses[order_id] = response
                response_event.set()

        except Exception as e:
            print(f"Validator thread error: {e}")
