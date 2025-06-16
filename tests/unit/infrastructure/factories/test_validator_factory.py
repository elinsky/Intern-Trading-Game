"""Tests for validator factory functionality."""

import tempfile
from pathlib import Path

import yaml

from intern_trading_game.domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintType,
)
from intern_trading_game.infrastructure.config.loader import ConfigLoader
from intern_trading_game.infrastructure.factories.validator_factory import (
    ValidatorFactory,
)


class TestValidatorFactory:
    """Test creating validators from configuration."""

    def test_create_validator_with_market_maker_constraints(self):
        """Test creating validator with market maker constraints loaded.

        Given - Config with market maker constraints
        When - Factory creates validator from config
        Then - Validator has constraints loaded for market_maker role
        """
        # Given - Config with market maker constraints
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "constraints": [
                            {
                                "type": "position_limit",
                                "parameters": {
                                    "max_position": 50,
                                    "symmetric": True,
                                },
                                "error_code": "MM_POS_LIMIT",
                                "error_message": "Position exceeds ±50",
                            },
                            {
                                "type": "instrument_allowed",
                                "parameters": {
                                    "allowed_instruments": [
                                        "SPX_4500_CALL",
                                        "SPX_4500_PUT",
                                    ]
                                },
                                "error_code": "INVALID_INSTRUMENT",
                                "error_message": "Instrument not found",
                            },
                        ]
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create validator via factory
            loader = ConfigLoader(config_path)
            validator = ValidatorFactory.create_from_config(loader)

            # Then - Should be ConstraintBasedOrderValidator
            assert isinstance(validator, ConstraintBasedOrderValidator)

            # Then - Should have market maker constraints loaded
            # The validator stores constraints internally by role
            # We can verify by checking the internal structure
            assert "market_maker" in validator._role_constraints_cache
            assert len(validator._role_constraints_cache["market_maker"]) == 2

            # Check the constraints were created correctly
            mm_constraints = validator._role_constraints_cache["market_maker"]

            # Position limit constraint
            pos_constraint = mm_constraints[0]
            assert (
                pos_constraint.constraint_type == ConstraintType.POSITION_LIMIT
            )
            assert pos_constraint.parameters["max_position"] == 50

            # Instrument allowed constraint
            inst_constraint = mm_constraints[1]
            assert (
                inst_constraint.constraint_type
                == ConstraintType.INSTRUMENT_ALLOWED
            )

        finally:
            config_path.unlink()

    def test_create_validator_with_multiple_roles(self):
        """Test creating validator with constraints for multiple roles.

        Given - Config with market_maker and hedge_fund roles
        When - Factory creates validator
        Then - Validator has constraints loaded for both roles
        """
        # Given - Config with multiple roles
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "constraints": [
                            {
                                "type": "position_limit",
                                "parameters": {
                                    "max_position": 50,
                                    "symmetric": True,
                                },
                                "error_code": "MM_POS_LIMIT",
                                "error_message": "MM limit",
                            }
                        ]
                    },
                    "hedge_fund": {
                        "constraints": [
                            {
                                "type": "position_limit",
                                "parameters": {
                                    "max_position": 150,
                                    "symmetric": False,
                                },
                                "error_code": "HF_POS_LIMIT",
                                "error_message": "HF limit",
                            }
                        ]
                    },
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create validator
            loader = ConfigLoader(config_path)
            validator = ValidatorFactory.create_from_config(loader)

            # Then - Should have constraints for both roles
            assert "market_maker" in validator._role_constraints_cache
            assert "hedge_fund" in validator._role_constraints_cache

            # Each role has its own constraints
            assert len(validator._role_constraints_cache["market_maker"]) == 1
            assert len(validator._role_constraints_cache["hedge_fund"]) == 1

            # Different parameters for each role
            mm_constraint = validator._role_constraints_cache["market_maker"][
                0
            ]
            hf_constraint = validator._role_constraints_cache["hedge_fund"][0]

            assert mm_constraint.parameters["max_position"] == 50
            assert hf_constraint.parameters["max_position"] == 150

        finally:
            config_path.unlink()

    def test_create_validator_with_no_roles(self):
        """Test creating validator when no roles are configured.

        Given - Config with no roles section
        When - Factory creates validator
        Then - Validator is created but has no constraints
        """
        # Given - Config without roles
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"exchange": {"matching_mode": "continuous"}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create validator
            loader = ConfigLoader(config_path)
            validator = ValidatorFactory.create_from_config(loader)

            # Then - Validator created but no constraints
            assert isinstance(validator, ConstraintBasedOrderValidator)
            assert len(validator._role_constraints_cache) == 0

        finally:
            config_path.unlink()

    def test_create_validator_with_empty_constraints(self):
        """Test creating validator when role has no constraints.

        Given - Role exists but has empty constraints list
        When - Factory creates validator
        Then - Validator has role registered but no constraints
        """
        # Given - Role with no constraints
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"roles": {"retail": {"constraints": []}}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create validator
            loader = ConfigLoader(config_path)
            validator = ValidatorFactory.create_from_config(loader)

            # Then - Role registered but no constraints
            assert "retail" in validator._role_constraints_cache
            assert len(validator._role_constraints_cache["retail"]) == 0

        finally:
            config_path.unlink()

    def test_factory_always_creates_new_instance(self):
        """Test that factory creates independent validator instances.

        Given - Same config used twice
        When - Factory creates two validators
        Then - They are separate instances
        """
        # Given - A config
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
                                "error_code": "MM_POS_LIMIT",
                                "error_message": "Limit",
                            }
                        ]
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Create two validators
            loader = ConfigLoader(config_path)
            validator1 = ValidatorFactory.create_from_config(loader)
            validator2 = ValidatorFactory.create_from_config(loader)

            # Then - Should be different instances
            assert validator1 is not validator2

            # But both have the same configuration
            assert len(validator1._role_constraints_cache["market_maker"]) == 1
            assert len(validator2._role_constraints_cache["market_maker"]) == 1

        finally:
            config_path.unlink()
