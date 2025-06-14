"""Unit tests for core interfaces.

Tests the TradingStrategy interface, StrategyAction dataclass,
and TradingContext interface following Given-When-Then pattern.
"""

from typing import Dict, List

from intern_trading_game.domain.exchange.order import Order
from intern_trading_game.domain.interfaces import (
    StrategyAction,
    TradingContext,
    TradingStrategy,
)
from intern_trading_game.domain.models import MarketData, NewsEvent, Signal


class MockTradingContext(TradingContext):
    """Mock implementation of TradingContext for testing."""

    def __init__(self, positions: Dict[str, int] = None):
        self.positions = positions or {}
        self.open_orders = []
        self.trades = []

    def get_position(self, instrument: str) -> int:
        return self.positions.get(instrument, 0)

    def get_all_positions(self) -> Dict[str, int]:
        return self.positions.copy()

    def get_open_orders(self) -> List[Order]:
        return self.open_orders.copy()

    def get_last_trades(self, n: int = 10) -> List[Dict]:
        return self.trades[-n:]


class SimpleTradingStrategy(TradingStrategy):
    """Simple concrete implementation for testing."""

    def __init__(self, name: str = "TestBot"):
        self.name = name
        self.signals_received = []
        self.news_received = []

    def get_name(self) -> str:
        return self.name

    def make_trading_decision(
        self, market_data: MarketData, context: TradingContext
    ) -> StrategyAction:
        # Simple logic: return empty action
        return StrategyAction()

    def on_signal(self, signal: Signal) -> None:
        self.signals_received.append(signal)

    def on_news(self, event: NewsEvent) -> None:
        self.news_received.append(event)


class TestStrategyAction:
    """Test suite for StrategyAction dataclass."""

    def test_empty_strategy_action(self):
        """Test creating empty StrategyAction.

        Given - No trading decisions made
        When - We create default StrategyAction
        Then - All collections should be empty
        """
        # Given - Strategy makes no decisions

        # When - We create empty action
        action = StrategyAction()

        # Then - All fields are empty/false
        assert action.orders == []
        assert action.quotes == {}
        assert action.cancel_order_ids == []
        assert action.cancel_all is False

    def test_strategy_action_with_orders(self):
        """Test StrategyAction with orders and cancellations.

        Given - Strategy wants to submit orders and cancel others
        When - We create StrategyAction with multiple intents
        Then - Action should contain all trading intentions
        """
        # Given - Trading decisions including orders and cancels
        mock_order = {"instrument": "SPX_CALL_5200", "qty": 10}
        quotes = {"SPX_PUT_5000": (24.50, 24.70, 5)}
        cancels = ["ORD-123", "ORD-456"]

        # When - We create comprehensive action
        action = StrategyAction(
            orders=[mock_order],  # Simplified for test
            quotes=quotes,
            cancel_order_ids=cancels,
            cancel_all=False,
        )

        # Then - All intentions are captured
        assert len(action.orders) == 1
        assert action.orders[0]["instrument"] == "SPX_CALL_5200"
        assert len(action.quotes) == 1
        assert action.quotes["SPX_PUT_5000"] == (24.50, 24.70, 5)
        assert len(action.cancel_order_ids) == 2
        assert "ORD-123" in action.cancel_order_ids

    def test_cancel_all_flag(self):
        """Test StrategyAction with cancel_all flag.

        Given - Strategy wants to cancel all open orders
        When - We set cancel_all=True
        Then - Flag should override specific cancellations
        """
        # Given - Market conditions require cancelling everything

        # When - We create action with cancel_all
        action = StrategyAction(cancel_all=True)

        # Then - Cancel all flag is set
        assert action.cancel_all is True
        assert action.orders == []  # Can still be empty


