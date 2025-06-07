# System Architecture v2 - REST API & Multi-Threading

This document outlines the new multi-threaded, API-based architecture for the Intern Trading Game with hybrid in-memory/database design for maximum exchange performance.

## Overview

The system uses a hybrid architecture optimizing for exchange performance while maintaining data persistence. The critical trading path operates entirely in-memory, while a separate thread handles asynchronous database writes.

## Architecture Diagram

```mermaid
graph TB

%% External Layer - Multiple Bot Processes
subgraph "External Bot Processes"
    B1[Bot 1]
    B2[Bot 2]
    B3[Bot 3]
    BN[Bot N]
end

%% API Layer
subgraph "API Layer (Main Process)"
    subgraph "Thread 1: FastAPI Server"
        REST[REST API<br/>Port 8000]
        WS[WebSocket Server<br/>Market Data & Trades]
        AUTH[Auth Service<br/>API Key Validation]
    end
end

%% Core Processing Threads
subgraph "Core Processing (Threads)"
    subgraph "Thread 2: Order Validator"
        OV[Order Validator<br/>Role Constraints]
        VC[Validation Cache<br/>Positions & Limits]
    end

    subgraph "Thread 3: Matching Engine"
        ME[Continuous Matcher<br/>Price-Time Priority]
        OB[Order Books<br/>Per Instrument]
    end

    subgraph "Thread 4: Trade Publisher"
        TP[Trade Publisher<br/>Execution Reports]
        PS[Position Service<br/>P&L Tracking]
    end

    subgraph "Thread 5: Market Simulator"
        PM[Price Model<br/>GBM Generator]
        VSM[Volatility State Machine<br/>Low/Med/High]
        MD[Market Publisher<br/>Price Streaming]
    end

    subgraph "Thread 6: Event Generator"
        EG[Event Generator<br/>News & Market Events]
        ES[Event Scheduler<br/>Poisson Process]
        SG[Signal Generator<br/>Trading Signals]
    end

    subgraph "Thread 7: Database Writer"
        DBW[DB Writer<br/>Batch Inserts]
    end
end

%% Thread-Safe Queues
subgraph "Thread Communication (Queues)"
    OQ[Order Queue<br/>Thread-Safe]
    VQ[Validation Queue<br/>Thread-Safe]
    MQ[Match Queue<br/>Thread-Safe]
    TQ[Trade Queue<br/>Thread-Safe]
    PQ[Price Queue<br/>Thread-Safe]
    EQ[Event Queue<br/>Thread-Safe]
    SQ[Signal Queue<br/>Thread-Safe]
end

%% Fast Path - In-Memory Stores
subgraph "In-Memory State (Nanosecond Access)"
    POS[Position Cache<br/>Dict with RLock]
    OB_STATE[Order Book State<br/>SortedLists]
    CACHE[Price Cache<br/>Latest Prices]
    VOL[Volatility State<br/>Current Regime]
    ROLE[Role Registry<br/>Team Configs]
end

%% Slow Path - Database
subgraph "Database (Async Persistence)"
    DB[(PostgreSQL/SQLite)]
    DB_TRADES[Trade History]
    DB_PRICES[Price History]
    DB_EVENTS[Event Log]
    DB_SNAP[Position Snapshots]
end

%% Async DB Queues
subgraph "Async DB Queues"
    DBQ[Trade DB Queue]
    DBPQ[Price DB Queue]
    DBEQ[Event DB Queue]
end

%% External Bot Connections
B1 -->|HTTP POST /orders| REST
B2 -->|HTTP POST /orders| REST
B3 -->|HTTP GET /positions| REST
BN -->|WebSocket /market-data| WS

%% API to Queue Flow
REST -->|New Orders| OQ
AUTH -.->|Validates| REST

%% Order Processing Pipeline (FAST PATH)
OQ -->|Orders| OV
OV -->|Valid Orders| VQ
VQ -->|To Match| MQ
MQ -->|Process| ME
ME -->|Trades| TQ
TQ -->|Results| TP

%% Market Simulation Flow
PM -->|Prices| PQ
VSM -->|Vol State| PM
PQ -->|Broadcast| MD
MD -->|Stream| WS

%% Event Generation Flow
EG -->|News Events| EQ
EQ -->|Process| VSM
EQ -->|Trigger Signals| SG
SG -->|Signals| SQ
SQ -->|Broadcast| WS

%% Trade Results Flow
TP -->|Executions| WS
TP -->|Update| PS

%% Position Service Updates (FAST PATH)
PS -->|Update| POS

%% Async Database Writes (SLOW PATH)
TP -.->|Async| DBQ
DBQ -->|Batch| DBW
DBW -->|Insert| DB_TRADES

MD -.->|Async| DBPQ
DBPQ -->|Batch| DBW
DBW -->|Insert| DB_PRICES

EG -.->|Async| DBEQ
DBEQ -->|Batch| DBW
DBW -->|Insert| DB_EVENTS

%% Periodic Snapshots
PS -.->|Snapshot| DBW
DBW -->|Save| DB_SNAP

%% Shared State Access (FAST PATH)
OV -.->|Read| POS
OV -.->|Read| ROLE
REST -.->|Read via PS| POS
ME -.->|Update| OB_STATE
VSM -.->|Update| VOL
PM -.->|Read| VOL
MD -.->|Update| CACHE

%% Signal Examples (Generic)
SG -->|Volatility Forecasts| SQ
SG -->|Price Divergence Signals| SQ
SG -->|Market Sentiment| SQ
SG -->|Technical Indicators| SQ
```

