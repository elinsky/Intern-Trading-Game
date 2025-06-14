"""Unit tests for core data models.

Tests the fundamental data structures including UnderlyingMarketData,
Signal, NewsEvent, and GameConfig following Given-When-Then pattern.
"""

from datetime import datetime, time

from intern_trading_game.domain.events import NewsEvent
from intern_trading_game.domain.game import GameConfig
from intern_trading_game.domain.signals import Signal
from intern_trading_game.domain.underlying import UnderlyingMarketData


class TestUnderlyingMarketData:
    """Test suite for UnderlyingMarketData dataclass."""

    def test_underlying_market_data_creation(self):
        """Test creating UnderlyingMarketData for different products.

        Given - Market information for SPX and SPY
        When - We create separate UnderlyingMarketData instances
        Then - Each instance should contain product-specific data
        """
        # Given - Market information at a timestamp
        timestamp = datetime(2024, 3, 21, 10, 30, 0)
        spx_price = 5234.50
        spy_price = 523.15

        # When - We create separate instances for each underlying
        spx_data = UnderlyingMarketData(
            symbol="SPX", timestamp=timestamp, price=spx_price
        )
        spy_data = UnderlyingMarketData(
            symbol="SPY", timestamp=timestamp, price=spy_price
        )

        # Then - Each instance has correct product-specific data
        assert spx_data.symbol == "SPX"
        assert spx_data.timestamp == timestamp
        assert spx_data.price == 5234.50

        assert spy_data.symbol == "SPY"
        assert spy_data.timestamp == timestamp
        assert spy_data.price == 523.15

    def test_underlying_data_product_agnostic(self):
        """Test that UnderlyingMarketData works for any product.

        Given - Different underlying products
        When - We create instances for various underlyings
        Then - The class should handle any product equally well
        """
        # Given - Various underlying products
        timestamp = datetime.now()

        # When - We create instances for different products
        ndx_data = UnderlyingMarketData(
            symbol="NDX", timestamp=timestamp, price=15000.0
        )
        vix_data = UnderlyingMarketData(
            symbol="VIX", timestamp=timestamp, price=18.5
        )

        # Then - All products work with the same structure
        assert ndx_data.symbol == "NDX"
        assert ndx_data.price == 15000.0

        assert vix_data.symbol == "VIX"
        assert vix_data.price == 18.5


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
            horizon_minutes=15,
            data=signal_data,
            accuracy=0.66,
        )

        # Then - Signal contains correct information
        assert signal.signal_type == "volatility"
        assert signal.horizon_minutes == 15
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
            horizon_minutes=5,
            data=signal_data,
            accuracy=0.80,
        )

        # Then - Signal contains tracking information
        assert signal.signal_type == "tracking_error"
        assert signal.horizon_minutes == 5
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
            timestamp_announced=datetime(2024, 3, 21, 14, 0, 0),
        )

        # Then - Event captures market-moving news
        assert event.event_id == "NEWS-001"
        assert event.event_type == "regime_shift"
        assert "Fed" in event.description
        assert event.impact_magnitude == 0.02
        assert event.timestamp_announced == datetime(2024, 3, 21, 14, 0, 0)

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
            timestamp_announced=datetime(2024, 3, 21, 14, 30, 0),
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
        assert config.trading_days == ["Tuesday", "Thursday"]
        assert config.market_open == time(9, 30)
        assert config.market_close == time(15, 0)
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
            bot_timeout_seconds=2.0,  # Fast timeout
            enable_volatility_events=False,  # Disable for testing
        )

        # Then - Custom values are set
        assert config.bot_timeout_seconds == 2.0
        assert config.enable_volatility_events is False

    def test_market_hours(self):
        """Test market hours configuration.

        Given - GameConfig with market hours
        When - We check the trading schedule
        Then - Hours should match standard equity markets
        """
        # Given - Standard game config
        config = GameConfig(session_name="test")

        # When - We check market hours
        open_time = config.market_open
        close_time = config.market_close

        # Then - Hours match equity market standards
        assert open_time == time(9, 30)  # 9:30 AM CT
        assert close_time == time(15, 0)  # 3:00 PM CT
