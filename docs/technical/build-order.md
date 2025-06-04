# Build Order Checklist

This document outlines the recommended build order for implementing the Intern Trading Game components.

## Initial Setup Phase (Partially Complete)

The following interfaces and models were defined to establish the project structure. Items marked complete have been implemented, while unchecked items will be defined as needed during component implementation.

### 1. Define Core Interfaces
- [x] **TickController** - Implemented as `GameLoop` class with `run_tick()` and phase event publishing
- [ ] **ExchangeEngine** - Methods: `process_orders()`, `execute_batch_matching()`
- [ ] **OrderValidator** - Methods: `validate_order()`, `check_constraints()`

### 2. Define Domain Service Interfaces
- [ ] **PriceModel** - Method: `generate_prices(tick) -> dict`
- [ ] **VolatilityStateMachine** - Methods: `get_current_regime()`, `process_event()`
- [ ] **EventSystem** - Methods: `generate_events()`, `publish_signals()`
- [ ] **RoleService** - Method: `validate_role_constraints()`
- [ ] **PositionService** - Methods: `update_position()`, `get_portfolio_stats()`
- [ ] **MarketDataService** - Method: `distribute_market_data()`

### 3. Define Data Models
- [x] Order, Trade (already exist in exchange module)
- [ ] Position
- [x] MarketState (implemented as `MarketData`)
- [x] SignalEvent (implemented as `Signal`)
- [x] NewsEvent, GameConfig, TickPhase using `@dataclass`

### 4. Bootstrap Tick Loop
- [x] Create `game_loop.py` with basic `run_tick()` function
- [x] Add print/log stubs for each tick phase

## Component Build Order

### Phase 1: Core Infrastructure
- [x] **Tick Controller** - Game timing and orchestration (implemented as GameLoop)
- [ ] **Price Model** - Underlying price generation (stub only)
- [ ] **Exchange Engine** - Enhance existing order matching
- [ ] **Position Service** - Basic position tracking

### Phase 2: Market Dynamics
- [ ] **Order Validator** - Order validation and role constraints
- [ ] **Volatility State Machine** - Regime management
- [ ] **Event System** - News and market events
- [ ] **Market Data Service** - Data distribution

### Phase 3: Game Features
- [ ] **Role Service** - Role-specific logic
- [ ] **Data Persistence** - Save game state
- [ ] **Bot API** - External interface

## Detailed Tasks

### Tick Controller (First Component)
- [x] Create basic tick loop with 5-minute intervals
- [x] Implement trading schedule enforcement (configurable in GameConfig)
- [x] Add tick event publishing mechanism (phase methods)
- [x] Implement order window timing (T+0:30 to T+3:00)
- [x] Add batch matching trigger at T+3:30

### Define Phase 1 Interfaces (Next Step)
- [ ] Define PriceModel interface in core/interfaces.py
- [ ] Define PositionService interface in core/interfaces.py
- [ ] Define Position data model in core/models.py
- [ ] Update GameLoop to use PriceModel interface type hints
- [ ] Document interface contracts and expected behavior

### Price Model (Second Component)
- [ ] Implement Geometric Brownian Motion for SPX underlying
- [ ] Add correlated SPY price generation (SPX/10 with tracking error)
- [ ] Create volatility parameter interface for regime integration
- [ ] Implement 3% daily tracking error with mean reversion
- [ ] Add price snapshots at T+0:00 for each tick
- [ ] Generate strike prices based on current SPX level
- [ ] Calculate theoretical option prices using Black-Scholes
- [ ] Add price validation and bounds checking

### Position Service (Third Component)
- [ ] Create position tracking data structure per participant
- [ ] Implement trade-to-position update logic
- [ ] Add real-time P&L calculation with mark-to-market
- [ ] Calculate portfolio Greeks aggregation
- [ ] Implement position limit monitoring and alerts
- [ ] Add trade history and audit trail
- [ ] Create position snapshot for game state saving
- [ ] Implement role-based margin calculations

### Exchange Enhancement (Fourth Component)
- [ ] Enhance ExchangeVenue with batch matching at T+3:30
- [ ] Add order validation hooks for OrderValidator integration
- [ ] Implement order amendment and cancellation
- [ ] Add trade execution callbacks for position updates
- [ ] Create order audit trail and history
- [ ] Implement market data snapshots after matching
- [ ] Add support for role-specific order handling

### Order Validator (Phase 2 Component)
- [ ] Implement role-based position limit checking
- [ ] Add order size validation per role constraints
- [ ] Validate trading window enforcement (T+0:30 to T+3:00)
- [ ] Check instrument availability and validity
- [ ] Implement fee calculation based on role type
- [ ] Add margin/capital requirement validation
- [ ] Create validation error response system
- [ ] Add order amendment and cancellation rules
