"""Tests for role-based constraint configuration."""

import tempfile
from pathlib import Path

import pytest
import yaml

from intern_trading_game.domain.exchange.validation.order_validator import (
    ConstraintConfig,
    ConstraintType,
)
from intern_trading_game.infrastructure.config.loader import ConfigLoader


class TestRoleConstraintConfig:
    """Test loading role constraints from configuration."""

    def test_load_market_maker_constraints(self):
        """Test loading constraints for market maker role.

        Given - YAML config with market maker constraints
        When - Config loader reads the role constraints
        Then - Returns list of ConstraintConfig objects
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
            # When - Load role constraints
            loader = ConfigLoader(config_path)
            constraints = loader.get_role_constraints("market_maker")

            # Then - Should return list of ConstraintConfig objects
            assert len(constraints) == 2

            # Check position limit constraint
            pos_constraint = constraints[0]
            assert isinstance(pos_constraint, ConstraintConfig)
            assert (
                pos_constraint.constraint_type == ConstraintType.POSITION_LIMIT
            )
            assert pos_constraint.parameters["max_position"] == 50
            assert pos_constraint.parameters["symmetric"] is True
            assert pos_constraint.error_code == "MM_POS_LIMIT"
            assert pos_constraint.error_message == "Position exceeds ±50"

            # Check instrument allowed constraint
            inst_constraint = constraints[1]
            assert (
                inst_constraint.constraint_type
                == ConstraintType.INSTRUMENT_ALLOWED
            )
            assert inst_constraint.parameters["allowed_instruments"] == [
                "SPX_4500_CALL",
                "SPX_4500_PUT",
            ]
            assert inst_constraint.error_code == "INVALID_INSTRUMENT"

        finally:
            config_path.unlink()

    def test_missing_role_returns_empty_list(self):
        """Test that missing role returns empty constraint list.

        Given - Config without hedge_fund role
        When - Request constraints for hedge_fund
        Then - Returns empty list
        """
        # Given - Config with only market_maker
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
                                "error_message": "Position limit",
                            }
                        ]
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Request non-existent role
            loader = ConfigLoader(config_path)
            constraints = loader.get_role_constraints("hedge_fund")

            # Then - Should return empty list
            assert constraints == []

        finally:
            config_path.unlink()

    def test_role_without_constraints(self):
        """Test role defined but with no constraints.

        Given - Role exists but has empty constraints list
        When - Load constraints for that role
        Then - Returns empty list
        """
        # Given - Role with empty constraints
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {"roles": {"retail": {"constraints": []}}}
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load constraints
            loader = ConfigLoader(config_path)
            constraints = loader.get_role_constraints("retail")

            # Then - Should return empty list
            assert constraints == []

        finally:
            config_path.unlink()

    def test_invalid_constraint_type_raises_error(self):
        """Test that invalid constraint type raises error.

        Given - Config with invalid constraint type
        When - Try to load constraints
        Then - Raises ValueError with helpful message
        """
        # Given - Invalid constraint type
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            config_data = {
                "roles": {
                    "market_maker": {
                        "constraints": [
                            {
                                "type": "invalid_type",
                                "parameters": {},
                                "error_code": "TEST",
                                "error_message": "Test",
                            }
                        ]
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When/Then - Should raise ValueError
            loader = ConfigLoader(config_path)
            with pytest.raises(ValueError) as exc_info:
                loader.get_role_constraints("market_maker")

            assert "Invalid constraint type" in str(exc_info.value)
            assert "invalid_type" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields raises error.

        Given - Constraint missing error_code field
        When - Try to load constraints
        Then - Raises KeyError
        """
        # Given - Missing error_code
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
                                # Missing error_code
                                "error_message": "Test",
                            }
                        ]
                    }
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When/Then - Should raise KeyError
            loader = ConfigLoader(config_path)
            with pytest.raises(KeyError) as exc_info:
                loader.get_role_constraints("market_maker")

            assert "error_code" in str(exc_info.value)

        finally:
            config_path.unlink()

    def test_multiple_roles_config(self):
        """Test loading constraints from config with multiple roles.

        Given - Config with multiple roles
        When - Load constraints for each role
        Then - Each role gets its own constraints
        """
        # Given - Multiple roles
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
                                "error_message": "MM position limit",
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
                                "error_message": "HF position limit",
                            }
                        ]
                    },
                }
            }
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # When - Load constraints for each role
            loader = ConfigLoader(config_path)
            mm_constraints = loader.get_role_constraints("market_maker")
            hf_constraints = loader.get_role_constraints("hedge_fund")

            # Then - Each role has different constraints
            assert len(mm_constraints) == 1
            assert len(hf_constraints) == 1

            assert mm_constraints[0].parameters["max_position"] == 50
            assert mm_constraints[0].parameters["symmetric"] is True

            assert hf_constraints[0].parameters["max_position"] == 150
            assert hf_constraints[0].parameters["symmetric"] is False

        finally:
            config_path.unlink()
