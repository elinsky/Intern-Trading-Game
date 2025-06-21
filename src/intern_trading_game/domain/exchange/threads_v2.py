"""Exchange service thread implementations with response coordinator.

This module contains updated thread functions that use the OrderResponseCoordinator
instead of global dictionaries for managing order responses.
"""

import time
from datetime import datetime
from queue import Queue
from typing import Optional

from ...constants.errors import ErrorCodes, ErrorMessages
from ...infrastructure.api.models import ApiError, ApiResponse
from ...infrastructure.messaging.websocket_messages import MessageType
from ...services.order_matching import OrderMatchingService
from ...services.order_validation import OrderValidationService
from ..exchange.response.interfaces import OrderResponseCoordinatorInterface


def handle_new_order_validation(
    order,
    team_info,
    request_id,
    validation_service,
    match_queue,
    websocket_queue,
    response_coordinator,
):
    """Handle validation of a new order."""
    result = validation_service.validate_new_order(order, team_info)

    if result.status == "accepted":
        # Send to matching engine
        match_queue.put((order, team_info))
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
        response_coordinator.notify_completion(
            request_id=request_id,
            api_response=response,
            order_id=order.order_id,
        )

    elif result.status == "rejected":
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
            order_id=None,
            data=None,
            error=ApiError(
                code=result.error_code,
                message=result.error_message,
                details=None,
            ),
            timestamp=datetime.now(),
        )
        response_coordinator.notify_completion(
            request_id=request_id,
            api_response=response,
        )

    else:
        # Unexpected status
        handle_unexpected_status(
            result.status, request_id, response_coordinator
        )


def handle_order_cancellation(
    order_id,
    team_info,
    request_id,
    validation_service,
    websocket_queue,
    response_coordinator,
):
    """Handle order cancellation request."""
    success, reason = validation_service.validate_cancellation(
        order_id, team_info.team_id
    )

    if success:
        # Send cancel acknowledgment
        websocket_queue.put(
            (
                MessageType.CANCEL_ACK.value,
                team_info.team_id,
                {
                    "order_id": order_id,
                    "client_order_id": None,
                    "cancelled_quantity": 0,
                    "reason": "user_requested",
                },
            )
        )

        response = ApiResponse(
            success=True,
            request_id=request_id,
            order_id=order_id,
            data=None,
            error=None,
            timestamp=datetime.now(),
        )
    else:
        # Send cancel rejection
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

        response = ApiResponse(
            success=False,
            request_id=request_id,
            order_id=None,
            data=None,
            error=ApiError(
                code=ErrorCodes.CANCEL_FAILED,
                message=ErrorMessages.format_cancel_failed(
                    reason or "Unknown error"
                ),
                details=None,
            ),
            timestamp=datetime.now(),
        )

    response_coordinator.notify_completion(
        request_id=request_id,
        api_response=response,
    )


def handle_unexpected_status(status, request_id, response_coordinator):
    """Handle unexpected validation status."""
    print(f"Unexpected validation status: {status}")
    response = ApiResponse(
        success=False,
        request_id=request_id,
        order_id=None,
        data=None,
        error=ApiError(
            code=ErrorCodes.INTERNAL_ERROR,
            message=f"Unexpected validation status: {status}",
            details=None,
        ),
        timestamp=datetime.now(),
    )
    response_coordinator.notify_completion(
        request_id=request_id,
        api_response=response,
    )


def handle_validator_error(e, request_id, response_coordinator):
    """Handle errors in validator thread."""
    print(f"Validator thread error: {e}")
    if request_id:
        try:
            error_response = ApiResponse(
                success=False,
                request_id=request_id,
                order_id=None,
                data=None,
                error=ApiError(
                    code=ErrorCodes.INTERNAL_ERROR,
                    message=f"Validator thread error: {str(e)}",
                    details=None,
                ),
                timestamp=datetime.now(),
            )
            response_coordinator.notify_completion(
                request_id=request_id,
                api_response=error_response,
            )
        except Exception:
            pass  # nosec B110 - Best effort error handling, failures are logged above


def validator_thread_v2(
    order_queue: Queue,
    match_queue: Queue,
    websocket_queue: Queue,
    validation_service: OrderValidationService,
    response_coordinator: OrderResponseCoordinatorInterface,
):
    """Thread 2: Order Validator - validates orders from queue.

    This updated version uses the OrderResponseCoordinator for managing
    order responses instead of global dictionaries.

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
    response_coordinator : OrderResponseCoordinatorInterface
        Coordinator for managing order response lifecycle

    Notes
    -----
    Messages follow a 5-tuple format:
    (message_type, data, team_info, response_event, request_id)

    The response_event is no longer used directly - instead, the
    request_id is registered with the coordinator which manages
    the event signaling internally.
    """
    print("Validator thread v2 started with response coordinator")

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
                handle_new_order_validation(
                    data,
                    team_info,
                    request_id,
                    validation_service,
                    match_queue,
                    websocket_queue,
                    response_coordinator,
                )
            elif message_type == "cancel_order":
                handle_order_cancellation(
                    data,
                    team_info,
                    request_id,
                    validation_service,
                    websocket_queue,
                    response_coordinator,
                )

        except Exception as e:
            handle_validator_error(
                e,
                request_id if "request_id" in locals() else None,
                response_coordinator,
            )


def matching_thread_v2(
    match_queue: Queue,
    trade_queue: Queue,
    websocket_queue: Queue,
    exchange,
    response_coordinator: Optional[OrderResponseCoordinatorInterface] = None,
):
    """Thread 3: Matching Engine - processes validated orders.

    This updated version optionally uses the OrderResponseCoordinator
    for error cases. Most responses are handled by the validator thread,
    but exchange errors may need direct response handling.

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
    response_coordinator : Optional[OrderResponseCoordinatorInterface]
        Coordinator for managing order response lifecycle (optional)

    Notes
    -----
    This thread primarily forwards results to the trade publisher.
    The response coordinator is only used for exceptional error cases
    where the validator thread hasn't already handled the response.
    """
    print("Matching engine thread v2 started")

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

                # If we have a response coordinator and can extract request_id,
                # send error response directly. Otherwise, log and continue.
                if response_coordinator:
                    # Note: In a full implementation, we'd need to track
                    # request_id through the pipeline or use order_id mapping
                    print(f"Exchange error for order {order.order_id}: {e}")
                    # For now, just log - the validator has already responded

        except Exception as e:
            print(f"Matching thread error: {e}")
