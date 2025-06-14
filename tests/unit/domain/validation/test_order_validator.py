"""Tests for the order validation system.

These tests verify that the constraint-based order validator correctly
enforces trading rules without any hardcoded role-specific logic.
"""

import pytest

from intern_trading_game.domain.exchange.order import Order, OrderSide
from intern_trading_game.domain.interfaces import ValidationContext
from intern_trading_game.domain.validation.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintConfig,
    ConstraintType,
    OrderRateConstraint,
    OrderSizeConstraint,
    OrderTypeConstraint,
    PortfolioLimitConstraint,
    PositionLimitConstraint,
    PriceRangeConstraint,
    get_universal_constraints,
    load_constraints_from_dict,
)


class TestConstraints:
    """Test individual constraint implementations."""

    def test_position_limit_constraint_symmetric(self):
        # Given - A symmetric position limit constraint of ±50
        constraint = PositionLimitConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.POSITION_LIMIT,
            parameters={"max_position": 50, "symmetric": True},
            error_code="POS_LIMIT",
            error_message="Position limit exceeded",
        )

        # When - Checking an order that would result in position of +60
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.BUY,
            quantity=20,
            price=100.0,
            trader_id="MM1",
        )
        context = ValidationContext(
            order=order,
            trader_id="MM1",
            trader_role="market_maker",
            current_positions={"SPX_CALL_4500": 40},
        )

        result = constraint.check(context, config)

        # Then - The constraint rejects the order
        assert not result.is_valid
        assert "60 outside ±50" in result.error_detail

    def test_position_limit_constraint_absolute(self):
        # Given - An absolute position limit constraint of 150
        constraint = PositionLimitConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.POSITION_LIMIT,
            parameters={"max_position": 150, "symmetric": False},
            error_code="POS_LIMIT",
            error_message="Position limit exceeded",
        )

        # When - Checking an order that would result in position of -140
        order = Order(
            instrument_id="SPX_PUT_4400",
            side=OrderSide.SELL,
            quantity=40,
            price=95.0,
            trader_id="HF1",
        )
        context = ValidationContext(
            order=order,
            trader_id="HF1",
            trader_role="hedge_fund",
            current_positions={"SPX_PUT_4400": -100},
        )

        result = constraint.check(context, config)

        # Then - The constraint accepts the order
        assert result.is_valid

    def test_order_size_constraint(self):
        # Given - An order size constraint with min=1, max=500
        constraint = OrderSizeConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.ORDER_SIZE,
            parameters={"min_size": 1, "max_size": 500},
            error_code="SIZE_LIMIT",
            error_message="Order size out of range",
        )

        # When - Checking an order for 600 contracts
        order = Order(
            instrument_id="SPY_CALL_440",
            side=OrderSide.BUY,
            quantity=600,
            price=12.0,
            trader_id="HF1",
        )
        context = ValidationContext(
            order=order,
            trader_id="HF1",
            trader_role="hedge_fund",
        )

        result = constraint.check(context, config)

        # Then - The constraint rejects the order
        assert not result.is_valid
        assert "600 not in [1, 500]" in result.error_detail


