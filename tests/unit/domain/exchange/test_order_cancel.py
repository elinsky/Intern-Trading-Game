"""Unit tests for order cancellation functionality.

These tests verify the core cancellation logic without requiring
the full API threading infrastructure. They test:
- Exchange-level cancellation behavior
- Order state transitions during cancellation
- FIFO queue ordering guarantees
- Idempotency and edge cases
"""

from queue import Queue
from typing import Any, List, Tuple
from unittest.mock import Mock

import pytest

from intern_trading_game.domain.exchange.components.core.models import (
    Instrument,
    Order,
    OrderSide,
    OrderType,
)
from intern_trading_game.domain.exchange.components.core.types import (
    PhaseState,
    PhaseType,
)
from intern_trading_game.domain.exchange.components.orderbook.matching_engine import (
    BatchMatchingEngine,
    ContinuousMatchingEngine,
)
from intern_trading_game.domain.exchange.venue import ExchangeVenue


class MockQueueProcessor:
    """Simulates queue processing without threads.

    This mock helps us test FIFO ordering and message processing
    logic without the complexity of actual threading.
    """

    def __init__(self, exchange: ExchangeVenue):
        self.exchange = exchange
        self.processed_messages: List[Tuple[str, Any]] = []
        self.message_queue = Queue()

    def submit_message(self, message_type: str, data: Any, team_id: str):
        """Add a message to the queue."""
        self.message_queue.put((message_type, data, team_id))

    def process_all_messages(self):
        """Process all queued messages in FIFO order."""
        while not self.message_queue.empty():
            message_type, data, team_id = self.message_queue.get()
            self.processed_messages.append((message_type, data))

            if message_type == "new_order":
                order = data
                self.exchange.submit_order(order)
            elif message_type == "cancel_order":
                order_id = data
                self.exchange.cancel_order(order_id, team_id)

    def get_processing_order(self) -> List[str]:
        """Get the order in which messages were processed."""
        return [msg[0] for msg in self.processed_messages]


@pytest.fixture
def mock_phase_manager():
    """Create a mock phase manager for testing."""
    manager = Mock()
    # Default to continuous trading phase
    manager.get_current_phase_state.return_value = PhaseState(
        phase_type=PhaseType.CONTINUOUS,
        is_order_submission_allowed=True,
        is_order_cancellation_allowed=True,
        is_matching_enabled=True,
        execution_style="continuous",
    )
    return manager


@pytest.fixture
def exchange(mock_phase_manager):
    """Create a fresh exchange instance for testing."""
    return ExchangeVenue(
        phase_manager=mock_phase_manager,
        continuous_engine=ContinuousMatchingEngine(),
        batch_engine=BatchMatchingEngine(),
    )


@pytest.fixture
def test_instrument(exchange):
    """Create and list a test instrument."""
    instrument = Instrument(
        symbol="TEST_OPTION",
        strike=100.0,
        option_type="call",
        underlying="TEST",
    )
    exchange.list_instrument(instrument)
    return instrument


def test_cancel_own_order(exchange, test_instrument):
    """Test successful cancellation of own order.

    Given - A trader has a resting limit order
    The order is in the book providing liquidity.

    When - The trader cancels their order
    Using the correct trader_id for ownership check.

    Then - The order is removed from the book
    The cancel operation returns True for success.
    """
    # Submit order
    order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=95.0,
    )
    result = exchange.submit_order(order)
    assert result.status == "new"

    # Verify order in book
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 1
    assert book.best_bid()[0] == 95.0

    # Cancel the order
    success = exchange.cancel_order(order.order_id, "TRADER_1")
    assert success is True

    # Verify order removed
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 0
    assert book.best_bid() is None


def test_cannot_cancel_others_order(exchange, test_instrument):
    """Test that traders cannot cancel orders they don't own.

    Given - Trader 1 has a resting order

    When - Trader 2 attempts to cancel it

    Then - The cancel is rejected with ValueError
    """
    # Trader 1 places order
    order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=95.0,
    )
    result = exchange.submit_order(order)
    assert result.status == "new"

    # Trader 2 tries to cancel - should raise ValueError
    with pytest.raises(ValueError, match="does not own order"):
        exchange.cancel_order(order.order_id, "TRADER_2")

    # Verify order still in book
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 1


def test_cancel_non_existent_order(exchange):
    """Test cancelling an order that doesn't exist.

    Given - No order with ID 'FAKE_123'

    When - Cancel request sent

    Then - Returns False
    """
    success = exchange.cancel_order("FAKE_123", "TRADER_1")
    assert success is False


