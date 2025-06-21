# Phase Transition Implementation Plan

## Overview

This document outlines the design and implementation plan for the Exchange Phase Transition system. The system automatically executes actions when the market transitions between phases (e.g., executing the opening auction when moving from OPENING_AUCTION to CONTINUOUS).

## Architecture Context

### Current State

- The `ExchangeVenue` has methods for phase-specific actions (`execute_opening_auction()`, `cancel_all_orders()`)
- These methods must be called manually at the right time
- The `PhaseManager` knows what phase we're in but doesn't trigger actions

### Problem

- No automatic triggering of phase transition actions
- Tests expect automatic behavior but it doesn't exist
- Risk of missing critical market operations

### Solution

- Create `ExchangePhaseTransitionHandler` to monitor phase changes and execute actions
- Integrate with existing matching thread (no new threads needed)
- Maintain clean separation of concerns

## Design Philosophy

### Separation of Concerns

```
PhaseManager                          ExchangePhaseTransitionHandler
────────────                          ─────────────────────────────
Knows WHEN phases change       vs.    Knows WHAT to do when they change
"It's 9:30 AM, so CONTINUOUS"         "OPENING_AUCTION→CONTINUOUS = run auction"
Handles time and schedules            Handles actions and execution
```

### SOLID Principles

1. **Single Responsibility**
   - PhaseManager: Determine current phase based on time
   - TransitionHandler: Execute actions on phase changes
   - ExchangeVenue: Manage order books and matching

2. **Open/Closed**
   - New transitions can be added to handler without modifying existing code
   - Dispatch table pattern for extensibility

3. **Liskov Substitution**
   - Any `ExchangeOperations` implementation works with handler
   - Any `PhaseManagerInterface` implementation works with venue

4. **Interface Segregation**
   - `ExchangeOperations` protocol exposes only what handler needs
   - Minimal interface prevents tight coupling

5. **Dependency Inversion**
   - Handler depends on `ExchangeOperations` abstraction, not concrete `ExchangeVenue`
   - Venue depends on `PhaseManagerInterface`, not concrete implementation

## Detailed Design

### Component Diagram

```
┌─────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│  PhaseManager   │────────▶│   ExchangeVenue      │────────▶│ TransitionHandler│
│                 │         │                      │         │                 │
│ get_current_    │         │ - phase_manager     │         │ - _last_phase   │
│   phase_state() │         │ - _transition_      │         │ - _transition_  │
└─────────────────┘         │     handler         │         │     actions     │
                            │ - check_phase_      │         │                 │
                            │     transitions()   │         │ handle_         │
                            │                      │         │   transition()  │
                            └──────────────────────┘         └─────────────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │   MatchingThread     │
                            │                      │
                            │ Calls check_phase_   │
                            │ transitions()        │
                            │ periodically         │
                            └──────────────────────┘
```

### ExchangeOperations Protocol

```python
class ExchangeOperations(Protocol):
    """Minimal interface needed by transition handler."""

    def execute_opening_auction(self) -> None:
        """Execute the opening auction batch match."""
        ...

    def cancel_all_orders(self) -> None:
        """Cancel all resting orders across all instruments."""
        ...
```

### Transition Handler Design

```python
class ExchangePhaseTransitionHandler:
    def __init__(self, exchange_operations: ExchangeOperations):
        self._exchange = exchange_operations
        self._last_phase: Optional[PhaseType] = None

        # Dispatch table for transitions
        self._transition_actions = {
            (PhaseType.OPENING_AUCTION, PhaseType.CONTINUOUS):
                self._on_market_open,
            (PhaseType.CONTINUOUS, PhaseType.CLOSED):
                self._on_market_close,
        }

    def check_and_handle_transition(self, current_phase: PhaseType) -> bool:
        """Main method called periodically to check for transitions."""
        # Detect transition and execute action if needed

    def handle_transition(self, from_phase: PhaseType, to_phase: PhaseType):
        """Execute action for specific transition."""
        # Look up and execute action from dispatch table
```

### Integration Points

1. **ExchangeVenue Constructor**
   - Create `_transition_handler` instance
   - Pass `self` as the `ExchangeOperations` implementation

2. **New Method: check_phase_transitions()**
   - Get current phase from phase_manager
   - Call handler's check_and_handle_transition()

3. **MatchingThread Integration**
   - Add `self.exchange.check_phase_transitions()` to main loop
   - Runs every ~100ms (when queue.get times out)

## Implementation Plan (TDD)

### Commit 1: Define ExchangeOperations Protocol
**Branch**: `feat/phase-transition-protocol`
**Commit Message**: `feat: add ExchangeOperations protocol for phase transition handler`

**Files**:

- Create `src/intern_trading_game/domain/exchange/phase/protocols.py`

