# Batch Auction Pricing Strategy Implementation Plan

## Executive Summary

This document outlines the implementation plan for fixing GitHub issue #17: "Critical Bug: Batch matching engine uses incorrect pricing for opening auctions". The current BatchMatchingEngine uses continuous crossing logic (trading at the passive/sell price) instead of proper auction pricing logic. This implementation introduces a Strategy Pattern to support multiple auction pricing algorithms, with an initial focus on Maximum Volume (MV) pricing with midpoint selection.

### The Problem

**Current Behavior**: Orders always trade at the sell order price

- Example: Buy 10@128.00 vs Sell 10@127.00 → trades at 127.00

**Expected Behavior**: Proper auction pricing

- Maximum volume price (maximizes total shares traded)
- Midpoint pricing as tiebreaker when multiple prices have same max volume
- Example: Buy 10@128.00 vs Sell 10@127.00 -> should trade at 127.50

### The Solution

Implement the Strategy Pattern with pluggable batch auction pricing strategies, starting with:

1. **EquilibriumPricingStrategy**: Current behavior for backward compatibility
2. **MaximumVolumePricingStrategy**: Based on arXiv:1304.3135v1 with midpoint modification

## Detailed Design

### Architecture Overview

```
Exchange Domain
├── book/
│   ├── matching_engine.py (existing - will be modified)
│   ├── order_book.py (existing - unchanged)
│   └── batch_auction_strategies.py (NEW)
│       ├── Protocol: BatchAuctionPricingStrategy
│       ├── Data: AuctionClearingResult
│       ├── Implementation: EquilibriumPricingStrategy
│       └── Implementation: MaximumVolumePricingStrategy
```

### Component Design

#### 1. Protocol Definition

```python
# exchange/book/batch_auction_strategies.py

from typing import Protocol, List, Tuple, Optional, Dict
from dataclasses import dataclass
from ..models.order import Order

@dataclass
class AuctionClearingResult:
    """
    Result of batch auction pricing calculation.

    Attributes
    ----------
    clearing_price : float
        The uniform price at which all trades will execute
    max_volume : int
        Maximum number of units that can trade at this price
    algorithm : str
        Name of the algorithm used (for transparency/debugging)
    price_range : Optional[Tuple[float, float]]
        When multiple prices maximize volume, shows the range
    """
    clearing_price: float
    max_volume: int
    algorithm: str
    price_range: Optional[Tuple[float, float]] = None

class BatchAuctionPricingStrategy(Protocol):
    """
    Protocol for batch auction pricing strategies.

    All strategies must determine a single uniform clearing price
    for batch auction execution.
    """

    def calculate_clearing_price(
        self,
        bids: List[Order],
        asks: List[Order]
    ) -> AuctionClearingResult:
        """
        Determine the uniform clearing price for a batch auction.

        Parameters
        ----------
        bids : List[Order]
            Buy orders sorted by price descending (highest first).
            Orders at the same price level are randomly ordered.
        asks : List[Order]
            Sell orders sorted by price ascending (lowest first).
            Orders at the same price level are randomly ordered.

        Returns
        -------
        AuctionClearingResult
            The clearing price and associated information.

        Notes
        -----
        The strategy determines the price, not the individual matches.
        The matching engine will handle the actual order execution
        at the determined clearing price.
        """
        ...
```

#### 2. Maximum Volume Pricing Strategy

