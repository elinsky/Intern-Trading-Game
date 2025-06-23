"""Service integration tests for fee calculation across the trading pipeline.

Tests how trading fees integrate with order matching, trade processing,
and position management without threading complexity.
"""

from datetime import datetime

from intern_trading_game.domain.exchange.components.core.models import (
    Order,
    OrderSide,
    OrderType,
)
from intern_trading_game.infrastructure.api.models import TeamInfo


class TestFeeCalculationIntegration:
    """Test fee calculation integration across services."""

    def test_market_maker_rebate_calculation(self, service_context):
        """Test market maker receives rebate for providing liquidity.

        Given - Market maker providing liquidity with resting order
        MM places a limit order that sits in the book.
        When another trader hits their quote, MM provides liquidity.
        MMs earn $0.02 rebate per contract for this service.

        When - Order fills against resting liquidity
        Incoming market order matches MM's resting limit order.
        TradeProcessingService calculates fees based on liquidity type.

        Then - MM receives maker rebate, taker pays fee
        MM gets +$0.02 per contract (positive = money received).
        Taker pays -$0.05 per contract (negative = money paid).
        Fee calculation correctly identifies liquidity roles.
        """
        # Given - Market maker providing liquidity
        market_maker = TeamInfo(
            team_id="MM_REBATE_TEST",
            team_name="Rebate Test MM",
            role="market_maker",
            api_key="rebate_key",
            created_at=datetime.now(),
        )

        retail_trader = TeamInfo(
            team_id="RETAIL_TAKER",
            team_name="Retail Taker",
            role="retail",  # Will pay taker fees
            api_key="retail_key",
            created_at=datetime.now(),
        )

        # Initialize positions
        positions = service_context["positions"]
        positions[market_maker.team_id] = {}
        positions[retail_trader.team_id] = {}

        # MM places resting sell order (provides liquidity)
        mm_order = Order(
            trader_id=market_maker.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=10,
            price=128.50,
        )

        # Submit MM order (becomes resting liquidity)
        mm_result = service_context[
            "matching_service"
        ].submit_order_to_exchange(mm_order)
        assert mm_result.status == "new"

        # Retail trader submits market buy (takes liquidity)
        retail_order = Order(
            trader_id=retail_trader.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=10,
        )

        # When - Market order hits resting liquidity
        retail_result = service_context[
            "matching_service"
        ].submit_order_to_exchange(retail_order)

        # Should fill immediately
        assert retail_result.status == "filled"
        assert len(retail_result.fills) == 1
        fill = retail_result.fills[0]
        assert fill.quantity == 10
        assert fill.price == 128.50

        # Process trade for retail trader (taker)
        retail_response = service_context[
            "trade_service"
        ].process_trade_result(retail_result, retail_order, retail_trader)

        # Then - Verify taker fees
        assert retail_response.status == "filled"
        assert retail_response.fees is not None
        assert retail_response.liquidity_type == "taker"

        # Retail pays taker fee: -$0.05 per contract
        expected_taker_fee = -0.05 * 10  # -$0.50
        assert retail_response.fees == expected_taker_fee

        # Process trade for market maker (maker) - need to create maker result
        # In real system, both sides get trade events
        mm_trade_result = retail_result  # Same trade, different perspective
        mm_trade_result.trader_id = (
            market_maker.team_id
        )  # Simulate MM perspective

        mm_response = service_context["trade_service"].process_trade_result(
            mm_trade_result, mm_order, market_maker
        )

        # MM gets maker rebate: +$0.02 per contract
        expected_maker_rebate = 0.02 * 10  # +$0.20
        assert mm_response.fees == expected_maker_rebate
        assert mm_response.liquidity_type == "maker"

    def test_hedge_fund_fee_structure(self, service_context):
        """Test hedge fund fee calculation differs from market makers.

        Given - Hedge fund trading (no maker rebates)
        HFs don't get the enhanced $0.02 maker rebate.
        They pay standard $0.05 taker fees like everyone else.

        When - HF provides and takes liquidity
        Test both maker and taker scenarios for hedge fund.

        Then - No maker rebate, standard taker fees
        HF gets $0.00 for providing liquidity (no rebate).
        HF pays -$0.05 for taking liquidity (standard fee).
        """
        # Given - Hedge fund team
        hedge_fund = TeamInfo(
            team_id="HF_FEE_TEST",
            team_name="Test Hedge Fund",
            role="hedge_fund",
            api_key="hf_key",
            created_at=datetime.now(),
        )

        retail_trader = TeamInfo(
            team_id="RETAIL_TRADER",
            team_name="Retail Test",
            role="retail",
            api_key="retail_key_2",
            created_at=datetime.now(),
        )

        # Initialize positions
        positions = service_context["positions"]
        positions[hedge_fund.team_id] = {}
        positions[retail_trader.team_id] = {}

        # HF places resting order (maker scenario)
        hf_order = Order(
            trader_id=hedge_fund.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=5,
            price=127.00,
        )

        hf_result = service_context[
            "matching_service"
        ].submit_order_to_exchange(hf_order)
        assert hf_result.status == "new"

        # Retail hits HF order
        retail_order = Order(
            trader_id=retail_trader.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=5,
            price=127.00,
        )

        retail_result = service_context[
            "matching_service"
        ].submit_order_to_exchange(retail_order)
        assert retail_result.status == "filled"

        # Process HF trade (maker)
        hf_response = service_context["trade_service"].process_trade_result(
            retail_result, hf_order, hedge_fund
        )

        # Then - HF gets no maker rebate (unlike market makers)
        assert hf_response.fees == 0.0  # No rebate
        assert hf_response.liquidity_type == "maker"

        # Test HF as taker
        hf_taker_order = Order(
            trader_id=hedge_fund.team_id,
            instrument_id="SPX_4500_PUT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=3,
        )

        # Need liquidity for HF to take
        retail_maker_order = Order(
            trader_id=retail_trader.team_id,
            instrument_id="SPX_4500_PUT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=3,
            price=50.00,
        )

        service_context["matching_service"].submit_order_to_exchange(
            retail_maker_order
        )

        hf_taker_result = service_context[
            "matching_service"
        ].submit_order_to_exchange(hf_taker_order)
        hf_taker_response = service_context[
            "trade_service"
        ].process_trade_result(hf_taker_result, hf_taker_order, hedge_fund)

        # HF pays standard taker fee
        expected_taker_fee = -0.05 * 3  # -$0.15
        assert hf_taker_response.fees == expected_taker_fee
        assert hf_taker_response.liquidity_type == "taker"

    def test_fee_calculation_with_partial_fills(self, service_context):
        """Test fee calculation accuracy with partial order fills.

        Given - Large order that fills partially across multiple resting orders
        Incoming order for 20 contracts.
        Book has 3 resting orders: 5@128.00, 8@128.25, 10@128.50.

        When - Large order sweeps multiple price levels
        TradeProcessingService must calculate fees for each fill.
        Each fill may have different liquidity provider.

        Then - Fees calculated correctly per fill
        Each fill generates appropriate maker/taker fees.
        Total fees sum correctly across all fills.
        """
        # Given - Multiple market makers providing liquidity at different levels
        mm1 = TeamInfo(
            team_id="MM1",
            team_name="MM 1",
            role="market_maker",
            api_key="mm1",
            created_at=datetime.now(),
        )
        mm2 = TeamInfo(
            team_id="MM2",
            team_name="MM 2",
            role="market_maker",
            api_key="mm2",
            created_at=datetime.now(),
        )
        mm3 = TeamInfo(
            team_id="MM3",
            team_name="MM 3",
            role="market_maker",
            api_key="mm3",
            created_at=datetime.now(),
        )

        large_buyer = TeamInfo(
            team_id="BUYER",
            team_name="Large Buyer",
            role="retail",
            api_key="buyer",
            created_at=datetime.now(),
        )

        # Initialize positions
        positions = service_context["positions"]
        for team in [mm1, mm2, mm3, large_buyer]:
            positions[team.team_id] = {}

        # Build order book with multiple levels
        orders = [
            (
                mm1,
                Order(
                    trader_id=mm1.team_id,
                    instrument_id="SPX_4500_CALL",
                    order_type=OrderType.LIMIT,
                    side=OrderSide.SELL,
                    quantity=5,
                    price=128.00,
                ),
            ),
            (
                mm2,
                Order(
                    trader_id=mm2.team_id,
                    instrument_id="SPX_4500_CALL",
                    order_type=OrderType.LIMIT,
                    side=OrderSide.SELL,
                    quantity=8,
                    price=128.25,
                ),
            ),
            (
                mm3,
                Order(
                    trader_id=mm3.team_id,
                    instrument_id="SPX_4500_CALL",
                    order_type=OrderType.LIMIT,
                    side=OrderSide.SELL,
                    quantity=10,
                    price=128.50,
                ),
            ),
        ]

        # Submit all maker orders
        for team, order in orders:
            result = service_context[
                "matching_service"
            ].submit_order_to_exchange(order)
            assert result.status == "new"

        # Large buy order that sweeps book
        large_order = Order(
            trader_id=large_buyer.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=20,  # Will partially fill (5+8+7=20, leaves 3 unfilled)
        )

        # When - Submit large order
        result = service_context["matching_service"].submit_order_to_exchange(
            large_order
        )

        # Should partially fill
        assert result.status in ["filled", "partially_filled"]
        assert len(result.fills) >= 2  # Multiple fills across price levels

        # Process trade
        response = service_context["trade_service"].process_trade_result(
            result, large_order, large_buyer
        )

        # Then - Verify fee calculation
        total_filled = sum(fill.quantity for fill in result.fills)
        expected_taker_fee = -0.05 * total_filled

        assert response.fees == expected_taker_fee
        assert response.liquidity_type == "taker"
        assert response.filled_quantity == total_filled

    def test_position_update_with_fees_integration(self, service_context):
        """Test positions update correctly alongside fee tracking.

        Given - Market maker trading with fee calculations
        MM both provides and takes liquidity in same session.
        Positions should reflect net trading activity.

        When - Multiple trades with different fee structures
        MM makes market and also takes liquidity.

        Then - Positions and fees tracked independently and correctly
        Position reflects net contract quantities.
        Fees accumulate separately from position.
        Both systems maintain consistency.
        """
        # Given - Active market maker
        mm = TeamInfo(
            team_id="MM_POSITION_FEE",
            team_name="Position Fee Test MM",
            role="market_maker",
            api_key="pos_fee_key",
            created_at=datetime.now(),
        )

        counterparty = TeamInfo(
            team_id="COUNTERPARTY",
            team_name="Counterparty",
            role="retail",
            api_key="counter_key",
            created_at=datetime.now(),
        )

        # Initialize positions
        positions = service_context["positions"]
        positions[mm.team_id] = {}
        positions[counterparty.team_id] = {}

        # Trade 1: MM provides liquidity (should get rebate)
        mm_sell = Order(
            trader_id=mm.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=10,
            price=128.00,
        )

        service_context["matching_service"].submit_order_to_exchange(mm_sell)

        counter_buy = Order(
            trader_id=counterparty.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=10,
        )

        result1 = service_context["matching_service"].submit_order_to_exchange(
            counter_buy
        )
        response1 = service_context["trade_service"].process_trade_result(
            result1, mm_sell, mm
        )

        # Verify first trade
        mm_positions = service_context["position_service"].get_positions(
            mm.team_id
        )
        assert mm_positions["SPX_4500_CALL"] == -10  # Sold 10
        assert response1.fees == 0.02 * 10  # Maker rebate
        assert response1.liquidity_type == "maker"

        # Trade 2: MM takes liquidity (should pay fee)
        counter_sell = Order(
            trader_id=counterparty.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=5,
            price=127.50,
        )

        service_context["matching_service"].submit_order_to_exchange(
            counter_sell
        )

        mm_buy = Order(
            trader_id=mm.team_id,
            instrument_id="SPX_4500_CALL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=5,
        )

        result2 = service_context["matching_service"].submit_order_to_exchange(
            mm_buy
        )
        response2 = service_context["trade_service"].process_trade_result(
            result2, mm_buy, mm
        )

        # Then - Verify final state
        mm_positions_final = service_context["position_service"].get_positions(
            mm.team_id
        )
        assert mm_positions_final["SPX_4500_CALL"] == -5  # Net: -10 + 5 = -5
        assert response2.fees == -0.05 * 5  # Taker fee
        assert response2.liquidity_type == "taker"

        # Position correctly reflects net trading
        # Fees calculated per trade based on liquidity role