## Performance Architecture

### Critical Path
```
Order Submission → Validation → Matching → Position Update → Trade Notification
     ~100ns         ~500ns      ~2μs        ~100ns           ~1μs
                          Total: < 5 microseconds
```

### Async Path (Non-Blocking)
```
Trade → DB Queue → Batch Accumulation → Database Write
         ~100ns      (up to 100ms)        ~10-50ms
                    Never blocks trading
```

## Fast Path Components

### In-Memory Order Books
```python
class OrderBook:
    def __init__(self):
        # SortedList maintains order automatically
        self.bids = SortedList(key=lambda x: (-x.price, x.timestamp))
        self.asks = SortedList(key=lambda x: (x.price, x.timestamp))
        self.lock = threading.Lock()  # Per-instrument lock
```

### Position Cache
```python
class PositionCache:
    def __init__(self):
        self.positions = {}  # {team_id: {instrument: quantity}}
        self.lock = threading.RLock()  # Reentrant lock

    def update_atomic(self, team_id, instrument, delta):
        with self.lock:  # ~50ns overhead
            if team_id not in self.positions:
                self.positions[team_id] = {}
            current = self.positions[team_id].get(instrument, 0)
            self.positions[team_id][instrument] = current + delta
```

## Slow Path Components

### Database Writer Thread
```python
class DatabaseWriter:
    def __init__(self, db_conn):
        self.db = db_conn
        self.trade_batch = []
        self.price_batch = []

    def run(self):
        while True:
            # Accumulate trades for batch insert
            try:
                while len(self.trade_batch) < 1000:
                    trade = trade_queue.get(timeout=0.1)
                    self.trade_batch.append(trade)
            except Empty:
                pass

            # Batch insert (much faster than individual inserts)
            if self.trade_batch:
                self.db.insert_trades(self.trade_batch)
                self.trade_batch.clear()
```

## Hybrid Design Benefits

### Reliability Features
- **Crash Recovery**: Reload positions from last snapshot + trade log
- **Audit Trail**: Complete trade history in database
- **Analytics**: Can query historical data without impacting trading

### Memory Layout Optimization
```python
# Cache-friendly data structures
positions = {
    "team1": {"SPX_CALL": 10, "SPX_PUT": -5},  # Dict lookup: O(1)
    "team2": {"SPX_CALL": 20, "SPY_CALL": 15}
}

# Pre-allocated arrays for ultra-low latency
order_pool = [Order() for _ in range(100000)]  # Object pool
trade_pool = [Trade() for _ in range(100000)]  # Avoid allocation
```

## Database Schema

### Trade History Table
```sql
CREATE TABLE trades (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    buyer_id VARCHAR(50) NOT NULL,
    seller_id VARCHAR(50) NOT NULL,
    instrument VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL,
    buyer_fee DECIMAL(10,2),
    seller_fee DECIMAL(10,2),
    INDEX idx_timestamp (timestamp),
    INDEX idx_buyer (buyer_id),
    INDEX idx_seller (seller_id)
);
```

### Position Snapshots Table
```sql
CREATE TABLE position_snapshots (
    snapshot_time TIMESTAMP NOT NULL,
    team_id VARCHAR(50) NOT NULL,
    positions JSONB NOT NULL,  -- {"SPX_CALL": 10, "SPX_PUT": -5}
    pnl DECIMAL(15,2),
    PRIMARY KEY (snapshot_time, team_id)
);
```

## Thread Responsibilities

### Thread 1: FastAPI Server (Async)
- Handles all HTTP requests
- Manages WebSocket connections
- Validates API keys
- Routes orders to processing pipeline

### Thread 2: Order Validator
- Validates orders against role constraints
- Checks position limits (via OrderValidator constraints)
- Enforces trading rules
- Fast-fail invalid orders

### Thread 3: Matching Engine
- Continuous order matching
- Maintains order books
- Executes trades immediately
- Price-time priority algorithm

### Thread 4: Trade Publisher & Position Service
- Broadcasts executions to bots
- Updates position tracking
- Calculates P&L
- Triggers async database writes

### Thread 5: Market Simulator
- Runs price generation model
- Manages volatility regimes
- Broadcasts market data
- Handles regime transitions

### Thread 6: Event Generator
- Schedules random events
- Processes event impacts
- Generates trading signals
- Maintains event history

### Thread 7: Database Writer
- Batch inserts trades to database
- Saves price history asynchronously
- Stores event logs
- Takes periodic position snapshots

## Configuration

### Performance Tuning
```yaml
performance:
  order_queue_size: 10000
  batch_size: 1000
  db_write_interval_ms: 100
  position_snapshot_interval_s: 60

threading:
  matching_engine_priority: high
  db_writer_priority: low

memory:
  preallocate_orders: 100000
  preallocate_trades: 100000
  position_cache_size: 1000
```

## Next Steps

1. Implement in-memory matching engine with SortedList
2. Add position cache with RLock
3. Create database writer thread
4. Implement batch insert logic
5. Add position snapshot system
6. Performance benchmark (target: <10μs per trade)
