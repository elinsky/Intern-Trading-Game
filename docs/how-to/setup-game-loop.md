# How to Set Up and Run the Game Loop

This guide walks you through setting up and running a basic trading
game session using the core game loop infrastructure.

## Prerequisites

- Python 3.8 or higher
- The `intern_trading_game` package installed
- Basic understanding of the game architecture

## Step 1: Import Required Components

```python
from datetime import datetime
from intern_trading_game.core.game_loop import GameLoop
from intern_trading_game.core.models import GameConfig
from intern_trading_game.core.interfaces import (
    TradingStrategy,
    TradingContext,
    StrategyAction
)
from intern_trading_game.exchange.venue import ExchangeVenue
```

## Step 2: Create a Simple Trading Strategy

Implement the `TradingStrategy` interface:

```python
class SimpleMarketMaker(TradingStrategy):
    """Example market maker strategy."""

    def get_name(self) -> str:
        return "SimpleMarketMaker"

    def make_trading_decision(
        self,
        market_data: MarketData,
        context: TradingContext
    ) -> StrategyAction:
        # For now, just return empty action
        # Real strategies would analyze market_data
        return StrategyAction()

    def on_signal(self, signal: Signal) -> None:
        # Market makers don't receive signals
        pass

    def on_news(self, event: NewsEvent) -> None:
        # Store news for future decisions
        pass
```

## Step 3: Configure the Game Session

```python
# Create game configuration
config = GameConfig(
    session_name="my_first_game",
    total_ticks=10,  # Short game for testing
    tick_duration_seconds=300,  # 5 minutes per tick
    bot_timeout_seconds=5.0  # 5 second timeout
)

# Create exchange (using existing implementation)
exchange = ExchangeVenue()

# Create strategy instances
strategies = [
    SimpleMarketMaker(),
    # Add more strategies here
]
```

## Step 4: Initialize and Run the Game Loop

```python
# Create game loop
game = GameLoop(
    config=config,
    exchange=exchange,
    strategies=strategies,
    real_time=False  # Run as fast as possible for testing
)

# Run the full session
game.run_session()
```

## Step 5: Run Individual Ticks (Advanced)

For more control, you can run ticks individually:

```python
# Run ticks one at a time
for i in range(config.total_ticks):
    print(f"Starting tick {i}")
    game.run_tick()

    # Do something between ticks
    # e.g., save state, analyze results
```

## Understanding Tick Phases

Each tick follows this timeline:

- **T+0:00** - Price Publication
  - New SPX/SPY prices generated
  - Market data prepared

- **T+0:30** - Order Window Opens
  - Strategies receive market data
  - Can submit orders/quotes

- **T+3:00** - Order Window Closes
  - No new orders accepted

- **T+3:30** - Batch Matching
  - All orders matched by exchange

- **T+5:00** - Tick End
  - Tick completes, next tick begins

## Real-Time vs Fast Mode

```python
# Real-time mode (enforces actual delays)
game_realtime = GameLoop(
    config=config,
    exchange=exchange,
    strategies=strategies,
    real_time=True  # Will wait actual time between phases
)

# Fast mode (no delays, good for testing)
game_fast = GameLoop(
    config=config,
    exchange=exchange,
    strategies=strategies,
    real_time=False  # Executes as fast as possible
)
```

## Next Steps

- Implement a real trading strategy with order logic
- Connect a Price Model for realistic price generation
- Add position tracking with Position Service
- Enable role-specific features and constraints

## Common Issues

**Strategies not responding:**
- Check that `make_trading_decision` returns a `StrategyAction`
- Ensure strategy doesn't exceed `bot_timeout_seconds`

**No prices generated:**
- Price Model service needs to be connected
- For now, stub prices are used

**Orders not matching:**
- Exchange integration is not complete in this version
- Full order matching will be added in next iteration
