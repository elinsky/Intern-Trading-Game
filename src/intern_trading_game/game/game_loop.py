"""Main game loop implementation for the Intern Trading Game.

This module contains the GameLoop class that orchestrates the
entire trading simulation. It manages tick progression and phase
timing, publishing events that other components react to.
"""

import time
from datetime import datetime, timedelta
from typing import List, Optional

from ..domain.exchange.venue import ExchangeVenue
from ..domain.interfaces import TradingStrategy
from ..domain.models import GameConfig, TickPhase


class GameLoop:
    """Main game orchestrator managing tick cycles and timing.

    The GameLoop acts as the Tick Controller from the architecture,
    managing the progression of time and publishing phase events.
    Other components (strategies, exchange, price model) react to
    these events independently.

    Parameters
    ----------
    config : GameConfig
        Configuration parameters for the game session
    exchange : ExchangeVenue
        Exchange engine for triggering batch matching
    strategies : List[TradingStrategy]
        Trading strategies participating in the game
    price_model : object, optional
        Price generation service (stub if not provided)
    market_data_service : object, optional
        Service for distributing market data (stub if not provided)
    real_time : bool, default=False
        Whether to enforce real-time delays

    Attributes
    ----------
    current_tick : int
        Current tick number (0-indexed)
    tick_start_time : Optional[datetime]
        Real-world time when current tick started

    Notes
    -----
    The game loop follows a strict 5-minute tick cycle:
    - T+0:00: Market data phase - new prices generated
    - T+0:30: Pre-open phase - orders accepted
    - T+3:00: Open phase - order acceptance ends
    - T+3:30: Trading phase - matching occurs
    - T+5:00: Closed phase - tick completes

    The Tick Controller does not handle orders directly - it only
    publishes timing events that other services respond to.

    TradingContext
    --------------
    Market Assumptions
        - Perfect tick timing (no drift)
        - All components react to phase events
        - No direct order handling

    Trading Rules
        - Components must respect phase timing
        - Order submission only during window
        - Matching only at designated time

    Examples
    --------
    >>> config = GameConfig(session_name="test_game")
    >>> exchange = ExchangeVenue()
    >>> strategies = [MarketMakerBot(), HedgeFundBot()]
    >>> game = GameLoop(config, exchange, strategies)
    >>> game.run_session()  # Run entire game
    """

    def __init__(
        self,
        config: GameConfig,
        exchange: ExchangeVenue,
        strategies: List[TradingStrategy],
        price_model: object = None,
        market_data_service: object = None,
        real_time: bool = False,
    ):
        self.config = config
        self.exchange = exchange
        self.strategies = strategies
        self.price_model = price_model
        self.market_data_service = market_data_service
        self.real_time = real_time

        # Game state
        self.current_tick = 0
        self.tick_start_time: Optional[datetime] = None

    def run_session(self) -> None:
        """Run the complete trading session.

        Executes all configured ticks, managing the timing and
        phase progression for the entire game.

        Notes
        -----
        This method blocks until all ticks are complete or an
        error occurs. Progress is logged to console.
        """
        print(f"\n{'='*60}")
        print(f"Starting game session: {self.config.session_name}")
        print(f"Total ticks: {self.config.total_ticks}")
        print(f"Strategies: {[s.get_name() for s in self.strategies]}")
        print(f"Real-time mode: {self.real_time}")
        print(f"{'='*60}\n")

        for tick in range(self.config.total_ticks):
            self.run_tick()

        print(f"\n{'='*60}")
        print("Game session complete!")
        print(f"{'='*60}\n")

    def run_tick(self) -> None:
        """Execute one complete 5-minute trading tick.

        Manages tick timing and publishes phase events. Does not
        directly handle any trading logic - only orchestrates timing.

        Notes
        -----
        Each tick follows the phase schedule defined in TickPhase.
        In non-real-time mode, executes as fast as possible.
        """
        self.tick_start_time = datetime.now()
        print(f"\n{'='*50}")
        print(f"TICK {self.current_tick} - {self.tick_start_time}")
        print(f"{'='*50}")

        # T+0:00 - Market Data Phase
        self._trigger_market_data_update()
        self._wait_until_phase(TickPhase.PRE_OPEN)

        # T+0:30 - Pre-Open Phase
        self._signal_pre_open()
        self._wait_until_phase(TickPhase.OPEN)

        # T+3:00 - Open Phase
        self._signal_open()
        self._wait_until_phase(TickPhase.TRADING)

        # T+3:30 - Trading Phase
        self._trigger_trading()
        self._wait_until_phase(TickPhase.CLOSED)

        # T+5:00 - Closed Phase
        self._signal_closed()

        self.current_tick += 1

    def _wait_until_phase(self, phase: TickPhase) -> None:
        """Wait until specified phase time if in real-time mode.

        Parameters
        ----------
        phase : TickPhase
            Phase to wait until
        """
        if not self.real_time or self.tick_start_time is None:
            return

        target_time = self.tick_start_time + timedelta(
            seconds=phase.total_seconds
        )
        wait_seconds = (target_time - datetime.now()).total_seconds()

        if wait_seconds > 0:
            print(f"  Waiting {wait_seconds:.1f}s until {phase.name}...")
            time.sleep(wait_seconds)

    def _trigger_market_data_update(self) -> None:
        """Signal market data update phase.

        Publishes event at T+0:00 that triggers:
        - Price Model to generate new SPX/SPY prices
        - Market Data Service to prepare distribution
        """
        print("T+0:00 - Market data update...")

        if self.price_model:
            # Trigger: price_model.on_tick_start(self.current_tick)
            print("  Price Model triggered (stub)")
        else:
            print("  No Price Model connected")

        if self.market_data_service:
            # Trigger: market_data_service.prepare_tick_data()
            print("  Market Data Service triggered (stub)")

    def _signal_pre_open(self) -> None:
        """Signal pre-open phase where orders are accepted.

        Publishes event at T+0:30 that triggers:
        - Strategies can begin submitting orders
        - Order Validator begins accepting orders
        - Market Data Service distributes data to strategies
        """
        print("T+0:30 - PRE-OPEN phase")

        # In full implementation, this would publish an event
        # that strategies and other services subscribe to

        # For now, directly notify strategies
        if self.market_data_service:
            print("  Market data distributed to all strategies")
        else:
            # Stub - directly call strategies
            print("  Notifying strategies (stub implementation)")
            for strategy in self.strategies:
                print(f"    - {strategy.get_name()} notified")

    def _signal_open(self) -> None:
        """Signal open phase - order submission ends.

        Publishes event at T+3:00 that triggers:
        - Order Validator stops accepting new orders
        - Strategies cannot submit new orders
        """
        print("T+3:00 - OPEN phase - order submission closed")
        print("  No new orders accepted")

    def _trigger_trading(self) -> None:
        """Signal trading phase - execute matching.

        Publishes event at T+3:30 that triggers:
        - Exchange Engine to match orders (batch or continuous)
        - Position Service to update from trades
        """
        print("T+3:30 - TRADING phase - executing matches...")

        if self.exchange:
            # In full implementation:
            # self.exchange.execute_batch_matching() for batch mode
            # or continuous matching already active
            print("  Exchange matching triggered (stub)")
        else:
            print("  No Exchange connected")

    def _signal_closed(self) -> None:
        """Signal end of current tick.

        Publishes event at T+5:00 that triggers:
        - Services to finalize tick processing
        - Prepare for next tick
        """
        print(f"T+5:00 - Tick {self.current_tick} complete")

        # Log tick summary
        if self.tick_start_time is not None:
            elapsed = (datetime.now() - self.tick_start_time).total_seconds()
            print(f"  Real tick duration: {elapsed:.1f}s")

        # Note: Orders persist across ticks (not cleared)
