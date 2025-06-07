# Test Improvement Plan - Phases 1-3

## Overview

This document outlines the test improvement strategy for the Intern Trading Game, focusing on three phases that will significantly improve test coverage and code quality. The plan prioritizes functional business value over raw coverage metrics.

## Phase 1: Quick Wins (1-2 days)

### Objective
Add critical unit tests for core domain models and missing constraint tests to establish a solid testing foundation.

### Tasks

#### 1.1 OrderBook Unit Tests **COMPLETED**
- [x] Test price-time priority matching algorithm
- [x] Test market order matching (immediate execution)
- [x] Test limit order matching (price levels)
- [x] Test partial fill scenarios
- [x] Test order cancellation and cleanup
- [x] Test best bid/ask tracking
- [x] Test depth snapshot generation
- [x] Test edge cases (empty book, single order)
- [x] Test realistic trading scenarios (MM spread capture, momentum sweeps)
- [x] Test performance with 1000+ orders
- [x] Test algorithm fairness (FIFO time priority)

#### 1.2 Order Model Tests **IN PROGRESS**
- [x] Test validation rules (negative prices/quantities) - *Completed via OrderBook tests*
- [ ] No fractional quantities allowed
- [x] No prices in fractional pennies - *Added validation & tests*
- [x] Test order type determination from price - *Completed via OrderBook tests*
- [x] Test fill logic and remaining quantity tracking - *Completed via OrderBook tests*
- [x] Test state transitions (new -> partially filled -> filled) - *Completed via OrderBook tests*
- [x] Test property methods (is_buy, is_filled, is_limit) - *Completed via OrderBook tests*
- [x] Test string-to-enum conversions - *Completed via OrderBook tests*
- [x] Added filled_quantity property - *Enhancement completed*

#### 1.3 Trade Model Tests
- [ ] Test validation of prices and quantities
- [ ] Test aggressor side validation
- [ ] Test value calculation
- [ ] Test serialization (to_dict)

#### 1.4 Missing Constraint Tests in OrderValidator

- [ ] Test PortfolioLimitConstraint with various position scenarios
- [ ] Test OrderRateConstraint with rapid order submission
- [ ] Test OrderTypeConstraint for role-specific order types
- [ ] Test PriceRangeConstraint for limit order price bounds
- [ ] Test constraint creation from configuration

#### 1.5 Create Shared Test Fixtures Module

- [ ] Create tests/fixtures/__init__.py
- [ ] Create tests/fixtures/market_data.py with helpers:
  - [ ] create_test_order()
  - [ ] create_spx_option()
  - [ ] create_spy_option()
  - [ ] create_market_maker_order()
  - [ ] create_hedge_fund_order()
  - [ ] create_arbitrage_order()

### Success Criteria

- Core domain models have >90% test coverage
- All constraint types have comprehensive tests
- Shared fixtures reduce test boilerplate

## Phase 2: Refactoring (3-4 days)

### Objective

Refactor the API layer to extract business logic from threading code, making it testable and maintainable.

### Tasks

#### 2.1 Extract Validation Message Processing

- [ ] Create `process_validation_message()` function
- [ ] Extract business logic from `validator_thread()`
- [ ] Add unit tests for validation message processing
- [ ] Test various message types and validation scenarios

#### 2.2 Extract Matching Message Processing

- [ ] Create `process_matching_message()` function
- [ ] Extract business logic from `matching_thread()`
- [ ] Add unit tests for matching message processing
- [ ] Test order submission and cancellation flows

#### 2.3 Extract Trade Publishing Logic

- [ ] Create `process_trade_publication()` function
- [ ] Extract business logic from `trade_publisher_thread()`
- [ ] Add unit tests for trade publication
- [ ] Test trade formatting and distribution

#### 2.4 Extract WebSocket Message Handling
- [ ] Create message handler functions for each message type
- [ ] Extract business logic from `websocket_thread()`
- [ ] Add unit tests for message handlers
- [ ] Test subscription management and data filtering

#### 2.5 Refactor Auth Module

- [ ] Add unit tests for TeamRegistry methods
- [ ] Test get_team_by_api_key() with various scenarios
- [ ] Test get_team_by_id() with edge cases
- [ ] Mock FastAPI dependency for get_current_team()

### Success Criteria

- Business logic separated from threading/framework code
- Each extracted function has comprehensive unit tests
- api/main.py coverage increases to >60%
- api/auth.py coverage increases to >80%

## Phase 3: Integration Testing (2-3 days)

### Objective
Create a robust test harness for integration tests and re-enable the skipped tests with proper setup.

### Tasks

#### 3.1 Create Integration Test Harness

- [ ] Design test fixture for running threaded components
- [ ] Implement proper setup/teardown for threads
- [ ] Create context manager for test isolation
- [ ] Add utilities for queue testing

#### 3.2 Re-enable Skipped API Tests

- [ ] Remove pytest.skip from test_api.py
- [ ] Update tests to use new test harness
- [ ] Fix any race conditions or timing issues
- [ ] Ensure tests run reliably in CI

#### 3.3 Add End-to-End Trading Scenarios

- [ ] Test complete order lifecycle (submit -> validate -> match -> publish)
- [ ] Test multi-participant trading scenarios
- [ ] Test role-based constraints in practice
- [ ] Test error handling and recovery

#### 3.4 Add WebSocket Integration Tests

- [ ] Test real-time order updates
- [ ] Test market data streaming
- [ ] Test connection handling and reconnection
- [ ] Test subscription filtering

#### 3.5 Performance and Load Tests

- [ ] Test with 100+ concurrent orders
- [ ] Test queue processing under load
- [ ] Test WebSocket with multiple subscribers
- [ ] Identify and document performance boundaries

### Success Criteria

- All integration tests pass reliably
- No skipped tests in the test suite
- End-to-end scenarios cover major use cases
- Performance boundaries documented

## Implementation Notes

### Testing Best Practices

1. Follow Given-When-Then pattern with detailed business context
2. Use parameterized tests for multiple scenarios
3. Keep tests isolated and independent
4. Use realistic trading data in tests
5. Document complex test scenarios

### Code Quality Standards

1. All new code must pass pre-commit hooks
2. Maintain <79 character line length
3. Use type hints for all new functions
4. Follow existing code patterns and conventions

### Risk Mitigation

1. Run full test suite after each major change
2. Keep refactoring commits separate from test additions
3. Ensure backward compatibility during refactoring
4. Document any breaking changes

## Timeline

- **Phase 1**: Start immediately, complete in 1-2 days
- **Phase 2**: Begin after Phase 1, complete in 3-4 days
- **Phase 3**: Begin after Phase 2, complete in 2-3 days
- **Total Duration**: 6-9 days

## Success Metrics

1. **Coverage Improvements**:

   - Overall coverage: >80%
   - Core domain models: >90%
   - API layer: >60%

2. **Test Quality**:

   - No skipped tests
   - All tests follow Given-When-Then pattern
   - Comprehensive business scenario coverage

3. **Code Quality**:

   - Reduced coupling in API layer
   - Improved testability
   - Clear separation of concerns
