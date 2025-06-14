"""Domain models for the trading system."""

# Import from new domain locations
from ..events.news_event import NewsEvent
from ..exchange.core.instrument import Instrument
from ..game.config import GameConfig
from ..signals.signal import Signal
from ..underlying.market_data import UnderlyingMarketData

# Keep old name for backward compatibility during migration
MarketData = UnderlyingMarketData

__all__ = [
    "GameConfig",
    "MarketData",  # Deprecated, use UnderlyingMarketData
    "NewsEvent",
    "Signal",
    "UnderlyingMarketData",
    "Instrument",
]