**Implementation**:
```python
from typing import Protocol

class ExchangeOperations(Protocol):
    """Protocol defining operations needed by phase transition handler.

    This protocol defines the minimal interface required from ExchangeVenue
    for handling phase transitions. Using a protocol ensures loose coupling
    and makes testing easier.

    Notes
    -----
    This follows the Interface Segregation Principle - the handler only
    needs these two methods, not the entire ExchangeVenue interface.
    """

    def execute_opening_auction(self) -> None:
        """Execute the opening auction batch match.

        This method should process all orders collected during pre-open
        using batch matching to establish fair opening prices.
        """
        ...

    def cancel_all_orders(self) -> None:
        """Cancel all resting orders across all instruments.

        This method should cancel every resting order in all order books,
        typically called when the market closes.
        """
        ...
```

### Commit 2: Create TransitionHandler Tests
**Commit Message**: `test: add failing tests for ExchangePhaseTransitionHandler`

**Files**:

- Create `tests/unit/domain/exchange/phase/test_transition_handler.py`

**Unit Test Cases**:

#### Basic Functionality Tests
1. `test_detects_phase_transition` - Returns True when phase changes
2. `test_no_transition_when_phase_unchanged` - Returns False when same phase
3. `test_first_check_records_phase` - First call just records, no transition
4. `test_reset_clears_state` - Reset allows fresh start

#### Transition Action Tests
5. `test_executes_opening_auction_on_market_open` - Calls auction method
6. `test_cancels_orders_on_market_close` - Calls cancel method
7. `test_no_action_for_unknown_transitions` - No calls for other transitions
8. `test_handles_direct_transition_call` - handle_transition works directly

#### Edge Cases and Error Scenarios
9. `test_multiple_rapid_transitions` - Handles back-to-back phase changes
10. `test_skipped_phase_transitions` - Handles non-adjacent phase changes
11. `test_idempotent_transition_handling` - Same transition twice is safe
12. `test_transition_from_closed_to_preopen` - New day transition (no action)

#### Business Scenario Tests
13. `test_handles_weekend_to_monday_transition` - CLOSED → PRE_OPEN after weekend
14. `test_handles_holiday_scenarios` - Extended CLOSED period doesn't break state
15. `test_auction_not_called_during_closed` - Safety check for invalid transitions

### Commit 3: Implement TransitionHandler
**Commit Message**: `feat: implement ExchangePhaseTransitionHandler`

**Files**:

- Create `src/intern_trading_game/domain/exchange/phase/transition_handler.py`
- Implement full handler with comprehensive docstrings

### Commit 4: Add ExchangeVenue Integration Tests
**Commit Message**: `test: add failing integration tests for phase-aware ExchangeVenue`

**Files**:

- Create `tests/unit/domain/exchange/test_venue_phase_integration.py`

**Integration Test Cases**:

#### Basic Integration Tests
1. `test_venue_creates_transition_handler` - Handler is initialized
2. `test_check_phase_transitions_method_exists` - Method is callable

#### Opening Auction Scenarios
3. `test_automatic_opening_auction_execution` - Basic auction on open
4. `test_opening_auction_with_multiple_instruments` - Auction across instruments
5. `test_opening_auction_with_partial_fills` - Handles partial matches
6. `test_opening_auction_with_no_crossing_orders` - Safe when no matches
7. `test_opening_auction_establishes_opening_price` - Sets market price

#### Market Close Scenarios
8. `test_automatic_order_cancellation_on_close` - Basic close behavior
9. `test_close_cancels_orders_across_all_instruments` - Comprehensive cancel
10. `test_close_with_no_orders` - Safe when books empty
11. `test_close_during_active_trading` - Handles orders mid-flight

#### Complex Business Scenarios
12. `test_full_trading_day_lifecycle` - PRE_OPEN → AUCTION → CONTINUOUS → CLOSED
13. `test_orders_rejected_after_automatic_close` - Post-close order handling
14. `test_position_state_preserved_through_transitions` - Positions unaffected
15. `test_trade_history_preserved_through_transitions` - Audit trail intact

#### Edge Cases
16. `test_rapid_phase_changes_handled_correctly` - Stress test transitions
17. `test_phase_transition_during_order_submission` - Concurrent operations
18. `test_transition_with_locked_market` - Bid equals ask scenarios
19. `test_transition_with_wide_spread_market` - No crossing orders

### Commit 5: Integrate Handler into ExchangeVenue
**Commit Message**: `feat: integrate phase transition handler into ExchangeVenue`

**Changes**:

- Update `__init__` to create handler
- Add `check_phase_transitions()` method
- Import necessary types

### Commit 6: Update Matching Thread
**Commit Message**: `feat: add phase transition checking to matching thread`

**Files**:

- Update `src/intern_trading_game/domain/exchange/threads.py`
- Add test to verify thread calls the method

