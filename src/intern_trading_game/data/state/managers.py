"""Shared state management with thread-safe access."""

import threading
from typing import Dict


def create_shared_state():
    """Create all shared state objects with proper locking.

    Returns
    -------
    dict
        Dictionary containing all shared state objects and their locks.
    """
    return {
        # Position tracking (thread-safe)
        "positions": {},
        "positions_lock": threading.RLock(),
        # Track orders per second
        "orders_this_second": {},
        "orders_lock": threading.RLock(),
        # Pending orders waiting for response
        "pending_orders": {},
        "order_responses": {},
    }


# Helper functions for service dependency injection
def get_team_positions(
    team_id: str, positions: Dict, positions_lock: threading.RLock
) -> Dict[str, int]:
    """Thread-safe retrieval of team positions."""
    with positions_lock:
        return positions.get(team_id, {}).copy()


def get_team_order_count(
    team_id: str, orders_this_second: Dict, orders_lock: threading.RLock
) -> int:
    """Thread-safe retrieval of team order count for current second."""
    with orders_lock:
        return orders_this_second.get(team_id, 0)
