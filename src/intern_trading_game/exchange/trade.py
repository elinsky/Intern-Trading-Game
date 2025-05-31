"""
Trade module for the Intern Trading Game.

This module defines the Trade class, which represents an executed trade.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Trade:
    """
    Represents an executed trade between two orders.

    Attributes:
        instrument_id (str): The ID of the instrument that was traded.
        buyer_id (str): The ID of the trader who bought.
        seller_id (str): The ID of the trader who sold.
        price (float): The execution price of the trade.
        quantity (float): The quantity that was traded.
        timestamp (datetime): When the trade occurred.
        trade_id (str): A unique identifier for this trade.
        buyer_order_id (str): The ID of the buy order.
        seller_order_id (str): The ID of the sell order.
    """

    instrument_id: str
    buyer_id: str
    seller_id: str
    price: float
    quantity: float
    buyer_order_id: str
    seller_order_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate the trade after creation."""
        if self.price <= 0:
            raise ValueError("Trade price must be positive")

        if self.quantity <= 0:
            raise ValueError("Trade quantity must be positive")

    @property
    def value(self) -> float:
        """
        Calculate the total value of this trade.

        Returns:
            float: The trade value (price * quantity).
        """
        return self.price * self.quantity

    def to_dict(self) -> dict:
        """
        Convert the trade to a dictionary representation.

        Returns:
            dict: A dictionary containing the trade details.
        """
        return {
            "trade_id": self.trade_id,
            "instrument_id": self.instrument_id,
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "price": self.price,
            "quantity": self.quantity,
            "timestamp": self.timestamp.isoformat(),
            "buyer_order_id": self.buyer_order_id,
            "seller_order_id": self.seller_order_id,
            "value": self.value,
        }
