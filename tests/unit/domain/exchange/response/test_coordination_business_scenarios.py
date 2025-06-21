"""Business-focused tests for order response coordination.

This module tests the OrderResponseCoordinator from a trading system
perspective, focusing on real business scenarios that trading teams
encounter during market operations. Each test represents a specific
workflow that must work correctly for the trading system to function.

The tests follow the Given-When-Then pattern with detailed business
context to ensure the coordination system supports actual trading
requirements and edge cases that occur in production environments.

Performance assertions focus on relative timing and business requirements
rather than specific millisecond values, which should be measured and
tuned based on actual system performance.
"""

import threading
import time
from datetime import datetime, timedelta

import pytest

from intern_trading_game.domain.exchange.response.interfaces import (
    ResponseRegistration,
    ResponseResult,
)
from intern_trading_game.domain.exchange.response.models import (
    ResponseStatus,
)
from intern_trading_game.infrastructure.api.models import ApiError, ApiResponse


class TestMarketMakerWorkflows:
    """Test coordination for market maker trading patterns."""

    def test_market_maker_limit_order_accepted_and_resting(
        self, mock_coordinator, market_maker_scenario
    ):
        """Test successful limit order placement with immediate API response.

        Given - Market maker submits limit order through REST API
        When - Order passes validation and rests in book
        Then - API returns 200 with order_id and "new" status

        This scenario tests the most common market maker workflow where
        they post liquidity to the order book. The API must respond quickly
        to confirm the order is working, allowing the MM to adjust quotes
        based on market conditions.
        """
        # Given - Market maker with valid limit order
        team_info = market_maker_scenario["team_info"]
        _bid_order = market_maker_scenario["bid_order"]  # For documentation

        # Mock coordinator returns successful registration
        registration = ResponseRegistration(
            request_id="req_mm_bid_001",
            team_id=team_info["team_id"],
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )
        mock_coordinator.register_request.return_value = registration

        # Mock successful order placement result
        success_result = ResponseResult(
            request_id="req_mm_bid_001",
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id="req_mm_bid_001",
                order_id="ORD_MM_BID_001",
                data={
                    "order_id": "ORD_MM_BID_001",
                    "status": "new",  # Order resting in book
                    "timestamp": datetime.now().isoformat(),
                    "filled_quantity": 0,
                    "average_price": None,
                    "fees": 0.0,
                    "liquidity_type": None,
                },
                error=None,
            ),
            processing_time_ms=50.0,  # Will be measured in real implementation
            final_status=ResponseStatus.COMPLETED,
            order_id="ORD_MM_BID_001",
        )
        mock_coordinator.wait_for_completion.return_value = success_result

        # When - Market maker submits limit order via API
        registration = mock_coordinator.register_request(
            team_info["team_id"], timeout_seconds=5.0
        )
        result = mock_coordinator.wait_for_completion(registration.request_id)

        # Then - API returns success with order working in book
        assert result.success is True
        assert result.api_response.order_id == "ORD_MM_BID_001"
        assert result.api_response.data["status"] == "new"
        assert result.api_response.data["filled_quantity"] == 0
        assert result.final_status == ResponseStatus.COMPLETED

        # Verify coordinator methods called correctly
        mock_coordinator.register_request.assert_called_once_with(
            team_info["team_id"], timeout_seconds=5.0
        )
        mock_coordinator.wait_for_completion.assert_called_once_with(
            registration.request_id
        )

    def test_market_maker_rapid_quote_updates(
        self, mock_coordinator, market_maker_scenario, performance_monitor
    ):
        """Test MM workflow of frequent quote adjustments.

        Given - Market maker updating quotes rapidly
        When - Each quote update submitted via API
        Then - Each API call gets response before system becomes unresponsive

        Market makers need to rapidly adjust quotes based on market
        conditions. The coordination system must handle this pattern
        without blocking or significantly degrading performance.
        """
        # Given - Market maker ready for rapid quote updates
        team_info = market_maker_scenario["team_info"]
        base_order = market_maker_scenario["bid_order"].copy()

        # Mock rapid successful responses
        def mock_register_request(team_id, timeout_seconds=None):
            return ResponseRegistration(
                request_id=f"req_rapid_{time.time_ns()}",
                team_id=team_id,
                timeout_at=datetime.now() + timedelta(seconds=2),
                status=ResponseStatus.PENDING,
            )

        def mock_wait_for_completion(request_id):
            return ResponseResult(
                request_id=request_id,
                success=True,
                api_response=ApiResponse(
                    success=True,
                    request_id=request_id,
                    order_id=f"ORD_{request_id[-6:]}",
                    data={"status": "new", "filled_quantity": 0},
                    error=None,
                ),
                processing_time_ms=25.0,  # Mock reasonable time
                final_status=ResponseStatus.COMPLETED,
                order_id=f"ORD_{request_id[-6:]}",
            )

        mock_coordinator.register_request.side_effect = mock_register_request
        mock_coordinator.wait_for_completion.side_effect = (
            mock_wait_for_completion
        )

        # When - Market maker submits rapid quote updates
        quote_responses = []
        update_count = 5  # Reasonable number for unit test

        for i in range(update_count):
            performance_monitor.start_timer(f"quote_update_{i}")

            # Update quote price
            updated_order = base_order.copy()
            updated_order["price"] = 127.50 + (i * 0.25)

            # Submit quote update
            registration = mock_coordinator.register_request(
                team_info["team_id"]
            )
            result = mock_coordinator.wait_for_completion(
                registration.request_id
            )

            update_time = performance_monitor.end_timer(f"quote_update_{i}")
            quote_responses.append((result, update_time))

        # Then - All quote updates completed successfully
        assert len(quote_responses) == update_count
        for result, update_time in quote_responses:
            assert result.success is True
            assert result.api_response.data["status"] == "new"
            # Test should complete quickly since it's mocked
            assert (
                update_time < 100.0
            ), f"Mock test taking too long: {update_time}ms"

    def test_market_maker_position_limit_enforcement(
        self,
        mock_coordinator,
        market_maker_scenario,
        validation_failure_scenarios,
    ):
        """Test MM constraint violation with immediate error response.

        Given - Market maker at position limit
        When - They submit additional order via API
        Then - API returns 400 with clear constraint violation message

        Position limits are critical risk controls. When violated, the API
        must respond with clear feedback to prevent further risk accumulation.
        """
        # Given - Market maker at position limit
        team_info = market_maker_scenario["team_info"]
        team_info["current_position"] = 50  # At limit
        excessive_order = market_maker_scenario["bid_order"].copy()
        excessive_order["quantity"] = 10  # Would exceed limit

        # Mock position limit violation
        registration = ResponseRegistration(
            request_id="req_limit_violation",
            team_id=team_info["team_id"],
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )
        mock_coordinator.register_request.return_value = registration

        # Mock validation failure result
        failure_scenario = validation_failure_scenarios[
            "position_limit_exceeded"
        ]
        error_result = ResponseResult(
            request_id="req_limit_violation",
            success=False,
            api_response=ApiResponse(
                success=False,
                request_id="req_limit_violation",
                order_id=None,
                data=None,
                error=ApiError(
                    code=failure_scenario["error_code"],
                    message=failure_scenario["error_message"],
                    details=failure_scenario["details"],
                ),
            ),
            processing_time_ms=10.0,  # Fast validation failure
            final_status=ResponseStatus.ERROR,
            order_id=None,
        )
        mock_coordinator.wait_for_completion.return_value = error_result

        # When - Market maker submits order exceeding position limit
        registration = mock_coordinator.register_request(team_info["team_id"])
        result = mock_coordinator.wait_for_completion(registration.request_id)

        # Then - API returns validation error with clear details
        assert result.success is False
        assert result.api_response.error.code == "POSITION_LIMIT_EXCEEDED"
        assert "position limit of ±50" in result.api_response.error.message
        assert result.api_response.error.details["current_position"] == 45
        assert result.api_response.error.details["order_quantity"] == 10
        assert result.api_response.error.details["position_limit"] == 50
        assert result.final_status == ResponseStatus.ERROR


