# Thread Layer Design Principles

This document explains the architectural principles and design philosophy behind the thread layer in the Intern Trading Game. While the architecture documents ([v3](../architecture-v3.md) and [v4](../architecture-v4.md)) describe *what* the threads do, this document explains *why* they exist, *how* to work with them effectively, and *how* they evolve in a service-oriented architecture.

## Table of Contents

1. [Core Purpose](#core-purpose)
2. [Architectural Principles](#architectural-principles)
3. [The Producer-Consumer Pattern](#the-producer-consumer-pattern)
4. [Separation of Concerns](#separation-of-concerns)
5. [Testing Philosophy](#testing-philosophy)
6. [Common Patterns](#common-patterns)
7. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
8. [Threading in Service-Oriented Architecture](#threading-in-service-oriented-architecture)
9. [Future Evolution](#future-evolution-microservices-and-beyond)

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
    orders_this_second[team_id] += 1
```

### 5. Response Coordination

Use proper coordination services instead of global state. See [Order Response Coordination](order-response-coordination.md) for the correct pattern:

```python
# Good: Coordination service
coordinator = OrderResponseCoordinator(config)
registration = coordinator.register_request(team_id)
# ... in thread ...
coordinator.notify_completion(request_id, api_response)
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

## Threading in Service-Oriented Architecture

As we transition from a monolithic design to a service-oriented architecture (v4), the threading model evolves while maintaining the same core principles. This section explains how threading works in a world of services, both in our current monolith and future microservices.

### Current State: Functional Threading in a Monolith

In our current implementation, threads are organized by function, not by service ownership:

```python
# Current thread organization (functional grouping)
validator_thread()      # Validates orders from any service
matching_thread()       # Matches orders in the exchange
trade_publisher()       # Publishes trades, updates positions
websocket_thread()      # Delivers messages to clients
```

**Key Characteristics**:

- Threads cross service boundaries freely
- Services are stateless helpers used by threads
- Queues connect processing stages, not services
- Shared state (positions, orders) accessed by multiple threads

This is a perfectly valid design for a monolith! The threads act as a pipeline processing orders through various stages.

### Transition State: Aligning Threads with Services

As we strengthen service boundaries, threads naturally align with service responsibilities:

```python
# Thread-to-service alignment
class ExchangeService:
    """Owns order matching domain"""
    threads = [
        exchange_validator_thread,  # Validates exchange rules
        exchange_matcher_thread,    # Matches orders
    ]

class PositionService:
    """Owns position tracking domain"""
    threads = [
        position_tracker_thread,    # Consumes trades, updates positions
    ]

class MarketDataService:
    """Owns market simulation domain"""
    threads = [
        price_generator_thread,     # Generates prices
        market_publisher_thread,    # Publishes market data
    ]
```

**Benefits of Alignment**:

- Clear ownership: each thread belongs to one service
- Natural boundaries: threads don't cross service domains
- Easier extraction: services can be moved with their threads
- Better encapsulation: services hide their threading complexity

### Service Threading Patterns

#### Pattern 1: Service as Queue Processor
Services own threads that process specific queues:

```python
class PositionService:
    def __init__(self):
        self.positions = {}  # Service-owned state
        self.lock = RLock()  # Service-owned synchronization

    def start_processing(self):
        """Start service threads"""
        Thread(target=self._process_trades, daemon=True).start()

    def _process_trades(self):
        """Service-owned thread processes trades"""
        while True:
            trade = trade_queue.get()
            with self.lock:
                self._update_position(trade)
                self._check_limits(trade)
                self._publish_update(trade)
```

#### Pattern 2: Service with Internal Pipeline
Services can have multiple threads forming an internal pipeline:

```python
class MarketDataService:
    def __init__(self):
        # Internal queues for service pipeline
        self.raw_price_queue = Queue()
        self.validated_price_queue = Queue()

    def start_processing(self):
        # Multiple threads within service
        Thread(target=self._generate_prices).start()
        Thread(target=self._validate_prices).start()
        Thread(target=self._publish_prices).start()
```

#### Pattern 3: Service as API Server
Services expose APIs while using threads internally:

```python
class PositionService:
    def get_position(self, team_id: str, instrument: str) -> int:
        """Synchronous API hides threading complexity"""
        with self.lock:
            return self.positions.get(team_id, {}).get(instrument, 0)

    def would_exceed_limit(self, order: Order) -> bool:
        """Called by other services via API"""
        with self.lock:
            current = self.get_position(order.team_id, order.instrument)
            new_position = current + order.signed_quantity()
            return abs(new_position) > self.limits[order.team_id]
```

### Inter-Service Communication Evolution

#### Current: Direct Queue Sharing
```python
# Services share queues directly
trade_queue = Queue()  # Shared between Exchange and Position services

# Exchange service writes
trade_queue.put(trade)

# Position service reads
trade = trade_queue.get()
```

#### Better: Service-Owned Queues
```python
# Each service owns its input queues
class PositionService:
    def __init__(self):
        self.trade_input_queue = Queue()  # Service owns this

    def submit_trade(self, trade):
        """API method for other services"""
        self.trade_input_queue.put(trade)
```

#### Future: Event Bus or Message Broker
```python
# Services publish/subscribe to events
class ExchangeService:
    def _publish_trade(self, trade):
        event_bus.publish('trade.executed', trade)

class PositionService:
    def __init__(self):
        event_bus.subscribe('trade.executed', self._handle_trade)
```

### State Management in Service Threading

#### Anti-Pattern: Shared Mutable State
```python
# BAD: Global state accessed by multiple services
global_positions = {}  # Shared between services
positions_lock = RLock()  # Global lock

def update_position(trade):
    with positions_lock:  # Any thread can grab this
        global_positions[trade.team][trade.instrument] += trade.quantity
```

#### Pattern: Service-Owned State
```python
# GOOD: Each service owns its state
class PositionService:
    def __init__(self):
        self._positions = {}  # Private to service
        self._lock = RLock()  # Private lock

    def update_position(self, trade):
        """Only position service threads can update"""
        with self._lock:
            self._positions[trade.team][trade.instrument] += trade.quantity
```

### Thread Safety in Services

#### Rule 1: Services Own Their Locks
Each service should manage its own synchronization:

```python
class Service:
    def __init__(self):
        self._state = {}
        self._lock = RLock()  # Service-private lock

    def read_operation(self):
        with self._lock:  # Service controls locking
            return self._state.copy()
```

#### Rule 2: Minimize Lock Scope
Services should minimize time holding locks:

```python
class PositionService:
    def process_trade(self, trade):
        # Compute outside lock
        update = self._calculate_update(trade)

        # Hold lock only for state mutation
        with self._lock:
            self._apply_update(update)

        # Publish outside lock
        self._publish_event(update)
```

#### Rule 3: Avoid Lock Ordering Issues
When services interact, avoid deadlocks:

```python
# BAD: Can deadlock if services call each other
class ServiceA:
    def method_a(self):
        with self.lock_a:
            service_b.method_b()  # Danger!

class ServiceB:
    def method_b(self):
        with self.lock_b:
            service_a.method_a()  # Deadlock!
```

### Testing Service Threading

#### Unit Testing Threads
```python
def test_position_service_threading():
    # Create service with mock dependencies
    mock_trade_source = MockQueue()
    service = PositionService(trade_source=mock_trade_source)

    # Start service threads
    service.start()

    # Inject test data
    test_trade = Trade(team='TEAM1', instrument='SPX', quantity=10)
    mock_trade_source.put(test_trade)

    # Verify processing (with timeout)
    assert wait_for(lambda: service.get_position('TEAM1', 'SPX') == 10)
```

#### Integration Testing
```python
def test_service_integration():
    # Create real services
    exchange = ExchangeService()
    positions = PositionService()

    # Wire them together
    exchange.trade_publisher = positions.trade_consumer

    # Test end-to-end
    order = Order(team='TEAM1', instrument='SPX', quantity=10)
    exchange.submit_order(order)

    # Verify entire flow
    assert wait_for(lambda: positions.get_position('TEAM1', 'SPX') == 10)
```

### Performance Considerations

#### Service Threading Overhead

1. **Monolith (Current)**:

   - Minimal overhead: direct function calls
   - Shared memory: no serialization
   - Single process: CPU cache friendly

2. **Service-Oriented Monolith**:

   - Small overhead: service method calls
   - Still shared memory: fast data passing
   - Better isolation: fewer lock conflicts

3. **Microservices (Future)**:

   - Network overhead: RPC/HTTP calls
   - Serialization cost: data marshaling
   - But: independent scaling, fault isolation

#### Optimization Strategies

1. **Batch Operations**:
```python
class PositionService:
    def update_positions_batch(self, trades: List[Trade]):
        """Process multiple trades in one lock acquisition"""
        with self._lock:
            for trade in trades:
                self._update_single(trade)
```

2. **Read-Write Locks**:
```python
from threading import RWLock  # If available

class PositionService:
    def __init__(self):
        self._rwlock = RWLock()

    def read_position(self):
        with self._rwlock.read():  # Multiple readers OK
            return self._positions.copy()

    def update_position(self):
        with self._rwlock.write():  # Exclusive access
            self._positions[key] = value
```

3. **Lock-Free Structures** (Advanced):
```python
from concurrent.atomic import AtomicLong

class PositionService:
    def __init__(self):
        # For simple counters, atomic operations
        self._trade_count = AtomicLong(0)

    def increment_trades(self):
        self._trade_count.increment()  # No lock needed
```

## Future Evolution: Microservices and Beyond

### Stage 1: Service-Oriented Monolith (Current Goal)

- Services with clear boundaries
- Thread ownership by service
- Internal queues and locks
- Shared process, separate concerns

### Stage 2: Modular Monolith

- Services in separate modules/packages
- Well-defined service APIs
- Could run services in-process or out
- Database per service (logical separation)

### Stage 3: Selective Extraction

- Extract high-value services first (e.g., Position Service)
- Keep core exchange as monolith (performance)
- Mixed deployment: some services remote
- Use async messaging between services

### Stage 4: Full Microservices

- All services independently deployed
- Service mesh for communication
- Distributed tracing and monitoring
- Each service chooses its tech stack

### Threading in Each Stage

**Monolith**: Threads coordinate pipeline stages
**Service-Oriented**: Threads owned by services
**Modular**: Services hide threading behind APIs
**Microservices**: Each service has internal threading

### Key Principles for Evolution

1. **Start Simple**: Don't over-engineer early
2. **Maintain Performance**: Measure before distributing
3. **Evolve Gradually**: One service at a time
4. **Keep Options Open**: Design for future flexibility

### Conclusion

Threading in a service-oriented architecture is about:

- **Ownership**: Services own their threads
- **Encapsulation**: Threading is an implementation detail
- **Evolution**: From shared threads to service threads
- **Performance**: Balance isolation with efficiency

The journey from functional threads to service-owned threads is gradual and should be driven by real needs, not architectural purity. Our current threading model is a solid foundation that can evolve as the system grows.

## Navigation

← Back to [Technical Docs](../index.md) | [Architecture v4](../architecture-v4.md) →
