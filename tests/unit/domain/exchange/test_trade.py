# Copyright © 2025 Brian Elinsky — All rights reserved.
# Proprietary software - see LICENSE file for details.

"""Unit tests for the Trade model."""

from datetime import datetime

import pytest

from intern_trading_game.domain.exchange.core.trade import Trade
from tests.fixtures import TEST_PRICES, create_test_trade


class TestTradeValidation:
    """Test Trade model validation rules."""

    @pytest.mark.parametrize(
        "invalid_params,expected_error",
        [
            ({"price": 0}, "Trade price must be positive"),
            ({"price": -100}, "Trade price must be positive"),
            ({"quantity": 0}, "Trade quantity must be positive"),
            ({"quantity": -10}, "Trade quantity must be positive"),
            (
                {"aggressor_side": "invalid"},
                "Aggressor side must be 'buy' or 'sell'",
            ),
            (
                {"aggressor_side": "BUY"},
                "Aggressor side must be 'buy' or 'sell'",
            ),
        ],
    )
    def test_trade_validation(self, invalid_params, expected_error):
        """
        Test that Trade validates all required business rules.

        Given valid default parameters for a trade
        When creating a trade with one invalid parameter
        Then the trade creation should fail with appropriate error message
        """
        # Given - Valid base parameters for an options trade
        base_params = {
            "instrument_id": "SPX_4500_CALL",
            "buyer_id": "MM_001",
            "seller_id": "HF_002",
            "price": 128.50,
            "quantity": 10,
            "buyer_order_id": "BUY_123",
            "seller_order_id": "SELL_456",
            "aggressor_side": "buy",
        }

        # When - Override with invalid parameter
        params = {**base_params, **invalid_params}

        # Then - Trade creation should fail with expected error
        with pytest.raises(ValueError, match=expected_error):
            Trade(**params)

    def test_trade_rejects_fractional_quantity(self):
        """
        Test that Trade rejects fractional quantities.

        Options contracts trade in whole units only. Fractional
        contracts are not allowed in real markets.

        Given trade parameters with fractional quantity
        When creating a trade
        Then the trade should be rejected
        """
        # Given - Trade with fractional quantity (invalid for options)
        with pytest.raises(
            ValueError, match="Trade quantity must be a whole number"
        ):
            Trade(
                instrument_id="SPX_4500_CALL",
                buyer_id="MM_001",
                seller_id="HF_002",
                price=128.50,
                quantity=10.5,  # Fractional contracts not allowed
                buyer_order_id="BUY_123",
                seller_order_id="SELL_456",
                aggressor_side="buy",
            )

    def test_valid_trade_creation(self):
        """
        Test successful creation of a valid trade.

        Given all valid parameters for an options trade
        When creating a trade
        Then the trade should be created with all fields set correctly
        """
        # Given - Valid options trade parameters
        # Market maker sold 10 SPX calls at 128.50 to hedge fund
        # Hedge fund was aggressor (crossed the spread to buy)
        trade = Trade(
            instrument_id="SPX_4500_CALL",
            buyer_id="HF_002",
            seller_id="MM_001",
            price=128.50,
            quantity=10,
            buyer_order_id="BUY_789",
            seller_order_id="SELL_456",
            aggressor_side="buy",  # HF crossed spread
        )

        # Then - All fields should be set correctly
        assert trade.instrument_id == "SPX_4500_CALL"
        assert trade.buyer_id == "HF_002"
        assert trade.seller_id == "MM_001"
        assert trade.price == 128.50
        assert trade.quantity == 10
        assert trade.aggressor_side == "buy"
        assert isinstance(trade.timestamp, datetime)
        assert isinstance(trade.trade_id, str)


class TestTradeBusinessLogic:
    """Test Trade business logic and calculations."""

    def test_trade_value_calculation(self):
        """
        Test trade value calculation.

        Trade value represents the total economic value exchanged.
        For options, this is price * quantity * multiplier (usually 100).
        However, this model stores just price * quantity.

        Given a trade with known price and quantity
        When accessing the value property
        Then it should return price * quantity
        """
        # Given - SPX option trade at typical ask price for 10 contracts
        trade = create_test_trade(
            price=TEST_PRICES["typical_ask"],
            quantity=10,
            buyer_id="HF_002",
            seller_id="MM_001",
            aggressor_side="buy",  # HF lifted the offer
        )

        # When/Then - Value should be price * quantity
        assert trade.value == 1005.0  # $100.50 * 10 contracts

    def test_trade_to_dict(self):
        """
        Test trade serialization to dictionary.

        The to_dict method is used for API responses and persistence.
        It must include all trade fields plus calculated value.

        Given a complete trade
        When converting to dictionary
        Then all fields should be present and properly formatted
        """
        # Given - A completed options trade with known timestamp
        timestamp = datetime(2025, 1, 13, 14, 30, 0)
        trade = create_test_trade(
            instrument_id="SPX_4500_PUT",
            buyer_id="ARB_003",
            seller_id="MM_001",
            price=95.25,
            quantity=5,
            buyer_order_id="BUY_999",
            seller_order_id="SELL_888",
            aggressor_side="sell",  # MM hit the bid
            timestamp=timestamp,
            trade_id="TRADE_12345",
        )

        # When - Convert to dictionary
        trade_dict = trade.to_dict()

        # Then - All fields should be present
        assert trade_dict == {
            "trade_id": "TRADE_12345",
            "instrument_id": "SPX_4500_PUT",
            "buyer_id": "ARB_003",
            "seller_id": "MM_001",
            "price": 95.25,
            "quantity": 5,
            "aggressor_side": "sell",
            "timestamp": "2025-01-13T14:30:00",
            "buyer_order_id": "BUY_999",
            "seller_order_id": "SELL_888",
            "value": 476.25,  # 95.25 * 5
        }

    def test_aggressor_side_preserved(self):
        """
        Test that aggressor side is correctly preserved.

        Aggressor side determines maker/taker for fee calculation.
        This is critical business logic that must be preserved.

        Given trades with different aggressor sides
        When accessing the aggressor_side field
        Then it should match what was provided at creation
        """
        # Given - Buy aggressor (taker buys from maker)
        buy_aggressor = create_test_trade(
            instrument_id="SPX_4500_CALL",
            buyer_id="HF_002",  # Taker
            seller_id="MM_001",  # Maker
            price=128.50,
            quantity=10,
            buyer_order_id="BUY_123",
            seller_order_id="SELL_456",
            aggressor_side="buy",
        )

        # Given - Sell aggressor (taker sells to maker)
        sell_aggressor = create_test_trade(
            instrument_id="SPX_4500_CALL",
            buyer_id="MM_001",  # Maker
            seller_id="HF_002",  # Taker
            price=128.00,
            quantity=10,
            buyer_order_id="BUY_789",
            seller_order_id="SELL_012",
            aggressor_side="sell",
        )

        # Then - Aggressor side should be preserved
        assert buy_aggressor.aggressor_side == "buy"
        assert sell_aggressor.aggressor_side == "sell"
