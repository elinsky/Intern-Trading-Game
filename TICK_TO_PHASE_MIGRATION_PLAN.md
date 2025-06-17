# Tick to Phase Migration Plan

## Executive Summary

This document outlines the comprehensive plan to migrate the Intern Trading Game from a tick-based trading system to a continuous phase-based system. The migration will be completed in two major commits:

1. **Commit 1**: Remove all tick-based code
2. **Commit 2**: Implement new phase-based system

## Current State Analysis

### Tick-Based System (To Be Removed)
- **TickPhase Enum**: 6 phases per 5-minute tick (MARKET_DATA, PRE_OPEN, OPEN, TRADING, CLOSING, CLOSED)
- **Tick Timing**: Each tick is 300 seconds with phase offsets
- **Batch Processing**: Orders collected during windows, matched at specific times
- **WebSocket Messages**: `tick_start` and `tick_phase` events
- **Configuration**: `tick_duration_seconds`, `total_ticks`, etc.

### Phase-Based System (To Be Implemented)
- **PhaseType Enum**: 3 simple phases (PRE_OPEN, CONTINUOUS, CLOSED)
- **Time-Based**: Direct time evaluation, no tick counting
- **Continuous Processing**: Real-time order matching during CONTINUOUS phase
- **WebSocket Messages**: Phase state changes only
- **Configuration**: Schedule-based phase definitions

## Migration Plan

### Phase 1: Remove Tick-Based Code ✅

#### 1.1 Domain Model Changes

**File: `/src/intern_trading_game/domain/models/core.py`**

- [x] Delete entire `TickPhase` class (lines 16-75)
- [x] Update `MarketData` class:
  - [x] Remove `tick: int` field
  - [x] Update docstring to remove tick references
  - [x] Update examples to remove tick usage
- [x] Update `NewsEvent` class:
  - [x] Change `tick_announced: int` to `timestamp_announced: datetime`
  - [x] Update docstring and examples
- [x] Update `GameConfig` class:
  - [x] Remove `tick_duration_seconds: int = 300`
  - [x] Remove `total_ticks: int = 390`
  - [x] Remove `ticks_per_hour` property
  - [x] Remove `ticks_per_day` property
  - [x] Update docstring to remove tick references
- [x] Update `__all__` export list (remove `TickPhase`)

#### 1.2 WebSocket Infrastructure

**File: `/src/intern_trading_game/infrastructure/api/websocket_messages.py`**

- [x] Remove from `MessageType` enum:
  - [x] `TICK_START = "tick_start"`
  - [x] `TICK_PHASE = "tick_phase"`
- [x] Delete functions:
  - [x] `build_tick_start()` (lines ~557-593)
  - [x] `build_tick_phase()` (lines ~596-622)

**File: `/src/intern_trading_game/infrastructure/api/websocket.py`**

- [x] Remove any tick-related message handling
- [x] Remove tick phase broadcasting logic

#### 1.3 Import Updates

**File: `/src/intern_trading_game/domain/models/__init__.py`**

- [x] Remove `TickPhase` from imports
- [x] Update `__all__` if present

**File: `/src/intern_trading_game/domain/models.py`**

- [x] Remove any tick-related re-exports
- [x] Update imports

#### 1.4 Interface Updates

**File: `/src/intern_trading_game/domain/interfaces.py`**

- [x] Remove `TickPhase` imports
- [x] Update any interfaces that reference tick phases
- [x] Update method signatures that use tick parameters

#### 1.5 Validation Service Updates

**File: `/src/intern_trading_game/domain/validation/order_validator.py`**

- [x] Remove `TickPhase` import
- [x] Remove any tick phase validation logic
- [x] Update validation context if it includes tick data

**File: `/src/intern_trading_game/services/order_validation.py`**

- [x] Remove `TickPhase` import
- [x] Update any methods that check tick phases
- [x] Remove tick-based order window validation

#### 1.6 Test Updates

**File: `/tests/unit/domain/test_models.py`**

- [x] Remove all `TickPhase` tests
- [x] Update `MarketData` tests to remove tick field
- [x] Update `GameConfig` tests to remove tick properties

**File: `/tests/unit/domain/validation/test_order_validator.py`**

- [x] Remove tick phase validation tests
- [x] Update test fixtures that use tick phases

**File: `/tests/unit/services/test_order_validation_service.py`**

- [x] Remove tick phase related tests
- [x] Update mock data to remove tick references

**File: `/tests/unit/infrastructure/api/test_websocket.py`**

- [x] Remove `tick_start` message tests
- [x] Remove `tick_phase` message tests
- [x] Remove `tick_number` references

#### 1.7 Documentation Updates

**File: `/docs/technical/reference/websocket-api.md`**

- [x] Remove `tick_start` section (lines ~157-173)
- [x] Remove `tick_phase` section (lines ~175-189)
- [x] Update overview to mention continuous trading
- [x] Remove all references to "5-minute ticks"
- [x] Update examples to remove tick usage

**File: `/docs/technical/explanation/trading-phases.md`**

- [x] Update to focus on new phase system
- [x] Remove batch mode references
- [x] Add continuous trading explanation

**File: `/docs/game/configuration/example-config.yaml`**

- [x] Remove `tick_duration_minutes: 5`
- [x] Remove `order_window_minutes: 3`
- [x] Add placeholder for phase schedule config