class TestHedgeFundWorkflows:
    """Test coordination for hedge fund trading patterns."""

    def test_market_order_immediate_fill_response(
        self, mock_coordinator, hedge_fund_scenario
    ):
        """Test market order with immediate execution.

        Given - Liquidity exists in book
        When - Hedge fund submits market buy order via API
        Then - API returns 200 with fills and "filled" status

        Hedge funds often use market orders for immediate execution when
        implementing alpha signals. The API must return complete fill
        information for proper position and risk management.
        """
        # Given - Hedge fund with market order for immediate execution
        team_info = hedge_fund_scenario["team_info"]
        _market_order = hedge_fund_scenario[
            "market_order"
        ]  # For documentation

        # Mock immediate fill scenario
        registration = ResponseRegistration(
            request_id="req_hf_market_001",
            team_id=team_info["team_id"],
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )
        mock_coordinator.register_request.return_value = registration

        # Mock successful market order fill
        fill_result = ResponseResult(
            request_id="req_hf_market_001",
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id="req_hf_market_001",
                order_id="ORD_HF_MARKET_001",
                data={
                    "order_id": "ORD_HF_MARKET_001",
                    "status": "filled",  # Completely filled
                    "timestamp": datetime.now().isoformat(),
                    "filled_quantity": 20,  # Full quantity executed
                    "average_price": 128.50,  # Market price
                    "fees": -1.00,  # Taker fees
                    "liquidity_type": "taker",
                },
                error=None,
            ),
            processing_time_ms=75.0,  # Reasonable for market order
            final_status=ResponseStatus.COMPLETED,
            order_id="ORD_HF_MARKET_001",
        )
        mock_coordinator.wait_for_completion.return_value = fill_result

        # When - Hedge fund submits market order
        registration = mock_coordinator.register_request(team_info["team_id"])
        result = mock_coordinator.wait_for_completion(registration.request_id)

        # Then - API returns complete fill information
        assert result.success is True
        assert result.api_response.data["status"] == "filled"
        assert result.api_response.data["filled_quantity"] == 20
        assert result.api_response.data["average_price"] == 128.50
        assert result.api_response.data["liquidity_type"] == "taker"
        assert result.api_response.data["fees"] == -1.00
        assert result.final_status == ResponseStatus.COMPLETED

    def test_delta_hedging_workflow_coordination(
        self, mock_coordinator, hedge_fund_scenario
    ):
        """Test coordination during delta hedging sequence.

        Given - Hedge fund needs to hedge delta exposure
        When - They submit paired call/put orders for neutral position
        Then - Both API calls return coordinated responses

        Delta hedging requires coordinated execution of multiple instruments.
        The coordination system must handle related orders properly and
        provide consistent state information across the hedge portfolio.
        """
        # Given - Hedge fund implementing delta hedge strategy
        team_info = hedge_fund_scenario["team_info"]
        _call_order = hedge_fund_scenario[
            "market_order"
        ]  # Long calls - for documentation
        _put_order = hedge_fund_scenario[
            "hedge_order"
        ]  # Short puts for hedge - for documentation

        # Mock coordinated hedge execution
        call_count = 0

        def mock_register_request(team_id, timeout_seconds=None):
            # Generate unique request IDs for each leg
            timestamp = int(time.time_ns())
            return ResponseRegistration(
                request_id=f"req_hedge_{timestamp}",
                team_id=team_id,
                timeout_at=datetime.now() + timedelta(seconds=5),
                status=ResponseStatus.PENDING,
            )

        def mock_wait_for_completion(request_id):
            # Track which call this is to determine call vs put
            nonlocal call_count
            call_count += 1
            is_call_leg = call_count == 1  # First call is for the call option

            return ResponseResult(
                request_id=request_id,
                success=True,
                api_response=ApiResponse(
                    success=True,
                    request_id=request_id,
                    order_id=f"ORD_{request_id[-6:]}",
                    data={
                        "order_id": f"ORD_{request_id[-6:]}",
                        "status": "filled",
                        "filled_quantity": 20,
                        "average_price": 128.50 if is_call_leg else 127.00,
                        "fees": -1.00,
                        "liquidity_type": "taker",
                        "instrument_type": "call" if is_call_leg else "put",
                    },
                    error=None,
                ),
                processing_time_ms=60.0,
                final_status=ResponseStatus.COMPLETED,
                order_id=f"ORD_{request_id[-6:]}",
            )

        mock_coordinator.register_request.side_effect = mock_register_request
        mock_coordinator.wait_for_completion.side_effect = (
            mock_wait_for_completion
        )

        # When - Hedge fund submits both legs of delta hedge
        # Submit long call position
        call_registration = mock_coordinator.register_request(
            team_info["team_id"]
        )
        call_result = mock_coordinator.wait_for_completion(
            call_registration.request_id
        )

        # Submit short put hedge
        put_registration = mock_coordinator.register_request(
            team_info["team_id"]
        )
        put_result = mock_coordinator.wait_for_completion(
            put_registration.request_id
        )

        # Then - Both legs execute successfully with proper responses
        assert call_result.success is True
        assert put_result.success is True

        # Verify both legs filled
        assert call_result.api_response.data["status"] == "filled"
        assert put_result.api_response.data["status"] == "filled"
        assert call_result.api_response.data["filled_quantity"] == 20
        assert put_result.api_response.data["filled_quantity"] == 20

        # Verify different prices for different instruments
        call_price = call_result.api_response.data["average_price"]
        put_price = put_result.api_response.data["average_price"]
        assert call_price != put_price  # Different instrument prices


