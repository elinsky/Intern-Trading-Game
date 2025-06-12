# API Reference

Complete API documentation for the Intern Trading Game. This section provides detailed specifications for all APIs, endpoints, and interfaces.

## Core APIs

### Exchange Interface

- **[API Overview](api-overview.md)** - High-level overview of the API architecture and design principles
- **[Exchange API](exchange-api.md)** - Core exchange interface for order management and market data

### Communication Protocols

- **[REST API](rest-api.md)** - HTTP REST endpoints for order submission, account info, and historical data
- **[WebSocket API](websocket-api.md)** - Real-time streaming API for market data and order updates

### Validation & Rules

- **[Validation API](validation-api.md)** - Order validation rules and error codes
- **[Math Examples](math-examples.md)** - Mathematical formulas and calculations used in the system

## API Quick Reference

### REST Endpoints

- `POST /api/orders` - Submit new order
- `GET /api/orders/{id}` - Get order status
- `DELETE /api/orders/{id}` - Cancel order
- `GET /api/market-data` - Get current market data
- `GET /api/positions` - Get current positions

[Full REST API Documentation →](rest-api.md)

### WebSocket Channels

- `market-data` - Real-time price updates
- `order-updates` - Order status changes
- `trades` - Executed trades feed
- `positions` - Position updates

[Full WebSocket API Documentation →](websocket-api.md)

## Generated API Docs

The following API documentation is auto-generated from source code:

- Order Book API
- Order API
- Trade API
- Venue API
- Instrument API

## Integration Examples

Looking for integration examples? Check out:

- **[How to Submit Orders](../how-to/how-to-submit-orders.md)** - Practical order submission guide
- **[Market Maker Tutorial](../tutorials/market-maker-tutorial.md)** - Complete bot implementation

## Navigation

← Back to [Technical Docs](../index.md) | [How-To Guides](../how-to/index.md) →
