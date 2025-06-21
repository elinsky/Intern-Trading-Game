"""Additional tests for ExchangeVenue to improve coverage.

Tests focus on error handling and edge cases not covered in the main test file.
This complements test_exchange.py by covering error paths and less common scenarios.
"""

from unittest.mock import Mock, patch

import pytest

from intern_trading_game.domain.exchange.book.matching_engine import (
    BatchMatchingEngine,
)
from intern_trading_game.domain.exchange.models.instrument import Instrument
from intern_trading_game.domain.exchange.models.order import Order
from intern_trading_game.domain.exchange.types import PhaseState, PhaseType
from intern_trading_game.domain.exchange.venue import ExchangeVenue
from tests.fixtures import (
    create_matched_orders,
    create_order_book_scenario,
    create_test_order,
    create_test_spread,
)


@pytest.fixture
def mock_phase_manager():
    """Create a mock phase manager for testing."""
    manager = Mock()
    # Default to continuous trading phase
    manager.get_current_phase_state.return_value = PhaseState(
        phase_type=PhaseType.CONTINUOUS,
        is_order_submission_allowed=True,
        is_order_cancellation_allowed=True,
        is_matching_enabled=True,
        execution_style="continuous",
    )
    return manager


@pytest.fixture
def exchange(mock_phase_manager):
    """Create an exchange with a test SPX option."""
    exchange = ExchangeVenue(phase_manager=mock_phase_manager)
    # Create SPX option with proper date format
    spx_option = Instrument(
        symbol="SPX_CALL_4500",
        strike=4500.0,
        expiry="2024-12-31",
        option_type="call",
        underlying="SPX",
    )
    exchange.list_instrument(spx_option)
    return exchange


@pytest.fixture
def spx_instrument_id():
    """Return the instrument ID for tests."""
    # This matches the instrument created in exchange fixture
    return "SPX_CALL_4500"


class TestExchangeVenueErrors:
    """Test error handling in ExchangeVenue."""

    def test_duplicate_instrument_listing(self, exchange):
        """Test that listing duplicate instruments raises ValueError.

        Given - An exchange with an instrument already listed
        When - We try to list the same instrument again
        Then - ValueError should be raised
        """
        # Given - Exchange already has SPX option from fixture

        # When/Then - Try to list the same instrument again
        duplicate_instrument = Instrument(
            symbol="SPX_CALL_4500",  # Same ID as existing
            strike=4500.0,
            expiry="2024-12-31",
            option_type="call",
            underlying="SPX",
        )
        with pytest.raises(
            ValueError, match="Instrument with ID .* already exists"
        ):
            exchange.list_instrument(duplicate_instrument)

    def test_submit_order_instrument_not_found(self, exchange):
        """Test submitting order for non-existent instrument.

        Given - An exchange with only TEST instrument
        When - We submit an order for a different instrument
        Then - ValueError should be raised
        """
        # Given - Exchange only has TEST instrument

        # When/Then - Submit order for non-existent instrument
        order = Order(
            instrument_id="NONEXISTENT",
            side="buy",
            quantity=10,
            price=100.0,
            trader_id="trader1",
        )
        with pytest.raises(
            ValueError, match="Instrument NONEXISTENT not found"
        ):
            exchange.submit_order(order)

    def test_submit_order_duplicate_order_id(
        self, exchange, spx_instrument_id
    ):
        """Test submitting order with duplicate order ID.

        Given - An exchange with an existing order
        When - We submit a new order with the same order ID
        Then - ValueError should be raised
        """
        # Given - Submit first order
        order1 = create_test_order(
            instrument_id=spx_instrument_id,
            side="buy",
            quantity=10,
            price=128.0,
            trader_id="MM_001",
        )
        exchange.submit_order(order1)

        # When/Then - Try to submit order with same ID
        # Force the same order_id
        order2 = create_test_order(
            instrument_id=spx_instrument_id,
            side="sell",
            quantity=5,
            price=128.0,
            trader_id="HF_002",
        )
        order2.order_id = order1.order_id  # Force duplicate ID

        with pytest.raises(
            ValueError, match=f"Order ID {order1.order_id} already exists"
        ):
            exchange.submit_order(order2)

    def test_cancel_order_not_in_any_book(self, exchange, spx_instrument_id):
        """Test canceling an order that exists but is not in any book.

        Given - An exchange tracking an order ID that's not in any book
        When - We try to cancel it
        Then - False should be returned
        """
        # Given - Submit and fill an order completely
        order1 = Order(
            instrument_id=spx_instrument_id,
            side="buy",
            quantity=10,
            price=100.0,
            trader_id="trader1",
        )
        order2 = Order(
            instrument_id=spx_instrument_id,
            side="sell",
            quantity=10,
            price=100.0,
            trader_id="trader2",
        )

        exchange.submit_order(order1)
        exchange.submit_order(order2)  # This should match and fill both orders

        # The order ID still exists in all_order_ids but not in the book
        # Try to cancel the filled order
        cancelled = exchange.cancel_order(order1.order_id, "trader1")

        # Then - Should return False
        assert cancelled is False

    def test_get_trade_history_instrument_not_found(self, exchange):
        """Test getting trade history for non-existent instrument.

        Given - An exchange with only TEST instrument
        When - We request trade history for a different instrument
        Then - ValueError should be raised
        """
        # Given - Exchange only has TEST instrument

        # When/Then - Request trade history for non-existent instrument
        with pytest.raises(
            ValueError, match="Instrument NONEXISTENT not found"
        ):
            exchange.get_trade_history("NONEXISTENT")

    def test_get_market_summary_instrument_not_found(self, exchange):
        """Test getting market summary for non-existent instrument.

        Given - An exchange with only TEST instrument
        When - We request market summary for a different instrument
        Then - ValueError should be raised
        """
        # Given - Exchange only has TEST instrument

        # When/Then - Request market summary for non-existent instrument
        with pytest.raises(
            ValueError, match="Instrument NONEXISTENT not found"
        ):
            exchange.get_market_summary("NONEXISTENT")


