# Build Order Checklist - v2 API Architecture

## Phase 1: Core Foundation ✅ COMPLETE

### Exchange Infrastructure
- [x] **Order** - Basic order data model
- [x] **Trade** - Trade execution record
- [x] **OrderBook** - Bid/ask order storage
- [x] **OrderResult** - Enhanced with error_code, error_message fields
- [x] **ExchangeVenue** - Core exchange with submit_order()
- [x] **MatchingEngine Interface** - Strategy pattern for swappable engines
- [x] **BatchMatchingEngine** - Fair randomized batch matching
- [x] **Exchange Tests** - 45+ comprehensive test cases

### Validation System
- [x] **OrderValidator Interface** - Base validation contract
- [x] **ValidationContext** - Order validation state container
- [x] **ConstraintBasedOrderValidator** - Role-agnostic validation
- [x] **8 Constraint Types**:
  - [x] POSITION_LIMIT - Per-instrument position limits
  - [x] PORTFOLIO_LIMIT - Total portfolio constraints
  - [x] ORDER_SIZE - Min/max order quantities
  - [x] ORDER_RATE - Orders per tick limiting
  - [x] ORDER_TYPE_ALLOWED - Role-specific order types
  - [x] TRADING_WINDOW - Phase-based order acceptance
  - [x] INSTRUMENT_ALLOWED - Instrument restrictions
  - [x] PRICE_RANGE - Limit order price bounds
- [x] **Validation Tests** - Complete test coverage

### Game Loop (Legacy)
- [x] **GameLoop** - 5-minute tick orchestration
- [x] **TickPhase Enum** - PRE_OPEN, TRADING, etc.
- [x] **GameConfig** - Configuration data model
- [x] **TradingStrategy Interface** - Bot interface

### Documentation
- [x] **Architecture v2** - Complete system design with 7 threads
- [x] **Validation API Reference** - Constraint documentation
- [x] **Trading Phases Guide** - Batch/continuous market modes

## Phase 2: REST API Foundation

### 2.1 FastAPI Setup
- [ ] **Main application** - FastAPI app instance
- [ ] **CORS configuration** - Allow external bot connections
- [ ] **Exception handlers** - Consistent error responses
- [ ] **Request models** - Pydantic schemas for validation
- [ ] **Response models** - Standardized API responses

### 2.2 Authentication
- [ ] **TeamInfo model** - Bot registration data
- [ ] **API key generation** - Unique keys per team
- [ ] **Auth middleware** - Validate API keys
- [ ] **Team registry** - In-memory team storage
- [ ] **POST /auth/register** - Team registration endpoint

### 2.3 Basic Endpoints
- [ ] **POST /orders** - Submit new order
- [ ] **DELETE /orders/{id}** - Cancel order
- [ ] **GET /positions/{team_id}** - Query positions
- [ ] **GET /market/prices** - Current prices
- [ ] **GET /health** - API health check

## Phase 3: Thread-Safe State

### 3.1 In-Memory Stores
- [ ] **PositionCache** - Dict with RLock for positions
- [ ] **OrderBookState** - Thread-safe SortedList wrapper
- [ ] **MarketCache** - Latest prices with read lock
- [ ] **VolatilityState** - Current regime tracking
- [ ] **RoleRegistry** - Team role configurations

### 3.2 Queue Infrastructure
- [ ] **OrderQueue** - API → Validator
- [ ] **ValidationQueue** - Validator → Matcher
- [ ] **MatchQueue** - For matching engine
- [ ] **TradeQueue** - Matcher → Publisher
- [ ] **PriceQueue** - Price Model → Market Data
- [ ] **EventQueue** - Events → Processing
- [ ] **SignalQueue** - Signals → Distribution

### 3.3 Database Queues
- [ ] **TradeDBQueue** - Async trade persistence
- [ ] **PriceDBQueue** - Market data archival
- [ ] **EventDBQueue** - Event log storage

## Phase 4: Threading Implementation

### 4.1 Thread 2: Order Validator
- [ ] **Validator thread wrapper** - Queue consumer loop
- [ ] **Context builder** - Create ValidationContext from state
- [ ] **Error response handler** - Format rejection messages
- [ ] **Constraint config loader** - Load from YAML
- [ ] **Integration with queues** - Connect to pipeline

