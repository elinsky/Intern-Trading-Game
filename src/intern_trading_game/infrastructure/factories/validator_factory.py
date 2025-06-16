"""Factory for creating configured validator instances.

This module provides factory methods to create ConstraintBasedOrderValidator
instances with role-based constraints loaded from configuration.
"""

from ...domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
)
from ..config.loader import ConfigLoader


class ValidatorFactory:
    """Factory for creating configured validator instances.

    This class provides static methods to create ConstraintBasedOrderValidator
    instances based on configuration, loading all role-based constraints
    automatically.
    """

    @staticmethod
    def create_from_config(
        config_loader: ConfigLoader,
    ) -> ConstraintBasedOrderValidator:
        """Create validator with constraints loaded from configuration.

        Creates a ConstraintBasedOrderValidator and loads all role constraints
        defined in the configuration file.

        Parameters
        ----------
        config_loader : ConfigLoader
            Configuration loader instance with access to config data

        Returns
        -------
        ConstraintBasedOrderValidator
            Configured validator instance with all role constraints loaded

        Notes
        -----
        The factory loads constraints for all roles found in the configuration.
        Roles without constraints or missing roles are handled gracefully.

        The validator is always a new instance - this factory does not cache
        or reuse validator instances.
        """
        # Create new validator instance
        validator = ConstraintBasedOrderValidator()

        # Load configuration data
        config_data = config_loader.load()
        roles_data = config_data.get("roles", {})

        # Load constraints for each role
        for role_name in roles_data:
            constraints = config_loader.get_role_constraints(role_name)
            if constraints:
                validator.load_constraints(role_name, constraints)
                print(
                    f"Loaded {len(constraints)} constraints for role: {role_name}"
                )
            else:
                # Still register the role even if it has no constraints
                validator.load_constraints(role_name, [])
                print(f"Loaded role with no constraints: {role_name}")

        return validator
