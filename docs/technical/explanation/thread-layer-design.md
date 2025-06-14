# Thread Layer Design Principles

This document explains the architectural principles and design philosophy behind the thread layer in the Intern Trading Game. While `architecture-v3.md` describes *what* the threads do, this document explains *why* they exist and *how* to work with them effectively.

## Table of Contents

1. [Core Purpose](#core-purpose)
2. [Architectural Principles](#architectural-principles)
3. [The Producer-Consumer Pattern](#the-producer-consumer-pattern)
4. [Separation of Concerns](#separation-of-concerns)
5. [Testing Philosophy](#testing-philosophy)
6. [Common Patterns](#common-patterns)
7. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

## Core Purpose

The thread layer exists to solve three fundamental problems in trading systems:

### 1. **Latency vs Throughput**

- **Problem**: Order validation, matching, and settlement take time (10-50ms total)
- **Solution**: Return immediately to the client, process asynchronously
- **Result**: API latency ~1ms, throughput increases 10-50x

### 2. **Fairness**

- **Problem**: Multiple bots submitting orders simultaneously
- **Solution**: FIFO queues ensure first-come-first-served processing
- **Result**: No bot can "jump the queue" regardless of connection speed

### 3. **Resilience**

- **Problem**: One slow operation (e.g., position calculation) blocks everything
- **Solution**: Pipeline architecture - each stage processes independently
- **Result**: System remains responsive even under load

## Architectural Principles

### Principle 1: Threads are Infrastructure, Not Business Logic

Threads should be "dumb pipes" that:

- Pull messages from queues
- Call services to process them
- Route results to appropriate queues
- Handle errors without crashing

Threads should NOT:

- Implement validation rules
- Calculate fees or positions
- Make business decisions
- Know about domain concepts

### Principle 2: Single Responsibility

Each thread has exactly ONE job:

```
Validator Thread:  Route orders based on validation result
Matching Thread:   Submit orders and route trades
Publisher Thread:  Process trades and update state
WebSocket Thread:  Bridge sync→async for real-time updates
```

This makes threads easy to understand, test, and debug.

### Principle 3: Fail-Safe Operation

Threads must:

- Continue processing after errors
- Log failures for debugging
- Never corrupt shared state
- Shutdown gracefully on signal

## The Producer-Consumer Pattern

The thread layer implements a classic producer-consumer pipeline:

```
[Producer] → [Queue] → [Consumer/Producer] → [Queue] → [Consumer]
```

### Why Queues?

1. **Decoupling**: Producers and consumers don't know about each other
2. **Buffering**: Handle burst traffic without dropping messages
3. **Thread-Safe**: Python's Queue handles all synchronization
4. **Backpressure**: Queues can be bounded to prevent memory issues

### Message Flow Example

```python
# API produces order
order_queue.put(("new_order", order, team_info, response_event))

# Validator consumes and produces
message = order_queue.get()  # Blocks until message available
if valid:
    match_queue.put((order, team_info))  # Produce to next stage
else:
    websocket_queue.put(rejection)  # Produce to WebSocket

# Matcher consumes and produces
order, team = match_queue.get()
trade = exchange.match(order)
trade_queue.put((trade, order, team))

# And so on...
```

## Separation of Concerns

The thread layer carefully separates infrastructure concerns from business logic:

### Infrastructure Concerns (Thread Layer Handles)

- Queue management (get/put operations)
- Thread lifecycle (startup/shutdown)
- Message routing based on results
- Lock management for shared state
- Error recovery and logging
- Event synchronization

### Business Logic (Service Layer Handles)

- Validation rules and constraints
- Order matching algorithms
- Fee calculations
- Position management
- Risk checks
- Market rules

### Example: Order Validation

```python
# THREAD LAYER (Infrastructure)
def validator_thread(...):
    while True:
        message = order_queue.get()
        if message is None:
            break  # Shutdown

        # Call service for business logic
        result = validation_service.validate_new_order(order, team)

        # Route based on result (infrastructure concern)
        if result.status == "accepted":
            match_queue.put((order, team))
        else:
            websocket_queue.put(create_rejection(result))

# SERVICE LAYER (Business Logic)
class OrderValidationService:
    def validate_new_order(self, order, team):
        # Check position limits
        # Verify order rate limits
        # Validate price bounds
        # Apply role-specific rules
        return ValidationResult(...)
```

## Testing Philosophy

Testing threads requires a different approach than testing business logic:

### What to Test in Threads

1. **Message Routing**
2.
   - Accepted orders go to match_queue
   - Rejected orders go to websocket_queue
   - Trades go to trade_queue

3. **Queue Operations**
4.
   - Thread blocks on empty queue
   - Thread processes messages in order
   - Shutdown signal works correctly

5. **State Updates**
6.
   - Locks are acquired/released properly
   - Shared state updates are atomic
   - No race conditions

7. **Error Handling**
8.
   - Thread continues after exceptions
   - Errors are logged appropriately
   - No message loss on error

### What NOT to Test in Threads

- Business rules (test in services)
- Calculations (test in domain)
- Complex logic (should be in services)

### Testing Strategy

```python
def test_validator_routes_accepted_orders():
    # Given - Mock service to accept order
    mock_service.validate_new_order.return_value = accepted_result

    # When - Send order through thread
    order_queue.put(("new_order", order, team, event))
    order_queue.put(None)  # Shutdown

    validator_thread(...)  # Run directly, no actual threading

    # Then - Verify routing
    assert not match_queue.empty()
    assert match_queue.get() == (order, team)
```

## Common Patterns

### 1. Message Tuple Format

Use consistent tuple formats for queue messages:

```python
# Order validation messages
("new_order", order, team_info, response_event)
("cancel_order", order_id, team_info, response_event)

# Trade messages
(trade_result, original_order, team_info)

# WebSocket messages
(message_type, team_id, message_data)
```

### 2. Graceful Shutdown

Use `None` as a sentinel value:

```python
def some_thread(queue, ...):
    while True:
        message = queue.get()
        if message is None:  # Shutdown signal
            break
        # Process message
```

### 3. Service Injection

Inject services at thread creation:

```python
thread = Thread(
    target=validator_thread,
    args=(queues..., validation_service, ...)
)
```

### 4. Lock Context Managers

Always use context managers for locks:

```python
with orders_lock:
    orders_this_tick[team_id] += 1
```

## Anti-Patterns to Avoid

### 1. Business Logic in Threads

**Bad**: Thread makes business decisions
```python
def validator_thread(...):
    if order.quantity > 100:  # Business rule!
        reject_order("Too large")
```

**Good**: Service makes decisions
```python
def validator_thread(...):
    result = validation_service.validate(order)
    if result.rejected:
        websocket_queue.put(rejection)
```

### 2. Shared Service State

**Bad**: Services maintain state
```python
class ValidationService:
    def __init__(self):
        self.orders_count = {}  # Shared mutable state!
```

**Good**: Pass state via functions
```python
class ValidationService:
    def __init__(self, get_order_count_func):
        self._get_order_count = get_order_count_func
```

### 3. Complex Thread Logic

**Bad**: Thread does too much
```python
def validator_thread(...):
    # 200 lines of validation logic
    # Fee calculations
    # Position checks
    # Risk management
```

**Good**: Thread just coordinates
```python
def validator_thread(...):
    while True:
        message = queue.get()
        result = service.process(message)
        route_message(result)
```

### 4. Synchronous Blocking

**Bad**: Thread waits for external resources
```python
def matching_thread(...):
    response = requests.get("https://api.example.com")  # Blocks!
```

**Good**: Use queues for async operations
```python
def matching_thread(...):
    external_data_queue.put(request)
    # Continue processing other orders
```

## Communication Patterns

The thread layer implements a clean separation of communication channels:

### Validator Thread → API Response Only

The validator thread communicates validation results directly back to the API:

```python
# Accepted order
response = ApiResponse(
    success=True,
    order_id=order.order_id,
    timestamp=datetime.now()
)
order_responses[order.order_id] = response
response_event.set()  # Unblock API

# Rejected order
response = ApiResponse(
    success=False,
    error=ApiError(
        code="POSITION_LIMIT",
        message="Would exceed limit of 50"
    )
)
order_responses[order.order_id] = response
response_event.set()  # Unblock API
```

**Key Point**: The validator does NOT send WebSocket messages for validation results.

### Exchange/Matcher → WebSocket Only

The exchange and downstream threads communicate events via WebSocket:

```python
# From matcher thread
websocket_queue.put((
    "new_order_ack",
    team_id,
    {"order_id": order_id, "status": "in_book"}
))

# From publisher thread
websocket_queue.put((
    "execution_report",
    team_id,
    {"order_id": order_id, "price": price, "quantity": qty}
))
```

This separation ensures:
- No duplicate messages (validation results aren't sent twice)
- Clear ownership (validator owns sync responses, exchange owns async events)
- Predictable latency (API always responds quickly)

See [API Communication Design](api-communication-design.md) for complete details.

## Summary

The thread layer is a critical piece of infrastructure that enables:

- High-throughput order processing
- Fair, first-come-first-served execution
- Resilient operation under load

By keeping threads focused on infrastructure concerns and delegating business logic to services, we achieve:

- Testable code (threads and services tested separately)
- Maintainable architecture (clear responsibilities)
- Scalable design (easy to add new processing stages)

Remember: Threads are about **coordination**, not **computation**.
