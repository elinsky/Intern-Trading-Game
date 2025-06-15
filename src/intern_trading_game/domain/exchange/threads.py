"""Exchange service thread implementations.

This module contains thread functions that are owned by the Exchange Service,
following the service-oriented architecture principle of thread ownership.
"""

import threading
import time
from datetime import datetime
from queue import Queue
from typing import Dict

from ...constants.errors import ErrorCodes, ErrorMessages
from ...infrastructure.api.models import ApiError, ApiResponse, OrderResponse
from ...infrastructure.api.websocket_messages import MessageType
from ...services.order_matching import OrderMatchingService
from ...services.order_validation import OrderValidationService


def validator_thread(
    order_queue: Queue,
    match_queue: Queue,
    websocket_queue: Queue,
    validation_service: OrderValidationService,
    pending_orders: Dict[str, threading.Event],
    order_responses: Dict[str, ApiResponse],
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

    Parameters
    ----------
    order_queue : Queue
        Queue containing order validation requests
    match_queue : Queue
        Queue for sending validated orders to matching engine
    websocket_queue : Queue
        Queue for sending WebSocket messages to clients
    validation_service : OrderValidationService
        Service for order validation logic (owns rate limiting state)
    pending_orders : Dict[str, threading.Event]
        Events for coordinating order responses
    order_responses : Dict[str, ApiResponse]
        Response storage for order submissions

    Notes
    -----
    The thread uses a blocking get() on the order queue, which means
    it sleeps when no messages are available, minimizing CPU usage.

    Messages follow a 5-tuple format:
    (message_type, data, team_info, response_event, request_id)
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

    1. Receive ("new_order", order, team_info, response_event, request_id)
    2. Build ValidationContext with current state
    3. Run constraint validation
    4. If valid: forward to match_queue and create success ApiResponse
    5. If invalid: send rejection via WebSocket and create error ApiResponse

    For cancellations:

    1. Receive ("cancel_order", order_id, team_info, response_event, request_id)
    2. Call exchange.cancel_order() with ownership check
    3. Send cancel_ack or cancel_reject via WebSocket
    4. Return ApiResponse via response_event
    """
    print("Validator thread started")

    while True:
        try:
            # Get message from queue (5-tuple format)
            queue_data = order_queue.get()
            if queue_data is None:  # Shutdown signal
                break

            # Unpack the consistent 5-tuple format
            message_type, data, team_info, response_event, request_id = (
                queue_data
            )

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

                    # Update order count through validation service
                    # Use current time for rate limiting accuracy
                    validation_service.increment_order_count(
                        team_info.team_id, time.time()
                    )

                    # Create success response
                    response = ApiResponse(
                        success=True,
                        request_id=request_id,
                        order_id=order.order_id,
                        data=None,
                        error=None,
                        timestamp=datetime.now(),
                    )
                    response_key = f"{order.order_id}:{request_id}"
                    order_responses[response_key] = response
                    response_event.set()

                elif result.status == "rejected":
                    # When rejected, error fields are guaranteed to be set
                    assert result.error_code is not None
                    assert result.error_message is not None

                    # Send rejection via WebSocket
                    websocket_queue.put(
                        (
                            MessageType.NEW_ORDER_REJECT.value,
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
                    response = ApiResponse(
                        success=False,
                        request_id=request_id,
                        order_id=None,  # No order_id on failure
                        data=None,
                        error=ApiError(
                            code=result.error_code,
                            message=result.error_message,
                            details=None,
                        ),
                        timestamp=datetime.now(),
                    )
                    response_key = f"{order.order_id}:{request_id}"
                    order_responses[response_key] = response
                    response_event.set()

                else:
                    # Unexpected status - log and treat as rejection
                    print(f"Unexpected validation status: {result.status}")
                    response = ApiResponse(
                        success=False,
                        request_id=request_id,
                        order_id=None,
                        data=None,
                        error=ApiError(
                            code=ErrorCodes.INTERNAL_ERROR,
                            message=f"Unexpected validation status: {result.status}",
                            details=None,
                        ),
                        timestamp=datetime.now(),
                    )
                    response_key = f"{order.order_id}:{request_id}"
                    order_responses[response_key] = response
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
                            MessageType.CANCEL_ACK.value,
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
                    response = ApiResponse(
                        success=True,
                        request_id=request_id,
                        order_id=order_id,
                        data=None,
                        error=None,
                        timestamp=datetime.now(),
                    )
                else:
                    # Use failure reason from service
                    error_code = ErrorCodes.CANCEL_FAILED

                    # Send cancel rejection via WebSocket
                    websocket_queue.put(
                        (
                            MessageType.CANCEL_REJECT.value,
                            team_info.team_id,
                            {
                                "order_id": order_id,
                                "client_order_id": None,
                                "reason": reason,
                            },
                        )
                    )

                    # Create rejection response
                    response = ApiResponse(
                        success=False,
                        request_id=request_id,
                        order_id=None,
                        data=None,
                        error=ApiError(
                            code=error_code,
                            message=ErrorMessages.format_cancel_failed(
                                reason or "Unknown error"
                            ),
                            details=None,
                        ),
                        timestamp=datetime.now(),
                    )

                # Send response back to API thread
                response_key = f"{order_id}:{request_id}"
                order_responses[response_key] = response
                response_event.set()

        except Exception as e:
            print(f"Validator thread error: {e}")


def matching_thread(
    match_queue: Queue,
    trade_queue: Queue,
    websocket_queue: Queue,
    exchange,
    pending_orders: Dict[str, threading.Event],
    order_responses: Dict[str, OrderResponse],
):
    """Thread 3: Matching Engine - processes validated orders.

    This thread owns the order matching logic for the Exchange Service.
    It receives validated orders from the validator thread and submits
    them to the exchange venue for matching.

    Parameters
    ----------
    match_queue : Queue
        Queue containing validated orders ready for matching
    trade_queue : Queue
        Queue for sending trade results to the publisher
    websocket_queue : Queue
        Queue for sending WebSocket acknowledgments
    exchange : ExchangeVenue
        The exchange venue for order matching
    pending_orders : Dict[str, threading.Event]
        Events for coordinating order responses
    order_responses : Dict[str, OrderResponse]
        Response storage for order submissions

    Notes
    -----
    This thread handles the core matching logic for the exchange,
    converting validated orders into trade executions. It also
    sends order acknowledgments via WebSocket when orders are
    successfully accepted by the exchange.

    The thread forwards all trade results to the trade publisher
    for position updates and execution reporting.

    TradingContext
    --------------
    The matching engine implements price-time priority matching,
    where orders with better prices are matched first, and for
    orders at the same price, earlier orders have priority.

    Examples
    --------
    Order processing flow:
    1. Receive (order, team_info) from match_queue
    2. Submit order to exchange venue
    3. Send WebSocket ACK if order accepted
    4. Forward (result, order, team_info) to trade_queue
    """
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
