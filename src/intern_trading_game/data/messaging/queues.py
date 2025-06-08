"""Thread-safe queues for inter-thread communication."""

from queue import Queue


def create_queues():
    """Create all the thread-safe queues used for communication.

    Returns
    -------
    dict
        Dictionary containing all queues with descriptive names.
    """
    return {
        "order_queue": Queue(),  # API -> Validator
        "validation_queue": Queue(),  # Validator -> Matcher (future)
        "match_queue": Queue(),  # For matching engine
        "trade_queue": Queue(),  # Matcher -> Publisher
        "response_queue": Queue(),  # For order responses back to API
        "websocket_queue": Queue(),  # Threads -> WebSocket
    }
