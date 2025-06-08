# Integration Test Structure

This directory contains integration tests organized by testing scope and abstraction level.

## Test Organization

### `/api/` - API Integration Tests
Tests the REST and WebSocket APIs with all threads running.

- **Scope**: Full API with in-memory components
- **Speed**: Slow (requires all threads)
- **When to run**: On pull requests

Examples:

- `test_api.py` - REST API endpoints
- `test_order_cancel_api.py` - Order cancellation flows
- `test_websocket_integration.py` - WebSocket message delivery

### `/services/` - Service Integration Tests
Tests direct integrations between services without threads.

- **Scope**: Service-to-service interactions
- **Speed**: Fast (no threading overhead)
- **When to run**: Frequently during development

Examples:

- Order validation with constraints
- Trade processing with fee calculation
- Position updates with thread safety

### `/pipelines/` - Pipeline Integration Tests
Tests individual processing pipelines with queues.

- **Scope**: Single thread with real queues
- **Speed**: Medium
- **When to run**: Before commits

Examples:

- Order validation pipeline
- Matching engine pipeline
- Trade publishing pipeline

### `/system/` - System Integration Tests
Tests complete end-to-end scenarios.

- **Scope**: Full system including persistence
- **Speed**: Very slow
- **When to run**: Before releases

Examples:

- Multi-tick trading scenarios
- Volatility regime changes
- Database persistence and recovery

## Running Tests

```bash
# Run all integration tests
pytest tests/integration/

# Run by level
pytest tests/integration/services/     # Fast
pytest tests/integration/pipelines/    # Medium
pytest tests/integration/api/          # Slow
pytest tests/integration/system/       # Very slow

# Run with markers
pytest -m "integration and not slow"
pytest -m "integration and api"
```

## Test Fixtures

See `conftest.py` for shared fixtures available at each level:

- `service_context` - Minimal service setup
- `pipeline_context` - Single pipeline with queues
- `api_context` - Full API with threads
- `system_context` - Complete system

## Writing New Tests

1. Choose the appropriate directory based on what you're testing
2. Use the smallest scope that covers your test case
3. Leverage shared fixtures from `conftest.py`
4. Follow the Given-When-Then pattern with business context
5. Make tests deterministic (control time, randomness)
6. Test both success and error paths