def test_cancel_already_filled_order(exchange, test_instrument):
    """Test cancel attempt on filled order.

    Given - An order that was completely filled

    When - Trader tries to cancel

    Then - Cancel fails
    """
    # Place sell order
    sell_order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.SELL,
        quantity=10,
        price=100.0,
    )
    exchange.submit_order(sell_order)

    # Place matching buy that fills it
    buy_order = Order(
        trader_id="TRADER_2",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=10,
    )
    buy_result = exchange.submit_order(buy_order)
    assert buy_result.status == "filled"

    # Try to cancel the filled sell order
    success = exchange.cancel_order(sell_order.order_id, "TRADER_1")
    assert success is False


def test_cancel_partially_filled_order(exchange, test_instrument):
    """Test cancellation of partially filled order.

    Given - Order filled 5 of 10 contracts

    When - Trader cancels remaining

    Then - Remaining 5 cancelled, filled quantity unchanged
    """
    # Place large sell order
    sell_order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.SELL,
        quantity=10,
        price=100.0,
    )
    exchange.submit_order(sell_order)

    # Partially fill with smaller buy
    buy_order = Order(
        trader_id="TRADER_2",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=5,
        price=100.0,
    )
    buy_result = exchange.submit_order(buy_order)
    assert buy_result.status == "filled"
    assert buy_result.fills[0].quantity == 5

    # Verify partial fill state
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.asks) == 1
    # The remaining order should have 5 quantity
    remaining_order = book.asks[0].orders[0]
    assert remaining_order.remaining_quantity == 5

    # Cancel remaining
    success = exchange.cancel_order(sell_order.order_id, "TRADER_1")
    assert success is True

    # Verify book is empty
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.asks) == 0


def test_cancel_new_order_state(exchange, test_instrument):
    """Test cancellation of order in 'new' state.

    Given - An order that is resting in the book (new state)

    When - Owner cancels the order

    Then - Cancel succeeds and order is removed
    """
    # Submit a new order
    order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=95.0,
    )
    result = exchange.submit_order(order)
    assert result.status == "new"

    # Verify it's in the book
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 1

    # Cancel the order
    success = exchange.cancel_order(order.order_id, "TRADER_1")
    assert success is True

    # Verify it's removed
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 0


def test_cancel_partially_filled_order_state(exchange, test_instrument):
    """Test cancellation of order in 'partially_filled' state.

    Given - An order that has been partially filled

    When - Owner cancels the remaining quantity

    Then - Remaining quantity is cancelled, filled portion remains executed
    """
    # Place a large sell order
    sell_order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.SELL,
        quantity=20,
        price=100.0,
    )
    sell_result = exchange.submit_order(sell_order)
    assert sell_result.status == "new"

    # Partially fill it with a smaller buy
    buy_order = Order(
        trader_id="TRADER_2",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=8,
        price=100.0,
    )
    buy_result = exchange.submit_order(buy_order)
    assert buy_result.status == "filled"
    assert buy_result.fills[0].quantity == 8

    # Verify partial fill state in book
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.asks) == 1
    remaining_order = book.asks[0].orders[0]
    assert remaining_order.remaining_quantity == 12  # 20 - 8

    # Cancel the remaining portion
    success = exchange.cancel_order(sell_order.order_id, "TRADER_1")
    assert success is True

    # Verify book is now empty
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.asks) == 0


def test_cannot_cancel_already_cancelled_order(exchange, test_instrument):
    """Test that cancelled orders cannot be cancelled again.

    Given - An order that was previously cancelled

    When - Another cancel attempt is made

    Then - The second cancel fails gracefully
    """
    # Place and cancel an order
    order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=95.0,
    )
    exchange.submit_order(order)

    # First cancel succeeds
    success = exchange.cancel_order(order.order_id, "TRADER_1")
    assert success is True

    # Second cancel fails
    success = exchange.cancel_order(order.order_id, "TRADER_1")
    assert success is False


