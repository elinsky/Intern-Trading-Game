"""Batch auction pricing strategies for the exchange.

This module implements different strategies for determining the clearing price
in batch auctions, following the Strategy Pattern for extensibility.

The key insight is that batch auctions need a uniform clearing price where
all trades execute, unlike continuous trading where each trade can have a
different price. This ensures fairness and prevents gaming.

The Maximum Volume (MV) algorithm is based on:
Niu, J., & Parsons, S. (2013). Maximizing Matching in Double-sided Auctions.
arXiv:1304.3135v1

The paper presents two algorithms:
- Algorithm 1: The MV algorithm for constructing matching sets
- Algorithm 2: The MV-getQ function for calculating maximum trading volume

Our implementation follows these algorithms closely but adds uniform pricing
for fairness in the trading game context.

References
----------
Niu, J., & Parsons, S. (2013). Maximizing Matching in Double-sided Auctions.
arXiv:1304.3135v1
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Set, Tuple

from ..components.core.models import Order


@dataclass
class AuctionClearingResult:
    """Result of batch auction pricing calculation.

    This dataclass encapsulates all the information needed from a pricing
    strategy, including not just the price but also volume and metadata
    about how the price was determined.

    Attributes
    ----------
    clearing_price : float
        The uniform price at which all trades will execute.
        All eligible trades in the batch execute at this single price.
    max_volume : int
        Maximum number of units that can trade at the clearing price.
        This represents the total liquidity that will be matched.
    algorithm : str
        Name of the algorithm used (for transparency/debugging).
        Examples: "maximum_volume", "equilibrium", "reference_price".
    price_range : Optional[Tuple[float, float]]
        When multiple prices maximize volume, shows the range.
        For example, if prices 99, 100, 101 all allow max volume,
        price_range would be (99, 101) and clearing_price would be 100.

    Notes
    -----
    The price_range field is particularly important for understanding
    the algorithm's behavior. When it's not None, it indicates that
    multiple prices could have been chosen, and the algorithm selected
    one (typically the midpoint) according to its rules.
    """

    clearing_price: float
    max_volume: int
    algorithm: str
    price_range: Optional[Tuple[float, float]] = None


class BatchAuctionPricingStrategy(Protocol):
    """Protocol for batch auction pricing strategies.

    All strategies must determine a single uniform clearing price
    for batch auction execution. This is the key difference from
    continuous trading - everyone gets the same price.

    The strategy is responsible only for price determination, not
    for the actual matching of orders. The matching engine will
    handle order execution at the determined price.

    Design Rationale
    ----------------
    Using a protocol (interface) allows us to:
    1. Add new pricing algorithms without modifying the engine
    2. Test strategies in isolation
    3. Switch strategies at runtime via configuration
    4. Maintain backward compatibility

    Implementation Notes
    --------------------
    Strategies should be stateless - all information needed should
    come from the order lists. This allows strategies to be reused
    across multiple auctions without side effects.
    """

    def calculate_clearing_price(
        self, bids: List[Order], asks: List[Order]
    ) -> AuctionClearingResult:
        """Determine the uniform clearing price for a batch auction.

        This is the core method that each strategy must implement.
        It takes the current order book state and determines the
        optimal clearing price according to the strategy's rules.

        Parameters
        ----------
        bids : List[Order]
            Buy orders sorted by price descending (highest first).
            Orders at the same price level may be in any order.
            Example: [Buy 10@128, Buy 5@127.50, Buy 20@127]
        asks : List[Order]
            Sell orders sorted by price ascending (lowest first).
            Orders at the same price level may be in any order.
            Example: [Sell 5@127, Sell 10@127.50, Sell 15@128]

        Returns
        -------
        AuctionClearingResult
            The clearing price and associated information.
            All trades will execute at result.clearing_price.

        Notes
        -----
        The strategy determines the price, not the individual matches.
        The matching engine will handle the actual order execution
        at the determined clearing price, including partial fills
        and randomization at the marginal price.

        Common clearing price rules:

        - Maximum volume: Choose price that maximizes total traded volume
        - Equilibrium: Find where supply meets demand
        - Reference price: Use external reference with bounds
        - VWAP: Volume-weighted average of crossable orders
        """
        ...


class MaximumVolumePricingStrategy:
    """Implements the MV algorithm from arXiv:1304.3135v1 with midpoint selection.

    This strategy maximizes the total trading volume by finding the
    price(s) where the most shares can trade. When multiple prices
    achieve the same maximum volume, it selects the midpoint.

    The algorithm conceptually:

    1. Builds cumulative supply and demand curves
    2. Finds price(s) where total executable volume is maximized
    3. If multiple prices maximize volume, selects midpoint
    4. Returns uniform clearing price

    Why Maximum Volume?
    -------------------

    - Maximizes liquidity provision and market depth
    - Encourages participation by maximizing fills
    - Reduces market impact of large orders
    - Natural price discovery through supply/demand

    Midpoint Modification
    --------------------
    The original paper doesn't specify which price to choose when
    multiple prices maximize volume. We choose the midpoint to:

    - Provide fairness between buyers and sellers
    - Reduce systematic bias toward either side
    - Align with common exchange practices (NYSE, Nasdaq)
    - Create stable, predictable behavior

    Examples
    --------
    Simple case - single crossing price:
    >>> bids = [Order(price=128, quantity=10, ...)]
    >>> asks = [Order(price=127, quantity=10, ...)]
    >>> strategy.calculate_clearing_price(bids, asks)
    AuctionClearingResult(clearing_price=127.5, max_volume=10, ...)

    Multiple prices maximize volume:
    >>> # When prices 99, 100, 101 all allow 30 shares to trade
    >>> # Algorithm selects midpoint: (99 + 101) / 2 = 100
    """

    def calculate_clearing_price(
        self, bids: List[Order], asks: List[Order]
    ) -> AuctionClearingResult:
        """Calculate clearing price using maximum volume algorithm.

        The algorithm finds the price that allows the most shares to
        trade, with midpoint selection for ties.

        Parameters
        ----------
        bids : List[Order]
            Buy orders sorted by price descending
        asks : List[Order]
            Sell orders sorted by price ascending

        Returns
        -------
        AuctionClearingResult
            Clearing price that maximizes volume
        """
        # Defensive check: no orders on either side
        if not bids or not asks:
            return AuctionClearingResult(
                clearing_price=0.0, max_volume=0, algorithm="maximum_volume"
            )

        # Find crossing range
        crossing_range = self._find_crossing_range(bids, asks)
        if crossing_range is None:
            # Defensive: no price overlap between buyers and sellers
            return AuctionClearingResult(
                clearing_price=0.0, max_volume=0, algorithm="maximum_volume"
            )

        min_ask, max_bid = crossing_range

        # Collect prices in crossing range
        crossing_prices = self._collect_crossing_prices(
            bids, asks, min_ask, max_bid
        )

        # Find prices that maximize volume
        optimal_result = self._find_optimal_prices(bids, asks, crossing_prices)
        if optimal_result is None:
            # Defensive: no valid trades despite crossing range
            return AuctionClearingResult(
                clearing_price=0.0, max_volume=0, algorithm="maximum_volume"
            )

        optimal_prices, max_volume = optimal_result

        # Select final clearing price
        clearing_price = self._select_clearing_price(optimal_prices)

        # Defensive validation: ensure consistency
        assert (
            clearing_price > 0
        ), "Clearing price must be positive when trades occur"
        assert max_volume > 0, "Max volume must be positive when trades occur"

        return AuctionClearingResult(
            clearing_price=clearing_price,
            max_volume=max_volume,
            algorithm="maximum_volume",
            price_range=(
                (min(optimal_prices), max(optimal_prices))
                if len(optimal_prices) > 1
                else None
            ),
        )

    def _calculate_volume_at_price(
        self, bids: List[Order], asks: List[Order], price: float
    ) -> int:
        """Calculate maximum tradeable volume at given price.

        At any given price, the tradeable volume is limited by the
        lesser of eligible buy volume and eligible sell volume.

        Parameters
        ----------
        bids : List[Order]
            All buy orders
        asks : List[Order]
            All sell orders
        price : float
            Price to evaluate

        Returns
        -------
        int
            Maximum volume that can trade at this price
        """
        # Calculate eligible volumes
        eligible_buy_volume = sum(
            bid.quantity
            for bid in bids
            if bid.price is not None and bid.price >= price
        )
        eligible_sell_volume = sum(
            ask.quantity
            for ask in asks
            if ask.price is not None and ask.price <= price
        )

        # Volume is limited by the smaller side
        return int(min(eligible_buy_volume, eligible_sell_volume))

    def _find_crossing_range(
        self, bids: List[Order], asks: List[Order]
    ) -> Optional[Tuple[float, float]]:
        """Find the price range where bids and asks overlap.

        Parameters
        ----------
        bids : List[Order]
            Buy orders
        asks : List[Order]
            Sell orders

        Returns
        -------
        Optional[Tuple[float, float]]
            (min_ask, max_bid) if crossing exists, None otherwise
        """
        max_bid = max(bid.price for bid in bids if bid.price is not None)
        min_ask = min(ask.price for ask in asks if ask.price is not None)

        if max_bid < min_ask:
            return None
        return (min_ask, max_bid)

    def _collect_crossing_prices(
        self,
        bids: List[Order],
        asks: List[Order],
        min_ask: float,
        max_bid: float,
    ) -> Set[float]:
        """Collect all unique prices in the crossing range.

        Parameters
        ----------
        bids : List[Order]
            Buy orders
        asks : List[Order]
            Sell orders
        min_ask : float
            Minimum ask price
        max_bid : float
            Maximum bid price

        Returns
        -------
        Set[float]
            All unique prices in crossing range
        """
        all_prices = set()
        for order in bids + asks:
            if order.price is not None and min_ask <= order.price <= max_bid:
                all_prices.add(order.price)
        return all_prices

    def _find_optimal_prices(
        self, bids: List[Order], asks: List[Order], prices: Set[float]
    ) -> Optional[Tuple[List[float], int]]:
        """Find prices that maximize trading volume.

        Parameters
        ----------
        bids : List[Order]
            Buy orders
        asks : List[Order]
            Sell orders
        prices : Set[float]
            Candidate prices to evaluate

        Returns
        -------
        Optional[Tuple[List[float], int]]
            (optimal_prices, max_volume) or None if no volume
        """
        price_volumes: Dict[float, int] = {}
        for price in prices:
            volume = self._calculate_volume_at_price(bids, asks, price)
            price_volumes[price] = volume

        if not price_volumes:
            return None

        max_volume = max(price_volumes.values())
        if max_volume == 0:
            return None

        optimal_prices = [
            price
            for price, volume in price_volumes.items()
            if volume == max_volume
        ]

        return (optimal_prices, max_volume)

    def _select_clearing_price(self, optimal_prices: List[float]) -> float:
        """Select final clearing price from optimal candidates.

        When multiple prices maximize volume, selects midpoint.

        Parameters
        ----------
        optimal_prices : List[float]
            Prices that maximize volume

        Returns
        -------
        float
            Selected clearing price
        """
        if len(optimal_prices) == 1:
            return optimal_prices[0]
        # Multiple prices achieve max volume - select midpoint
        return (min(optimal_prices) + max(optimal_prices)) / 2
