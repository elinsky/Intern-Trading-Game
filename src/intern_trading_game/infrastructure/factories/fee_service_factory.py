"""Factory for creating configured fee service instances.

This module provides factory methods to create TradingFeeService
instances with role-based fee schedules loaded from configuration.
"""

from ...domain.positions import TradingFeeService
from ..config.loader import ConfigLoader


class FeeServiceFactory:
    """Factory for creating configured fee service instances.

    This class provides static methods to create TradingFeeService
    instances based on configuration, loading all role-based fee
    schedules automatically.
    """

    @staticmethod
    def create_from_config(config_loader: ConfigLoader) -> TradingFeeService:
        """Create fee service with schedules loaded from configuration.

        Creates a TradingFeeService with all role fee schedules
        defined in the configuration file.

        Parameters
        ----------
        config_loader : ConfigLoader
            Configuration loader instance with access to config data

        Returns
        -------
        TradingFeeService
            Configured fee service instance with all role schedules loaded

        Raises
        ------
        ValueError
            If any role has incomplete fee configuration

        Notes
        -----
        The factory loads fee schedules for all roles found in the
        configuration. Each role must have both maker_rebate and
        taker_fee defined or an error will be raised.

        The fee service is always a new instance - this factory does
        not cache or reuse service instances.

        Examples
        --------
        >>> config_loader = ConfigLoader()
        >>> fee_service = FeeServiceFactory.create_from_config(config_loader)
        >>> fee = fee_service.calculate_fee(100, "market_maker", "maker")
        >>> print(f"Rebate: ${fee:.2f}")
        Rebate: $2.00
        """
        # Load fee schedules from configuration
        fee_schedules = config_loader.get_fee_schedules()

        # Print loaded roles for operational visibility
        if fee_schedules:
            role_names = sorted(fee_schedules.keys())
            print(
                f"Loaded fee schedules for {len(fee_schedules)} roles: {', '.join(role_names)}"
            )
        else:
            print("No fee schedules found in configuration")

        # Create and return configured service
        return TradingFeeService(fee_schedules)