```python
class MaximumVolumePricingStrategy:
    """
    Implements the MV algorithm from arXiv:1304.3135v1.

    This strategy maximizes the total trading volume by finding the
    price(s) where the sum of supply and demand is minimized. When
    multiple prices achieve the same maximum volume, it selects the
    midpoint.

    The algorithm conceptually:

    1. Builds cumulative supply and demand curves
    2. Finds price(s) where S(p) + D(p) is minimized
    3. If multiple prices minimize, selects midpoint
    4. Returns uniform clearing price

    Why Maximum Volume?
    -------------------

    - Maximizes liquidity provision
    - Increases market participation
    - Suitable for opening auctions where price discovery is key
    - Reduces the impact of strategic behavior

    Midpoint Modification
    --------------------

    The original paper doesn't specify which price to choose when
    multiple prices maximize volume. We choose the midpoint to:

    - Provide fairness between buyers and sellers
    - Reduce systematic bias
    - Align with common exchange practices
    """

    def calculate_clearing_price(
        self,
        bids: List[Order],
        asks: List[Order]
    ) -> AuctionClearingResult:
        """Calculate clearing price using MV algorithm."""
        if not bids or not asks:
            # No crossing possible
            return AuctionClearingResult(
                clearing_price=0.0,
                max_volume=0,
                algorithm="maximum_volume"
            )

        # Build supply and demand curves
        supply_curve = self._build_supply_curve(asks)
        demand_curve = self._build_demand_curve(bids)

        # Find prices that minimize S(p) + D(p)
        min_sum = float('inf')
        optimal_prices = []

        # Check all unique prices in the market
        all_prices = sorted(set(
            [order.price for order in bids + asks]
        ))

        for price in all_prices:
            supply_at_price = supply_curve.get(price, 0)
            demand_at_price = demand_curve.get(price, 0)
            total = supply_at_price + demand_at_price

            if total < min_sum:
                min_sum = total
                optimal_prices = [price]
            elif total == min_sum:
                optimal_prices.append(price)

        # Select clearing price
        if len(optimal_prices) == 1:
            clearing_price = optimal_prices[0]
            price_range = None
        else:
            # Multiple prices maximize volume - choose midpoint
            clearing_price = (optimal_prices[0] + optimal_prices[-1]) / 2
            price_range = (optimal_prices[0], optimal_prices[-1])

        # Calculate actual tradeable volume at clearing price
        max_volume = self._calculate_volume_at_price(
            bids, asks, clearing_price
        )

        return AuctionClearingResult(
            clearing_price=clearing_price,
            max_volume=max_volume,
            algorithm="maximum_volume",
            price_range=price_range
        )

    def _build_supply_curve(self, asks: List[Order]) -> Dict[float, int]:
        """
        Build cumulative supply curve.

        S(p) = total quantity offered to sell at price p or lower.
        """
        supply = {}
        cumulative = 0

        for ask in asks:  # Already sorted ascending
            cumulative += ask.quantity
            supply[ask.price] = cumulative

        return supply

    def _build_demand_curve(self, bids: List[Order]) -> Dict[float, int]:
        """
        Build cumulative demand curve.

        D(p) = total quantity demanded to buy at price p or higher.
        """
        demand = {}
        cumulative = 0

        # Process in reverse order (lowest to highest price)
        for bid in reversed(bids):  # bids sorted descending
            cumulative += bid.quantity
            demand[bid.price] = cumulative

        return demand

    def _calculate_volume_at_price(
        self,
        bids: List[Order],
        asks: List[Order],
        price: float
    ) -> int:
        """Calculate maximum tradeable volume at given price."""
        # Eligible orders
        eligible_buy_volume = sum(
            b.quantity for b in bids if b.price >= price
        )
        eligible_sell_volume = sum(
            a.quantity for a in asks if a.price <= price
        )

        return min(eligible_buy_volume, eligible_sell_volume)
```

#### 3. Equilibrium Pricing Strategy

```python
class EquilibriumPricingStrategy:
    """
    Traditional equilibrium pricing (current behavior).

    This strategy finds the price where supply meets demand,
    typically using the passive side price. This maintains
    backward compatibility with the current system.

    Why Keep This?
    --------------

    - Backward compatibility
    - Some markets prefer traditional equilibrium
    - Allows A/B testing between strategies
    - Simpler mental model for some traders
    """

    def calculate_clearing_price(
        self,
        bids: List[Order],
        asks: List[Order]
    ) -> AuctionClearingResult:
        """Calculate using traditional equilibrium approach."""
        if not bids or not asks:
            return AuctionClearingResult(
                clearing_price=0.0,
                max_volume=0,
                algorithm="equilibrium"
            )

        # Find crossing point
        buy_idx = sell_idx = 0

        while buy_idx < len(bids) and sell_idx < len(asks):
            buy_order = bids[buy_idx]
            sell_order = asks[sell_idx]

            if buy_order.price >= sell_order.price:
                # Orders cross - use sell price (passive side)
                clearing_price = sell_order.price
                max_volume = self._calculate_volume_at_price(
                    bids, asks, clearing_price
                )

                return AuctionClearingResult(
                    clearing_price=clearing_price,
                    max_volume=max_volume,
                    algorithm="equilibrium"
                )

            # Move to next order
            if buy_order.price > sell_order.price:
                sell_idx += 1
            else:
                buy_idx += 1

        # No crossing
        return AuctionClearingResult(
            clearing_price=0.0,
            max_volume=0,
            algorithm="equilibrium"
        )
```

### Integration with BatchMatchingEngine

#### Modified BatchMatchingEngine

