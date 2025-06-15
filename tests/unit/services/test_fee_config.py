"""Unit tests for fee configuration models."""

import pytest

from intern_trading_game.domain.positions import FeeSchedule
from intern_trading_game.infrastructure.config.fee_config import (
    load_fee_schedules_from_config,
)


class TestFeeSchedule:
    """Test suite for FeeSchedule."""

    def test_fee_schedule_creation(self):
        """Test creating a fee schedule with rebates and fees."""
        schedule = FeeSchedule(maker_rebate=0.02, taker_fee=-0.01)

        assert schedule.maker_rebate == 0.02
        assert schedule.taker_fee == -0.01

    def test_get_fee_for_maker(self):
        """Test getting maker fee/rebate."""
        schedule = FeeSchedule(maker_rebate=0.02, taker_fee=-0.01)

        fee = schedule.get_fee_for_liquidity_type("maker")
        assert fee == 0.02  # Positive = rebate

    def test_get_fee_for_taker(self):
        """Test getting taker fee."""
        schedule = FeeSchedule(maker_rebate=0.02, taker_fee=-0.01)

        fee = schedule.get_fee_for_liquidity_type("taker")
        assert fee == -0.01  # Negative = fee

    def test_invalid_liquidity_type(self):
        """Test error handling for invalid liquidity type."""
        schedule = FeeSchedule(maker_rebate=0.02, taker_fee=-0.01)

        with pytest.raises(ValueError, match="Invalid liquidity type"):
            schedule.get_fee_for_liquidity_type("invalid")

    @pytest.mark.parametrize(
        "maker_rebate,taker_fee,liquidity_type,expected",
        [
            (0.02, -0.01, "maker", 0.02),  # MM maker rebate
            (0.02, -0.01, "taker", -0.01),  # MM taker fee
            (0.01, -0.02, "maker", 0.01),  # HF maker rebate
            (-0.01, -0.03, "maker", -0.01),  # Retail maker fee
            (-0.01, -0.03, "taker", -0.03),  # Retail taker fee
        ],
    )
    def test_various_fee_schedules(
        self, maker_rebate, taker_fee, liquidity_type, expected
    ):
        """Test different fee schedule configurations."""
        schedule = FeeSchedule(maker_rebate=maker_rebate, taker_fee=taker_fee)
        assert schedule.get_fee_for_liquidity_type(liquidity_type) == expected


class TestLoadFeeSchedules:
    """Test suite for load_fee_schedules_from_config."""

    @pytest.fixture
    def sample_role_fees(self):
        """Create sample fee schedules."""
        return {
            "market_maker": FeeSchedule(0.02, -0.01),
            "hedge_fund": FeeSchedule(0.01, -0.02),
            "retail": FeeSchedule(-0.01, -0.03),
        }

    def test_role_fees_dict_structure(self, sample_role_fees):
        """Test fee schedules dictionary structure."""
        assert len(sample_role_fees) == 3
        assert "market_maker" in sample_role_fees
        assert "hedge_fund" in sample_role_fees
        assert "retail" in sample_role_fees

    def test_get_schedule_for_role(self, sample_role_fees):
        """Test retrieving schedule for specific role."""
        mm_schedule = sample_role_fees["market_maker"]
        assert mm_schedule.maker_rebate == 0.02
        assert mm_schedule.taker_fee == -0.01

    def test_get_schedule_unknown_role(self, sample_role_fees):
        """Test error handling for unknown role."""
        assert "unknown" not in sample_role_fees

    def test_from_config_dict_full(self):
        """Test loading from complete configuration dictionary."""
        config_dict = {
            "roles": {
                "market_maker": {
                    "fees": {"maker_rebate": 0.02, "taker_fee": -0.01},
                    "position_limits": {"per_option": 50},
                },
                "hedge_fund": {
                    "fees": {"maker_rebate": 0.01, "taker_fee": -0.02},
                    "signals": {"volatility_forecast": {"accuracy": 0.66}},
                },
                "retail": {
                    "fees": {"maker_rebate": -0.01, "taker_fee": -0.03},
                    "order_generation": {"mean": 3},
                },
            }
        }

        role_fees = load_fee_schedules_from_config(config_dict)

        # Verify all roles loaded
        assert len(role_fees) == 3

        # Check market maker fees
        mm_schedule = role_fees["market_maker"]
        assert mm_schedule.maker_rebate == 0.02
        assert mm_schedule.taker_fee == -0.01

        # Check hedge fund fees
        hf_schedule = role_fees["hedge_fund"]
        assert hf_schedule.maker_rebate == 0.01
        assert hf_schedule.taker_fee == -0.02

        # Check retail fees
        retail_schedule = role_fees["retail"]
        assert retail_schedule.maker_rebate == -0.01
        assert retail_schedule.taker_fee == -0.03

    def test_from_config_dict_missing_fees(self):
        """Test loading when some roles don't have fees defined."""
        config_dict = {
            "roles": {
                "market_maker": {
                    "fees": {"maker_rebate": 0.02, "taker_fee": -0.01}
                },
                "arbitrage_desk": {
                    # No fees section
                    "position_limits": {"per_option": 100}
                },
            }
        }

        role_fees = load_fee_schedules_from_config(config_dict)

        # Only market_maker should be loaded
        assert len(role_fees) == 1
        assert "market_maker" in role_fees
        assert "arbitrage_desk" not in role_fees

    def test_from_config_dict_empty(self):
        """Test loading from empty configuration."""
        role_fees = load_fee_schedules_from_config({})
        assert len(role_fees) == 0

    def test_from_config_dict_defaults(self):
        """Test default values when fees partially specified."""
        config_dict = {
            "roles": {
                "test_role": {
                    "fees": {"maker_rebate": 0.05}  # No taker_fee
                }
            }
        }

        role_fees = load_fee_schedules_from_config(config_dict)
        schedule = role_fees["test_role"]

        assert schedule.maker_rebate == 0.05
        assert schedule.taker_fee == 0.0  # Default
