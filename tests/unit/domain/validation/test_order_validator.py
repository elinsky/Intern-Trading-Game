"""Tests for the order validation system.

These tests verify that the constraint-based order validator correctly
enforces trading rules without any hardcoded role-specific logic.
"""

import pytest

from intern_trading_game.domain.exchange.order import Order, OrderSide
from intern_trading_game.domain.interfaces import ValidationContext
from intern_trading_game.domain.models import TickPhase
from intern_trading_game.domain.validation.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintConfig,
    ConstraintType,
    OrderSizeConstraint,
    PositionLimitConstraint,
    TradingWindowConstraint,
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
            tick_phase=TickPhase.PRE_OPEN,
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
            tick_phase=TickPhase.PRE_OPEN,
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
            tick_phase=TickPhase.PRE_OPEN,
        )

        result = constraint.check(context, config)

        # Then - The constraint rejects the order
        assert not result.is_valid
        assert "600 not in [1, 500]" in result.error_detail

    def test_trading_window_constraint(self):
        # Given - A trading window constraint allowing only PRE_OPEN phase
        constraint = TradingWindowConstraint()
        config = ConstraintConfig(
            constraint_type=ConstraintType.TRADING_WINDOW,
            parameters={
                "allowed_phases": [
                    TickPhase.PRE_OPEN.name,
                ]
            },
            error_code="WINDOW_CLOSED",
            error_message="Trading window closed",
        )

        # When - Attempting to submit an order during TRADING phase
        order = Order(
            instrument_id="SPX_CALL_4500",
            side=OrderSide.BUY,
            quantity=10,
            price=100.0,
            trader_id="MM1",
        )
        context = ValidationContext(
            order=order,
            trader_id="MM1",
            trader_role="market_maker",
            tick_phase=TickPhase.TRADING,
        )

        result = constraint.check(context, config)

        # Then - The constraint rejects the order
        assert not result.is_valid
        assert TickPhase.TRADING.name in result.error_detail


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
            tick_phase=TickPhase.PRE_OPEN,
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
            tick_phase=TickPhase.PRE_OPEN,
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
            tick_phase=TickPhase.PRE_OPEN,
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

        # Then - Constraints are correctly parsed and universal constraints added
        mm_constraints = role_constraints["market_maker"]
        assert len(mm_constraints) >= 3  # 2 explicit + universal

        pos_constraint = next(
            c
            for c in mm_constraints
            if c.constraint_type == ConstraintType.POSITION_LIMIT
        )
        assert pos_constraint.parameters["max_position"] == 50
        assert pos_constraint.parameters["symmetric"] is True
        assert pos_constraint.error_code == "MM_POS"

        window_constraints = [
            c
            for c in mm_constraints
            if c.constraint_type == ConstraintType.TRADING_WINDOW
        ]
        assert len(window_constraints) == 1

    def test_universal_constraints(self):
        # Given - Requesting universal constraints
        constraints = get_universal_constraints()

        # Then - Trading window constraint is returned
        assert len(constraints) >= 1
        window_constraint = constraints[0]
        assert (
            window_constraint.constraint_type == ConstraintType.TRADING_WINDOW
        )
        assert window_constraint.error_code == "TRADING_WINDOW_CLOSED"