class TestOrderValidator:
    """Test the complete order validator."""

    def test_validator_with_multiple_constraints(self):
        # Given - A validator with position and size constraints
        validator = ConstraintBasedOrderValidator()

        constraints = [
            ConstraintConfig(
                constraint_type=ConstraintType.POSITION_LIMIT,
                parameters={"max_position": 50, "symmetric": True},
                error_code="MM_POS_LIMIT",
                error_message="Market maker position limit",
            ),
            ConstraintConfig(
                constraint_type=ConstraintType.ORDER_SIZE,
                parameters={"min_size": 1, "max_size": 1000},
                error_code="MM_SIZE",
                error_message="Market maker order size",
            ),
        ]
        validator.load_constraints("market_maker", constraints)

        # When - Validating an order that satisfies all constraints
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.BUY,
            quantity=25,
            price=100.0,
            trader_id="MM1",
        )
        context = ValidationContext(
            order=order,
            trader_id="MM1",
            trader_role="market_maker",
            current_positions={"SPX_CALL_4500": 20},
        )

        result = validator.validate_order(context)

        # Then - The order is accepted
        assert result.status == "accepted"
        assert result.order_id == order.order_id
        assert result.remaining_quantity == 25

    def test_validator_fail_fast(self):
        # Given - A validator with two constraints
        validator = ConstraintBasedOrderValidator()

        constraints = [
            ConstraintConfig(
                constraint_type=ConstraintType.ORDER_SIZE,
                parameters={"min_size": 100, "max_size": 500},
                error_code="SIZE_ERROR",
                error_message="Order too small",
            ),
            ConstraintConfig(
                constraint_type=ConstraintType.POSITION_LIMIT,
                parameters={"max_position": 10},
                error_code="POS_ERROR",
                error_message="Position too large",
            ),
        ]
        validator.load_constraints("test_role", constraints)

        # When - An order violates the first constraint
        order = Order(
            instrument_id="TEST",
            side=OrderSide.BUY,
            quantity=50,  # Too small
            price=100.0,
            trader_id="TEST1",
        )
        context = ValidationContext(
            order=order,
            trader_id="TEST1",
            trader_role="test_role",
            current_positions={"TEST": 100},  # Would also fail position limit
        )

        result = validator.validate_order(context)

        # Then - Only the first constraint failure is reported
        assert result.status == "rejected"
        assert result.error_code == "SIZE_ERROR"
        assert "50 not in [100, 500]" in result.error_message

    @pytest.mark.parametrize(
        "current_pos,order_side,order_qty,should_accept",
        [
            (0, OrderSide.BUY, 50, True),  # New position within limit
            (40, OrderSide.BUY, 10, True),  # At limit exactly
            (40, OrderSide.BUY, 11, False),  # Over limit
            (-40, OrderSide.SELL, 10, True),  # Negative at limit
            (-40, OrderSide.SELL, 11, False),  # Negative over limit
            (30, OrderSide.SELL, 40, True),  # Flipping position within limit
            (30, OrderSide.SELL, 90, False),  # Flipping position over limit
        ],
    )
    def test_symmetric_position_limits(
        self, current_pos, order_side, order_qty, should_accept
    ):
        # Given - A symmetric position limit of ±50
        validator = ConstraintBasedOrderValidator()
        constraints = [
            ConstraintConfig(
                constraint_type=ConstraintType.POSITION_LIMIT,
                parameters={"max_position": 50, "symmetric": True},
                error_code="MM_POS",
                error_message="Position limit",
            )
        ]
        validator.load_constraints("market_maker", constraints)

        # When - Testing various position scenarios
        order = Order(
            instrument_id="TEST",
            side=order_side,
            quantity=order_qty,
            price=100.0,
            trader_id="MM1",
        )
        context = ValidationContext(
            order=order,
            trader_id="MM1",
            trader_role="market_maker",
            current_positions={"TEST": current_pos},
        )

        result = validator.validate_order(context)

        # Then - Order is accepted/rejected based on resulting position
        if should_accept:
            assert result.status == "accepted"
        else:
            assert result.status == "rejected"
            assert result.error_code == "MM_POS"


