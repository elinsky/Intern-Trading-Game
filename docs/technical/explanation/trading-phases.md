# Trading Phases Guide

## Overview

The Intern Trading Game uses a continuous trading model with distinct market phases that control when orders can be submitted and when matching occurs. This guide explains the phase-based trading system.

## Trading Phases

The system operates in one of three phases at any given time:

### 1. PRE_OPEN

- **Order Submission**: ✅ Allowed
- **Order Cancellation**: ✅ Allowed
- **Matching**: ❌ Disabled
- **Use Case**: Queue orders before market opens

During pre-market, traders can submit and cancel orders to build the opening order book. No matching occurs, allowing participants to establish positions without immediate execution risk.

### 2. CONTINUOUS

- **Order Submission**: ✅ Allowed
- **Order Cancellation**: ✅ Allowed
- **Matching**: ✅ Enabled (real-time)
- **Use Case**: Normal trading hours

The main trading session with continuous matching. Orders execute immediately if they cross with existing orders in the book. This provides price discovery and liquidity throughout the trading day.

### 3. CLOSED

- **Order Submission**: ❌ Not allowed
- **Order Cancellation**: ❌ Not allowed
- **Matching**: ❌ Disabled
- **Use Case**: Market closed

No trading activity permitted. All orders are rejected during this phase.

## Phase Schedule

The default schedule follows standard equity market hours:

- **08:00-09:30 CT**: PRE_OPEN
- **09:30-16:00 CT**: CONTINUOUS
- **16:00-08:00 CT**: CLOSED
- **Weekends**: CLOSED

## Implementation Details

### Phase Evaluation

The system evaluates the current phase based on:

1. Current time of day
2. Day of week
3. Configured market hours

### Order Validation

Orders are validated against the current phase before acceptance:

- In PRE_OPEN: Orders accepted but held in book
- In CONTINUOUS: Orders accepted and immediately matched
- In CLOSED: Orders rejected with appropriate error

### Phase Transitions

Phase transitions occur automatically based on time:

- PRE_OPEN -> CONTINUOUS at market open (09:30)
- CONTINUOUS -> CLOSED at market close (16:00)
- CLOSED -> PRE_OPEN at pre-market open (08:00)

## Future Enhancements

The phase system is designed to be extensible:

1. **Configuration-Driven Schedules**: Define custom phase schedules via YAML
2. **Holiday Support**: Automatic market closures on holidays
3. **Special Sessions**: Support for extended hours or special trading sessions
4. **Auction Phases**: Opening/closing auctions with special matching rules

## API Integration

### REST API

The REST API respects phase rules:

- Order submission endpoints check current phase
- Appropriate error messages for phase violations

### WebSocket

Phase changes can be broadcast via WebSocket (future enhancement):

- `phase_change` messages notify connected clients
- Clients can adjust behavior based on current phase

## Example Usage

```python
# Bot adjusts behavior based on phase
if current_phase == "PRE_OPEN":
    # Submit opening orders
    submit_opening_positions()
elif current_phase == "CONTINUOUS":
    # Active trading strategy
    execute_trading_strategy()
else:  # CLOSED
    # No trading, perhaps analyze data
    analyze_market_data()
```