class TestExchangeVenueAdditionalMethods:
    """Test additional methods for coverage."""

    def test_get_all_instruments(self, exchange):
        """Test getting all instruments.

        Given - An exchange with one instrument
        When - We call get_all_instruments
        Then - List with all instruments should be returned
        """
        # Given - Exchange has SPX option from fixture

        # When - Get all instruments
        instruments = exchange.get_all_instruments()

        # Then - Should return list with the instrument
        assert len(instruments) == 1
        assert instruments[0].symbol == "SPX_CALL_4500"
        assert instruments[0].underlying == "SPX"
        assert instruments[0].strike == 4500.0
        assert instruments[0].option_type == "call"

    def test_get_all_instruments_multiple(self, mock_phase_manager):
        """Test getting all instruments with multiple instruments.

        Given - An exchange with multiple instruments
        When - We call get_all_instruments
        Then - List with all instruments should be returned
        """
        # Given - Exchange with multiple instruments
        exchange = ExchangeVenue(phase_manager=mock_phase_manager)

        inst1 = Instrument(symbol="AAPL", underlying="AAPL")
        inst2 = Instrument(
            symbol="AAPL_150C",
            strike=150.0,
            expiry="2024-12-31",
            option_type="call",
            underlying="AAPL",
        )

        exchange.list_instrument(inst1)
        exchange.list_instrument(inst2)

        # When - Get all instruments
        instruments = exchange.get_all_instruments()

        # Then - Should return list with both instruments
        assert len(instruments) == 2
        symbols = {inst.symbol for inst in instruments}
        assert symbols == {"AAPL", "AAPL_150C"}

    def test_execute_batch_continuous_mode(self, exchange):
        """Test execute_batch in continuous mode.

        Given - An exchange in continuous mode (default)
        When - We call execute_batch
        Then - Empty dict should be returned
        """
        # Given - Exchange in continuous mode (default)

        # When - Execute batch
        results = exchange.execute_batch()

        # Then - Should return empty dict
        assert results == {}

    def test_execute_batch_batch_mode(self):
        """Test execute_batch in batch mode.

        Given - An exchange in batch mode with pending orders
        When - We call execute_batch
        Then - Results with order statuses should be returned
        """
        # Given - Exchange in batch mode with appropriate phase
        phase_manager = Mock()
        phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.PRE_OPEN,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="batch",
        )

        batch_engine = BatchMatchingEngine()
        exchange = ExchangeVenue(
            phase_manager=phase_manager, matching_engine=batch_engine
        )

        # List instrument
        inst = Instrument(
            symbol="SPX_CALL_4500",
            strike=4500.0,
            expiry="2024-12-31",
            option_type="call",
            underlying="SPX",
        )
        exchange.list_instrument(inst)

        # Submit orders (they will be pending in batch mode)
        order1 = Order(
            instrument_id="SPX_CALL_4500",
            side="buy",
            quantity=10,
            price=128.0,
            trader_id="MM_001",
        )
        order2 = Order(
            instrument_id="SPX_CALL_4500",
            side="sell",
            quantity=10,
            price=128.0,
            trader_id="HF_002",
        )

        result1 = exchange.submit_order(order1)
        result2 = exchange.submit_order(order2)

        # Orders should be pending in batch mode
        assert result1.status == "pending_new"
        assert result2.status == "pending_new"

        # When - Execute batch
        batch_results = exchange.execute_batch()

        # Then - Should return results for processed orders
        assert "SPX_CALL_4500" in batch_results
        assert len(batch_results["SPX_CALL_4500"]) == 2

        # Both orders should have been processed
        assert order1.order_id in batch_results["SPX_CALL_4500"]
        assert order2.order_id in batch_results["SPX_CALL_4500"]

    def test_get_matching_mode(self, exchange):
        """Test getting matching mode.

        Given - An exchange in continuous mode
        When - We call get_matching_mode
        Then - 'continuous' should be returned
        """
        # Given - Exchange in continuous mode (default)

        # When - Get matching mode
        mode = exchange.get_matching_mode()

        # Then - Should return 'continuous'
        assert mode == "continuous"

    def test_get_matching_mode_batch(self):
        """Test getting matching mode for batch engine.

        Given - An exchange in batch mode
        When - We call get_matching_mode
        Then - 'batch' should be returned
        """
        # Given - Exchange in batch mode with appropriate phase
        phase_manager = Mock()
        phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.PRE_OPEN,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="batch",
        )

        batch_engine = BatchMatchingEngine()
        exchange = ExchangeVenue(
            phase_manager=phase_manager, matching_engine=batch_engine
        )

        # When - Get matching mode
        mode = exchange.get_matching_mode()

        # Then - Should return 'batch'
        assert mode == "batch"

    def test_get_trade_history_success(self, exchange, spx_instrument_id):
        """Test successfully getting trade history.

        Given - An exchange with executed trades
        When - We request trade history
        Then - List of trades should be returned
        """
        # Given - Execute some trades
        order1 = Order(
            instrument_id=spx_instrument_id,
            side="buy",
            quantity=10,
            price=128.0,
            trader_id="MM_001",
        )
        order2 = Order(
            instrument_id=spx_instrument_id,
            side="sell",
            quantity=10,
            price=128.0,
            trader_id="HF_002",
        )

        exchange.submit_order(order1)
        exchange.submit_order(order2)  # This should match and create a trade

        # When - Get trade history
        trades = exchange.get_trade_history(spx_instrument_id, limit=5)

        # Then - Should return the trade
        assert len(trades) == 1
        assert trades[0].price == 128.0
        assert trades[0].quantity == 10

    def test_get_market_summary_success(self, exchange, spx_instrument_id):
        """Test successfully getting market summary.

        Given - An exchange with orders in the book
        When - We request market summary
        Then - Summary with bid/ask and trades should be returned
        """
        # Given - Add some orders to create market depth
        exchange.submit_order(
            Order(
                instrument_id=spx_instrument_id,
                side="buy",
                quantity=10,
                price=127.0,
                trader_id="MM_001",
            )
        )
        exchange.submit_order(
            Order(
                instrument_id=spx_instrument_id,
                side="sell",
                quantity=5,
                price=129.0,
                trader_id="MM_002",
            )
        )

        # When - Get market summary
        summary = exchange.get_market_summary(spx_instrument_id)

        # Then - Should return complete summary
        assert summary["instrument_id"] == spx_instrument_id
        assert summary["best_bid"] == (127.0, 10)
        assert summary["best_ask"] == (129.0, 5)
        assert "last_trades" in summary
        assert "depth" in summary

    def test_cancel_order_book_returns_none(self, exchange, spx_instrument_id):
        """Test cancel order when book.cancel_order returns None.

        Given - An order exists but book.cancel_order returns None
        When - We try to cancel it
        Then - False should be returned
        """
        # Given - Submit an order
        order = Order(
            instrument_id=spx_instrument_id,
            side="buy",
            quantity=10,
            price=128.0,
            trader_id="MM_001",
        )
        exchange.submit_order(order)

        # Mock the order book to return the order on get_order but None on cancel_order
        with patch.object(
            exchange.order_books[spx_instrument_id], "get_order"
        ) as mock_get:
            with patch.object(
                exchange.order_books[spx_instrument_id], "cancel_order"
            ) as mock_cancel:
                mock_get.return_value = order
                mock_cancel.return_value = None  # Simulate cancel failure

                # When - Try to cancel the order
                result = exchange.cancel_order(order.order_id, "MM_001")

                # Then - Should return False
                assert result is False
                # Order ID should still be in all_order_ids since cancel failed
                assert order.order_id in exchange.all_order_ids