### 4.2 Thread 3: Matching Engine
- [ ] **Convert BatchMatchingEngine to continuous** - Immediate execution
- [ ] **Thread wrapper** - Process match queue
- [ ] **Per-instrument locks** - Prevent order book races
- [ ] **Trade generation** - Create Trade objects
- [ ] **Queue integration** - Send trades to publisher

### 4.3 Thread 4: Trade Publisher
- [ ] **Publisher thread** - Consume trade queue
- [ ] **Position Service** - Update position cache
- [ ] **P&L calculation** - Real-time profit/loss
- [ ] **WebSocket broadcast** - Send to connected bots
- [ ] **Async DB write trigger** - Queue for persistence

### 4.4 Thread 5: Market Simulator
- [ ] **Price Model (GBM)** - Geometric Brownian Motion
- [ ] **SPX price generation** - Primary underlying
- [ ] **SPY correlation** - SPX/10 with tracking error
- [ ] **Volatility integration** - Use current regime
- [ ] **Market Publisher** - Stream via WebSocket

### 4.5 Thread 6: Event Generator
- [ ] **Event types** - Fed, economic, geopolitical
- [ ] **Poisson process** - Random event timing
- [ ] **Impact calculator** - Regime shifts, price jumps
- [ ] **Signal Generator** - Create trading signals
- [ ] **Signal distribution** - Role-based filtering

### 4.6 Thread 7: Database Writer
- [ ] **Batch accumulator** - Collect 1000 trades
- [ ] **Bulk insert logic** - Efficient DB writes
- [ ] **Position snapshots** - Periodic state saves
- [ ] **Error handling** - Queue overflow management
- [ ] **Performance monitoring** - Track write latency

## Phase 5: WebSocket Layer

### 5.1 WebSocket Server
- [x] **WebSocket endpoint setup** - /ws routes (ready for integration)
- [x] **Connection manager** - Track active connections
- [x] **Authentication** - Validate on connect
- [ ] **Heartbeat/ping** - Keep connections alive
- [ ] **Reconnection support** - Handle disconnects

### 5.2 Data Streams
- [x] **Message types defined** - Following FIX conventions
- [x] **Trade execution reports** - Real-time fills
- [x] **Order acknowledgments** - new_order_ack/reject
- [x] **Position snapshots** - On connection
- [x] **Market data format** - Price updates structure
- [ ] **Full integration** - Connect to main.py
- [ ] **Signal distribution** - Role-based filtering

## Phase 6: Database Layer

### 6.1 Schema Design
- [ ] **trades table** - Execution history
- [ ] **prices table** - Market data archive
- [ ] **events table** - News event log
- [ ] **positions table** - Snapshot storage
- [ ] **teams table** - Registration data

### 6.2 SQLAlchemy Models
- [ ] **Trade model** - ORM mapping
- [ ] **Price model** - Time series data
- [ ] **Event model** - Event records
- [ ] **Position model** - State snapshots
- [ ] **Database session management** - Thread-safe access

## Phase 7: Integration & Testing

### 7.1 Integration Points
- [ ] **OrderValidator ↔ Exchange** - Validation before matching
- [ ] **PositionService ↔ OrderValidator** - Position limit checks
- [ ] **All threads connected** - Full pipeline test
- [ ] **Database persistence** - Verify async writes
- [ ] **WebSocket stability** - Multi-client test

### 7.2 Example Bots
- [ ] **Python REST bot** - Reference implementation
- [ ] **WebSocket market data** - Streaming example
- [ ] **Java bot skeleton** - Multi-language support
- [ ] **Performance test bot** - Load generation
- [ ] **Migration guide** - From embedded to API

### 7.3 Performance Testing
- [ ] **Single bot baseline** - Latency measurement
- [ ] **10 bot test** - Concurrency check
- [ ] **30 bot stress test** - Full load
- [ ] **Order latency < 10μs** - Matching performance
- [ ] **1000 orders/second** - Throughput target

## Next Immediate Tasks

1. Create `src/intern_trading_game/api/main.py` with FastAPI app
2. Implement `POST /orders` endpoint with Pydantic models
3. Create `PositionCache` class with thread-safe operations
4. Add `OrderQueue` and basic validator thread
5. Test order flow with single REST client
