# Build Order Checklist

This document outlines the recommended build order for implementing the Intern Trading Game components.

## Immediate Next Steps: Define Interfaces and Stubs

### 1. Define Core Interfaces
- [ ] **TickController** - Methods: `advance_tick()`, `publish_event()`
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
- [ ] Order, Trade, Position, MarketState, SignalEvent using `@dataclass`

### 4. Bootstrap Tick Loop
- [ ] Create `game_loop.py` with basic `run_tick()` function
- [ ] Add print/log stubs for each tick phase

## Component Build Order

### Phase 1: Core Infrastructure
- [ ] **Tick Controller** - Game timing and orchestration
- [ ] **Price Model** - Underlying price generation
- [ ] **Exchange Engine** - Enhance existing order matching
- [ ] **Position Service** - Basic position tracking

### Phase 2: Market Dynamics
- [ ] **Volatility State Machine** - Regime management
- [ ] **Event System** - News and market events
- [ ] **Market Data Service** - Data distribution
- [ ] **Order Validator** - Order validation logic

### Phase 3: Game Features
- [ ] **Role Service** - Role-specific logic
- [ ] **Data Persistence** - Save game state
- [ ] **Bot API** - External interface

## Detailed Tasks

### Tick Controller (First Component)
- [ ] Create basic tick loop with 5-minute intervals
- [ ] Implement trading schedule enforcement (Tue/Thu, 9:30-3:00 CT)
- [ ] Add tick event publishing mechanism
- [ ] Implement order window timing (T+0:30 to T+3:00)
- [ ] Add batch matching trigger at T+3:30

### Price Model (Second Component)
- [ ] Implement Geometric Brownian Motion for SPX
- [ ] Add correlated SPY price generation (SPX/10 with noise)
- [ ] Create volatility parameter interface
- [ ] Implement tracking error generation
- [ ] Add price publication at T+0:00
