# Trading Phases Guide

## Overview

The Intern Trading Game uses a phase-based trading model with distinct market phases that control when orders can be submitted and when matching occurs. The system automatically handles critical market operations during phase transitions, such as executing opening auctions and cancelling orders at market close.

## Trading Phases

The system operates in one of four phases at any given time:

### 1. PRE_OPEN

- **Order Submission**: ✅ Allowed
- **Order Cancellation**: ✅ Allowed
- **Matching**: ❌ Disabled
- **Use Case**: Queue orders before market opens

During pre-market, traders can submit and cancel orders to build the opening order book. No matching occurs, allowing participants to establish positions without immediate execution risk. Orders submitted during this phase are queued for the opening auction.

### 2. OPENING_AUCTION

- **Order Submission**: Not allowed
- **Order Cancellation**: Not allowed
- **Matching**: Batch execution
- **Use Case**: Establish fair opening prices

The opening auction phase is a brief window (typically 30 seconds) before continuous trading begins. During this phase, the order book is frozen and all pre-open orders are matched simultaneously using batch matching to determine fair opening prices across all instruments.

### 3. CONTINUOUS

- **Order Submission**: ✅ Allowed
- **Order Cancellation**: ✅ Allowed
- **Matching**: ✅ Enabled (real-time)
- **Use Case**: Normal trading hours

The main trading session with continuous matching. Orders execute immediately if they cross with existing orders in the book. This provides price discovery and liquidity throughout the trading day.

### 4. CLOSED

- **Order Submission**: ❌ Not allowed
- **Order Cancellation**: ❌ Not allowed
- **Matching**: ❌ Disabled
- **Use Case**: Market closed

No trading activity permitted. All orders are rejected during this phase.

## Phase Schedule

The default schedule follows standard equity market hours:

- **08:00-09:29:30 CT**: PRE_OPEN
- **09:29:30-09:30:00 CT**: OPENING_AUCTION
- **09:30:00-16:00:00 CT**: CONTINUOUS
- **16:00:00-08:00:00 CT**: CLOSED
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

- **CLOSED -> PRE_OPEN** at 08:00 CT - Market prepares to open
- **PRE_OPEN -> OPENING_AUCTION** at 09:29:30 CT - Order book freezes for auction
- **OPENING_AUCTION -> CONTINUOUS** at 09:30:00 CT - Normal trading begins
- **CONTINUOUS -> CLOSED** at 16:00:00 CT - Market closes for the day

### Automatic Phase Transition Actions

The system automatically executes critical market operations during specific phase transitions:

#### Opening Auction (PRE_OPEN -> OPENING_AUCTION)

When transitioning to the OPENING_AUCTION phase:

- Order book is frozen (no new orders or cancellations)
- Opening auction executes automatically using batch matching
- Fair opening prices are established for all instruments with crossing orders
- Trades are generated and published before continuous trading begins

#### Market Close (CONTINUOUS -> CLOSED)

When transitioning to the CLOSED phase:

- All resting orders across all instruments are automatically cancelled
- Order books are cleared to prevent stale orders from persisting
- No manual intervention required - ensures clean start for next trading day

### Phase Transition Handler

The automatic phase transition actions are managed by the `ExchangePhaseTransitionHandler`, which:

- Monitors phase changes by comparing current phase with previous phase
- Executes appropriate actions based on a dispatch table of transitions
- Integrates seamlessly with the exchange's matching thread
- Follows separation of concerns: PhaseManager knows WHEN phases change, handler knows WHAT to do

### Configuration Parameters

The phase transition system can be fine-tuned with these parameters:

#### phase_check_interval (default: 0.1 seconds)

- Maximum delay before checking for market phase transitions
- Controls responsiveness to phase changes like market open/close
- Lower values = faster response but more CPU overhead
- Higher values = reduced overhead but may delay critical operations

#### order_queue_timeout (default: 0.01 seconds)

- Maximum wait time for new orders before checking market phases
- Determines phase check frequency during quiet markets
- Lower values = more responsive during quiet periods but higher CPU usage
- Higher values = less CPU usage but potentially delayed phase transitions

Example configuration:
```yaml
exchange:
  phase_check_interval: 0.1  # Check phases every 100ms max
  order_queue_timeout: 0.01  # Check after 10ms of no orders
```

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
elif current_phase == "OPENING_AUCTION":
    # Wait - no actions allowed during auction
    log.info("Opening auction in progress...")
elif current_phase == "CONTINUOUS":
    # Active trading strategy
    execute_trading_strategy()
else:  # CLOSED
    # No trading, perhaps analyze data
    analyze_market_data()
```
