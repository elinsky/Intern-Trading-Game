"""Unit tests for the game loop implementation.

Tests the GameLoop class that orchestrates tick cycles and manages
game timing following Given-When-Then pattern.
"""

from datetime import datetime
from unittest.mock import Mock, patch

from intern_trading_game.core.game_loop import GameLoop
from intern_trading_game.core.interfaces import TradingStrategy
from intern_trading_game.core.models import GameConfig
from intern_trading_game.exchange.venue import ExchangeVenue


class MockStrategy(TradingStrategy):
    """Mock strategy for testing game loop."""

    def __init__(self, name: str):
        self.name = name
        self.market_data_calls = 0

    def get_name(self) -> str:
        return self.name

    def make_trading_decision(self, market_data, context):
        self.market_data_calls += 1
        from intern_trading_game.core.interfaces import StrategyAction

        return StrategyAction()


class TestGameLoop:
    """Test suite for GameLoop class."""

    def test_game_loop_initialization(self):
        """Test creating GameLoop with basic components.

        Given - Game configuration and required components
        When - We create a GameLoop instance
        Then - It should initialize with correct state
        """
        # Given - Basic game components
        config = GameConfig(session_name="test_game", total_ticks=5)
        exchange = ExchangeVenue()
        strategies = [MockStrategy("Bot1"), MockStrategy("Bot2")]

        # When - We create the game loop
        game = GameLoop(
            config=config,
            exchange=exchange,
            strategies=strategies,
            real_time=False,
        )

        # Then - Game initializes correctly
        assert game.config.session_name == "test_game"
        assert game.current_tick == 0
        assert len(game.strategies) == 2
        assert game.real_time is False
        assert game.tick_start_time is None

    def test_single_tick_execution(self):
        """Test running a single tick without real-time delays.

        Given - GameLoop configured for fast execution
        When - We run one tick
        Then - All phases should execute in order
        """
        # Given - Game loop for testing
        config = GameConfig(
            session_name="test", total_ticks=1, bot_timeout_seconds=1.0
        )
        exchange = Mock(spec=ExchangeVenue)
        strategies = [MockStrategy("TestBot")]

        game = GameLoop(
            config=config,
            exchange=exchange,
            strategies=strategies,
            real_time=False,  # No delays
        )

        # When - We run one tick
        with patch("builtins.print") as mock_print:
            game.run_tick()

        # Then - All phases are executed
        # Check phase announcements were printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        phase_msgs = [msg for msg in print_calls if "T+" in msg]

        assert any("T+0:00" in msg for msg in phase_msgs)
        assert any("T+0:30" in msg for msg in phase_msgs)
        assert any("T+3:00" in msg for msg in phase_msgs)
        assert any("T+3:30" in msg for msg in phase_msgs)
        assert any("T+5:00" in msg for msg in phase_msgs)

        # Tick counter advances
        assert game.current_tick == 1

    def test_phase_triggers_without_services(self):
        """Test that phases trigger even without connected services.

        Given - GameLoop without price model or market data service
        When - We run tick phases
        Then - Phases should complete with stub messages
        """
        # Given - Minimal game loop
        config = GameConfig(session_name="minimal", total_ticks=1)
        exchange = Mock(spec=ExchangeVenue)
        strategies = []

        game = GameLoop(
            config=config,
            exchange=exchange,
            strategies=strategies,
            price_model=None,  # No price model
            market_data_service=None,  # No market data service
        )

        # When - We run the tick
        with patch("builtins.print") as mock_print:
            game.run_tick()

        # Then - Stub messages indicate missing services
        print_output = " ".join(
            call[0][0] for call in mock_print.call_args_list
        )
        assert "No Price Model connected" in print_output
        assert "stub implementation" in print_output

    def test_multiple_strategies_notification(self):
        """Test that all strategies are notified during order window.

        Given - Multiple trading strategies
        When - Order window opens
        Then - All strategies should be notified
        """
        # Given - Game with multiple strategies
        config = GameConfig(session_name="multi", total_ticks=1)
        exchange = Mock(spec=ExchangeVenue)
        strategies = [
            MockStrategy("MarketMaker"),
            MockStrategy("HedgeFund"),
            MockStrategy("Arbitrage"),
            MockStrategy("Retail"),
        ]

        game = GameLoop(
            config=config, exchange=exchange, strategies=strategies
        )

        # When - We run a tick
        with patch("builtins.print") as mock_print:
            game.run_tick()

        # Then - All strategies are mentioned in output
        print_output = " ".join(
            call[0][0] for call in mock_print.call_args_list
        )
        assert "MarketMaker notified" in print_output
        assert "HedgeFund notified" in print_output
        assert "Arbitrage notified" in print_output
        assert "Retail notified" in print_output

    def test_batch_matching_trigger(self):
        """Test that batch matching is triggered at correct phase.

        Given - GameLoop with connected exchange
        When - Tick reaches batch matching phase
        Then - Exchange should be triggered for matching
        """
        # Given - Game with exchange
        config = GameConfig(session_name="matching", total_ticks=1)
        exchange = Mock(spec=ExchangeVenue)
        strategies = [MockStrategy("TestBot")]

        game = GameLoop(
            config=config, exchange=exchange, strategies=strategies
        )

        # When - We run tick to completion
        with patch("builtins.print") as mock_print:
            game.run_tick()

        # Then - Trading phase is triggered
        print_output = " ".join(
            call[0][0] for call in mock_print.call_args_list
        )
        assert "T+3:30 - TRADING phase - executing matches" in print_output
        assert "Exchange matching triggered" in print_output

    def test_full_session_execution(self):
        """Test running a complete multi-tick session.

        Given - GameLoop configured for short session
        When - We run the full session
        Then - All ticks should execute sequentially
        """
        # Given - Short game session
        config = GameConfig(
            session_name="full_test",
            total_ticks=3,  # Just 3 ticks
        )
        exchange = Mock(spec=ExchangeVenue)
        strategies = [MockStrategy("Bot1")]

        game = GameLoop(
            config=config, exchange=exchange, strategies=strategies
        )

        # When - We run full session
        with patch("builtins.print") as mock_print:
            game.run_session()

        # Then - All ticks execute
        print_output = " ".join(
            call[0][0] for call in mock_print.call_args_list
        )
        assert "TICK 0" in print_output
        assert "TICK 1" in print_output
        assert "TICK 2" in print_output
        assert "Game session complete!" in print_output
        assert game.current_tick == 3

    def test_tick_timing_tracking(self):
        """Test that tick timing is properly tracked.

        Given - GameLoop tracking tick start times
        When - A tick executes
        Then - Start time should be recorded
        """
        # Given - Game loop setup
        config = GameConfig(session_name="timing", total_ticks=1)
        exchange = Mock(spec=ExchangeVenue)
        strategies = []

        game = GameLoop(
            config=config, exchange=exchange, strategies=strategies
        )

        # When - We run a tick
        game.run_tick()

        # Then - Tick start time is recorded
        assert game.tick_start_time is not None
        assert isinstance(game.tick_start_time, datetime)
        # Should be very recent (within last second)
        time_diff = (datetime.now() - game.tick_start_time).total_seconds()
        assert time_diff < 1.0
