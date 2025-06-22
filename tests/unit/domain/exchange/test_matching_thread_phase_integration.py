"""Functional tests for matching thread phase transition integration.

These tests verify that the matching thread properly checks for phase
transitions on a regular basis regardless of order flow patterns.
"""

import threading
import time
from queue import Queue
from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.models.instrument import Instrument
from intern_trading_game.domain.exchange.models.order import Order
from intern_trading_game.domain.exchange.threads_v2 import matching_thread_v2
from intern_trading_game.domain.exchange.types import PhaseState, PhaseType
from intern_trading_game.domain.exchange.venue import ExchangeVenue


class TestMatchingThreadPhaseIntegration:
    """Test phase transition checking in the matching thread."""

    @pytest.fixture
    def mock_phase_manager(self):
        """Create a mock phase manager."""
        manager = Mock()
        manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous",
        )
        return manager

    @pytest.fixture
    def exchange(self, mock_phase_manager):
        """Create exchange with mock phase manager."""
        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        # Add test instrument
        instrument = Instrument(
            symbol="TEST-INSTRUMENT",
            underlying="TEST",
            strike=100.0,
            expiry="2024-12-31",
            option_type="call",
        )
        exchange.list_instrument(instrument)

        return exchange

    @pytest.fixture
    def team_info(self):
        """Create mock team info."""
        team = Mock()
        team.team_id = "team1"
        return team

    @pytest.fixture
    def test_order(self):
        """Create a test order."""
        return Order(
            instrument_id="TEST-INSTRUMENT",
            side="buy",
            quantity=10,
            price=100.0,
            trader_id="trader1",
        )

    def test_phase_transitions_checked_during_quiet_periods(
        self, exchange, team_info, mock_phase_manager
    ):
        """Test phase transitions are checked when no orders arrive.

        Given - Matching thread running with no orders
        The thread should still check for phase transitions regularly
        even when the market is quiet.

        When - Thread runs for 250ms with no orders
        The timeout mechanism should trigger phase checks.

        Then - Phase transitions are checked multiple times
        At least 2 checks should occur (at 100ms and 200ms).
        """
        # Given - Set up queues and mock exchange method
        match_queue = Queue()
        trade_queue = Queue()
        websocket_queue = Queue()

        # Mock the check_phase_transitions method to track calls
        exchange.check_phase_transitions = Mock()

        # When - Run thread in background for 250ms
        thread_running = threading.Event()

        def run_thread():
            thread_running.set()
            matching_thread_v2(
                match_queue=match_queue,
                trade_queue=trade_queue,
                websocket_queue=websocket_queue,
                exchange=exchange,
            )

        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()

        # Wait for thread to start
        thread_running.wait(timeout=1.0)

        # Let it run for 250ms with no orders
        time.sleep(0.25)

        # Stop the thread
        match_queue.put(None)
        thread.join(timeout=1.0)

        # Then - Phase transitions should be checked multiple times
        assert exchange.check_phase_transitions.call_count >= 2
        print(
            f"Phase checks during quiet period: {exchange.check_phase_transitions.call_count}"
        )

    def test_phase_transitions_checked_during_busy_periods(
        self, exchange, team_info, test_order, mock_phase_manager
    ):
        """Test phase transitions are checked even with continuous orders.

        Given - Orders arriving every 50ms (faster than 100ms check interval)
        This simulates a busy trading period where orders arrive continuously.

        When - Thread processes orders for 250ms
        Even with continuous order flow, phase checks must still occur.

        Then - Phase transitions are checked despite busy order flow
        At least 2 phase checks should occur even with orders every 50ms.
        """
        # Given - Set up queues and tracking
        match_queue = Queue()
        trade_queue = Queue()
        websocket_queue = Queue()

        exchange.check_phase_transitions = Mock()

        # Create orders with different IDs to avoid conflicts
        orders = []
        for i in range(6):  # 6 orders over 250ms = one every ~40ms
            order = Order(
                instrument_id="TEST-INSTRUMENT",
                side="buy",
                quantity=10,
                price=100.0,
                trader_id="trader1",
                order_id=f"order_{i}",  # Unique IDs
            )
            orders.append((order, team_info))

        # When - Start thread and feed it orders continuously
        thread_running = threading.Event()

        def run_thread():
            thread_running.set()
            matching_thread_v2(
                match_queue=match_queue,
                trade_queue=trade_queue,
                websocket_queue=websocket_queue,
                exchange=exchange,
            )

        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()

        # Wait for thread to start
        thread_running.wait(timeout=1.0)

        # Feed orders every 40ms for 250ms total
        def feed_orders():
            for order_data in orders:
                match_queue.put(order_data)
                time.sleep(0.04)  # 40ms between orders

        order_thread = threading.Thread(target=feed_orders)
        order_thread.daemon = True
        order_thread.start()

        # Let it run for 300ms (includes order processing time)
        time.sleep(0.3)

        # Stop the thread
        match_queue.put(None)
        thread.join(timeout=1.0)
        order_thread.join(timeout=1.0)

        # Then - Phase transitions still checked despite busy period
        assert exchange.check_phase_transitions.call_count >= 2
        print(
            f"Phase checks during busy period: {exchange.check_phase_transitions.call_count}"
        )

    def test_phase_transitions_checked_with_mixed_order_patterns(
        self, exchange, team_info, test_order, mock_phase_manager
    ):
        """Test phase checking with realistic mixed order patterns.

        Given - Mixed pattern: busy periods, quiet periods, single orders
        Real markets have varying order flow - sometimes busy, sometimes quiet.

        When - Thread experiences: 75ms quiet, order, 75ms quiet, order, 100ms quiet
        This tests the specific scenario you mentioned.

        Then - Phase transitions are checked regularly throughout
        Checks should occur regardless of the irregular order pattern.
        """
        # Given - Set up queues and tracking
        match_queue = Queue()
        trade_queue = Queue()
        websocket_queue = Queue()

        exchange.check_phase_transitions = Mock()

        thread_running = threading.Event()

        def run_thread():
            thread_running.set()
            matching_thread_v2(
                match_queue=match_queue,
                trade_queue=trade_queue,
                websocket_queue=websocket_queue,
                exchange=exchange,
            )

        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()

        # Wait for thread to start
        thread_running.wait(timeout=1.0)

        # When - Execute mixed pattern
        start_time = time.time()

        # 75ms quiet
        time.sleep(0.075)

        # Send order
        order1 = Order(
            instrument_id="TEST-INSTRUMENT",
            side="buy",
            quantity=10,
            price=100.0,
            trader_id="trader1",
            order_id="mixed_1",
        )
        match_queue.put((order1, team_info))

        # 75ms quiet
        time.sleep(0.075)

        # Send order
        order2 = Order(
            instrument_id="TEST-INSTRUMENT",
            side="sell",
            quantity=10,
            price=100.0,
            trader_id="trader1",
            order_id="mixed_2",
        )
        match_queue.put((order2, team_info))

        # 100ms quiet
        time.sleep(0.1)

        total_time = time.time() - start_time

        # Stop thread
        match_queue.put(None)
        thread.join(timeout=1.0)

        # Then - Regular phase checks occurred
        expected_checks = int(total_time / 0.1)  # Every 100ms
        assert exchange.check_phase_transitions.call_count >= expected_checks
        print(
            f"Mixed pattern phase checks: {exchange.check_phase_transitions.call_count} in {total_time:.3f}s"
        )

    def test_guaranteed_phase_check_frequency(
        self, exchange, team_info, mock_phase_manager
    ):
        """Test that phase checks occur at guaranteed intervals.

        Given - Thread configured to check phases every 100ms
        The system should provide timing guarantees for phase checking.

        When - Thread runs for exactly 500ms
        Regardless of order patterns, timing should be predictable.

        Then - Phase checks occur approximately every 100ms
        Should get ~5 checks with some tolerance for timing precision.
        """
        # Given - Set up with precise timing tracking
        match_queue = Queue()
        trade_queue = Queue()
        websocket_queue = Queue()

        check_times = []

        def track_phase_checks():
            check_times.append(time.time())

        exchange.check_phase_transitions = Mock(side_effect=track_phase_checks)

        thread_running = threading.Event()

        def run_thread():
            thread_running.set()
            matching_thread_v2(
                match_queue=match_queue,
                trade_queue=trade_queue,
                websocket_queue=websocket_queue,
                exchange=exchange,
            )

        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()

        # Wait for thread to start
        thread_running.wait(timeout=1.0)

        # When - Run for exactly 500ms
        time.sleep(0.5)

        # Stop thread
        match_queue.put(None)
        thread.join(timeout=1.0)

        # Then - Analyze timing

        # Should get approximately 5 checks in 500ms (every 100ms)
        assert (
            len(check_times) >= 4
        ), f"Expected >=4 checks, got {len(check_times)}"
        assert (
            len(check_times) <= 7
        ), f"Expected <=7 checks, got {len(check_times)}"

        # Check intervals between consecutive checks
        if len(check_times) > 1:
            intervals = [
                check_times[i + 1] - check_times[i]
                for i in range(len(check_times) - 1)
            ]
            avg_interval = sum(intervals) / len(intervals)

            # Average should be close to 100ms (0.1s)
            assert (
                0.08 <= avg_interval <= 0.12
            ), f"Average interval {avg_interval:.3f}s not near 0.1s"

            print(f"Check intervals: {[f'{i:.3f}s' for i in intervals]}")
            print(f"Average interval: {avg_interval:.3f}s")

    def test_phase_transition_execution_during_order_processing(
        self, exchange, team_info, mock_phase_manager
    ):
        """Test that phase transitions execute even during order processing.

        Given - Market phase changes while orders are being processed
        This simulates the real scenario where phase changes during active trading.

        When - Phase changes from CONTINUOUS to CLOSED while processing orders
        The transition handler should execute despite ongoing order activity.

        Then - Market close actions are executed automatically
        Orders should be cancelled even if new orders were being processed.
        """
        # Given - Set up phase change simulation
        match_queue = Queue()
        trade_queue = Queue()
        websocket_queue = Queue()

        # Track phase manager calls and simulate phase change
        phase_call_count = 0

        def simulate_phase_change():
            nonlocal phase_call_count
            phase_call_count += 1

            # After 3 calls (~300ms), simulate market close
            if phase_call_count >= 3:
                mock_phase_manager.get_current_phase_state.return_value = (
                    PhaseState(
                        phase_type=PhaseType.CLOSED,
                        is_order_submission_allowed=False,
                        is_order_cancellation_allowed=False,
                        is_matching_enabled=False,
                        execution_style="none",
                    )
                )

        # Mock the transition handler to track calls
        original_handler = (
            exchange._transition_handler.check_and_handle_transition
        )
        handler_calls = []

        def track_handler_calls(phase):
            handler_calls.append(phase)
            return original_handler(phase)

        exchange._transition_handler.check_and_handle_transition = Mock(
            side_effect=track_handler_calls
        )

        # Override check_phase_transitions to simulate phase change
        original_check = exchange.check_phase_transitions

        def mock_check():
            simulate_phase_change()
            return original_check()

        exchange.check_phase_transitions = Mock(side_effect=mock_check)

        # When - Start thread and send some orders
        thread_running = threading.Event()

        def run_thread():
            thread_running.set()
            matching_thread_v2(
                match_queue=match_queue,
                trade_queue=trade_queue,
                websocket_queue=websocket_queue,
                exchange=exchange,
            )

        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()

        # Wait for thread to start
        thread_running.wait(timeout=1.0)

        # Send a few orders during phase transition period
        for i in range(3):
            order = Order(
                instrument_id="TEST-INSTRUMENT",
                side="buy",
                quantity=10,
                price=100.0,
                trader_id="trader1",
                order_id=f"transition_order_{i}",
            )
            match_queue.put((order, team_info))
            time.sleep(0.05)  # 50ms between orders

        # Let thread run long enough for phase transition to be detected
        time.sleep(0.4)

        # Stop thread
        match_queue.put(None)
        thread.join(timeout=1.0)

        # Then - Verify phase transition was detected and handled
        assert exchange.check_phase_transitions.call_count >= 3
        assert len(handler_calls) >= 3

        # Should have detected transition to CLOSED phase
        assert PhaseType.CLOSED in handler_calls
        print(f"Handler called with phases: {handler_calls}")

    def test_thread_shutdown_gracefully_after_phase_checking(
        self, exchange, team_info, mock_phase_manager
    ):
        """Test thread shuts down properly even with phase checking.

        Given - Thread running with regular phase checks
        The enhanced thread should still respond to shutdown signals.

        When - Shutdown signal is sent
        Thread should exit cleanly without hanging.

        Then - Thread terminates within reasonable time
        Should not be blocked by phase checking logic.
        """
        # Given - Set up thread with phase checking
        match_queue = Queue()
        trade_queue = Queue()
        websocket_queue = Queue()

        exchange.check_phase_transitions = Mock()

        thread_running = threading.Event()
        thread_finished = threading.Event()

        def run_thread():
            thread_running.set()
            try:
                matching_thread_v2(
                    match_queue=match_queue,
                    trade_queue=trade_queue,
                    websocket_queue=websocket_queue,
                    exchange=exchange,
                )
            finally:
                thread_finished.set()

        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()

        # Wait for thread to start and begin phase checking
        thread_running.wait(timeout=1.0)
        time.sleep(0.15)  # Let it do at least one phase check

        # When - Send shutdown signal
        shutdown_start = time.time()
        match_queue.put(None)

        # Then - Thread should finish quickly
        thread_finished.wait(timeout=2.0)
        shutdown_time = time.time() - shutdown_start

        assert thread_finished.is_set(), "Thread did not finish within timeout"
        assert (
            shutdown_time < 1.0
        ), f"Shutdown took too long: {shutdown_time:.3f}s"

        # Verify some phase checks occurred before shutdown
        assert exchange.check_phase_transitions.call_count > 0
        print(
            f"Thread shutdown in {shutdown_time:.3f}s after {exchange.check_phase_transitions.call_count} phase checks"
        )