class TestConfigurationLoading:
    """Test loading constraints from configuration."""

    def test_load_constraints_from_dict(self):
        # Given - A configuration dict with role-specific constraints
        config = {
            "roles": {
                "market_maker": {
                    "constraints": [
                        {
                            "type": "position_limit",
                            "max_position": 50,
                            "symmetric": True,
                            "error_code": "MM_POS",
                            "error_message": "Position exceeds ±50",
                        },
                        {
                            "type": "order_size",
                            "min_size": 1,
                            "max_size": 1000,
                            "error_code": "MM_SIZE",
                            "error_message": "Invalid order size",
                        },
                    ]
                },
                "hedge_fund": {
                    "constraints": [
                        {
                            "type": "position_limit",
                            "max_position": 150,
                            "symmetric": False,
                            "error_code": "HF_POS",
                            "error_message": "Position exceeds 150",
                        }
                    ]
                },
            }
        }

        # When - Loading constraints from configuration
        role_constraints = load_constraints_from_dict(config)

        # Then - Constraints are correctly parsed
        mm_constraints = role_constraints["market_maker"]
        assert len(mm_constraints) == 2  # Only explicit constraints now

        pos_constraint = next(
            c
            for c in mm_constraints
            if c.constraint_type == ConstraintType.POSITION_LIMIT
        )
        assert pos_constraint.parameters["max_position"] == 50
        assert pos_constraint.parameters["symmetric"] is True
        assert pos_constraint.error_code == "MM_POS"

        # No trading window constraints in new system

    def test_universal_constraints(self):
        # Given - Requesting universal constraints
        constraints = get_universal_constraints()

        # Then - No constraints returned (removed trading window)
        assert len(constraints) == 0

    def test_portfolio_limit_constraint(self):
        # Given - A portfolio limit constraint of 100 total
        constraint = PortfolioLimitConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.PORTFOLIO_LIMIT,
            parameters={"max_total_position": 100},
            error_code="PORTFOLIO_LIMIT",
            error_message="Total portfolio limit exceeded",
        )

        # When - Current positions total 80, order would add 30 more
        order = Order(
            instrument_id="SPX_CALL_4600",
            side=OrderSide.BUY,
            quantity=30,
            price=50.0,
            trader_id="HF1",
        )
        context = ValidationContext(
            order=order,
            trader_id="HF1",
            trader_role="hedge_fund",
            current_positions={
                "SPX_CALL_4500": 40,
                "SPX_PUT_4400": -30,  # Absolute value = 30
                "SPY_CALL_440": 10,
            },  # Total absolute = 80
        )

        result = constraint.check(context, config)

        # Then - The constraint rejects (80 + 30 = 110 > 100)
        assert not result.is_valid
        assert "110 would exceed 100" in result.error_detail

    def test_portfolio_limit_reducing_position(self):
        # Given - A portfolio limit constraint
        constraint = PortfolioLimitConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.PORTFOLIO_LIMIT,
            parameters={"max_total_position": 100},
            error_code="PORTFOLIO_LIMIT",
            error_message="Total portfolio limit exceeded",
        )

        # When - Order reduces existing position
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.SELL,  # Selling reduces long position
            quantity=20,
            price=100.0,
            trader_id="HF1",
        )
        context = ValidationContext(
            order=order,
            trader_id="HF1",
            trader_role="hedge_fund",
            current_positions={
                "SPX_CALL_4500": 50,  # Will reduce to 30
                "SPX_PUT_4400": 40,
            },  # Total was 90, will be 70
        )

        result = constraint.check(context, config)

        # Then - The constraint accepts (reducing position)
        assert result.is_valid

    def test_order_rate_constraint(self):
        # Given - Rate limit of 10 orders per second
        constraint = OrderRateConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.ORDER_RATE,
            parameters={"max_orders_per_second": 10},
            error_code="RATE_LIMIT",
            error_message="Order rate limit exceeded",
        )

        # When - Already submitted 10 orders this second
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.BUY,
            quantity=5,
            price=100.0,
            trader_id="MM1",
        )
        context = ValidationContext(
            order=order,
            trader_id="MM1",
            trader_role="market_maker",
            orders_this_second=10,
        )

        result = constraint.check(context, config)

        # Then - The constraint rejects
        assert not result.is_valid
        assert "Already submitted 10 orders this second" in result.error_detail

    @pytest.mark.parametrize(
        "orders_submitted,should_accept",
        [
            (0, True),  # First order
            (9, True),  # At limit minus one
            (10, False),  # At limit
            (15, False),  # Over limit
        ],
    )
    def test_order_rate_scenarios(self, orders_submitted, should_accept):
        # Given - Rate limit of 10 orders per second
        constraint = OrderRateConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.ORDER_RATE,
            parameters={"max_orders_per_second": 10},
            error_code="RATE_LIMIT",
            error_message="Order rate limit exceeded",
        )

        # When - Testing various submission counts
        order = Order(
            instrument_id="TEST",
            side=OrderSide.BUY,
            quantity=1,
            price=100.0,
            trader_id="TEST1",
        )
        context = ValidationContext(
            order=order,
            trader_id="TEST1",
            trader_role="test_role",
            orders_this_second=orders_submitted,
        )

        result = constraint.check(context, config)

        # Then - Accept/reject based on rate
        assert result.is_valid == should_accept

    def test_order_type_constraint(self):
        # Given - Only limit and market orders allowed
        constraint = OrderTypeConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.ORDER_TYPE_ALLOWED,
            parameters={"allowed_types": ["limit", "market"]},
            error_code="INVALID_TYPE",
            error_message="Order type not allowed",
        )

        # When - Submitting a limit order
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.BUY,
            quantity=10,
            price=100.0,  # Limit order has price
            trader_id="HF1",
        )
        context = ValidationContext(
            order=order,
            trader_id="HF1",
            trader_role="hedge_fund",
        )

        result = constraint.check(context, config)

        # Then - The constraint accepts limit orders
        assert result.is_valid

    def test_order_type_constraint_rejection(self):
        # Given - Only limit orders allowed (no market)
        constraint = OrderTypeConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.ORDER_TYPE_ALLOWED,
            parameters={"allowed_types": ["limit"]},
            error_code="NO_MARKET",
            error_message="Market orders not allowed",
        )

        # When - Submitting a market order
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.BUY,
            quantity=10,
            price=None,  # Market order has no price
            trader_id="HF1",
        )
        context = ValidationContext(
            order=order,
            trader_id="HF1",
            trader_role="hedge_fund",
        )

        result = constraint.check(context, config)

        # Then - The constraint rejects market orders
        assert not result.is_valid
        assert "market not in ['limit']" in result.error_detail

    def test_price_range_constraint_market_order(self):
        # Given - Price range constraint
        constraint = PriceRangeConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.PRICE_RANGE,
            parameters={"min_price": 10.0, "max_price": 200.0},
            error_code="PRICE_RANGE",
            error_message="Price outside valid range",
        )

        # When - Submitting a market order (no price)
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.BUY,
            quantity=10,
            price=None,  # Market order
            trader_id="MM1",
        )
        context = ValidationContext(
            order=order,
            trader_id="MM1",
            trader_role="market_maker",
        )

        result = constraint.check(context, config)

        # Then - Market orders always pass price checks
        assert result.is_valid

    @pytest.mark.parametrize(
        "price,should_accept",
        [
            (50.0, True),  # Within range
            (10.0, True),  # At minimum
            (200.0, True),  # At maximum
            (5.0, False),  # Below minimum
            (250.0, False),  # Above maximum
        ],
    )
    def test_price_range_constraint_limit_orders(self, price, should_accept):
        # Given - Price range 10-200
        constraint = PriceRangeConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.PRICE_RANGE,
            parameters={"min_price": 10.0, "max_price": 200.0},
            error_code="PRICE_RANGE",
            error_message="Price outside valid range",
        )

        # When - Testing various prices
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.BUY,
            quantity=10,
            price=price,
            trader_id="MM1",
        )
        context = ValidationContext(
            order=order,
            trader_id="MM1",
            trader_role="market_maker",
        )

        result = constraint.check(context, config)

        # Then - Accept/reject based on price
        assert result.is_valid == should_accept
        if not should_accept:
            assert f"Price {price} not in [10.0, 200.0]" in result.error_detail

    def test_constraint_creation_with_defaults(self):
        # Given - Creating constraints with missing optional parameters
        # OrderSizeConstraint should use 0 and infinity as defaults
        size_constraint = OrderSizeConstraint()
        size_config = ConstraintConfig(
            constraint_type=ConstraintType.ORDER_SIZE,
            parameters={},  # No min/max specified
            error_code="SIZE",
            error_message="Size error",
        )

        # When - Testing with any size
        order = Order(
            instrument_id="TEST",
            side=OrderSide.BUY,
            quantity=999999,  # Very large
            price=100.0,
            trader_id="TEST1",
        )
        context = ValidationContext(
            order=order,
            trader_id="TEST1",
            trader_role="test",
        )

        result = size_constraint.check(context, size_config)

        # Then - Should accept any size when no limits specified
        assert result.is_valid

    def test_constraint_config_from_dict(self):
        # Given - Configuration for various constraint types
        config = {
            "roles": {
                "test_role": {
                    "constraints": [
                        {
                            "type": "portfolio_limit",
                            "max_total_position": 200,
                            "error_code": "PORTFOLIO",
                            "error_message": "Portfolio too large",
                        },
                        {
                            "type": "order_rate",
                            "max_orders_per_second": 5,
                            "error_code": "RATE",
                            "error_message": "Too many orders",
                        },
                        {
                            "type": "order_type_allowed",
                            "allowed_types": ["limit"],
                            "error_code": "TYPE",
                            "error_message": "Invalid type",
                        },
                        {
                            "type": "price_range",
                            "min_price": 1.0,
                            "max_price": 1000.0,
                            "error_code": "PRICE",
                            "error_message": "Price out of range",
                        },
                    ]
                }
            }
        }

        # When - Loading constraints from config
        role_constraints = load_constraints_from_dict(config)

        # Then - All constraint types are created correctly
        test_constraints = role_constraints["test_role"]

        # Should have 4 explicit constraints only
        assert len(test_constraints) == 4

        # Check each constraint type is present
        constraint_types = {c.constraint_type for c in test_constraints}
        assert ConstraintType.PORTFOLIO_LIMIT in constraint_types
        assert ConstraintType.ORDER_RATE in constraint_types
        assert ConstraintType.ORDER_TYPE_ALLOWED in constraint_types
        assert ConstraintType.PRICE_RANGE in constraint_types

        # Verify parameters are preserved
        portfolio_constraint = next(
            c
            for c in test_constraints
            if c.constraint_type == ConstraintType.PORTFOLIO_LIMIT
        )
        assert portfolio_constraint.parameters["max_total_position"] == 200

        rate_constraint = next(
            c
            for c in test_constraints
            if c.constraint_type == ConstraintType.ORDER_RATE
        )
        assert rate_constraint.parameters["max_orders_per_second"] == 5
