"""Unit tests for core data models.

Tests the fundamental data structures including TickPhase, MarketData,
Signal, NewsEvent, and GameConfig following Given-When-Then pattern.
"""

from datetime import datetime, time

from intern_trading_game.core.models import (
    GameConfig,
    MarketData,
    NewsEvent,
    Signal,
    TickPhase,
)


class TestTickPhase:
    """Test suite for TickPhase enumeration."""

    def test_tick_phase_values(self):
        """Test that tick phases have correct timing values.

        Given - The TickPhase enumeration with defined phases
        When - We access the phase values
        Then - Each phase should have the correct (minutes, seconds) tuple
        """
        # Given - TickPhase enum is imported

        # When - We check each phase value
        price_pub = TickPhase.PRICE_PUBLICATION.value
        order_open = TickPhase.ORDER_WINDOW_OPEN.value
        order_close = TickPhase.ORDER_WINDOW_CLOSE.value
        matching = TickPhase.BATCH_MATCHING.value
        tick_end = TickPhase.TICK_END.value

        # Then - Values match expected timing
        assert price_pub == (0, 0), "Price publication at T+0:00"
        assert order_open == (0, 30), "Order window opens at T+0:30"
        assert order_close == (3, 0), "Order window closes at T+3:00"
        assert matching == (3, 30), "Batch matching at T+3:30"
        assert tick_end == (5, 0), "Tick ends at T+5:00"

    def test_total_seconds_calculation(self):
        """Test conversion of phase timing to total seconds.

        Given - TickPhase with (minutes, seconds) timing
        When - We call total_seconds property
        Then - It should return correct total seconds from tick start
        """
        # Given - Various tick phases

        # When - We calculate total seconds for each phase

        # Then - Calculations are correct
        assert TickPhase.PRICE_PUBLICATION.total_seconds == 0
        assert TickPhase.ORDER_WINDOW_OPEN.total_seconds == 30
        assert TickPhase.ORDER_WINDOW_CLOSE.total_seconds == 180
        assert TickPhase.BATCH_MATCHING.total_seconds == 210
        assert TickPhase.TICK_END.total_seconds == 300


class TestMarketData:
    """Test suite for MarketData dataclass."""

    def test_market_data_creation(self):
        """Test creating MarketData with required fields.

        Given - Market information for a specific tick
        When - We create a MarketData instance
        Then - All fields should be accessible and correct
        """
        # Given - Market information at tick 42
        tick_num = 42
        timestamp = datetime(2024, 3, 21, 10, 30, 0)
        spx = 5234.50
        spy = 523.15
        books = {}

        # When - We create MarketData
        data = MarketData(
            tick=tick_num,
            timestamp=timestamp,
            spx_price=spx,
            spy_price=spy,
            order_book_snapshots=books,
        )

        # Then - All fields are set correctly
        assert data.tick == 42
        assert data.timestamp == timestamp
        assert data.spx_price == 5234.50
        assert data.spy_price == 523.15
        assert data.order_book_snapshots == {}

    def test_market_data_immutability(self):
        """Test that MarketData acts as immutable data.

        Given - A MarketData instance
        When - We try to modify fields
        Then - The dataclass should allow modifications (not frozen)
        """
        # Given - MarketData instance
        data = MarketData(
            tick=1,
            timestamp=datetime.now(),
            spx_price=5200.0,
            spy_price=520.0,
            order_book_snapshots={},
        )

        # When - We modify a field
        original_price = data.spx_price
        data.spx_price = 5250.0

        # Then - Modification is allowed (dataclass not frozen)
        assert data.spx_price == 5250.0
        assert data.spx_price != original_price