class TestTradingContext:
    """Test suite for TradingContext interface."""

    def test_mock_context_positions(self):
        """Test accessing positions through context.

        Given - A trading context with existing positions
        When - Strategy queries its positions
        Then - Context should return accurate position data
        """
        # Given - Context with SPX options positions
        positions = {"SPX_CALL_5200": 10, "SPX_PUT_5000": -5, "SPY": 100}
        context = MockTradingContext(positions=positions)

        # When - We query positions
        spx_call_pos = context.get_position("SPX_CALL_5200")
        spy_pos = context.get_position("SPY")
        unknown_pos = context.get_position("AAPL")
        all_pos = context.get_all_positions()

        # Then - Positions are returned correctly
        assert spx_call_pos == 10
        assert spy_pos == 100
        assert unknown_pos == 0  # Default for unknown
        assert len(all_pos) == 3
        assert all_pos["SPX_PUT_5000"] == -5

    def test_context_isolation(self):
        """Test that context provides isolated copies.

        Given - A trading context with mutable data
        When - Strategy receives data from context
        Then - Modifying returned data shouldn't affect context
        """
        # Given - Context with positions
        context = MockTradingContext(positions={"SPX": 50})

        # When - Strategy gets and modifies position dict
        positions = context.get_all_positions()
        positions["SPX"] = 100  # Try to modify
        positions["NEW"] = 25  # Try to add

        # Then - Original context unchanged
        assert context.get_position("SPX") == 50
        assert context.get_position("NEW") == 0


class TestTradingStrategy:
    """Test suite for TradingStrategy interface."""

    def test_strategy_basic_implementation(self):
        """Test basic strategy implementation.

        Given - A simple trading strategy
        When - We call interface methods
        Then - Strategy should respond appropriately
        """
        # Given - Simple strategy instance
        strategy = SimpleTradingStrategy("TestBot")

        # When - We interact with the strategy
        name = strategy.get_name()

        # Then - Basic functionality works
        assert name == "TestBot"
        assert strategy.signals_received == []
        assert strategy.news_received == []

    def test_strategy_make_decision(self):
        """Test strategy decision making with market data.

        Given - Market data and trading context
        When - Strategy makes trading decision
        Then - Should return valid StrategyAction
        """
        # Given - Market conditions and context
        from datetime import datetime

        market_data = MarketData(
            timestamp=datetime.now(),
            spx_price=5200.0,
            spy_price=520.0,
            order_book_snapshots={},
        )
        context = MockTradingContext()
        strategy = SimpleTradingStrategy()

        # When - Strategy makes decision
        action = strategy.make_trading_decision(market_data, context)

        # Then - Returns valid StrategyAction
        assert isinstance(action, StrategyAction)
        assert action.orders == []  # Simple strategy does nothing

    def test_strategy_signal_handling(self):
        """Test strategy receiving and storing signals.

        Given - A strategy that tracks signals
        When - Signals are sent to strategy
        Then - Strategy should store them for future use
        """
        # Given - Strategy that collects signals
        strategy = SimpleTradingStrategy()

        # When - Multiple signals are sent
        vol_signal = Signal(
            signal_type="volatility",
            horizon_minutes=15,
            data={"low": 0.3, "medium": 0.5, "high": 0.2},
            accuracy=0.66,
        )
        strategy.on_signal(vol_signal)

        # Then - Signals are stored
        assert len(strategy.signals_received) == 1
        assert strategy.signals_received[0].signal_type == "volatility"

    def test_strategy_news_handling(self):
        """Test strategy receiving news events.

        Given - A strategy monitoring news
        When - News events occur
        Then - Strategy should process and store them
        """
        # Given - Strategy that tracks news
        from datetime import datetime

        strategy = SimpleTradingStrategy()

        # When - News event is published
        news = NewsEvent(
            event_id="NEWS-123",
            event_type="regime_shift",
            description="Major economic data released",
            impact_magnitude=0.015,
            timestamp_announced=datetime.now(),
        )
        strategy.on_news(news)

        # Then - News is captured
        assert len(strategy.news_received) == 1
        assert strategy.news_received[0].event_type == "regime_shift"