```python
# In exchange/book/matching_engine.py

class BatchMatchingEngine(MatchingEngine):
    def __init__(
        self,
        pricing_strategy: Optional[BatchAuctionPricingStrategy] = None
    ):
        """
        Initialize batch matching engine with pricing strategy.

        Parameters
        ----------
        pricing_strategy : BatchAuctionPricingStrategy, optional
            Strategy for determining clearing price.
            Defaults to EquilibriumPricingStrategy for backward compatibility.
        """
        self.pricing_strategy = pricing_strategy or EquilibriumPricingStrategy()
        self.pending_orders: Dict[str, List[Order]] = {}

    def execute_batch(
        self,
        order_books: Dict[str, OrderBook]
    ) -> Dict[str, Dict[str, OrderResult]]:
        """Execute batch with auction pricing."""
        ctx = BatchContext(
            pending_orders=self.pending_orders.copy(),
            order_books=order_books,
            engine=self,
            pricing_strategy=self.pricing_strategy  # Pass strategy
        )

        ctx.match_batch_orders()
        ctx.finalize_results()

        self.pending_orders.clear()
        return dict(ctx.results)
```

#### Modified BatchContext

```python
@dataclass
class BatchContext:
    """Context for batch matching with pricing strategy."""
    pending_orders: Dict[str, List[Order]]
    order_books: Dict[str, OrderBook]
    engine: "BatchMatchingEngine"
    pricing_strategy: BatchAuctionPricingStrategy  # NEW
    results: Dict[str, Dict[str, OrderResult]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    def match_batch_orders(self) -> None:
        """Match orders using auction pricing strategy."""
        for instrument_id, orders in self.pending_orders.items():
            if instrument_id not in self.order_books:
                continue

            # Separate and randomize within price levels
            buy_orders = self.engine._randomize_same_price_orders(
                [o for o in orders if o.side == "buy"],
                descending=True
            )
            sell_orders = self.engine._randomize_same_price_orders(
                [o for o in orders if o.side == "sell"],
                descending=False
            )

            # Use strategy to determine clearing price
            result = self.pricing_strategy.calculate_clearing_price(
                buy_orders, sell_orders
            )

            if result.max_volume > 0:
                # Execute matches at uniform clearing price
                self._execute_auction_matches(
                    instrument_id,
                    buy_orders,
                    sell_orders,
                    result.clearing_price,
                    result.max_volume
                )

            # Add remaining unmatched orders to book
            self._add_remaining_orders_to_book(
                instrument_id, buy_orders, sell_orders
            )

    def _execute_auction_matches(
        self,
        instrument_id: str,
        buy_orders: List[Order],
        sell_orders: List[Order],
        clearing_price: float,
        max_volume: int
    ) -> None:
        """
        Execute matches at the uniform clearing price.

        Key aspects:
        1. All trades execute at the same clearing price
        2. Orders at the marginal price are already randomized
        3. Partial fills are handled appropriately
        """
        # Find eligible orders
        eligible_buys = [b for b in buy_orders if b.price >= clearing_price]
        eligible_sells = [s for s in sell_orders if s.price <= clearing_price]

        # Match up to max_volume
        buy_idx = sell_idx = 0
        volume_matched = 0

        while (buy_idx < len(eligible_buys) and
               sell_idx < len(eligible_sells) and
               volume_matched < max_volume):

            buy_order = eligible_buys[buy_idx]
            sell_order = eligible_sells[sell_idx]

            # Calculate match quantity
            match_qty = min(
                buy_order.remaining_quantity,
                sell_order.remaining_quantity,
                max_volume - volume_matched
            )

            # Create trade at UNIFORM CLEARING PRICE
            trade = Trade(
                instrument_id=buy_order.instrument_id,
                buyer_order_id=buy_order.order_id,
                seller_order_id=sell_order.order_id,
                buyer_id=buy_order.trader_id,
                seller_id=sell_order.trader_id,
                price=clearing_price,  # NOT sell_order.price!
                quantity=match_qty,
                aggressor_side="auction"  # Neither side aggressed
            )

            self._record_trade(trade, buy_order, sell_order)
            volume_matched += match_qty

            # Advance indices
            if buy_order.is_filled:
                buy_idx += 1
            if sell_order.is_filled:
                sell_idx += 1
```

### Factory Pattern Support

