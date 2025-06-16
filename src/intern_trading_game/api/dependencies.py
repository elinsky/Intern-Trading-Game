"""FastAPI dependency injection utilities.

This module provides dependency functions for FastAPI endpoints,
enabling clean separation of concerns and testability.
"""

from fastapi import Request

from ..domain.exchange.venue import ExchangeVenue


def get_exchange(request: Request) -> ExchangeVenue:
    """Dependency to get exchange from app state.

    Retrieves the configured exchange instance from the FastAPI
    application state. This allows endpoints to access the exchange
    without importing global variables.

    Parameters
    ----------
    request : Request
        FastAPI request object containing app reference

    Returns
    -------
    ExchangeVenue
        The exchange instance from app state

    Raises
    ------
    AttributeError
        If exchange is not found in app state
    """
    return request.app.state.exchange