def test_multiple_cancel_idempotency(exchange, test_instrument):
    """Test that multiple cancels of same order are handled gracefully.

    Given - An order that gets cancelled

    When - Multiple cancel requests are sent

    Then - First succeeds, subsequent ones fail gracefully
    """
    # Place an order
    order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=95.0,
    )
    result = exchange.submit_order(order)
    assert result.status == "new"

    # First cancel - should succeed
    success1 = exchange.cancel_order(order.order_id, "TRADER_1")
    assert success1 is True

    # Second cancel - should fail gracefully
    success2 = exchange.cancel_order(order.order_id, "TRADER_1")
    assert success2 is False

    # Third cancel - still fails, no errors
    success3 = exchange.cancel_order(order.order_id, "TRADER_1")
    assert success3 is False

    # Verify order is gone
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 0


def test_queue_fifo_ordering(exchange, test_instrument):
    """Test that messages are processed in submission order.

    Given - A sequence of orders and cancels submitted

    When - They are processed through a queue

    Then - FIFO order is strictly maintained
    """
    processor = MockQueueProcessor(exchange)

    # Create orders
    order_a = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=95.0,
    )

    order_b = Order(
        trader_id="TRADER_2",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=5,
        price=94.0,
    )

    order_c = Order(
        trader_id="TRADER_3",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=15,
        price=93.0,
    )

    # Submit in specific order: Order A, Order B, Cancel A, Order C
    processor.submit_message("new_order", order_a, "TRADER_1")
    processor.submit_message("new_order", order_b, "TRADER_2")
    processor.submit_message("cancel_order", order_a.order_id, "TRADER_1")
    processor.submit_message("new_order", order_c, "TRADER_3")

    # Process all messages
    processor.process_all_messages()

    # Verify processing order
    processing_order = processor.get_processing_order()
    assert processing_order == [
        "new_order",
        "new_order",
        "cancel_order",
        "new_order",
    ]

    # Verify final state - Order A cancelled, B and C in book
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 2

    # Check specific orders are present
    order_ids = {
        order.order_id for level in book.bids for order in level.orders
    }
    assert order_a.order_id not in order_ids  # Cancelled
    assert order_b.order_id in order_ids  # Still there
    assert order_c.order_id in order_ids  # Still there


def test_cancel_cannot_jump_queue(exchange, test_instrument):
    """Test that urgent cancels still respect FIFO.

    Given - Many orders followed by a cancel

    When - All are processed

    Then - Cancel doesn't jump ahead of earlier orders
    """
    processor = MockQueueProcessor(exchange)

    # Submit 10 orders
    orders = []
    for i in range(10):
        order = Order(
            trader_id=f"TRADER_{i}",
            instrument_id=test_instrument.symbol,
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=1,
            price=100.0 - i,  # Different prices to avoid matching
        )
        orders.append(order)
        processor.submit_message("new_order", order, f"TRADER_{i}")

    # Submit 1 cancel for the 5th order
    processor.submit_message("cancel_order", orders[4].order_id, "TRADER_4")

    # Submit 5 more orders
    for i in range(10, 15):
        order = Order(
            trader_id=f"TRADER_{i}",
            instrument_id=test_instrument.symbol,
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=1,
            price=100.0 - i,
        )
        processor.submit_message("new_order", order, f"TRADER_{i}")

    # Process all
    processor.process_all_messages()

    # Verify the cancel was processed after the first 10 orders
    processing_order = processor.get_processing_order()
    cancel_index = processing_order.index("cancel_order")
    assert cancel_index == 10  # After first 10 orders

    # Verify total processing order
    expected = ["new_order"] * 10 + ["cancel_order"] + ["new_order"] * 5
    assert processing_order == expected

    # Verify final state
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 14  # 15 orders - 1 cancelled


def test_cancel_order_not_in_book(exchange, test_instrument):
    """Test edge case where order exists but not in book.

    Given - An order that was submitted but immediately filled

    When - Cancel is attempted

    Then - Cancel fails appropriately
    """
    # Place a sell order
    sell_order = Order(
        trader_id="TRADER_1",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.SELL,
        quantity=10,
        price=100.0,
    )
    sell_result = exchange.submit_order(sell_order)

    # Immediately match with aggressive buy
    buy_order = Order(
        trader_id="TRADER_2",
        instrument_id=test_instrument.symbol,
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=10,
        price=100.0,
    )
    buy_result = exchange.submit_order(buy_order)

    # Both should be filled
    assert sell_result.status == "new"  # Was new when submitted
    assert buy_result.status == "filled"

    # Try to cancel the sell order (already filled)
    success = exchange.cancel_order(sell_order.order_id, "TRADER_1")
    assert success is False

    # Verify book is empty
    book = exchange.get_order_book(test_instrument.symbol)
    assert len(book.bids) == 0
    assert len(book.asks) == 0
