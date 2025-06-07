"""Fee configuration models for the trading system.

This module defines the configuration structures for trading fees,
supporting role-specific fee schedules with maker/taker pricing.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class FeeSchedule:
    """Fee schedule for a trading role.

    Defines the fees and rebates for a specific trading role.
    Positive values represent rebates (money received), while
    negative values represent fees (money paid).

    Parameters
    ----------
    maker_rebate : float
        Rebate or fee for providing liquidity (positive = rebate)
    taker_fee : float
        Fee for taking liquidity (negative = fee)

    Notes
    -----
    The fee convention follows the YAML configuration:
    - Positive values = money received (rebate)
    - Negative values = money paid (fee)

    This is standard exchange convention where market makers
    are incentivized with rebates for providing liquidity.

    Examples
    --------
    >>> # Market maker schedule with rebates
    >>> mm_fees = FeeSchedule(
    ...     maker_rebate=0.02,   # Receive $0.02 per contract
    ...     taker_fee=-0.01      # Pay $0.01 per contract
    ... )
    >>>
    >>> # Retail schedule with only fees
    >>> retail_fees = FeeSchedule(
    ...     maker_rebate=-0.01,  # Pay $0.01 as maker
    ...     taker_fee=-0.03      # Pay $0.03 as taker
    ... )
    """

    maker_rebate: float
    taker_fee: float

    def get_fee_for_liquidity_type(self, liquidity_type: str) -> float:
        """Get the fee/rebate for a specific liquidity type.

        Parameters
        ----------
        liquidity_type : str
            Either "maker" or "taker"

        Returns
        -------
        float
            Fee amount (negative) or rebate amount (positive)

        Raises
        ------
        ValueError
            If liquidity_type is not "maker" or "taker"
        """
        if liquidity_type == "maker":
            return self.maker_rebate
        elif liquidity_type == "taker":
            return self.taker_fee
        else:
            raise ValueError(
                f"Invalid liquidity type: {liquidity_type}. "
                "Must be 'maker' or 'taker'"
            )


@dataclass
class FeeConfig:
    """Complete fee configuration for all trading roles.

    Contains fee schedules for each role in the trading system,
    loaded from the game configuration YAML file.

    Parameters
    ----------
    role_fees : Dict[str, FeeSchedule]
        Mapping from role name to fee schedule

    Notes
    -----
    This configuration is typically loaded from the game's
    YAML configuration file under the 'roles' section.

    The fee structure supports different pricing for different
    participant types, allowing the game to model realistic
    market dynamics where different participants have different
    economic incentives.

    Examples
    --------
    >>> # Load from configuration
    >>> config = FeeConfig(
    ...     role_fees={
    ...         "market_maker": FeeSchedule(0.02, -0.01),
    ...         "hedge_fund": FeeSchedule(0.01, -0.02),
    ...         "retail": FeeSchedule(-0.01, -0.03)
    ...     }
    ... )
    >>>
    >>> # Get fees for a specific role
    >>> mm_schedule = config.get_schedule("market_maker")
    >>> fee = mm_schedule.get_fee_for_liquidity_type("maker")
    """

    role_fees: Dict[str, FeeSchedule]

    def get_schedule(self, role: str) -> FeeSchedule:
        """Get the fee schedule for a specific role.

        Parameters
        ----------
        role : str
            The trading role

        Returns
        -------
        FeeSchedule
            The fee schedule for that role

        Raises
        ------
        KeyError
            If role is not found in configuration
        """
        if role not in self.role_fees:
            raise KeyError(
                f"Unknown role: {role}. "
                f"Available roles: {list(self.role_fees.keys())}"
            )
        return self.role_fees[role]

    @classmethod
    def from_config_dict(cls, config: Dict) -> "FeeConfig":
        """Create FeeConfig from configuration dictionary.

        Parses the roles section of the game configuration to
        extract fee schedules for each role.

        Parameters
        ----------
        config : Dict
            Configuration dictionary with 'roles' section

        Returns
        -------
        FeeConfig
            Parsed fee configuration

        Notes
        -----
        Expected configuration structure:
        ```yaml
        roles:
          market_maker:
            fees:
              maker_rebate: 0.02
              taker_fee: -0.01
          hedge_fund:
            fees:
              maker_rebate: 0.01
              taker_fee: -0.02
        ```

        Examples
        --------
        >>> config_dict = {
        ...     "roles": {
        ...         "market_maker": {
        ...             "fees": {
        ...                 "maker_rebate": 0.02,
        ...                 "taker_fee": -0.01
        ...             }
        ...         }
        ...     }
        ... }
        >>> fee_config = FeeConfig.from_config_dict(config_dict)
        """
        role_fees = {}

        roles_config = config.get("roles", {})
        for role_name, role_data in roles_config.items():
            fees_data = role_data.get("fees", {})
            if fees_data:
                role_fees[role_name] = FeeSchedule(
                    maker_rebate=fees_data.get("maker_rebate", 0.0),
                    taker_fee=fees_data.get("taker_fee", 0.0),
                )

        return cls(role_fees=role_fees)
