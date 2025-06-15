"""Trading fee calculation service.

This module provides fee calculation logic for the trading system,
handling role-specific fees and liquidity-based pricing.
"""

from typing import Dict

from .models import FeeSchedule


class TradingFeeService:
    """Service for calculating trading fees based on role and liquidity type.

    This service encapsulates all fee calculation logic, using configuration
    loaded from the game's YAML file to determine role-specific pricing.
    It supports different fee structures for different participant types,
    including market maker rebates and standard trading fees.

    The service is designed to be stateless and thread-safe, with all
    methods being pure functions that can be called concurrently from
    multiple threads without synchronization.

    Parameters
    ----------
    role_fees : Dict[str, FeeSchedule]
        Mapping from role name to fee schedule for all roles

    Attributes
    ----------
    role_fees : Dict[str, FeeSchedule]
        The fee schedules used for calculations

    Notes
    -----
    Fee calculation in the trading system follows maker/taker pricing:

    1. Makers provide liquidity by posting limit orders
    2. Takers remove liquidity by crossing the spread
    3. Market makers may receive rebates for providing liquidity
    4. All participants pay fees when taking liquidity

    The fee structure incentivizes liquidity provision, which is
    essential for maintaining orderly markets with tight spreads.

    TradingContext
    --------------
    In real markets, fee structures are a critical component of
    market microstructure. Exchanges use tiered fee schedules,
    volume discounts, and special programs to attract different
    types of participants.

    This implementation models the essential maker/taker dynamic
    while keeping the fee structure simple enough for the simulation.
    Market makers are incentivized to provide two-sided quotes through
    rebates, while other participants pay standard fees.

    Examples
    --------
    >>> # Create service with fee schedules
    >>> role_fees = {
    ...     "market_maker": FeeSchedule(0.02, -0.01),
    ...     "retail": FeeSchedule(-0.01, -0.03)
    ... }
    >>> fee_service = TradingFeeService(role_fees)
    >>>
    >>> # Calculate fees for a market maker
    >>> fee = fee_service.calculate_fee(10, "market_maker", "maker")
    >>> print(f"Rebate: ${fee:.2f}")  # $0.20 (positive = rebate)
    >>>
    >>> # Calculate fees for retail trader
    >>> fee = fee_service.calculate_fee(5, "retail", "taker")
    >>> print(f"Fee: ${fee:.2f}")  # -$0.15 (negative = fee)
    """

    def __init__(self, role_fees: Dict[str, FeeSchedule]):
        """Initialize the fee service with fee schedules.

        Parameters
        ----------
        role_fees : Dict[str, FeeSchedule]
            Mapping from role name to fee schedule
        """
        self.role_fees = role_fees

    def calculate_fee(
        self, quantity: int, role: str, liquidity_type: str
    ) -> float:
        """Calculate trading fee or rebate for a trade.

        Determines the appropriate fee based on the trader's role and
        whether they provided or took liquidity. Uses the configured
        fee schedule to support role-specific pricing.

        Parameters
        ----------
        quantity : int
            Number of contracts traded
        role : str
            Trader's role (e.g., "market_maker", "retail", "hedge_fund")
        liquidity_type : str
            Whether the order was "maker" or "taker"

        Returns
        -------
        float
            Total fee for the trade:
            - Positive values indicate rebates (money received)
            - Negative values indicate fees (money paid)

        Raises
        ------
        KeyError
            If role is not found in fee configuration
        ValueError
            If liquidity_type is not "maker" or "taker"

        Notes
        -----
        The fee calculation is simply:

        $$\\text{total fee} = \\text{quantity} \\times \\text{rate per contract}$$

        Where the rate depends on the role and liquidity type as
        defined in the configuration.

        TradingContext
        --------------
        Market makers are essential for maintaining liquid markets.
        The rebate structure incentivizes them to post limit orders
        that other traders can execute against. This creates depth
        in the order book and tighter bid-ask spreads.

        In contrast, traders who need immediate execution pay fees
        for the privilege of taking liquidity. This compensates the
        exchange and liquidity providers for the service.

        Examples
        --------
        >>> # Market maker providing liquidity
        >>> fee = fee_service.calculate_fee(100, "market_maker", "maker")
        >>> # If maker_rebate = 0.02, fee = 100 * 0.02 = $2.00 rebate
        >>>
        >>> # Retail trader taking liquidity
        >>> fee = fee_service.calculate_fee(50, "retail", "taker")
        >>> # If taker_fee = -0.03, fee = 50 * -0.03 = -$1.50 fee
        >>>
        >>> # Hedge fund as maker (may still pay fees)
        >>> fee = fee_service.calculate_fee(75, "hedge_fund", "maker")
        >>> # If maker_rebate = 0.01, fee = 75 * 0.01 = $0.75 rebate
        """
        # Get fee schedule for the role
        if role not in self.role_fees:
            raise KeyError(
                f"Unknown role: {role}. "
                f"Available roles: {list(self.role_fees.keys())}"
            )
        schedule = self.role_fees[role]

        # Get rate based on liquidity type
        rate = schedule.get_fee_for_liquidity_type(liquidity_type)

        # Calculate total fee
        return quantity * rate

    def determine_liquidity_type(
        self, aggressor_side: str, order_side: str
    ) -> str:
        """Determine if an order provided or took liquidity.

        Compares the aggressor side of a trade with the order side to
        determine whether the order was actively taking liquidity
        (taker) or passively providing it (maker).

        Parameters
        ----------
        aggressor_side : str
            The side that triggered the trade ("buy" or "sell")
        order_side : str
            The side of the order being evaluated ("buy" or "sell")

        Returns
        -------
        str
            "taker" if the order aggressed, "maker" if it provided liquidity

        Notes
        -----
        In a continuous trading system, every trade involves:
        - One aggressive order (taker) that crosses the spread
        - One or more passive orders (makers) resting in the book

        The matching engine determines the aggressor based on which
        order triggered the match (typically the incoming order).

        TradingContext
        --------------
        Understanding maker/taker dynamics is crucial for execution:

        - Takers get immediate execution but pay higher fees
        - Makers get better prices but face execution uncertainty
        - Smart routers optimize between these trade-offs

        Examples
        --------
        >>> # Buy order that lifted the offer
        >>> liq_type = fee_service.determine_liquidity_type("buy", "buy")
        >>> assert liq_type == "taker"  # Order was the aggressor
        >>>
        >>> # Sell order resting when hit by a buy
        >>> liq_type = fee_service.determine_liquidity_type("buy", "sell")
        >>> assert liq_type == "maker"  # Order was passive
        """
        if aggressor_side == order_side:
            return "taker"
        return "maker"

    def get_fee_schedule(self, role: str) -> FeeSchedule:
        """Get the complete fee schedule for a given role.

        Returns the fee schedule object containing both maker and
        taker rates for the specified role. Useful for displaying
        fee information or pre-calculating expected costs.

        Parameters
        ----------
        role : str
            Trader's role (e.g., "market_maker", "retail")

        Returns
        -------
        FeeSchedule
            Fee schedule with maker_rebate and taker_fee

        Raises
        ------
        KeyError
            If role is not found in configuration

        Notes
        -----
        This method provides transparency into the fee structure,
        allowing traders to make informed decisions about their
        execution strategy.

        TradingContext
        --------------
        Transparent fee schedules help traders optimize execution:
        - Market makers calculate required spreads for profitability
        - Other traders weigh urgency against fee costs
        - Algorithms can dynamically adjust aggressiveness

        Examples
        --------
        >>> schedule = fee_service.get_fee_schedule("market_maker")
        >>> print(f"Maker: {schedule.maker_rebate}")   # 0.02
        >>> print(f"Taker: {schedule.taker_fee}")      # -0.01
        """
        if role not in self.role_fees:
            raise KeyError(
                f"Unknown role: {role}. "
                f"Available roles: {list(self.role_fees.keys())}"
            )
        return self.role_fees[role]