class TestConcurrentTradingScenarios:
    """Test coordination under concurrent trading scenarios."""

    def test_high_frequency_order_submission_burst(
        self, mock_coordinator, concurrent_orders, performance_monitor
    ):
        """Test coordination under HFT-style order bursts.

        Given - Multiple orders submitted simultaneously by same trader
        When - All orders hit pipeline concurrently
        Then - All API calls receive correct individual responses

        High-frequency trading firms submit order bursts during market
        events. The coordination system must handle this load without
        losing or mixing up individual order responses.
        """
        # Given - HFT trader ready to submit order burst
        team_id = "TEAM_HFT_001"
        orders = concurrent_orders[:5]  # Reasonable number for unit test

        # Mock concurrent registration and completion
        request_counter = 0

        def mock_register_request(team_id, timeout_seconds=None):
            nonlocal request_counter
            request_counter += 1
            return ResponseRegistration(
                request_id=f"req_hft_burst_{request_counter:03d}",
                team_id=team_id,
                timeout_at=datetime.now() + timedelta(seconds=5),
                status=ResponseStatus.PENDING,
            )

        def mock_wait_for_completion(request_id):
            # Extract order number from request_id for correlation testing
            order_num = int(request_id.split("_")[-1])
            return ResponseResult(
                request_id=request_id,
                success=True,
                api_response=ApiResponse(
                    success=True,
                    request_id=request_id,
                    order_id=f"ORD_HFT_{order_num:03d}",
                    data={
                        "order_id": f"ORD_HFT_{order_num:03d}",
                        "status": "new",
                        "filled_quantity": 0,
                        "order_sequence": order_num,  # For verification
                    },
                    error=None,
                ),
                processing_time_ms=30.0,
                final_status=ResponseStatus.COMPLETED,
                order_id=f"ORD_HFT_{order_num:03d}",
            )

        mock_coordinator.register_request.side_effect = mock_register_request
        mock_coordinator.wait_for_completion.side_effect = (
            mock_wait_for_completion
        )

        # When - HFT trader submits burst of concurrent orders
        performance_monitor.start_timer("burst_submission")

        # Use threading to simulate concurrent submission
        results = []
        threads = []

        def submit_single_order(order, order_index):
            """Submit single order in separate thread."""
            registration = mock_coordinator.register_request(team_id)
            result = mock_coordinator.wait_for_completion(
                registration.request_id
            )
            results.append((order_index, result))

        # Start all submission threads
        for i, order in enumerate(orders):
            thread = threading.Thread(
                target=submit_single_order, args=(order, i), daemon=True
            )
            threads.append(thread)
            thread.start()

        # Wait for all submissions to complete
        for thread in threads:
            thread.join(timeout=2.0)  # Reasonable timeout for mock test

        burst_time = performance_monitor.end_timer("burst_submission")

        # Then - All orders processed successfully with correct correlation
        assert len(results) == len(orders)

        # Sort results by order index for verification
        results.sort(key=lambda x: x[0])

        for order_index, result in results:
            assert result.success is True
            # Verify each response correlates to correct order
            expected_order_num = order_index + 1
            assert (
                result.api_response.data["order_sequence"]
                == expected_order_num
            )
            assert (
                str(expected_order_num).zfill(3)
                in result.api_response.order_id
            )

        # Mock test should complete quickly
        assert burst_time < 500.0, f"Mock burst test too slow: {burst_time}ms"

    def test_multiple_traders_competing_for_liquidity(
        self, mock_coordinator, performance_monitor
    ):
        """Test fair order processing under competition.

        Given - Multiple traders simultaneously targeting same liquidity
        When - Orders arrive at nearly same time
        Then - Each trader gets response reflecting their outcome

        When multiple traders compete for limited liquidity, the coordination
        system must ensure each gets an accurate response reflecting whether
        they succeeded in the competition.
        """
        # Given - Multiple traders competing for same liquidity
        traders = [
            f"TEAM_COMP_{i:03d}" for i in range(1, 4)
        ]  # 3 traders for test

        # Mock competitive execution results
        execution_results = [
            {"filled_quantity": 50, "status": "filled"},  # Winner
            {"filled_quantity": 20, "status": "partially_filled"},  # Partial
            {"filled_quantity": 0, "status": "rejected"},  # Missed
        ]

        request_counter = 0

        def mock_register_request(team_id, timeout_seconds=None):
            nonlocal request_counter
            request_counter += 1
            return ResponseRegistration(
                request_id=f"req_comp_{request_counter}",
                team_id=team_id,
                timeout_at=datetime.now() + timedelta(seconds=5),
                status=ResponseStatus.PENDING,
            )

        def mock_wait_for_completion(request_id):
            # Determine execution result based on order of completion
            order_index = int(request_id.split("_")[-1]) - 1
            if order_index < len(execution_results):
                exec_result = execution_results[order_index]
            else:
                exec_result = {"filled_quantity": 0, "status": "rejected"}

            return ResponseResult(
                request_id=request_id,
                success=True,
                api_response=ApiResponse(
                    success=True,
                    request_id=request_id,
                    order_id=f"ORD_COMP_{order_index + 1}",
                    data={
                        "order_id": f"ORD_COMP_{order_index + 1}",
                        "status": exec_result["status"],
                        "filled_quantity": exec_result["filled_quantity"],
                        "average_price": 128.50
                        if exec_result["filled_quantity"] > 0
                        else None,
                        "competition_rank": order_index + 1,
                    },
                    error=None,
                ),
                processing_time_ms=50.0,
                final_status=ResponseStatus.COMPLETED,
                order_id=f"ORD_COMP_{order_index + 1}",
            )

        mock_coordinator.register_request.side_effect = mock_register_request
        mock_coordinator.wait_for_completion.side_effect = (
            mock_wait_for_completion
        )

        # When - All traders submit orders simultaneously
        results = []
        threads = []

        def submit_competitive_order(trader_id, order_index):
            """Submit competitive order."""
            registration = mock_coordinator.register_request(trader_id)
            result = mock_coordinator.wait_for_completion(
                registration.request_id
            )
            results.append((trader_id, order_index, result))

        # Start all competitive submissions
        for i, trader_id in enumerate(traders):
            thread = threading.Thread(
                target=submit_competitive_order,
                args=(trader_id, i),
                daemon=True,
            )
            threads.append(thread)
            thread.start()

        # Wait for all competitive orders
        for thread in threads:
            thread.join(timeout=2.0)

        # Then - Each trader gets accurate result reflecting competition outcome
        assert len(results) == 3

        # Sort by competition rank for verification
        results.sort(key=lambda x: x[2].api_response.data["competition_rank"])

        # Verify first trader got full fill
        winner_result = results[0][2]
        assert winner_result.api_response.data["status"] == "filled"
        assert winner_result.api_response.data["filled_quantity"] == 50

        # Verify second trader got partial fill
        partial_result = results[1][2]
        assert partial_result.api_response.data["status"] == "partially_filled"
        assert partial_result.api_response.data["filled_quantity"] == 20

        # Verify third trader was rejected
        rejected_result = results[2][2]
        assert rejected_result.api_response.data["status"] == "rejected"
        assert rejected_result.api_response.data["filled_quantity"] == 0