class TestExchangeVenueTrading:
    """Test realistic trading scenarios using fixtures."""

    def test_matched_orders_execution(self, exchange, spx_instrument_id):
        """Test execution of perfectly matched orders.

        Given - An exchange with an SPX option
        When - We submit matched buy and sell orders
        Then - Orders should match and create a trade
        """
        # Given - Create matched orders at $128.50
        buy_order, sell_order = create_matched_orders(
            price=128.50,
            quantity=10,
            buyer_id="MM_001",
            seller_id="HF_002",
            instrument_id=spx_instrument_id,
        )

        # When - Submit both orders
        buy_result = exchange.submit_order(buy_order)
        sell_result = exchange.submit_order(sell_order)

        # Then - Orders should match
        assert buy_result.status == "new"  # First order rests
        assert sell_result.status == "filled"  # Second order matches
        assert len(sell_result.fills) == 1
        assert sell_result.fills[0].price == 128.50
        assert sell_result.fills[0].quantity == 10

    def test_spread_creation(self, exchange, spx_instrument_id):
        """Test creating a market maker spread.

        Given - A market maker wanting to quote both sides
        When - They submit a bid/ask spread
        Then - Both orders should rest in the book
        """
        # Given - Market maker creates $1 wide spread around $128
        spread = create_test_spread(
            spread_width=1.0,
            mid_price=128.0,
            quantity=25,
            trader_id="MM_001",
            instrument_id=spx_instrument_id,
        )

        # When - Submit both sides
        bid_result = exchange.submit_order(spread["bid"])
        ask_result = exchange.submit_order(spread["ask"])

        # Then - Both orders should be accepted
        assert bid_result.status == "new"
        assert ask_result.status == "new"

        # Verify spread in order book
        book = exchange.get_order_book(spx_instrument_id)
        assert book.best_bid() == (127.5, 25)
        assert book.best_ask() == (128.5, 25)

    def test_partial_fill_scenario(self, exchange, spx_instrument_id):
        """Test partial order fills.

        Given - A large resting order
        When - A smaller opposite order arrives
        Then - Small order fills completely, large order partially
        """
        # Given - Large buy order for 100 contracts
        large_buy = create_test_order(
            side="buy",
            price=128.0,
            quantity=100,
            trader_id="HF_001",
            instrument_id=spx_instrument_id,
        )
        exchange.submit_order(large_buy)

        # When - Smaller sell order arrives
        small_sell = create_test_order(
            side="sell",
            price=128.0,
            quantity=25,
            trader_id="MM_002",
            instrument_id=spx_instrument_id,
        )
        sell_result = exchange.submit_order(small_sell)

        # Then - Small order fully filled, large order partially
        assert sell_result.status == "filled"
        assert sell_result.fills[0].quantity == 25

        # Check remaining liquidity
        book = exchange.get_order_book(spx_instrument_id)
        assert book.best_bid() == (128.0, 75)  # 100 - 25 = 75 remaining

    def test_order_book_scenario(self, exchange, spx_instrument_id):
        """Test building a realistic order book.

        Given - Multiple traders providing liquidity
        When - Orders are submitted at various price levels
        Then - Order book should reflect proper depth
        """
        # Given - Create a balanced order book scenario
        book_orders = create_order_book_scenario(
            scenario="balanced",
            instrument_id=spx_instrument_id,
        )

        # When - Submit all orders
        for bid in book_orders["bids"]:
            exchange.submit_order(bid)
        for ask in book_orders["asks"]:
            exchange.submit_order(ask)

        # Then - Verify book depth
        book = exchange.get_order_book(spx_instrument_id)
        depth = book.depth_snapshot()

        # Check bid side (best to worst)
        assert depth["bids"][0] == (99.5, 10)
        assert depth["bids"][1] == (99.0, 20)
        assert depth["bids"][2] == (98.5, 30)

        # Check ask side (best to worst)
        assert depth["asks"][0] == (100.5, 10)
        assert depth["asks"][1] == (101.0, 20)
        assert depth["asks"][2] == (101.5, 30)

    def test_price_improvement(self, exchange, spx_instrument_id):
        """Test that orders execute at the best available price.

        Given - A resting limit order
        When - A marketable order with worse price arrives
        Then - Execution should occur at the better price
        """
        # Given - Resting sell order at $128.00
        resting_sell = create_test_order(
            side="sell",
            price=128.00,
            quantity=20,
            trader_id="MM_001",
            instrument_id=spx_instrument_id,
        )
        exchange.submit_order(resting_sell)

        # When - Buy order arrives willing to pay $128.50
        aggressive_buy = create_test_order(
            side="buy",
            price=128.50,  # Willing to pay more
            quantity=15,
            trader_id="HF_001",
            instrument_id=spx_instrument_id,
        )
        buy_result = exchange.submit_order(aggressive_buy)

        # Then - Trade executes at the better price (seller's price)
        assert buy_result.status == "filled"
        assert buy_result.fills[0].price == 128.00  # Price improvement!
        assert buy_result.fills[0].quantity == 15

    def test_batch_mode_with_fixtures(self):
        """Test batch matching mode with realistic orders.

        Given - A batch exchange with multiple orders
        When - We execute the batch
        Then - Orders should match according to price-time priority
        """
        # Given - Create batch exchange with appropriate phase
        phase_manager = Mock()
        phase_manager.get_current_phase_state.return_value = PhaseState(
            phase_type=PhaseType.PRE_OPEN,
            is_order_submission_allowed=True,
            is_order_cancellation_allowed=True,
            is_matching_enabled=False,
            execution_style="batch",
        )

        batch_engine = BatchMatchingEngine()
        exchange = ExchangeVenue(
            phase_manager=phase_manager, matching_engine=batch_engine
        )
        spx_option = Instrument(
            symbol="SPX_CALL_4500",
            strike=4500.0,
            expiry="2024-12-31",
            option_type="call",
            underlying="SPX",
        )
        exchange.list_instrument(spx_option)

        # Submit multiple orders that should match
        buy1, sell1 = create_matched_orders(
            price=128.0,
            quantity=10,
            buyer_id="MM_001",
            seller_id="HF_001",
            instrument_id=spx_option.id,
        )

        buy2, sell2 = create_matched_orders(
            price=128.5,
            quantity=5,
            buyer_id="HF_002",
            seller_id="MM_002",
            instrument_id=spx_option.id,
        )

        # Submit all orders (they'll be pending)
        results = []
        for order in [buy1, sell1, buy2, sell2]:
            results.append(exchange.submit_order(order))

        # All should be pending
        assert all(r.status == "pending_new" for r in results)

        # When - Execute batch
        batch_results = exchange.execute_batch()

        # Then - Orders should have matched
        assert spx_option.id in batch_results
        order_results = batch_results[spx_option.id]

        # Both pairs should have matched at their respective prices
        assert len(order_results) == 4  # All 4 orders processed
