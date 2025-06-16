"""Fee configuration loading for the trading system.

This module handles loading fee configurations from YAML files,
creating domain models for the positions domain.
"""

from typing import Dict

from ...domain.positions.models import FeeSchedule


def load_fee_schedules_from_config(config: Dict) -> Dict[str, FeeSchedule]:
    """Load fee schedules from configuration dictionary.

    Parses the roles section of the game configuration to
    extract fee schedules for each role.

    Parameters
    ----------
    config : Dict
        Configuration dictionary with 'roles' section

    Returns
    -------
    Dict[str, FeeSchedule]
        Mapping from role name to fee schedule

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
    >>> role_fees = load_fee_schedules_from_config(config_dict)
    >>> print(role_fees["market_maker"].maker_rebate)
    0.02
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

    return role_fees


# Hardcoded fee schedules matching current behavior
# TODO: Load from YAML config file
def get_hardcoded_fee_schedules() -> Dict[str, FeeSchedule]:
    """Get hardcoded fee schedules for all roles.

    Returns
    -------
    Dict[str, FeeSchedule]
        Mapping from role name to fee schedule

    Notes
    -----
    This is a temporary solution until fee configuration
    is loaded from the YAML config file.
    """
    return {
        "market_maker": FeeSchedule(
            maker_rebate=0.02,  # Positive = rebate (receive money)
            taker_fee=-0.05,  # Negative = fee (pay money)
        ),
        "hedge_fund": FeeSchedule(
            maker_rebate=0.0,  # No rebate
            taker_fee=-0.05,  # Standard taker fee
        ),
        "arbitrage": FeeSchedule(
            maker_rebate=0.0,  # No rebate
            taker_fee=-0.05,  # Standard taker fee
        ),
        "retail": FeeSchedule(
            maker_rebate=0.0,  # No rebate
            taker_fee=-0.05,  # Standard taker fee
        ),
    }
