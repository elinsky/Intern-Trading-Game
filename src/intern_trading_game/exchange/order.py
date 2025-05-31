"""
Order module for the Intern Trading Game.

This module defines the Order class, which represents a trading order.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    """Enum representing the side of an order (buy or sell)."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Enum representing the type of order (limit or market)."""

    LIMIT = "limit"
    MARKET = "market"


@dataclass
class Order:
    """
    Represents a trading order in the exchange.

    Attributes:
        instrument_id (str): The ID of the instrument being traded.
        side (OrderSide): Whether this is a buy or sell order.
        quantity (float): The quantity to be traded.
        price (Optional[float]): The limit price (None for market orders).
        trader_id (str): The ID of the trader submitting the order.
        order_id (str): A unique identifier for this order.
        timestamp (datetime): When the order was created.
        order_type (OrderType): The type of order (limit or market).
        remaining_quantity (float): The unfilled quantity of the order.
    """

    instrument_id: str
    side: OrderSide
    quantity: float
    trader_id: str
    price: Optional[float] = None
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    order_type: OrderType = OrderType.LIMIT
    remaining_quantity: float = field(init=False)

    def __post_init__(self):
        """Validate and initialize the order after creation."""
        # Convert string side to enum if needed
        if isinstance(self.side, str):
            self.side = OrderSide(self.side.lower())

        # Determine order type based on price
        if self.price is None:
            self.order_type = OrderType.MARKET
        else:
            self.order_type = OrderType.LIMIT

        # Validate price for limit orders
        if self.order_type == OrderType.LIMIT and (
            self.price is None or self.price <= 0
        ):
            raise ValueError("Limit orders must have a positive price")

        # Validate quantity
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")

        # Initialize remaining quantity
        self.remaining_quantity = self.quantity

    @property
    def is_buy(self) -> bool:
        """
        Check if this is a buy order.

        Returns:
            bool: True if this is a buy order, False otherwise.
        """
        return self.side == OrderSide.BUY

    @property
    def is_sell(self) -> bool:
        """
        Check if this is a sell order.

        Returns:
            bool: True if this is a sell order, False otherwise.
        """
        return self.side == OrderSide.SELL

    @property
    def is_market_order(self) -> bool:
        """
        Check if this is a market order.

        Returns:
            bool: True if this is a market order, False otherwise.
        """
        return self.order_type == OrderType.MARKET

    @property
    def is_limit_order(self) -> bool:
        """
        Check if this is a limit order.

        Returns:
            bool: True if this is a limit order, False otherwise.
        """
        return self.order_type == OrderType.LIMIT

    @property
    def is_filled(self) -> bool:
        """
        Check if this order is completely filled.

        Returns:
            bool: True if the order is filled, False otherwise.
        """
        return self.remaining_quantity == 0

    def fill(self, quantity: float) -> None:
        """
        Mark a quantity of this order as filled.

        Args:
            quantity (float): The quantity that was filled.

        Raises:
            ValueError: If the quantity is invalid or exceeds the remaining
                quantity.
        """
        if quantity <= 0:
            raise ValueError("Fill quantity must be positive")

        if quantity > self.remaining_quantity:
            raise ValueError(
                f"Fill quantity {quantity} exceeds remaining quantity "
                f"{self.remaining_quantity}"
            )

        self.remaining_quantity -= quantity
