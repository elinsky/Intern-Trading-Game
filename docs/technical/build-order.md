# Build Order Checklist - v2 API Architecture

## Phase 1: Core Foundation COMPLETE

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

## Phase 2: REST API Foundation COMPLETE

### 2.1 FastAPI Setup

- [x] **Main application** - FastAPI app instance
- [x] **CORS configuration** - Allow external bot connections
- [x] **Exception handlers** - Consistent error responses
- [x] **Request models** - Pydantic schemas for validation
- [x] **Response models** - Standardized API responses

### 2.2 Authentication

- [x] **TeamInfo model** - Bot registration data
- [x] **API key generation** - Unique keys per team
- [x] **Auth middleware** - Validate API keys
- [x] **Team registry** - In-memory team storage
- [x] **POST /auth/register** - Team registration endpoint

### 2.3 Basic Endpoints

- [x] **POST /orders** - Submit new order with client_order_id
- [ ] **DELETE /orders/{id}** - Cancel order (deferred to commit 3)
- [x] **GET /positions/{team_id}** - Query positions
- [ ] **GET /market/prices** - Current prices (future)
- [x] **GET /health** - API health check with thread status

## Phase 3: Thread-Safe State

### 3.1 In-Memory Stores

- [ ] **PositionCache** - Dict with RLock for positions
- [ ] **OrderBookState** - Thread-safe SortedList wrapper
- [ ] **MarketCache** - Latest prices with read lock
- [ ] **VolatilityState** - Current regime tracking
- [ ] **RoleRegistry** - Team role configurations

### 3.2 Queue Infrastructure

- [ ] **OrderQueue** - API -> Validator
- [ ] **ValidationQueue** - Validator -> Matcher
- [ ] **MatchQueue** - For matching engine
- [ ] **TradeQueue** - Matcher -> Publisher
- [ ] **PriceQueue** - Price Model -> Market Data
- [ ] **EventQueue** - Events -> Processing
- [ ] **SignalQueue** - Signals -> Distribution

### 3.3 Database Queues

- [ ] **TradeDBQueue** - Async trade persistence
- [ ] **PriceDBQueue** - Market data archival
- [ ] **EventDBQueue** - Event log storage

## Phase 4: Threading Implementation (Partial)

### 4.1 Thread 2: Order Validator COMPLETE

- [x] **Validator thread wrapper** - Queue consumer loop
- [x] **Context builder** - Create ValidationContext from state
- [x] **Error response handler** - Format rejection messages
- [x] **Constraint config loader** - Load market maker constraints
- [x] **Integration with queues** - Connect to pipeline
- [x] **WebSocket rejection notifications** - Send via queue

### 4.2 Thread 3: Matching Engine COMPLETE

- [x] **Using ContinuousMatchingEngine** - Immediate execution
- [x] **Thread wrapper** - Process match queue
- [x] **Trade generation** - Exchange creates Trade objects
- [x] **Queue integration** - Send trades to publisher
- [x] **WebSocket order acknowledgments** - Send via queue

### 4.3 Thread 4: Trade Publisher

- [x] **Publisher thread** - Consume trade queue
- [x] **Position tracking** - Update position dictionary
- [x] **Fee calculation** - Based on maker/taker status
- [x] **WebSocket execution reports** - Send via queue
- [ ] **P&L calculation** - Real-time profit/loss (future)
- [ ] **Async DB write trigger** - Queue for persistence (future)

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

### 4.7 Thread 8: WebSocket Publisher COMPLETE

- [x] **WebSocket thread wrapper** - Async event loop
- [x] **Queue bridge** - asyncio.to_thread for sync/async
- [x] **Message router** - Route by type to broadcast methods
- [x] **Connection checks** - Only send to connected clients
- [x] **Error handling** - Continue on individual failures

## Phase 5: WebSocket Layer

### 5.1 WebSocket Server

- [x] **WebSocket endpoint setup** - /ws routes (ready for integration)
- [x] **Connection manager** - Track active connections
- [x] **Authentication** - Validate on connect
- [ ] **Heartbeat/ping** - Keep connections alive
- [ ] **Reconnection support** - Handle disconnects

### 5.2 Data Streams

- [x] **Message types defined** - Following FIX conventions
- [x] **Trade execution reports** - Real-time fills with fees
- [x] **Order acknowledgments** - new_order_ack/reject
- [x] **Position snapshots** - On connection
- [x] **Market data format** - Price updates structure
- [x] **Full integration** - Connected to main.py via Thread 8
- [ ] **Signal distribution** - Role-based filtering (future)

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
