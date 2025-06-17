"""Tests for fee schedule configuration loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from intern_trading_game.domain.positions.models import FeeSchedule
from intern_trading_game.infrastructure.config.loader import ConfigLoader


class TestFeeScheduleConfig:
    """Test loading fee schedules from configuration."""

    def test_load_market_maker_fee_schedule(self):
        """Test loading fee schedule for market maker role.

        Given - YAML config with market maker fee structure
        Market makers receive rebates for providing liquidity
        as an incentive to maintain tight bid-ask spreads.
        The game config specifies +$0.02 maker rebate.

        When - ConfigLoader reads the fee schedules
        The loader parses the roles section to extract
        role-specific fee structures for P&L calculation.

        Then - Market maker fee schedule has correct rebates
        The loaded schedule should match the game design
        where MMs earn rebates for posting limit orders.
        """
        # Given - Config with market maker fees
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "fees": {
                            "maker_rebate": 0.02,  # +$0.02 rebate
                            "taker_fee": -0.01,  # -$0.01 fee
                        }
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load fee schedules
            loader = ConfigLoader(config_path)
            fee_schedules = loader.get_fee_schedules()

            # Then - Market maker has correct fees
            assert "market_maker" in fee_schedules
            mm_schedule = fee_schedules["market_maker"]
            assert isinstance(mm_schedule, FeeSchedule)
            assert mm_schedule.maker_rebate == 0.02
            assert mm_schedule.taker_fee == -0.01

        finally:
            config_path.unlink()

    def test_load_all_role_fee_schedules(self):
        """Test loading fee schedules for all trading roles.

        Given - Complete game config with role-specific fees
        Each role has different fee structures based on their
        market function. Retail pays highest fees while
        market makers receive rebates.

        When - Load all fee schedules from config
        The system needs fee schedules for all roles to
        calculate P&L correctly during trade settlement.

        Then - All roles have proper fee schedules
        Each role's fees should align with game design
        where liquidity providers are incentivized.
        """
        # Given - Config with all role fees
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "fees": {
                            "maker_rebate": 0.02,
                            "taker_fee": -0.01,
                        }
                    },
                    "hedge_fund": {
                        "fees": {
                            "maker_rebate": 0.01,
                            "taker_fee": -0.02,
                        }
                    },
                    "arbitrage_desk": {
                        "fees": {
                            "maker_rebate": 0.01,
                            "taker_fee": -0.02,
                        }
                    },
                    "retail": {
                        "fees": {
                            "maker_rebate": -0.01,  # Pay as maker
                            "taker_fee": -0.03,
                        }
                    },
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load fee schedules
            loader = ConfigLoader(config_path)
            fee_schedules = loader.get_fee_schedules()

            # Then - All roles loaded correctly
            assert len(fee_schedules) == 4

            # Market maker gets best rebates
            assert fee_schedules["market_maker"].maker_rebate == 0.02
            assert fee_schedules["market_maker"].taker_fee == -0.01

            # Hedge fund gets smaller rebates
            assert fee_schedules["hedge_fund"].maker_rebate == 0.01
            assert fee_schedules["hedge_fund"].taker_fee == -0.02

            # Arbitrage desk same as hedge fund
            assert fee_schedules["arbitrage_desk"].maker_rebate == 0.01
            assert fee_schedules["arbitrage_desk"].taker_fee == -0.02

            # Retail pays fees even as maker
            assert fee_schedules["retail"].maker_rebate == -0.01
            assert fee_schedules["retail"].taker_fee == -0.03

        finally:
            config_path.unlink()

    def test_missing_fees_section_raises_error(self):
        """Test handling when role has no fees section.

        Given - Role defined but missing fees configuration
        This is a configuration error - every trading role
        needs fee structure for accurate P&L calculation.

        When - Load fee schedules for incomplete config
        System should detect roles without fee configuration
        and raise an error to prevent misconfiguration.

        Then - Raises error identifying the problem
        Clear error message helps fix the configuration
        by adding the missing fees section.
        """
        # Given - Role without fees section
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "constraints": [
                            {
                                "type": "position_limit",
                                "parameters": {"max_position": 50},
                                "error_code": "POS_LIMIT",
                                "error_message": "Position limit",
                            }
                        ]
                        # No fees section
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When/Then - Should raise error
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_fee_schedules()

            assert "Missing fees section" in str(exc_info.value)
            assert "market_maker" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_no_roles_section_returns_empty_dict(self):
        """Test handling when config has no roles section.

        Given - Config file without roles section
        During early development or minimal test configs,
        the roles section might not exist.

        When - Load fee schedules from minimal config
        The loader should handle missing sections gracefully.

        Then - Returns empty fee schedule dict
        No fees are configured, allowing system to start
        without fee calculations.
        """
        # Given - Config without roles
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "exchange": {"matching_mode": "continuous"},
                "instruments": [],
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load fee schedules
            loader = ConfigLoader(config_path)
            fee_schedules = loader.get_fee_schedules()

            # Then - Returns empty dict
            assert fee_schedules == {}

        finally:
            config_path.unlink()

    @pytest.mark.parametrize(
        "role,maker_rebate,taker_fee",
        [
            ("market_maker", 0.02, -0.01),  # Best rebates
            ("hedge_fund", 0.01, -0.02),  # Medium rebates
            ("arbitrage_desk", 0.01, -0.02),  # Same as HF
            ("retail", -0.01, -0.03),  # Pays most fees
        ],
    )
    def test_fee_schedules_match_game_design(
        self, role, maker_rebate, taker_fee
    ):
        """Test fee schedules align with game design docs.

        Given - Fee structure from game design documentation
        The game uses maker/taker fees to incentivize
        liquidity provision and simulate real markets.

        When - Load fees for each role
        Each role has specific fee tiers based on their
        market function and sophistication level.

        Then - Fees match documented game mechanics
        Market makers get best rates to encourage quoting,
        while retail traders pay highest fees.
        """
        # Given - Config matching game design
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    role: {
                        "fees": {
                            "maker_rebate": maker_rebate,
                            "taker_fee": taker_fee,
                        }
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load fee schedule
            loader = ConfigLoader(config_path)
            fee_schedules = loader.get_fee_schedules()

            # Then - Fees match expected values
            schedule = fee_schedules[role]
            assert schedule.maker_rebate == maker_rebate
            assert schedule.taker_fee == taker_fee

            # Verify fee logic
            if role == "market_maker":
                # MMs always get rebates as makers
                assert schedule.maker_rebate > 0
            elif role == "retail":
                # Retail always pays fees
                assert schedule.maker_rebate < 0
                assert schedule.taker_fee < 0

        finally:
            config_path.unlink()

    def test_partial_fee_data_raises_error(self):
        """Test handling partial fee configuration.

        Given - Role with only one fee type specified
        Incomplete fee data is a configuration error that
        could lead to incorrect P&L calculations.

        When - Load partially specified fees
        System should detect incomplete configuration
        and raise an error to prevent miscalculation.

        Then - Raises error for missing fee component
        Clear error message helps identify the issue
        in the configuration file.
        """
        # Given - Partial fee config
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "test_role": {
                        "fees": {
                            "maker_rebate": 0.015,
                            # taker_fee missing
                        }
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When/Then - Should raise error
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_fee_schedules()

            assert "Missing required fee" in str(exc_info.value)
            assert "taker_fee" in str(exc_info.value)
            assert "test_role" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_missing_maker_rebate_raises_error(self):
        """Test error when maker_rebate is missing.

        Given - Role with missing maker_rebate
        Both maker and taker fees are required for
        accurate P&L calculation.

        When - Load fee configuration
        System validates that both fee types are present.

        Then - Raises error for missing maker_rebate
        Error clearly identifies the missing field.
        """
        # Given - Missing maker_rebate
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "test_role": {
                        "fees": {
                            # maker_rebate missing
                            "taker_fee": -0.02,
                        }
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When/Then - Should raise error
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_fee_schedules()

            assert "Missing required fee" in str(exc_info.value)
            assert "maker_rebate" in str(exc_info.value)
            assert "test_role" in str(exc_info.value)

        finally:
            config_path.unlink()