### Phase 2: Implement Phase-Based System

#### 2.1 Core Phase Models

**File: `/src/intern_trading_game/domain/models/core.py`**

- [ ] Add `PhaseType` enum:
  ```python
  class PhaseType(str, Enum):
      PRE_OPEN = "pre_open"
      CONTINUOUS = "continuous"
      CLOSED = "closed"
  ```

- [ ] Add `PhaseState` dataclass:
  ```python
  @dataclass
  class PhaseState:
      phase_type: PhaseType
      is_order_submission_allowed: bool
      is_order_cancellation_allowed: bool
      is_matching_enabled: bool
      execution_style: str
  ```

- [ ] Add `from_phase_type` class method to `PhaseState`
- [ ] Update `MarketData` to include `phase_state: PhaseState`
- [ ] Update `__all__` exports

#### 2.2 Phase Evaluation Logic

**File: `/src/intern_trading_game/domain/services/phase_manager.py` (new file)**

- [ ] Create `PhaseManager` class
- [ ] Add `get_active_phase()` method with hardcoded schedule:
  ```python
  def get_active_phase(self, current_time: datetime) -> PhaseType:
      """Determine active phase based on current time."""
      # Hardcoded for MVP:
      # - PRE_OPEN: 8:00-9:30 CT weekdays
      # - CONTINUOUS: 9:30-16:00 CT weekdays
      # - CLOSED: All other times
  ```
- [ ] Add `get_phase_state()` method
- [ ] Add phase transition detection logic

#### 2.3 WebSocket Updates

**File: `/src/intern_trading_game/infrastructure/api/websocket_messages.py`**

- [ ] Add to `MessageType` enum:
  - [ ] `PHASE_CHANGE = "phase_change"`
- [ ] Add `build_phase_change()` function:
  ```python
  def build_phase_change(
      phase_state: PhaseState,
      timestamp: Optional[datetime] = None,
  ) -> dict
  ```

#### 2.4 Order Validation Updates

**File: `/src/intern_trading_game/services/order_validation.py`**

- [ ] Add phase state to validation context
- [ ] Implement phase-based validation:
  - [ ] PRE_OPEN: Allow orders, no matching
  - [ ] CONTINUOUS: Allow orders, enable matching
  - [ ] CLOSED: Reject all orders

#### 2.5 Exchange Integration

**File: `/src/intern_trading_game/exchange/venue.py`**

- [ ] Add phase state awareness to exchange
- [ ] Disable matching when `is_matching_enabled=False`
- [ ] Add phase state to exchange state

#### 2.6 Test Implementation

**File: `/tests/unit/domain/test_phase_models.py` (new file)**

- [ ] Test `PhaseType` enum
- [ ] Test `PhaseState` creation
- [ ] Test `from_phase_type` method

**File: `/tests/unit/domain/services/test_phase_manager.py` (new file)**

- [ ] Test phase evaluation logic
- [ ] Test weekend handling
- [ ] Test phase transitions
- [ ] Test edge cases (midnight, exact transition times)

#### 2.7 Documentation

**File: `/docs/technical/reference/websocket-api.md`**

- [ ] Add `phase_change` message documentation
- [ ] Update examples with phase-based approach

**File: `/docs/technical/explanation/trading-phases.md`**

- [ ] Document new phase system
- [ ] Explain phase rules and transitions
- [ ] Add configuration examples (future state)

## Implementation Details

### Phase State Rules

| Phase | Order Submission | Order Cancellation | Matching | Execution Style |
|-------|-----------------|-------------------|----------|-----------------|
| PRE_OPEN | ✅ | ✅ | ❌ | none |
| CONTINUOUS | ✅ | ✅ | ✅ | continuous |
| CLOSED | ❌ | ❌ | ❌ | none |

### Hardcoded Schedule (MVP)

```python
# Monday-Friday (CT timezone)
08:00-09:30: PRE_OPEN
09:30-16:00: CONTINUOUS
16:00-08:00: CLOSED

# Saturday-Sunday
00:00-24:00: CLOSED
```

### Future Configuration Format

```yaml
market_phases:
  - name: pre_open
    type: pre_open
    start_time: "08:00"
    end_time: "09:30"
    days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

  - name: rth_continuous
    type: continuous
    start_time: "09:30"
    end_time: "16:00"
    days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

  - name: closed
    type: closed
    start_time: "16:00"
    end_time: "08:00"
    days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
```

## Risk Analysis

### Potential Issues

1. **Import Errors**: Many files import `TickPhase` - must update all
2. **Test Failures**: Tests expecting tick behavior will fail
3. **Validation Logic**: Order validation currently may depend on tick phases
4. **Missing Implementation**: No tick controller exists, so removal might be easier

### Mitigation Strategies

1. Use grep to find all tick-related imports before starting
2. Run tests after each major change
3. Create new validation logic before removing old
4. Document any temporary hardcoding for future enhancement

## Success Criteria

- [ ] All tick-related code removed
- [ ] No references to `TickPhase`, `tick_number`, or tick timing
- [ ] New phase system implemented and tested
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Exchange honors phase rules for order handling and matching

## Notes

- No backwards compatibility needed (no users yet)
- Hardcoding phase schedule is acceptable for MVP
- Config-driven scheduling is a future enhancement
- Focus on simplicity and correctness over flexibility initially
