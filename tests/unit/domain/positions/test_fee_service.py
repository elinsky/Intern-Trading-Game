"""Unit tests for TradingFeeService."""

import pytest

from intern_trading_game.domain.positions import (
    FeeSchedule,
    TradingFeeService,
)


class TestTradingFeeService:
    """Test suite for TradingFeeService."""

    @pytest.fixture
    def role_fees(self):
        """Create test fee schedules."""
        return {
            "market_maker": FeeSchedule(0.02, -0.01),
            "hedge_fund": FeeSchedule(0.01, -0.02),
            "retail": FeeSchedule(-0.01, -0.03),
            "arbitrage_desk": FeeSchedule(0.01, -0.02),
        }

    @pytest.fixture
    def fee_service(self, role_fees):
        """Create a TradingFeeService instance."""
        return TradingFeeService(role_fees)

    def test_service_initialization(self, fee_service, role_fees):
        """Test service initializes with fee schedules."""
        assert fee_service.role_fees == role_fees

    def test_calculate_fee_market_maker_maker(self, fee_service):
        """Test market maker receives rebate as maker.

        Given - Market maker providing liquidity
        When - Fee calculated for maker order
        Then - Positive rebate returned
        """
        fee = fee_service.calculate_fee(100, "market_maker", "maker")
        assert fee == 2.00  # 100 * 0.02 = $2.00 rebate

    def test_calculate_fee_market_maker_taker(self, fee_service):
        """Test market maker pays fee as taker.

        Given - Market maker taking liquidity
        When - Fee calculated for taker order
        Then - Negative fee returned
        """
        fee = fee_service.calculate_fee(100, "market_maker", "taker")
        assert fee == -1.00  # 100 * -0.01 = $1.00 fee

    def test_calculate_fee_retail_both_negative(self, fee_service):
        """Test retail pays fees for both maker and taker.

        Given - Retail trader
        When - Fees calculated for maker and taker
        Then - Both return negative fees
        """
        maker_fee = fee_service.calculate_fee(50, "retail", "maker")
        taker_fee = fee_service.calculate_fee(50, "retail", "taker")

        assert maker_fee == -0.50  # 50 * -0.01 = $0.50 fee
        assert taker_fee == -1.50  # 50 * -0.03 = $1.50 fee

    def test_calculate_fee_zero_quantity(self, fee_service):
        """Test fee calculation with zero quantity."""
        fee = fee_service.calculate_fee(0, "market_maker", "maker")
        assert fee == 0.0

    def test_calculate_fee_unknown_role(self, fee_service):
        """Test fee calculation with unknown role raises error."""
        with pytest.raises(KeyError, match="Unknown role: unknown"):
            fee_service.calculate_fee(10, "unknown", "maker")

    def test_calculate_fee_invalid_liquidity_type(self, fee_service):
        """Test fee calculation with invalid liquidity type."""
        with pytest.raises(ValueError, match="Invalid liquidity type"):
            fee_service.calculate_fee(10, "market_maker", "invalid")

    @pytest.mark.parametrize(
        "quantity,role,liquidity_type,expected_fee",
        [
            # Market maker scenarios
            (100, "market_maker", "maker", 2.00),  # Rebate
            (100, "market_maker", "taker", -1.00),  # Fee
            (50, "market_maker", "maker", 1.00),  # Half rebate
            # Hedge fund scenarios
            (100, "hedge_fund", "maker", 1.00),  # Small rebate
            (100, "hedge_fund", "taker", -2.00),  # Larger fee
            # Retail scenarios
            (100, "retail", "maker", -1.00),  # Fee as maker
            (100, "retail", "taker", -3.00),  # Larger fee as taker
            # Edge cases
            (1, "market_maker", "maker", 0.02),  # Single contract
            (1000, "retail", "taker", -30.00),  # Large order
        ],
    )
    def test_fee_calculation_scenarios(
        self, fee_service, quantity, role, liquidity_type, expected_fee
    ):
        """Test various fee calculation scenarios."""
        fee = fee_service.calculate_fee(quantity, role, liquidity_type)
        assert fee == pytest.approx(expected_fee)

    def test_determine_liquidity_type_taker(self, fee_service):
        """Test determining taker liquidity.

        Given - Order side matches aggressor side
        When - Liquidity type determined
        Then - Returns 'taker'
        """
        # Buy order that aggressed
        assert fee_service.determine_liquidity_type("buy", "buy") == "taker"
        # Sell order that aggressed
        assert fee_service.determine_liquidity_type("sell", "sell") == "taker"

    def test_determine_liquidity_type_maker(self, fee_service):
        """Test determining maker liquidity.

        Given - Order side opposite to aggressor side
        When - Liquidity type determined
        Then - Returns 'maker'
        """
        # Sell order hit by buy aggressor
        assert fee_service.determine_liquidity_type("buy", "sell") == "maker"
        # Buy order hit by sell aggressor
        assert fee_service.determine_liquidity_type("sell", "buy") == "maker"

    def test_get_fee_schedule(self, fee_service):
        """Test retrieving complete fee schedule for a role."""
        schedule = fee_service.get_fee_schedule("market_maker")

        assert isinstance(schedule, FeeSchedule)
        assert schedule.maker_rebate == 0.02
        assert schedule.taker_fee == -0.01

    def test_get_fee_schedule_unknown_role(self, fee_service):
        """Test retrieving schedule for unknown role."""
        with pytest.raises(KeyError, match="Unknown role: invalid"):
            fee_service.get_fee_schedule("invalid")

    def test_fee_calculation_consistency(self, fee_service):
        """Test fee calculations are consistent with schedules."""
        # For each role, verify calculations match schedule
        for role in ["market_maker", "hedge_fund", "retail"]:
            schedule = fee_service.get_fee_schedule(role)

            # Test maker fee
            maker_fee = fee_service.calculate_fee(1, role, "maker")
            assert maker_fee == schedule.maker_rebate

            # Test taker fee
            taker_fee = fee_service.calculate_fee(1, role, "taker")
            assert taker_fee == schedule.taker_fee

    def test_service_with_empty_config(self):
        """Test service handles empty configuration gracefully."""
        empty_role_fees = {}
        service = TradingFeeService(empty_role_fees)

        with pytest.raises(KeyError):
            service.calculate_fee(10, "any_role", "maker")
