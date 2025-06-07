# Exchange API Reference

This document provides a comprehensive reference for the Intern Trading Game exchange API.

## Core Components

The exchange system consists of the following core components:

| Component | Description |
|-----------|-------------|
| `ExchangeVenue` | The main exchange venue that handles order submission and matching |
| `OrderBook` | Maintains the order book for a single instrument |
| `Order` | Represents a trading order (buy or sell) |
| `Trade` | Represents an executed trade between two orders |
| `Instrument` | Represents a tradeable instrument (stock or option) |

## ExchangeVenue

The `ExchangeVenue` class is the main entry point for interacting with the exchange.

### Methods

#### `list_instrument(instrument: Instrument) -> None`

Register an instrument with the exchange.

**Parameters:**
- `instrument` (Instrument): The instrument to register.

**Raises:**
- `ValueError`: If an instrument with the same ID already exists.

#### `submit_order(order: Order) -> OrderResult`

Submit an order to the exchange.

**Parameters:**
- `order` (Order): The order to submit.

**Returns:**
- `OrderResult`: The result of the order submission.

**Raises:**
- `ValueError`: If the instrument doesn't exist or the order ID is already in use.

#### `cancel_order(order_id: str, trader_id: str) -> bool`

Cancel an order.

**Parameters:**
- `order_id` (str): The ID of the order to cancel.
- `trader_id` (str): The ID of the trader who owns the order.

**Returns:**
- `bool`: True if the order was cancelled, False otherwise.

**Raises:**
- `ValueError`: If the trader doesn't own the order.

#### `get_order_book(instrument_id: str) -> Optional[OrderBook]`

Get the order book for an instrument.

**Parameters:**
- `instrument_id` (str): The ID of the instrument.

**Returns:**
- `Optional[OrderBook]`: The order book, or None if the instrument doesn't exist.

#### `get_trade_history(instrument_id: str, limit: int = 10) -> List[Trade]`

Get the trade history for an instrument.

**Parameters:**
- `instrument_id` (str): The ID of the instrument.
- `limit` (int, optional): The maximum number of trades to return. Defaults to 10.

**Returns:**
- `List[Trade]`: The most recent trades, newest first.

**Raises:**
- `ValueError`: If the instrument doesn't exist.

#### `get_market_summary(instrument_id: str) -> Dict[str, object]`

Get a summary of the current market state for an instrument.

**Parameters:**
- `instrument_id` (str): The ID of the instrument.

**Returns:**
- `Dict`: A dictionary containing the best bid/ask and recent trades.

**Raises:**
- `ValueError`: If the instrument doesn't exist.

#### `get_all_instruments() -> List[Instrument]`

Get all instruments listed on the exchange.

**Returns:**
- `List[Instrument]`: All registered instruments.

## Order

The `Order` class represents a trading order.

### Attributes

- `instrument_id` (str): The ID of the instrument being traded.
- `side` (OrderSide): Whether this is a buy or sell order.
- `quantity` (float): The quantity to be traded.
- `price` (Optional[float]): The limit price (None for market orders).
- `trader_id` (str): The ID of the trader submitting the order.
- `order_id` (str): A unique identifier for this order.
- `timestamp` (datetime): When the order was created.
- `order_type` (OrderType): The type of order (limit or market).
- `client_order_id` (Optional[str]): Client's reference ID for order tracking.
- `remaining_quantity` (float): The unfilled quantity of the order.

### Methods

#### `fill(quantity: float) -> None`

Mark a quantity of this order as filled.

**Parameters:**
- `quantity` (float): The quantity that was filled.

**Raises:**
- `ValueError`: If the quantity is invalid or exceeds the remaining quantity.

### Properties

- `is_buy` (bool): True if this is a buy order.
- `is_sell` (bool): True if this is a sell order.
- `is_market_order` (bool): True if this is a market order.
- `is_limit_order` (bool): True if this is a limit order.
- `is_filled` (bool): True if this order is completely filled.

## OrderBook

The `OrderBook` class maintains the order book for a single instrument.

### Methods

#### `add_order(order: Order) -> List[Trade]`

Add an order to the book and attempt to match it.

**Parameters:**
- `order` (Order): The order to add.

**Returns:**
- `List[Trade]`: Any trades that were generated.

#### `cancel_order(order_id: str) -> Optional[Order]`

Cancel and remove an order from the book.

**Parameters:**
- `order_id` (str): The ID of the order to cancel.

**Returns:**
- `Optional[Order]`: The cancelled order, or None if not found.

#### `best_bid() -> Optional[Tuple[float, float]]`

Get the best (highest) bid price and quantity.

**Returns:**
- `Optional[Tuple[float, float]]`: (price, quantity) or None if no bids.

#### `best_ask() -> Optional[Tuple[float, float]]`

Get the best (lowest) ask price and quantity.

**Returns:**
- `Optional[Tuple[float, float]]`: (price, quantity) or None if no asks.

#### `depth_snapshot(levels: int = 5) -> Dict[str, List[Tuple[float, float]]]`

Get a snapshot of the order book depth.

**Parameters:**
- `levels` (int, optional): The number of price levels to include. Defaults to 5.

**Returns:**
- `Dict[str, List[Tuple[float, float]]]`: A dictionary with 'bids' and 'asks' keys, each with a list of (price, quantity) tuples.

#### `get_order(order_id: str) -> Optional[Order]`

Get an order from the book by its ID.

**Parameters:**
- `order_id` (str): The ID of the order to get.

**Returns:**
- `Optional[Order]`: The order, or None if not found.

#### `get_recent_trades(limit: int = 10) -> List[Trade]`

Get the most recent trades.

**Parameters:**
- `limit` (int, optional): The maximum number of trades to return. Defaults to 10.

**Returns:**
- `List[Trade]`: The most recent trades, newest first.

## Instrument

The `Instrument` class represents a tradeable instrument.

### Attributes

- `symbol` (str): The unique identifier for the instrument.
- `strike` (Optional[float]): The strike price for options, None for other instruments.
- `expiry` (Optional[str]): The expiration date for options in ISO format (YYYY-MM-DD).
- `option_type` (Optional[str]): The type of option ('call' or 'put'), None for other instruments.
- `underlying` (Optional[str]): The underlying asset symbol for derivatives.

### Properties

- `id` (str): The unique identifier for this instrument (same as symbol).

## Trade

The `Trade` class represents an executed trade.

### Attributes

- `instrument_id` (str): The ID of the instrument that was traded.
- `buyer_id` (str): The ID of the trader who bought.
- `seller_id` (str): The ID of the trader who sold.
- `price` (float): The execution price of the trade.
- `quantity` (float): The quantity that was traded.
- `timestamp` (datetime): When the trade occurred.
- `trade_id` (str): A unique identifier for this trade.
- `buyer_order_id` (str): The ID of the buy order.
- `seller_order_id` (str): The ID of the sell order.
- `aggressor_side` (str): Which side initiated the trade ('buy' or 'sell').

The `aggressor_side` indicates which order crossed the spread to create the trade. This determines maker/taker status for fee calculations - the aggressor is always the taker.

### Properties

- `value` (float): The total value of this trade (price * quantity).

### Methods

#### `to_dict() -> dict`

Convert the trade to a dictionary representation.

**Returns:**
- `dict`: A dictionary containing the trade details.

## OrderResult

The `OrderResult` class represents the result of submitting an order.

### Attributes

- `order_id` (str): The ID of the submitted order.
- `status` (str): The status of the order ('accepted' or 'filled').
- `fills` (List[Trade]): Any trades that were generated.
- `remaining_quantity` (float): The unfilled quantity of the order.