class TestSignal:
    """Test suite for Signal dataclass."""

    def test_volatility_signal_creation(self):
        """Test creating a volatility forecast signal.

        Given - Volatility regime transition probabilities
        When - We create a volatility Signal
        Then - Signal should contain forecast data with probabilities
        """
        # Given - Volatility forecast for hedge fund
        signal_data = {"low": 0.2, "medium": 0.5, "high": 0.3}

        # When - We create the signal
        signal = Signal(
            signal_type="volatility",
            tick_horizon=3,
            data=signal_data,
            accuracy=0.66,
        )

        # Then - Signal contains correct information
        assert signal.signal_type == "volatility"
        assert signal.tick_horizon == 3
        assert signal.data["low"] == 0.2
        assert signal.data["medium"] == 0.5
        assert signal.data["high"] == 0.3
        assert signal.accuracy == 0.66

    def test_tracking_error_signal_creation(self):
        """Test creating a tracking error signal.

        Given - SPX/SPY tracking error prediction
        When - We create a tracking error Signal
        Then - Signal should contain tracking metrics
        """
        # Given - Tracking error forecast for arbitrage desk
        signal_data = {"magnitude": 0.15, "direction": "positive"}

        # When - We create the signal
        signal = Signal(
            signal_type="tracking_error",
            tick_horizon=1,
            data=signal_data,
            accuracy=0.80,
        )

        # Then - Signal contains tracking information
        assert signal.signal_type == "tracking_error"
        assert signal.tick_horizon == 1
        assert signal.data["magnitude"] == 0.15
        assert signal.data["direction"] == "positive"
        assert signal.accuracy == 0.80


class TestNewsEvent:
    """Test suite for NewsEvent dataclass."""

    def test_news_event_creation(self):
        """Test creating different types of news events.

        Given - Market news information
        When - We create NewsEvent instances
        Then - Events should represent different market impacts
        """
        # Given - Fed announcement that might shift volatility

        # When - We create a regime shift event
        event = NewsEvent(
            event_id="NEWS-001",
            event_type="regime_shift",
            description="Fed announces unexpected rate hike",
            impact_magnitude=0.02,
            tick_announced=45,
        )

        # Then - Event captures market-moving news
        assert event.event_id == "NEWS-001"
        assert event.event_type == "regime_shift"
        assert "Fed" in event.description
        assert event.impact_magnitude == 0.02
        assert event.tick_announced == 45

    def test_false_signal_event(self):
        """Test creating a false signal news event.

        Given - News that seems important but has no impact
        When - We create a false signal event
        Then - Event should have minimal impact magnitude
        """
        # Given - Seemingly important but ultimately irrelevant news

        # When - We create false signal
        event = NewsEvent(
            event_id="NEWS-002",
            event_type="false_signal",
            description="Analyst upgrades tech sector",
            impact_magnitude=0.001,
            tick_announced=50,
        )

        # Then - Event has minimal impact
        assert event.event_type == "false_signal"
        assert event.impact_magnitude < 0.01


class TestGameConfig:
    """Test suite for GameConfig dataclass."""

    def test_default_game_config(self):
        """Test GameConfig with default values.

        Given - A session name
        When - We create GameConfig with defaults
        Then - Standard game parameters should be set
        """
        # Given - Session name for a training game
        session = "training_session_1"

        # When - We create config with defaults
        config = GameConfig(session_name=session)

        # Then - Defaults match standard game setup
        assert config.session_name == "training_session_1"
        assert config.tick_duration_seconds == 300
        assert config.trading_days == ["Tuesday", "Thursday"]
        assert config.market_open == time(9, 30)
        assert config.market_close == time(15, 0)
        assert config.total_ticks == 390
        assert config.enable_volatility_events is True
        assert config.enable_news_events is True
        assert config.bot_timeout_seconds == 10.0

    def test_custom_game_config(self):
        """Test GameConfig with custom parameters.

        Given - Custom game requirements for testing
        When - We create GameConfig with overrides
        Then - Custom values should take precedence
        """
        # Given - Need faster game for integration testing

        # When - We create custom config
        config = GameConfig(
            session_name="quick_test",
            tick_duration_seconds=60,  # 1 minute ticks
            total_ticks=10,  # Very short game
            bot_timeout_seconds=2.0,  # Fast timeout
        )

        # Then - Custom values are set
        assert config.tick_duration_seconds == 60
        assert config.total_ticks == 10
        assert config.bot_timeout_seconds == 2.0

    def test_calculated_properties(self):
        """Test calculated properties of GameConfig.

        Given - GameConfig with specific tick duration
        When - We access calculated properties
        Then - Calculations should be correct
        """
        # Given - Standard 5-minute tick game
        config = GameConfig(session_name="test")

        # When - We check calculated properties
        ticks_per_hour = config.ticks_per_hour
        ticks_per_day = config.ticks_per_day

        # Then - Calculations match expected values
        assert ticks_per_hour == 12  # 60 min / 5 min
        assert ticks_per_day == 66  # 5.5 hours * 12 ticks/hour
