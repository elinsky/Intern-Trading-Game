# Test Fixture Refactoring Plan

## Overview

This document outlines a comprehensive plan to refactor the test suite to maximize usage of the centralized test fixtures. The goal is to reduce code duplication, improve consistency, and make tests more maintainable.

## Current Fixture Architecture

### 1. Centralized Test Data (`/tests/fixtures/market_data.py`)
- **Factory Functions**: `create_test_order()`, `create_spx_option()`, `create_spy_option()`, `create_test_trade()`, etc.
- **Test Constants**: `TEST_PRICES`, `TEST_QUANTITIES`, `TEST_SPREADS`
- **Scenario Builders**: `create_order_book_scenario()`, `create_matched_orders()`, `create_ladder_orders()`

### 2. Integration Fixtures (`/tests/integration/conftest.py`)
- **Service-level**: `service_context`, `test_team`, `exchange`, `validator`
- **API-level**: `api_context`, `client`, `registered_team`
- **System-level**: `system_context` (full end-to-end)

## High-Priority Refactoring Tasks

### 1. Remove Duplicate Code in Unit Tests

#### test_matching_engine.py
```python
# TODO: Remove duplicate create_test_order function (lines 54-74)
# Import from tests.fixtures instead
from tests.fixtures import create_test_order, create_matched_orders
```

#### test_trade.py
```python
# Replace manual Trade creation (lines 98-107, 204, 215)
# Before:
trade = Trade(
    instrument_id="SPX_4500_CALL",
    buyer_id="HF_002",
    seller_id="MM_001",
    price=128.50,
    quantity=10,
    buyer_order_id="BUY_789",
    seller_order_id="SELL_456",
    aggressor_side="buy",
)

# After:
from tests.fixtures import create_test_trade
trade = create_test_trade(
    price=128.50,
    quantity=10,
    buyer_id="HF_002",
    seller_id="MM_001",
    aggressor_side="buy"
)
```

### 2. Standardize Instrument Creation

#### test_exchange.py
```python
# Replace manual Instrument creation (lines 18-24, 66-72)
# Before:
test_instrument = Instrument(
    symbol="TEST_INSTRUMENT",
    strike=100.0,
    expiry="2024-12-31",
    option_type="call",
    underlying="TEST",
)

# After:
from tests.fixtures import create_spx_option
test_instrument = create_spx_option(strike=100.0, expiry_days=30)
```

### 3. Use Order Book Scenarios

#### test_order_book.py
```python
# Replace custom book_with_liquidity fixture
# Before:
@pytest.fixture
def book_with_liquidity():
    book = OrderBook()
    # 20+ lines of manual order creation
    return book

# After:
from tests.fixtures import create_order_book_scenario

@pytest.fixture
def book_with_liquidity():
    return create_order_book_scenario("balanced")
```

### 4. Leverage Matched Orders

#### test_matching_engine.py
```python
# For crossing order tests
# Before:
buy_order = create_test_order(side="buy", price=100.0, trader_id="trader1")
sell_order = create_test_order(side="sell", price=100.0, trader_id="trader1")

# After:
from tests.fixtures import create_matched_orders
buy_order, sell_order = create_matched_orders(price=100.0, buyer_id="trader1", seller_id="trader1")
```

## Integration Test Refactoring

### 1. Use test_team Fixture

#### test_fee_calculation_integration.py & test_order_lifecycle.py
```python
# Replace all manual TeamInfo creation
# Before (appears 10+ times across files):
team = TeamInfo(
    team_id="MM_TEST_001",
    team_name="Test Market Maker",
    role="market_maker",
    api_key="test_key_123",
    created_at=datetime.now(),
)

# After:
def test_something(service_context, test_team):
    team = test_team  # Already configured as market_maker
```

### 2. Create Multi-Team Fixture

For tests requiring multiple teams, add to `/tests/integration/conftest.py`:

```python
@pytest.fixture
def multi_team_setup(service_context):
    """Create multiple test teams for complex scenarios."""
    teams = {
        "market_maker": TeamInfo(
            team_id="MM_001",
            team_name="Market Maker 1",
            role="market_maker",
            api_key="mm_key_001",
            created_at=datetime.now(),
        ),
        "hedge_fund": TeamInfo(
            team_id="HF_001",
            team_name="Hedge Fund 1",
            role="hedge_fund",
            api_key="hf_key_001",
            created_at=datetime.now(),
        ),
        "retail": TeamInfo(
            team_id="RT_001",
            team_name="Retail Trader 1",
            role="retail",
            api_key="rt_key_001",
            created_at=datetime.now(),
        ),
    }
    
    # Register all teams and initialize positions
    for team in teams.values():
        team_registry.teams[team.team_id] = team
        team_registry.api_key_to_team[team.api_key] = team.team_id
        service_context["positions"][team.team_id] = {}
    
    yield teams
    
    # Cleanup
    for team in teams.values():
        del team_registry.teams[team.team_id]
        del team_registry.api_key_to_team[team.api_key]
```

## Implementation Order

### Phase 1: High-Priority Unit Tests (Week 1)
1. ✅ Remove duplicate create_test_order from test_matching_engine.py
2. ✅ Refactor test_trade.py to use create_test_trade()
3. ✅ Update test_exchange.py to use create_spx_option() and create_test_order()
4. ✅ Replace test_order_book.py fixtures with create_order_book_scenario()

### Phase 2: Integration Tests (Week 2)
5. ✅ Replace manual TeamInfo creation with test_team fixture
6. ✅ Create and use multi_team_setup fixture
7. ✅ Update service integration tests to use service_context

### Phase 3: Remaining Tests (Week 3)
8. ✅ Use create_matched_orders() in matching engine tests
9. ✅ Refactor test_order_validation_service.py
10. ✅ Standardize test constants using TEST_PRICES

### Phase 4: New Fixtures (Week 4)
11. ✅ Create fixture for common role configurations
12. ✅ Create parameterized fixtures for complex scenarios

## Additional Fixture Opportunities

### 1. Common Validation Constraints
```python
@pytest.fixture
def role_constraints():
    """Common constraint configurations by role."""
    return {
        "market_maker": [
            ConstraintConfig(
                constraint_type=ConstraintType.POSITION_LIMIT,
                parameters={"max_position": 50, "symmetric": True},
                error_code="MM_POS_LIMIT",
            ),
            ConstraintConfig(
                constraint_type=ConstraintType.QUOTE_REQUIREMENT,
                parameters={"min_quote_ratio": 0.8},
                error_code="MM_QUOTE_REQ",
            ),
        ],
        "hedge_fund": [
            ConstraintConfig(
                constraint_type=ConstraintType.DELTA_NEUTRAL,
                parameters={"max_delta": 50},
                error_code="HF_DELTA_LIMIT",
            ),
        ],
    }
```

### 2. Standard Test Scenarios
```python
@pytest.fixture
def volatility_scenarios():
    """Standard volatility regime test scenarios."""
    return {
        "calm_market": {"vol": 0.10, "regime": "low"},
        "normal_market": {"vol": 0.20, "regime": "medium"},
        "stressed_market": {"vol": 0.50, "regime": "high"},
    }
```

### 3. Order Flow Patterns
```python
@pytest.fixture
def order_flow_patterns():
    """Common order flow patterns for testing."""
    return {
        "aggressive_buying": lambda: create_ladder_orders(
            base_price=100.0, levels=5, step=0.50, side="buy"
        ),
        "market_making": lambda: create_test_spread(
            spread_width=1.0, mid_price=100.0, quantity=10
        ),
        "liquidation": lambda: create_ladder_orders(
            base_price=95.0, levels=10, step=-0.25, side="sell"
        ),
    }
```

## Benefits of This Refactoring

1. **Code Reduction**: Estimated 30-40% reduction in test code
2. **Consistency**: All tests use same data patterns
3. **Maintainability**: Single source of truth for test data
4. **Readability**: Tests focus on behavior, not setup
5. **Performance**: Fixture caching speeds up test suite
6. **Documentation**: Factory functions serve as examples

## Testing the Refactoring

After each refactoring phase:
1. Run full test suite: `pytest`
2. Check coverage: `pytest --cov=intern_trading_game`
3. Verify no tests broken: `pre-commit run --all-files`
4. Review test output for clarity

## Conclusion

This refactoring will significantly improve the test suite's maintainability and consistency. The centralized fixtures provide a robust foundation for testing while reducing duplication and improving developer experience.