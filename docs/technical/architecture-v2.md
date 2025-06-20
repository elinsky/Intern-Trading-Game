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

    subgraph "Thread 8: WebSocket Publisher"
        WSP[WebSocket Publisher<br/>Async Message Delivery]
        WSQ[Message Router<br/>Type-based Dispatch]
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
    WQ[WebSocket Queue<br/>Thread-Safe]
end

%% Fast Path - In-Memory Stores
subgraph "In-Memory State"
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
- Sends rejection notifications to WebSocket queue

### Thread 3: Matching Engine

- Continuous order matching
- Maintains order books
- Executes trades immediately
- Price-time priority algorithm
- Sends order acknowledgments to WebSocket queue

### Thread 4: Trade Publisher & Position Service

- Broadcasts executions to bots
- Sends execution reports to WebSocket queue
- Calculates fees based on maker/taker status
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

### Thread 8: WebSocket Publisher

- Bridges sync threads with async WebSocket connections
- Routes messages by type to appropriate broadcast methods
- Handles connection lifecycle per team
- Ensures message delivery to connected clients only

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
