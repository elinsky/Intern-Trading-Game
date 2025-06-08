# API Integration Tests

This directory contains comprehensive integration tests for the REST and WebSocket APIs with all threads running.

## Test Organization

### test_api.py - Full API Test Suite
Comprehensive tests covering all API functionality:
- **Authentication** (`TestAuthentication`) - Team registration and API key validation
- **Order Submission** (`TestOrderSubmission`) - Limit/market orders, validation, constraints
- **Position Tracking** (`TestPositionTracking`) - Position queries and team isolation
- **Thread Safety** (`TestThreadSafety`) - Concurrent order processing
- **Health Checks** (`TestHealthCheck`) - System status endpoints

### test_api_minimal.py - Minimal Test Suite
Essential tests proving the integration works:
- End-to-end order submission flow
- Position tracking after trades
- Authentication and authorization

### test_order_cancel_api.py - Order Cancellation
Dedicated tests for order cancellation flows:
- Successful cancellation
- Ownership validation
- FIFO processing with other orders

### test_websocket_integration.py - WebSocket Tests
Real-time update testing:
- Connection lifecycle
- Order acknowledgments
- Trade execution reports
- Position snapshots

## Running Tests

```bash
# Run all API integration tests
pytest tests/integration/api/ -v

# Run specific test class
pytest tests/integration/api/test_api.py::TestAuthentication -v

# Run with markers
pytest -m "integration and api" -v

# Run without slow tests
pytest -m "integration and api and not slow" -v
```

## Test Requirements

These tests require:
- Full FastAPI application with lifespan management
- All processing threads (validator, matching, publisher, websocket)
- In-memory exchange and order books
- Thread-safe state management

The `api_context` fixture in `conftest.py` handles all setup and teardown.

## Common Issues

1. **Thread timing** - Some tests may need small delays for thread synchronization
2. **State cleanup** - Each test should start with clean state (handled by fixture)
3. **Concurrent tests** - Thread pool tests may interfere with daemon threads

## Architecture Notes

Tests follow the protocol vs business validation distinction:
- **Protocol errors** (missing fields) -> HTTP 4xx
- **Business validation** (invalid instrument) -> HTTP 200 with rejected order