```python
# In infrastructure/factories/exchange_factory.py

def create_exchange_venue(
    config: Dict[str, Any],
    phase_manager: Optional[PhaseManager] = None
) -> ExchangeVenue:
    """Create exchange with configuration."""
    # Extract matching configuration
    matching_config = config.get("matching", {})
    mode = matching_config.get("mode", "continuous")

    if mode == "continuous":
        matching_engine = ContinuousMatchingEngine()
    else:  # batch
        # Determine pricing strategy
        strategy_name = matching_config.get("batch_pricing_strategy", "equilibrium")

        if strategy_name == "maximum_volume":
            strategy = MaximumVolumePricingStrategy()
        else:
            strategy = EquilibriumPricingStrategy()

        matching_engine = BatchMatchingEngine(pricing_strategy=strategy)

    return ExchangeVenue(
        matching_engine=matching_engine,
        phase_manager=phase_manager
    )
```

## Implementation Phases

### Phase 1: Design & Planning (Commit 1)
**Goal**: Document the design and prepare the codebase

**Tasks**:

1. ✅ Create this implementation plan document
2. Update architecture-v4.md to show new components
3. Create empty module structure:
   - `exchange/book/batch_auction_strategies.py`
   - Add imports to `__init__.py` files

**Commit Message**:
```
docs: add batch auction pricing strategy design and implementation plan

- Document solution for GitHub issue #17
- Design Strategy Pattern for auction pricing
- Plan implementation phases
- Update architecture to show new components
```

### Phase 2: Unit Tests (Commit 2)
**Goal**: Write comprehensive unit tests that fail

**Test Categories**:

1. **Protocol Tests** (`test_batch_auction_protocol.py`)
   - Test protocol compliance
   - Test data structures

2. **Maximum Volume Strategy Tests** (`test_maximum_volume_strategy.py`)
   - Basic cases (single crossing price)
   - Multiple prices with same volume → midpoint
   - No overlap cases
   - Edge cases (empty books, single order)
   - Large order books performance

3. **Equilibrium Strategy Tests** (`test_equilibrium_strategy.py`)
   - Current behavior preservation
   - Comparison with existing implementation

4. **Integration Tests** (`test_batch_matching_integration.py`)
   - Strategy injection
   - End-to-end batch execution
   - Partial fills
   - Order book state after auction

**Example Test**:
```python
def test_maximum_volume_midpoint_selection():
    """Test midpoint selection when multiple prices maximize volume."""
    strategy = MaximumVolumePricingStrategy()

    # Orders that create multiple optimal prices
    bids = [
        create_order(side="buy", price=102, quantity=10),
        create_order(side="buy", price=101, quantity=10),
        create_order(side="buy", price=100, quantity=10),
    ]
    asks = [
        create_order(side="sell", price=98, quantity=10),
        create_order(side="sell", price=99, quantity=10),
        create_order(side="sell", price=100, quantity=10),
    ]

    result = strategy.calculate_clearing_price(bids, asks)

    # Prices 99, 100, 101 all allow 20 volume
    # Should choose midpoint: (99 + 101) / 2 = 100
    assert result.clearing_price == 100.0
    assert result.max_volume == 20
    assert result.price_range == (99.0, 101.0)
```

**Commit Message**:
```
test: add failing tests for batch auction pricing strategies

- Test MaximumVolumePricingStrategy algorithm
- Test EquilibriumPricingStrategy for backward compatibility
- Test strategy integration with BatchMatchingEngine
- Test edge cases and performance

Part of fix for #17
```

### Phase 3: Implementation (Still Commit 2)

**Goal**: Implement strategies and make tests pass

**Tasks**:
1. Implement `batch_auction_strategies.py`
2. Update `BatchMatchingEngine` to use strategies
3. Update `BatchContext` for uniform pricing
4. Ensure all unit tests pass

**Commit Message**:
```
feat: implement batch auction pricing strategies

- Add BatchAuctionPricingStrategy protocol
- Implement MaximumVolumePricingStrategy with midpoint selection
- Implement EquilibriumPricingStrategy for compatibility
- Update BatchMatchingEngine to use strategies
- All trades now execute at uniform clearing price

Fixes #17
```

### Phase 4: Integration Tests (Commit 3)
**Goal**: Test full system integration

**Test Files**:
1. `test_venue_auction_pricing.py`
   - Test with ExchangeVenue
   - Test with phase transitions
   - Verify trades at correct prices

2. `test_exchange_factory_strategies.py`
   - Test factory creation
   - Test configuration parsing

**Commit Message**:
```
test: add integration tests for auction pricing strategies

- Test strategies with ExchangeVenue
- Test phase transition integration
- Test factory pattern support
- Verify backward compatibility
```

### Phase 5: Integration (Still Commit 3)
**Goal**: Integrate with system components

