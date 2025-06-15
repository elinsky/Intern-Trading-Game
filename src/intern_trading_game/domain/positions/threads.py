"""Position service thread implementations.

This module contains thread functions that are owned by the Position Service,
following the service-oriented architecture principle of thread ownership.
"""

from queue import Queue

from .position_service import PositionManagementService


def position_tracker_thread(
    position_queue: Queue,
    position_service: PositionManagementService,
) -> None:
    """Thread that tracks and updates positions based on executed trades.

    This thread is owned by the Position Service and is responsible for
    maintaining accurate position tracking as trades are executed. It
    consumes trade messages from the position queue and updates the
    position state accordingly.

    The thread follows the principle of single responsibility - it only
    handles position updates and does not deal with communication,
    validation, or other concerns.

    Parameters
    ----------
    position_queue : Queue
        Queue containing trade messages to process. Each message is a
        tuple of (OrderResult, Order, TeamInfo).
    position_service : PositionManagementService
        Service that manages position state and updates.

    Notes
    -----
    The thread processes messages continuously until it receives a None
    sentinel value, which signals shutdown. All exceptions are caught
    and logged to ensure the thread continues processing even if
    individual trades fail.

    The position updates are performed atomically using the service's
    internal locking mechanism to ensure thread safety.

    Examples
    --------
    Message format in queue:
    >>> position_queue.put((
    ...     order_result,  # OrderResult with fill information
    ...     order,         # Original Order object
    ...     team_info      # TeamInfo for the trading team
    ... ))
    """
    print("Position tracker thread started")

    while True:
        try:
            # Get trade result from queue
            trade_data = position_queue.get()
            if trade_data is None:  # Shutdown signal
                break

            result, order, team_info = trade_data

            # Process position updates for all fills
            if result.fills:
                for fill in result.fills:
                    # Update aggressor's position
                    if order.side.value == "buy":
                        aggressor_delta = fill.quantity
                    else:  # sell
                        aggressor_delta = -fill.quantity

                    position_service.update_position(
                        team_id=team_info.team_id,
                        instrument_id=order.instrument_id,
                        delta=aggressor_delta,
                    )

                    # Update counterparty's position
                    # Determine which team is the counterparty
                    if order.side.value == "buy":
                        # Aggressor bought, so counterparty sold
                        counterparty_team_id = fill.seller_id
                        counterparty_delta = -fill.quantity
                    else:
                        # Aggressor sold, so counterparty bought
                        counterparty_team_id = fill.buyer_id
                        counterparty_delta = fill.quantity

                    # Skip if counterparty is the same as aggressor (self-trading)
                    if counterparty_team_id != team_info.team_id:
                        position_service.update_position(
                            team_id=counterparty_team_id,
                            instrument_id=order.instrument_id,
                            delta=counterparty_delta,
                        )

            # Mark queue task as done
            position_queue.task_done()

        except Exception as e:
            print(f"Position tracker thread error: {e}")
            # Continue processing despite errors