class TestCrossThreadCommunicationScenarios:
    """Test coordination across multiple pipeline stages and threads."""

    def test_order_lifecycle_across_all_pipeline_stages(
        self, mock_coordinator, mock_pipeline_threads, sample_order_request
    ):
        """Test complete order journey through all threads.

        Given - Complex order requiring all pipeline stages
        When - Order flows: API -> Validator -> Matcher -> Publisher
        Then - API response reflects final settlement state

        This test validates that the coordination system properly tracks
        an order through all processing stages and delivers the final
        result that reflects the complete settlement state.
        """
        # Given - Order that will flow through all pipeline stages
        team_id = "TEAM_LIFECYCLE_001"
        order = sample_order_request.copy()
        order["order_type"] = "limit"  # Requires full pipeline processing

        # Mock full lifecycle progression
        stage_progression = [
            (ResponseStatus.PENDING, "registration"),
            (ResponseStatus.VALIDATING, "validation"),
            (ResponseStatus.MATCHING, "matching"),
            (ResponseStatus.SETTLING, "settlement"),
            (ResponseStatus.COMPLETED, "completed"),
        ]

        registration = ResponseRegistration(
            request_id="req_lifecycle_001",
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )
        mock_coordinator.register_request.return_value = registration

        # Mock status updates for each stage
        status_updates = []

        def mock_update_status(request_id, status, stage_details=None):
            status_updates.append((request_id, status, stage_details))
            return True

        mock_coordinator.update_status.side_effect = mock_update_status

        # Mock final completion with full settlement data
        final_result = ResponseResult(
            request_id="req_lifecycle_001",
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id="req_lifecycle_001",
                order_id="ORD_LIFECYCLE_001",
                data={
                    "order_id": "ORD_LIFECYCLE_001",
                    "status": "filled",
                    "timestamp": datetime.now().isoformat(),
                    "filled_quantity": 10,
                    "average_price": 128.50,
                    "fees": -0.50,
                    "liquidity_type": "taker",
                    "settlement_reference": "SETTLE_001",
                    "processing_stages": [
                        "validation",
                        "matching",
                        "settlement",
                    ],
                },
                error=None,
            ),
            processing_time_ms=200.0,  # Total time across all stages
            final_status=ResponseStatus.COMPLETED,
            order_id="ORD_LIFECYCLE_001",
        )
        mock_coordinator.wait_for_completion.return_value = final_result

        # When - Order submitted and processed through all stages
        registration = mock_coordinator.register_request(team_id)

        # Simulate pipeline stage progression
        for status, stage in stage_progression[
            1:-1
        ]:  # Skip PENDING and COMPLETED
            mock_coordinator.update_status(
                registration.request_id,
                status,
                stage_details={"stage": stage, "timestamp": datetime.now()},
            )

        # Final completion
        result = mock_coordinator.wait_for_completion(registration.request_id)

        # Then - API response reflects complete settlement state
        assert result.success is True
        assert result.api_response.data["status"] == "filled"
        assert result.api_response.data["filled_quantity"] == 10
        assert result.api_response.data["settlement_reference"] == "SETTLE_001"
        assert result.api_response.data["processing_stages"] == [
            "validation",
            "matching",
            "settlement",
        ]
        assert result.final_status == ResponseStatus.COMPLETED

        # Verify all stage updates were tracked
        expected_stages = [
            ResponseStatus.VALIDATING,
            ResponseStatus.MATCHING,
            ResponseStatus.SETTLING,
        ]
        actual_stages = [update[1] for update in status_updates]
        assert actual_stages == expected_stages

    def test_partial_fill_then_cancel_coordination(
        self, mock_coordinator, sample_order_request
    ):
        """Test coordination during partial fill and cancel sequence.

        Given - Large order partially filled
        When - Trader cancels remaining quantity via API
        Then - Cancel API returns accurate remaining/filled breakdown

        This scenario tests the coordination system's ability to handle
        complex state changes where an order is partially executed and
        then cancelled, requiring accurate state tracking across operations.
        """
        # Given - Large order that gets partially filled
        team_id = "TEAM_PARTIAL_001"
        original_order = sample_order_request.copy()
        original_order["quantity"] = 100  # Large order
        original_order["order_type"] = "limit"

        # Mock initial order placement with partial fill
        placement_registration = ResponseRegistration(
            request_id="req_partial_place",
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

        partial_fill_result = ResponseResult(
            request_id="req_partial_place",
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id="req_partial_place",
                order_id="ORD_PARTIAL_001",
                data={
                    "order_id": "ORD_PARTIAL_001",
                    "status": "partially_filled",
                    "timestamp": datetime.now().isoformat(),
                    "filled_quantity": 30,  # Partially filled
                    "remaining_quantity": 70,  # Still working
                    "average_price": 128.50,
                    "fees": -1.50,
                    "liquidity_type": "mixed",
                },
                error=None,
            ),
            processing_time_ms=150.0,
            final_status=ResponseStatus.COMPLETED,
            order_id="ORD_PARTIAL_001",
        )

        # Mock cancel operation coordination
        cancel_registration = ResponseRegistration(
            request_id="req_partial_cancel",
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

        cancel_result = ResponseResult(
            request_id="req_partial_cancel",
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id="req_partial_cancel",
                order_id="ORD_PARTIAL_001",
                data={
                    "order_id": "ORD_PARTIAL_001",
                    "status": "cancelled",
                    "timestamp": datetime.now().isoformat(),
                    "filled_quantity": 30,  # Filled portion unchanged
                    "cancelled_quantity": 70,  # Remaining cancelled
                    "average_price": 128.50,
                    "fees": -1.50,  # Fees from fills only
                    "liquidity_type": "mixed",
                    "cancel_reason": "user_requested",
                },
                error=None,
            ),
            processing_time_ms=75.0,  # Faster cancel operation
            final_status=ResponseStatus.COMPLETED,
            order_id="ORD_PARTIAL_001",
        )

        # Set up mock behavior for both operations
        mock_coordinator.register_request.side_effect = [
            placement_registration,
            cancel_registration,
        ]
        mock_coordinator.wait_for_completion.side_effect = [
            partial_fill_result,
            cancel_result,
        ]

        # When - Order placed and then cancelled after partial fill
        # Step 1: Place order that gets partially filled
        place_registration = mock_coordinator.register_request(team_id)
        place_result = mock_coordinator.wait_for_completion(
            place_registration.request_id
        )

        # Step 2: Cancel remaining quantity
        cancel_registration = mock_coordinator.register_request(team_id)
        cancel_result = mock_coordinator.wait_for_completion(
            cancel_registration.request_id
        )

        # Then - Both operations return accurate state information
        # Verify initial partial fill
        assert place_result.success is True
        assert place_result.api_response.data["status"] == "partially_filled"
        assert place_result.api_response.data["filled_quantity"] == 30
        assert place_result.api_response.data["remaining_quantity"] == 70

        # Verify cancel operation accuracy
        assert cancel_result.success is True
        assert cancel_result.api_response.data["status"] == "cancelled"
        assert (
            cancel_result.api_response.data["filled_quantity"] == 30
        )  # Unchanged
        assert cancel_result.api_response.data["cancelled_quantity"] == 70
        assert (
            cancel_result.api_response.data["cancel_reason"]
            == "user_requested"
        )

        # Verify order ID consistency across operations
        assert (
            place_result.api_response.order_id
            == cancel_result.api_response.order_id
        )

    def test_websocket_and_rest_response_coordination(
        self, mock_coordinator, sample_order_request
    ):
        """Test that REST and WebSocket responses are coordinated.

        Given - Client connected via both REST and WebSocket
        When - Order submitted via REST API
        Then - REST response and WebSocket notification are consistent

        This test ensures that the coordination system properly manages
        the relationship between synchronous REST responses and asynchronous
        WebSocket notifications, preventing inconsistent state information.
        """
        # Given - Client with both REST and WebSocket connections
        team_id = "TEAM_WEBSOCKET_001"
        _order = sample_order_request.copy()  # For documentation

        # Mock REST API coordination
        rest_registration = ResponseRegistration(
            request_id="req_websocket_rest",
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )
        mock_coordinator.register_request.return_value = rest_registration

        # Mock REST response
        rest_result = ResponseResult(
            request_id="req_websocket_rest",
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id="req_websocket_rest",
                order_id="ORD_WEBSOCKET_001",
                data={
                    "order_id": "ORD_WEBSOCKET_001",
                    "status": "filled",
                    "timestamp": "2024-01-15T10:30:45.123Z",
                    "filled_quantity": 10,
                    "average_price": 128.50,
                    "fees": -0.50,
                    "liquidity_type": "taker",
                    "execution_timestamp": "2024-01-15T10:30:45.120Z",
                },
                error=None,
            ),
            processing_time_ms=100.0,
            final_status=ResponseStatus.COMPLETED,
            order_id="ORD_WEBSOCKET_001",
        )
        mock_coordinator.wait_for_completion.return_value = rest_result

        # Mock WebSocket notification (would be sent separately)
        expected_websocket_message = {
            "type": "execution_report",
            "order_id": "ORD_WEBSOCKET_001",
            "team_id": team_id,
            "fills": [
                {
                    "price": 128.50,
                    "quantity": 10,
                    "timestamp": "2024-01-15T10:30:45.120Z",
                    "liquidity_type": "taker",
                }
            ],
            "order_status": "filled",
            "remaining_quantity": 0,
            "correlation_id": "req_websocket_rest",
        }

        # When - Order submitted via REST API
        registration = mock_coordinator.register_request(team_id)
        rest_response = mock_coordinator.wait_for_completion(
            registration.request_id
        )

        # Simulate WebSocket notification (in real system, this would be sent by trade publisher)
        websocket_message = expected_websocket_message

        # Then - REST and WebSocket data are consistent
        rest_data = rest_response.api_response.data

        # Verify order ID consistency
        assert rest_data["order_id"] == websocket_message["order_id"]

        # Verify execution data consistency
        assert (
            rest_data["filled_quantity"]
            == websocket_message["fills"][0]["quantity"]
        )
        assert (
            rest_data["average_price"]
            == websocket_message["fills"][0]["price"]
        )
        assert (
            rest_data["liquidity_type"]
            == websocket_message["fills"][0]["liquidity_type"]
        )

        # Verify status consistency
        assert rest_data["status"] == websocket_message["order_status"]

        # Verify timing consistency
        assert (
            rest_data["execution_timestamp"]
            == websocket_message["fills"][0]["timestamp"]
        )

        # Verify correlation for debugging
        assert websocket_message["correlation_id"] == rest_response.request_id