**Tasks**:
1. Update `exchange_factory.py`
2. Add configuration support
3. Update phase transition handler if needed
4. Ensure all integration tests pass

**Commit Message**:
```
feat: integrate batch auction pricing strategies

- Add factory support for strategy selection
- Add configuration for batch_pricing_strategy
- Maintain backward compatibility with default
- Support strategy selection via config
```

### Phase 6: Documentation (Commit 4)
**Goal**: Complete documentation

**Tasks**:
1. Update `batch-matching.md` with pricing details
2. Add strategy examples to configuration docs
3. Update API documentation
4. Create migration guide

**Commit Message**:
```
docs: document batch auction pricing strategies

- Explain maximum volume algorithm
- Document configuration options
- Add examples and use cases
- Create migration guide from old behavior
```

## Testing Strategy

### Unit Test Coverage
- Each strategy method tested independently
- Edge cases: empty books, single order, no overlap
- Performance tests with large order books
- Randomization verification

### Integration Test Coverage
- Full auction cycle with each strategy
- Partial fill handling
- Order book state verification
- Configuration and factory tests

### Backward Compatibility Tests
- Default behavior unchanged
- Existing tests still pass
- Can switch strategies without code changes

## Configuration

### YAML Configuration
```yaml
exchange:
  matching:
    mode: "batch"
    batch_pricing_strategy: "maximum_volume"  # or "equilibrium"
```

### Programmatic Configuration
```python
# Maximum volume pricing
engine = BatchMatchingEngine(
    pricing_strategy=MaximumVolumePricingStrategy()
)

# Traditional equilibrium
engine = BatchMatchingEngine(
    pricing_strategy=EquilibriumPricingStrategy()
)

# Default (backward compatible)
engine = BatchMatchingEngine()  # Uses EquilibriumPricingStrategy
```

## Future Extensions

### Additional Strategies
1. **TimeWeightedAuctionStrategy**: Weight by order arrival time
2. **SizeWeightedAuctionStrategy**: Weight by order size
3. **ReferencePrice Strategy**: Use external reference price
4. **CollarStrategy**: Constrain price within bounds

### Pro-Rata Allocation
Add pro-rata allocation as an option:
```python
class ProRataMaximumVolumeStrategy(MaximumVolumePricingStrategy):
    """MV with pro-rata allocation at marginal price."""
```

### Analytics and Monitoring
```python
@dataclass
class AuctionClearingResult:
    # ... existing fields ...

    # Analytics extensions
    price_improvement: Optional[float] = None
    market_impact: Optional[float] = None
    allocation_fairness: Optional[float] = None
```

## Design Rationale

### Why Strategy Pattern?

1. **Open/Closed Principle**: Add new algorithms without modifying engine
2. **Single Responsibility**: Each strategy focuses on one algorithm
3. **Testability**: Test strategies in isolation
4. **Flexibility**: Runtime algorithm selection
5. **Future-Proof**: Easy to add new strategies

### Why Uniform Pricing?

1. **Fairness**: All traders get same price
2. **No Gaming**: Can't manipulate by order timing
3. **Standard Practice**: How real exchanges work
4. **Simplicity**: Easier to understand and audit

### Why Random at Marginal Price?

1. **True Fairness**: No size or time advantages
2. **Game Context**: Equal opportunity important
3. **Simplicity**: Easier than pro-rata
4. **Flexibility**: Can add pro-rata later

### Why Midpoint for Ties?

1. **Fairness**: Balanced between buyers/sellers
2. **Reduces Bias**: No systematic advantage
3. **Market Practice**: Common in real exchanges
4. **Clear Rule**: Easy to verify and audit

## Success Criteria

1. **Bug Fixed**: Opening auctions use proper pricing
2. **Tests Pass**: All existing tests still work
3. **Configurable**: Can switch strategies easily
4. **Performant**: No significant slowdown
5. **Documented**: Clear explanation for users
6. **Extensible**: Easy to add new strategies

## Risk Mitigation

1. **Backward Compatibility**: Default to current behavior
2. **Thorough Testing**: Unit and integration tests
3. **Feature Flag**: Can disable via configuration
4. **Monitoring**: Log which strategy is used
5. **Gradual Rollout**: Test in dev before prod

## References

1. Niu, J., & Parsons, S. (2013). Maximizing Matching in Double-sided Auctions. arXiv:1304.3135v1
2. GitHub Issue #17: Critical Bug: Batch matching engine uses incorrect pricing
3. Current implementation: `src/intern_trading_game/domain/exchange/book/matching_engine.py`
