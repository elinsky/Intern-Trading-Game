"""Integration tests for config-driven validator creation."""

from pathlib import Path

from intern_trading_game.domain.exchange.models.order import (
    Order,
    OrderSide,
    OrderType,
)
from intern_trading_game.domain.exchange.validation.interfaces import (
    ValidationContext,
)
from intern_trading_game.infrastructure.config.loader import ConfigLoader
from intern_trading_game.infrastructure.factories.validator_factory import (
    ValidatorFactory,
)


class TestValidatorConfigIntegration:
    """Test full integration of config-driven validator."""

    def test_validator_from_default_config(self):
        """Test creating and using validator from default config.

        Given - Default config with market maker constraints
        When - Validator is created and validates orders
        Then - Constraints are properly enforced
        """
        # Given - Load default config
        config_path = Path("config/default.yaml")
        loader = ConfigLoader(config_path)
        validator = ValidatorFactory.create_from_config(loader)

        # When - Validate a valid order
        valid_order = Order(
            trader_id="MM1",
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=10,
            price=100.0,
        )

        context = ValidationContext(
            order=valid_order,
            trader_id="MM1",
            trader_role="market_maker",
            current_positions={"SPX_4500_CALL": 0},
            orders_this_second=0,
        )

        result = validator.validate_order(context)

        # Then - Order should be accepted
        assert result.status == "accepted"

    def test_validator_rejects_invalid_instrument(self):
        """Test validator rejects instruments not allowed for role.

        Given - Market maker with allowed instruments
        When - Order for non-allowed instrument
        Then - Order is rejected
        """
        # Given - Load default config
        config_path = Path("config/default.yaml")
        loader = ConfigLoader(config_path)
        validator = ValidatorFactory.create_from_config(loader)

        # When - Order for non-allowed instrument
        invalid_order = Order(
            trader_id="MM1",
            instrument_id="SPY_450_CALL",  # Not in allowed list
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=10,
            price=50.0,
        )

        context = ValidationContext(
            order=invalid_order,
            trader_id="MM1",
            trader_role="market_maker",
            current_positions={},
            orders_this_second=0,
        )

        result = validator.validate_order(context)

        # Then - Order should be rejected
        assert result.status == "rejected"
        assert result.error_code == "INVALID_INSTRUMENT"
        assert "not found" in result.error_message

    def test_validator_enforces_position_limits(self):
        """Test validator enforces position limits from config.

        Given - Market maker with ±50 position limit
        When - Order would breach position limit
        Then - Order is rejected
        """
        # Given - Load default config
        config_path = Path("config/default.yaml")
        loader = ConfigLoader(config_path)
        validator = ValidatorFactory.create_from_config(loader)

        # When - Order that would breach limit
        breach_order = Order(
            trader_id="MM1",
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=30,  # Would put position at 75
            price=100.0,
        )

        context = ValidationContext(
            order=breach_order,
            trader_id="MM1",
            trader_role="market_maker",
            current_positions={"SPX_4500_CALL": 45},  # Already near limit
            orders_this_second=0,
        )

        result = validator.validate_order(context)

        # Then - Order should be rejected
        assert result.status == "rejected"
        assert result.error_code == "MM_POS_LIMIT"
        assert "Position exceeds ±50" in result.error_message

    def test_validator_with_test_config(self):
        """Test validator with alternative test configuration.

        Given - Test config with different constraints
        When - Validator created from test config
        Then - Test constraints are enforced
        """
        # Given - Load test config
        config_path = Path("config/test-constraints.yaml")
        loader = ConfigLoader(config_path)
        validator = ValidatorFactory.create_from_config(loader)

        # When - Validate order against test constraints
        test_order = Order(
            trader_id="MM1",
            instrument_id="TEST_100_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=20,
            price=10.0,
        )

        context = ValidationContext(
            order=test_order,
            trader_id="MM1",
            trader_role="market_maker",
            current_positions={
                "TEST_100_CALL": 10
            },  # Would go to 30, exceeding test limit of 25
            orders_this_second=0,
        )

        result = validator.validate_order(context)

        # Then - Should be rejected with test message
        assert result.status == "rejected"
        assert result.error_code == "MM_POS_LIMIT"
        assert "Test position limit ±25" in result.error_message

    def test_no_constraints_for_unknown_role(self):
        """Test validator handles unknown roles gracefully.

        Given - Validator with only market_maker constraints
        When - Order from unknown role
        Then - Order is accepted (no constraints)
        """
        # Given - Default config
        config_path = Path("config/default.yaml")
        loader = ConfigLoader(config_path)
        validator = ValidatorFactory.create_from_config(loader)

        # When - Order from unknown role
        unknown_order = Order(
            trader_id="UNKNOWN1",
            instrument_id="ANY_INSTRUMENT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=1000,
            price=1.0,
        )

        context = ValidationContext(
            order=unknown_order,
            trader_id="UNKNOWN1",
            trader_role="unknown_role",  # Not configured
            current_positions={},
            orders_this_second=0,
        )

        result = validator.validate_order(context)

        # Then - Should be accepted (no constraints)
        assert result.status == "accepted"