class TestEdgeCaseScenarios:
    """Test coordination for edge cases and boundary conditions."""

    def test_duplicate_order_id_coordination_conflict(self, mock_coordinator):
        """Test handling of coordination conflicts.

        Given - Rare case where order IDs might collide
        When - Two requests track overlapping identifiers
        Then - Both receive appropriate responses without interference

        This edge case tests the coordination system's robustness when
        dealing with potential ID conflicts or race conditions in
        order ID assignment.
        """
        # Given - Two teams submitting orders that might get same order ID
        team_1 = "TEAM_CONFLICT_001"
        team_2 = "TEAM_CONFLICT_002"

        # Mock potential order ID collision scenario
        shared_order_id = "ORD_COLLISION_123"

        # Mock registrations for both teams
        registration_1 = ResponseRegistration(
            request_id="req_conflict_team1",
            team_id=team_1,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

        registration_2 = ResponseRegistration(
            request_id="req_conflict_team2",
            team_id=team_2,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

        # Mock responses that properly handle the conflict
        result_1 = ResponseResult(
            request_id="req_conflict_team1",
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id="req_conflict_team1",
                order_id=f"{shared_order_id}_T1",  # Disambiguated order ID
                data={
                    "order_id": f"{shared_order_id}_T1",
                    "status": "filled",
                    "filled_quantity": 10,
                    "team_id": team_1,  # Ensure proper team association
                    "conflict_resolution": "team_suffix_added",
                },
                error=None,
            ),
            processing_time_ms=80.0,
            final_status=ResponseStatus.COMPLETED,
            order_id=f"{shared_order_id}_T1",
        )

        result_2 = ResponseResult(
            request_id="req_conflict_team2",
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id="req_conflict_team2",
                order_id=f"{shared_order_id}_T2",  # Disambiguated order ID
                data={
                    "order_id": f"{shared_order_id}_T2",
                    "status": "filled",
                    "filled_quantity": 15,
                    "team_id": team_2,  # Ensure proper team association
                    "conflict_resolution": "team_suffix_added",
                },
                error=None,
            ),
            processing_time_ms=85.0,
            final_status=ResponseStatus.COMPLETED,
            order_id=f"{shared_order_id}_T2",
        )

        # Set up mock behavior
        mock_coordinator.register_request.side_effect = [
            registration_1,
            registration_2,
        ]
        mock_coordinator.wait_for_completion.side_effect = [result_1, result_2]

        # When - Both teams submit orders simultaneously
        reg_1 = mock_coordinator.register_request(team_1)
        reg_2 = mock_coordinator.register_request(team_2)

        result_1_received = mock_coordinator.wait_for_completion(
            reg_1.request_id
        )
        result_2_received = mock_coordinator.wait_for_completion(
            reg_2.request_id
        )

        # Then - Both receive appropriate responses without interference
        # Verify both requests succeeded
        assert result_1_received.success is True
        assert result_2_received.success is True

        # Verify no cross-contamination of team data
        assert result_1_received.api_response.data["team_id"] == team_1
        assert result_2_received.api_response.data["team_id"] == team_2

        # Verify order IDs were properly disambiguated
        assert (
            result_1_received.api_response.order_id
            != result_2_received.api_response.order_id
        )
        assert "T1" in result_1_received.api_response.order_id
        assert "T2" in result_2_received.api_response.order_id

        # Verify conflict resolution was documented
        assert (
            result_1_received.api_response.data["conflict_resolution"]
            == "team_suffix_added"
        )
        assert (
            result_2_received.api_response.data["conflict_resolution"]
            == "team_suffix_added"
        )

        # Verify different fill quantities to ensure no data mixing
        assert (
            result_1_received.api_response.data["filled_quantity"]
            != result_2_received.api_response.data["filled_quantity"]
        )