### Commit 7: Enable Integration Tests
**Commit Message**: `test: enable and update phase transition integration tests`

**Files**:

- Update `tests/unit/domain/exchange/test_phase_transitions.py`
- Update `tests/unit/domain/exchange/test_exchange_phase_integration.py`
- Remove all `@pytest.mark.skip` decorators
- Adjust test expectations for automatic behavior

### Commit 8: Add Documentation
**Commit Message**: `docs: add phase transition architecture documentation`

**Files**:

- Create `docs/technical/phase-transitions.md`
- Update architecture docs if needed

## Testing Strategy

### Unit Tests

- Mock the `ExchangeOperations` to verify handler behavior
- Test each transition combination
- Verify state management and reset functionality

### Integration Tests

- Use real `ExchangeVenue` with mock `PhaseManager`
- Verify end-to-end behavior
- Test with actual orders and order books

### Example Tests (Given-When-Then)

#### Unit Test Example: Handler Behavior
```python
def test_handles_multiple_rapid_transitions(self):
    # Given - Handler in PRE_OPEN phase with mock exchange
    # Market opens with rapid phase changes on some trading days
    mock_exchange = Mock(spec=ExchangeOperations)
    handler = ExchangePhaseTransitionHandler(mock_exchange)
    handler.check_and_handle_transition(PhaseType.PRE_OPEN)

    # When - Multiple rapid transitions occur
    # PRE_OPEN → OPENING_AUCTION → CONTINUOUS within seconds
    result1 = handler.check_and_handle_transition(PhaseType.OPENING_AUCTION)
    result2 = handler.check_and_handle_transition(PhaseType.CONTINUOUS)

    # Then - Each transition is detected and handled correctly
    assert result1 is True  # Transition detected
    assert result2 is True  # Transition detected
    # Opening auction should be called exactly once
    mock_exchange.execute_opening_auction.assert_called_once()
    # Market close should not be called
    mock_exchange.cancel_all_orders.assert_not_called()
```

#### Integration Test Example: Business Scenario
```python
def test_full_trading_day_lifecycle(self):
    # Given - Fresh market at start of trading day
    # It's 6:00 AM and the market is closed from overnight.
    exchange = ExchangeVenue(phase_manager=mock_phase_manager)
    exchange.list_instrument(create_test_option("SPX", 4500, "call"))

    # Start in CLOSED phase
    set_phase(mock_phase_manager, PhaseType.CLOSED)
    exchange.check_phase_transitions()

    # When - Market goes through full day lifecycle

    # 8:30 AM - Market enters PRE_OPEN
    set_phase(mock_phase_manager, PhaseType.PRE_OPEN)
    exchange.check_phase_transitions()

    # Submit pre-open orders from market makers
    mm_buy = Order(instrument_id="SPX-4500-CALL", side="buy",
                   quantity=10, price=127.50, trader_id="MM1")
    mm_sell = Order(instrument_id="SPX-4500-CALL", side="sell",
                    quantity=10, price=128.50, trader_id="MM1")
    buy_result = exchange.submit_order(mm_buy)
    sell_result = exchange.submit_order(mm_sell)
    assert buy_result.status == "pending_new"  # Held for auction

    # 9:29:30 AM - Enter OPENING_AUCTION (book frozen)
    set_phase(mock_phase_manager, PhaseType.OPENING_AUCTION)
    exchange.check_phase_transitions()

    # Try to submit order during auction - should be rejected
    late_order = Order(instrument_id="SPX-4500-CALL", side="buy",
                      quantity=5, price=128.00, trader_id="HF1")
    late_result = exchange.submit_order(late_order)
    assert late_result.status == "rejected"
    assert "auction" in late_result.error_message.lower()

    # 9:30:00 AM - Market opens to CONTINUOUS trading
    set_phase(mock_phase_manager, PhaseType.CONTINUOUS)
    exchange.check_phase_transitions()

    # Then - Opening auction has executed automatically
    book = exchange.get_order_book("SPX-4500-CALL")
    trades = book.get_recent_trades(10)
    assert len(trades) > 0  # Auction created trades
    assert trades[0].price == 128.00  # Crossed at mid-point

    # Continue trading day...
    # Submit more orders during continuous trading
    day_order = Order(instrument_id="SPX-4500-CALL", side="buy",
                     quantity=5, price=128.25, trader_id="ARB1")
    day_result = exchange.submit_order(day_order)
    assert day_result.status == "new"  # Accepted immediately

    # 4:00 PM - Market closes
    set_phase(mock_phase_manager, PhaseType.CLOSED)
    exchange.check_phase_transitions()

    # Then - All orders have been cancelled automatically
    final_book = exchange.get_order_book("SPX-4500-CALL")
    assert len(final_book.bids) == 0
    assert len(final_book.asks) == 0

    # Trades are preserved for audit
    assert len(trades) > 0  # Historical trades still available
```

