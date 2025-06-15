"""Domain models for position tracking and fee calculation.

This module contains the data models used within the positions domain,
including fee schedules for different trading roles.
"""

from dataclasses import dataclass


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