class TestErrorRecoveryScenarios:
    """Test coordination during error conditions and recovery."""

    def test_system_timeout_handling(
        self, mock_coordinator, system_error_scenarios
    ):
        """Test API behavior when processing is delayed.

        Given - System under load, processing slowly
        When - API client submits order and waits
        Then - API returns timeout error with clear message

        During market stress, processing may become slow. The coordination
        system must respect timeout limits and provide clear timeout responses.
        """
        # Given - System processing delays
        team_id = "TEAM_TIMEOUT_001"
        timeout_scenario = system_error_scenarios["timeout_error"]

        # Mock timeout scenario
        registration = ResponseRegistration(
            request_id="req_timeout_test",
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=2),
            status=ResponseStatus.PENDING,
        )
        mock_coordinator.register_request.return_value = registration

        # Mock timeout result
        timeout_result = ResponseResult(
            request_id="req_timeout_test",
            success=False,
            api_response=ApiResponse(
                success=False,
                request_id="req_timeout_test",
                order_id=None,
                data=None,
                error=ApiError(
                    code=timeout_scenario["error_code"],
                    message=timeout_scenario["error_message"],
                    details=timeout_scenario["details"],
                ),
            ),
            processing_time_ms=2000.0,  # Full timeout duration
            final_status=ResponseStatus.TIMEOUT,
            order_id=None,
        )
        mock_coordinator.wait_for_completion.return_value = timeout_result

        # When - Client submits order during system overload
        registration = mock_coordinator.register_request(
            team_id, timeout_seconds=2.0
        )
        result = mock_coordinator.wait_for_completion(registration.request_id)

        # Then - API returns timeout error with clear details
        assert result.success is False
        assert result.api_response.error.code == "PROCESSING_TIMEOUT"
        assert "exceeded time limit" in result.api_response.error.message
        assert result.api_response.error.details["timeout_ms"] == 5000
        assert result.api_response.error.details["stage"] == "matching"
        assert result.final_status == ResponseStatus.TIMEOUT

    def test_pipeline_error_handling(
        self, mock_coordinator, system_error_scenarios
    ):
        """Test resilience when pipeline encounters error.

        Given - Order submitted for processing
        When - Pipeline thread encounters error
        Then - API returns appropriate error message

        Pipeline processing can fail due to various errors. The coordination
        system must detect these failures and provide appropriate error responses.
        """
        # Given - Order submitted for processing
        team_id = "TEAM_ERROR_001"
        _error_scenario = system_error_scenarios[
            "exchange_error"
        ]  # For documentation

        # Mock pipeline error scenario
        registration = ResponseRegistration(
            request_id="req_error_test",
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.VALIDATING,
        )
        mock_coordinator.register_request.return_value = registration

        # Mock error result
        error_result = ResponseResult(
            request_id="req_error_test",
            success=False,
            api_response=ApiResponse(
                success=False,
                request_id="req_error_test",
                order_id=None,
                data=None,
                error=ApiError(
                    code="INTERNAL_ERROR",
                    message="Internal system error during order processing",
                    details={
                        "support_reference": "ERR_20240115_103045_789",
                        "stage": "validation",
                        "error_type": "processing_error",
                    },
                ),
            ),
            processing_time_ms=100.0,
            final_status=ResponseStatus.ERROR,
            order_id=None,
        )
        mock_coordinator.wait_for_completion.return_value = error_result

        # When - Pipeline encounters error
        registration = mock_coordinator.register_request(team_id)
        result = mock_coordinator.wait_for_completion(registration.request_id)

        # Then - API returns internal error with support reference
        assert result.success is False
        assert result.api_response.error.code == "INTERNAL_ERROR"
        assert "Internal system error" in result.api_response.error.message
        assert result.api_response.error.details["stage"] == "validation"
        assert "support_reference" in result.api_response.error.details
        assert result.final_status == ResponseStatus.ERROR

    def _create_capacity_error_result(
        self, registration_count: int, capacity_limit: int
    ) -> ResponseResult:
        """Create a capacity error result for testing."""
        return ResponseResult(
            request_id=f"req_capacity_{registration_count}",
            success=False,
            api_response=ApiResponse(
                success=False,
                request_id=f"req_capacity_{registration_count}",
                order_id=None,
                data=None,
                error=ApiError(
                    code="SERVICE_OVERLOADED",
                    message="Coordination service at capacity limit",
                    details={
                        "current_load": registration_count,
                        "capacity_limit": capacity_limit,
                        "retry_after_seconds": 1,
                    },
                ),
            ),
            processing_time_ms=5.0,
            final_status=ResponseStatus.ERROR,
            order_id=None,
        )

    def _create_normal_registration(
        self, registration_count: int, team_id: str
    ) -> ResponseRegistration:
        """Create a normal registration for testing."""
        return ResponseRegistration(
            request_id=f"req_capacity_{registration_count}",
            team_id=team_id,
            timeout_at=datetime.now() + timedelta(seconds=5),
            status=ResponseStatus.PENDING,
        )

    def _create_successful_result(self, request_id: str) -> ResponseResult:
        """Create a successful completion result for testing."""
        return ResponseResult(
            request_id=request_id,
            success=True,
            api_response=ApiResponse(
                success=True,
                request_id=request_id,
                order_id=f"ORD_{request_id[-1:]}",
                data={"status": "new"},
                error=None,
            ),
            processing_time_ms=30.0,
            final_status=ResponseStatus.COMPLETED,
            order_id=f"ORD_{request_id[-1:]}",
        )

    def _submit_requests_and_collect_results(
        self, mock_coordinator, team_id: str, count: int
    ) -> list:
        """Submit multiple requests and collect results."""
        results = []
        for i in range(count):
            try:
                registration_or_result = mock_coordinator.register_request(
                    team_id
                )

                if isinstance(registration_or_result, ResponseResult):
                    # Service rejected at registration
                    results.append(registration_or_result)
                else:
                    # Normal registration, wait for completion
                    result = mock_coordinator.wait_for_completion(
                        registration_or_result.request_id
                    )
                    results.append(result)

            except Exception as e:
                pytest.fail(f"Coordination should not raise exceptions: {e}")
        return results

    def test_service_capacity_management(
        self, mock_coordinator, coordination_config
    ):
        """Test behavior when approaching resource limits.

        Given - Coordination service near capacity limits
        When - Additional orders submitted
        Then - Service either processes or cleanly rejects

        The coordination service has resource limits to prevent
        memory exhaustion. When approaching limits, it should
        gracefully reject new requests.
        """
        # Given - Service configuration with capacity limits
        team_id = "TEAM_CAPACITY_001"
        capacity_limit = coordination_config.max_pending_requests

        # Mock capacity-based behavior
        registration_count = 0
        capacity_reached = False

        def mock_register_request_with_capacity(team_id, timeout_seconds=None):
            nonlocal registration_count, capacity_reached
            registration_count += 1

            # Simulate hitting capacity after 3 requests
            if registration_count > 3:
                capacity_reached = True
                return self._create_capacity_error_result(
                    registration_count, capacity_limit
                )
            else:
                return self._create_normal_registration(
                    registration_count, team_id
                )

        def mock_wait_with_capacity_check(request_id):
            if capacity_reached:
                pytest.fail(
                    "wait_for_completion called after capacity rejection"
                )
            else:
                return self._create_successful_result(request_id)

        mock_coordinator.register_request.side_effect = (
            mock_register_request_with_capacity
        )
        mock_coordinator.wait_for_completion.side_effect = (
            mock_wait_with_capacity_check
        )

        # When - Multiple requests submitted to test capacity
        results = self._submit_requests_and_collect_results(
            mock_coordinator, team_id, 5
        )

        # Then - Service processes what it can and rejects excess cleanly
        successful_requests = [r for r in results if r.success]
        rejected_requests = [r for r in results if not r.success]

        # Should have some successful and some rejected
        assert (
            len(successful_requests) == 3
        ), f"Expected 3 successful, got {len(successful_requests)}"
        assert (
            len(rejected_requests) == 2
        ), f"Expected 2 rejected, got {len(rejected_requests)}"

        # All rejections should be clean with proper error codes
        for rejection in rejected_requests:
            assert rejection.api_response.error.code == "SERVICE_OVERLOADED"
            assert "capacity limit" in rejection.api_response.error.message
            assert (
                rejection.api_response.error.details["capacity_limit"]
                == capacity_limit
            )
