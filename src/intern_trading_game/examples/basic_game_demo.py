"""Basic demonstration of the game loop infrastructure.

This example shows how to set up and run a minimal trading game
session with stub strategies. It demonstrates the core tick cycle
and phase progression without full trading logic.
"""

from intern_trading_game.core.game_loop import GameLoop
from intern_trading_game.core.interfaces import (
    StrategyAction,
    TradingContext,
    TradingStrategy,
)
from intern_trading_game.core.models import GameConfig, MarketData
from intern_trading_game.exchange.venue import ExchangeVenue


class DemoStrategy(TradingStrategy):
    """Minimal strategy implementation for demonstration.

    This strategy doesn't actually trade - it just shows
    the interface methods being called at appropriate times.
    """

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.tick_count = 0

    def get_name(self) -> str:
        """Return strategy identifier."""
        return f"{self.name} ({self.role})"

    def make_trading_decision(
        self, market_data: MarketData, context: TradingContext
    ) -> StrategyAction:
        """Make trading decisions based on market data.

        In this demo, we just acknowledge receiving data
        and return an empty action.
        """
        self.tick_count += 1

        # Log what we received
        print(f"    {self.name} received tick {market_data.tick}")
        print(f"      SPX: ${market_data.spx_price:.2f}")
        print(f"      SPY: ${market_data.spy_price:.2f}")

        # Return empty action (no trades)
        return StrategyAction()


def run_demo():
    """Run a demonstration game session.

    Sets up a minimal game with 4 bot strategies and runs
    a few ticks to show the phase progression.
    """
    print("\n" + "=" * 60)
    print("INTERN TRADING GAME - BASIC DEMO")
    print("=" * 60)

    # Step 1: Configure the game
    print("\n1. Creating game configuration...")
    config = GameConfig(
        session_name="demo_session",
        total_ticks=3,  # Just 3 ticks for demo
        tick_duration_seconds=300,  # Standard 5 minutes
        bot_timeout_seconds=5.0,  # 5 second timeout
    )
    print(f"   - Session: {config.session_name}")
    print(f"   - Total ticks: {config.total_ticks}")
    print(f"   - Tick duration: {config.tick_duration_seconds}s")

    # Step 2: Create the exchange
    print("\n2. Setting up exchange...")
    exchange = ExchangeVenue()
    print("   - Exchange initialized")

    # Step 3: Create trading strategies
    print("\n3. Creating trading strategies...")
    strategies = [
        DemoStrategy("MM_Bot", "Market Maker"),
        DemoStrategy("HF_Bot", "Hedge Fund"),
        DemoStrategy("ARB_Bot", "Arbitrage Desk"),
        DemoStrategy("RET_Bot", "Retail Trader"),
    ]
    for strategy in strategies:
        print(f"   - {strategy.get_name()}")

    # Step 4: Initialize game loop
    print("\n4. Initializing game loop...")
    game = GameLoop(
        config=config,
        exchange=exchange,
        strategies=strategies,
        real_time=False,  # Fast mode for demo
    )
    print("   - Game loop ready")

    # Step 5: Run the session
    print("\n5. Running game session...")
    print("   (Note: Running in fast mode - no real-time delays)")
    game.run_session()

    # Summary
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nWhat happened:")
    print("- Ran 3 complete 5-minute ticks")
    print("- Each tick followed the standard phases:")
    print("  - T+0:00: Price publication")
    print("  - T+0:30: Order window opened")
    print("  - T+3:00: Order window closed")
    print("  - T+3:30: Batch matching triggered")
    print("  - T+5:00: Tick completed")
    print("\nNext steps:")
    print("- Implement real trading logic in strategies")
    print("- Connect Price Model for realistic prices")
    print("- Add Position Service for tracking")
    print("- Enable full order matching")


if __name__ == "__main__":
    # Run the demonstration
    run_demo()
