# Trading Phases Guide

## Overview

The Intern Trading Game supports flexible market structures through configurable trading phases. This guide explains how to implement different market models: pure batch matching, continuous trading, and realistic hybrid models like CBOE SPX.

## Phase System Architecture

### Core Phases

The system defines six core phases that can be combined to create any market structure:

1. **MARKET_DATA** - Market data updates, price publication
2. **PRE_OPEN** - Order entry allowed, no matching
3. **OPEN** - Transition phase, order entry may close
4. **TRADING** - Active matching (batch or continuous)
5. **CLOSING** - End of session processing
6. **CLOSED** - No activity allowed

### Phase Capabilities

Each phase can be configured with different capabilities:

- **Order Entry**: Whether new orders are accepted
- **Order Cancellation**: Whether orders can be cancelled
- **Matching**: Whether trades execute
- **Market Data**: Whether prices/signals are distributed

## Market Structure Examples

### 1. Pure Batch Mode (Current Implementation)

Simple 5-minute batch auction cycles:

```yaml
phases:
  - name: MARKET_DATA
    start: "T+0:00"
    duration: 30
    capabilities:
      order_entry: false
      matching: false
      market_data: true

  - name: PRE_OPEN
    start: "T+0:30"
    duration: 150  # 2.5 minutes
    capabilities:
      order_entry: true
      matching: false
      cancellation: true

  - name: TRADING
    start: "T+3:30"
    duration: 30
    capabilities:
      order_entry: false
      matching: true  # Batch execution
      matching_type: batch

  - name: CLOSED
    start: "T+4:00"
    duration: 60
    capabilities:
      order_entry: false
      matching: false
```

**Use Case**: Simplified markets, teaching environments, stress testing

### 2. Pure Continuous Mode

Traditional continuous limit order book:

```yaml
trading_hours:
  market_open: "09:30"
  market_close: "16:00"

phases:
  - name: PRE_OPEN
    start: "09:00"
    end: "09:30"
    capabilities:
      order_entry: true
      matching: false
      cancellation: true

  - name: TRADING
    start: "09:30"
    end: "16:00"
    capabilities:
      order_entry: true
      matching: true
      matching_type: continuous
      cancellation: true
```

**Use Case**: Equity markets, FX markets, most futures

### 3. Realistic Hybrid Mode (CBOE SPX Style)

Complex schedule with multiple session types:

```yaml
sessions:
  # Global Trading Hours (overnight)
  gth_session:
    - name: PRE_OPEN
      start: "19:30"  # 7:30 PM
      end: "20:15"    # 8:15 PM
      capabilities:
        order_entry: true
        matching: false
        instruments: ["SPXW", "VIX"]  # Limited products

    - name: TRADING
      start: "20:15"  # 8:15 PM
      end: "09:15"   # 9:15 AM next day
      capabilities:
        order_entry: true
        matching: true
        matching_type: continuous
        instruments: ["SPXW", "VIX"]

  # Regular Trading Hours
  rth_session:
    - name: PRE_OPEN
      start: "09:15"
      end: "09:30"
      capabilities:
        order_entry: true
        matching: false
        order_types: ["LIMIT", "MARKET", "QUOTE"]
        description: "Opening rotation preparation"

    - name: OPENING_AUCTION
      start: "09:30"
      duration: 30  # seconds
      capabilities:
        order_entry: false
        matching: true
        matching_type: batch
        description: "Opening cross"

    - name: TRADING
      start: "09:30:30"
      end: "15:15"  # 3:15 PM for SPX
      capabilities:
        order_entry: true
        matching: true
        matching_type: continuous
        cancellation: true

    - name: CLOSING_AUCTION_PREP
      start: "15:15"
      end: "15:30"
      capabilities:
        order_entry: true
        matching: false
        order_types: ["LIMIT", "MOC", "LOC"]
        description: "Closing rotation preparation"

    - name: CLOSING_AUCTION
      start: "15:30"
      duration: 60
      capabilities:
        order_entry: false
        matching: true
        matching_type: batch
        use_settlement_price: true

    - name: POST_CLOSE
      start: "15:31"
      end: "16:30"
      capabilities:
        order_entry: false
        matching: false
        clearing_only: true
```

**Key Features**:

- Multiple sessions with different rules
- Opening and closing auctions
- Overnight trading for specific products
- Different order types by phase
- Settlement price determination