#### Edge Case Test Example
```python
def test_phase_transition_during_order_submission(self):
    # Given - Exchange in CONTINUOUS phase with active trading
    # This tests thread safety and concurrent operations
    exchange = ExchangeVenue(phase_manager=mock_phase_manager)
    exchange.list_instrument(test_instrument)
    set_phase(mock_phase_manager, PhaseType.CONTINUOUS)

    # Submit an order that will rest in the book
    resting_order = Order(instrument_id="TEST", side="buy",
                         quantity=100, price=95.00, trader_id="MM1")
    exchange.submit_order(resting_order)

    # When - Phase changes to CLOSED while order is being processed
    # Simulate a race condition where market closes during operations
    import threading

    def close_market():
        time.sleep(0.01)  # Small delay
        set_phase(mock_phase_manager, PhaseType.CLOSED)
        exchange.check_phase_transitions()

    # Start market close in background
    close_thread = threading.Thread(target=close_market)
    close_thread.start()

    # Try to submit order right as market is closing
    racing_order = Order(instrument_id="TEST", side="sell",
                        quantity=100, price=95.00, trader_id="HF1")
    result = exchange.submit_order(racing_order)

    close_thread.join()

    # Then - System handles the race condition gracefully
    # Either the order was accepted before close, or rejected after
    assert result.status in ["filled", "rejected"]

    # If rejected, should have clear reason
    if result.status == "rejected":
        assert "closed" in result.error_message.lower()

    # Final state should be consistent - no orders in closed market
    book = exchange.get_order_book("TEST")
    assert len(book.bids) == 0
    assert len(book.asks) == 0
```

## Migration Path

### Current (Monolith)

- Handler is created by ExchangeVenue
- Matching thread calls check method
- All in same process

### Future (Microservices)
```python
# Replace handler with RabbitMQ consumer
@channel.basic_consume('exchange.phase.transitions')
def on_phase_transition(message):
    event = json.loads(message.body)
    if event['from'] == 'OPENING_AUCTION' and event['to'] == 'CONTINUOUS':
        exchange.execute_opening_auction()
    elif event['from'] == 'CONTINUOUS' and event['to'] == 'CLOSED':
        exchange.cancel_all_orders()
```

## Test Helpers and Utilities

### Phase Test Helpers
```python
# tests/unit/domain/exchange/phase/helpers.py

def set_phase(mock_phase_manager, phase_type: PhaseType):
    """Helper to set phase state consistently in tests."""
    phase_states = {
        PhaseType.CLOSED: PhaseState(
            phase_type=PhaseType.CLOSED,
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=False,
            execution_style="none"
        ),
        PhaseType.PRE_OPEN: PhaseState(
            phase_type=PhaseType.PRE_OPEN,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="batch"
        ),
        PhaseType.OPENING_AUCTION: PhaseState(
            phase_type=PhaseType.OPENING_AUCTION,
            is_order_submission_allowed=False,
            is_order_cancellation_allowed=False,
            is_matching_enabled=True,
            execution_style="batch"
        ),
        PhaseType.CONTINUOUS: PhaseState(
            phase_type=PhaseType.CONTINUOUS,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=True,
            execution_style="continuous"
        ),
    }
    mock_phase_manager.get_current_phase_state.return_value = phase_states[phase_type]

def create_test_option(underlying: str, strike: float, option_type: str) -> Instrument:
    """Create a test option instrument."""
    return Instrument(
        symbol=f"{underlying}-{int(strike)}-{option_type.upper()}",
        underlying=underlying,
        instrument_type="option",
        strike=strike,
        option_type=option_type,
        expiration=datetime.now() + timedelta(days=30)
    )
```

## Success Criteria

1. **Automatic Behavior**: Phase transitions trigger actions without manual intervention
2. **No New Threads**: Reuses existing matching thread
3. **Clean Tests**: All integration tests pass without skip decorators
4. **Maintainable**: Easy to add new transitions
5. **Future-Ready**: Clear path to event-driven architecture
6. **Comprehensive Testing**: All business scenarios covered with clear tests

## Common Pitfalls to Avoid

1. **Don't Poll Too Frequently**: Every 100ms is sufficient
2. **Don't Add Time Logic**: Handler should not know about schedules
3. **Don't Over-Engineer**: No need for complex event systems yet
4. **Don't Break Encapsulation**: Keep handler within exchange domain

## Checklist for Implementation

- [ ] Create protocols.py with ExchangeOperations
- [ ] Write comprehensive unit tests for handler
- [ ] Implement handler with full docstrings
- [ ] Write integration tests for venue
- [ ] Integrate handler into venue
- [ ] Update matching thread
- [ ] Enable and fix all skipped tests
- [ ] Document the architecture
- [ ] Run full test suite
- [ ] Update CLAUDE.md if needed
