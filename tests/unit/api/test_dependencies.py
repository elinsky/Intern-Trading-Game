"""Behavior tests for API dependency injection."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request

from intern_trading_game.api.dependencies import get_exchange
from intern_trading_game.domain.exchange.venue import ExchangeVenue


class TestExchangeDependency:
    """Test exchange dependency injection for FastAPI."""

    def test_get_exchange_from_app_state(self):
        """Test retrieving exchange from app state.

        Given - FastAPI app with exchange in state
        When - Dependency function is called
        Then - Returns the exchange from app state
        """
        # Given - Mock app with exchange in state
        mock_exchange = Mock(spec=ExchangeVenue)
        mock_state = Mock()
        mock_state.exchange = mock_exchange

        mock_app = Mock(spec=FastAPI)
        mock_app.state = mock_state

        mock_request = Mock(spec=Request)
        mock_request.app = mock_app

        # When - Get exchange via dependency
        result = get_exchange(mock_request)

        # Then - Should return the exchange from state
        assert result is mock_exchange

    def test_missing_exchange_raises_error(self):
        """Test proper error when exchange not in app state.

        Given - FastAPI app without exchange in state
        When - Dependency function is called
        Then - AttributeError is raised
        """
        # Given - Mock app without exchange
        mock_state = Mock(spec=["some_other_attr"])  # Spec without 'exchange'

        mock_app = Mock(spec=FastAPI)
        mock_app.state = mock_state

        mock_request = Mock(spec=Request)
        mock_request.app = mock_app

        # When/Then - Should raise AttributeError
        with pytest.raises(AttributeError):
            get_exchange(mock_request)
