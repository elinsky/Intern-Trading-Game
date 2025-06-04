# Build Order Checklist

This document outlines the recommended build order for implementing the Intern Trading Game components.

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
