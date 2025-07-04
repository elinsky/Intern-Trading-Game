"""Shared fixtures for integration tests at different levels.

This module provides fixtures for testing at various integration boundaries:
- Service-level: Just services, no threads
- Pipeline-level: Single thread pipelines with queues
- API-level: Full API with all threads
- System-level: Complete system with persistence
"""

from queue import Queue
from typing import Dict

import pytest

from intern_trading_game.domain.exchange.components.core.models import (
    Instrument,
)
from intern_trading_game.domain.exchange.components.orderbook.matching_engine import (
    BatchMatchingEngine,
    ContinuousMatchingEngine,
)
from intern_trading_game.domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintConfig,
    ConstraintType,
)
from intern_trading_game.domain.exchange.venue import ExchangeVenue
from intern_trading_game.domain.game.game_service import GameService
from intern_trading_game.domain.positions import (
    FeeSchedule,
    PositionManagementService,
    TradeProcessingService,
    TradingFeeService,
)
from intern_trading_game.services import (
    OrderMatchingService,
    OrderValidationService,
)

# Service-level fixtures (no threads, minimal dependencies)


@pytest.fixture
def role_fees():
    """Provide test fee schedules."""
    return {
        "market_maker": FeeSchedule(
            maker_rebate=0.02,
            taker_fee=-0.05,
        ),
        "hedge_fund": FeeSchedule(
            maker_rebate=0.0,
            taker_fee=-0.05,
        ),
        "retail": FeeSchedule(
            maker_rebate=0.0,
            taker_fee=-0.05,
        ),
    }


@pytest.fixture
def exchange():
    """Create a clean exchange for testing."""
    from unittest.mock import Mock

    from intern_trading_game.domain.exchange.components.core.types import (
        PhaseState,
        PhaseType,
    )

    # Create a mock phase manager for continuous trading
    phase_manager = Mock()
    phase_manager.get_current_phase_state.return_value = PhaseState(
        phase_type=PhaseType.CONTINUOUS,
        is_order_submission_allowed=True,
        is_order_cancellation_allowed=True,
        is_matching_enabled=True,
        execution_style="continuous",
    )

    exchange = ExchangeVenue(
        phase_manager=phase_manager,
        continuous_engine=ContinuousMatchingEngine(),
        batch_engine=BatchMatchingEngine(),
    )

    # List test instruments
    instruments = [
        Instrument(
            symbol="SPX_4500_CALL",
            strike=4500.0,
            option_type="call",
            underlying="SPX",
        ),
        Instrument(
            symbol="SPX_4500_PUT",
            strike=4500.0,
            option_type="put",
            underlying="SPX",
        ),
    ]

    for instrument in instruments:
        exchange.list_instrument(instrument)

    return exchange


@pytest.fixture
def validator():
    """Create order validator with test constraints."""
    validator = ConstraintBasedOrderValidator()

    # Setup market maker constraints
    mm_constraint = ConstraintConfig(
        constraint_type=ConstraintType.POSITION_LIMIT,
        parameters={"max_position": 50, "symmetric": True},
        error_code="MM_POS_LIMIT",
        error_message="Position exceeds ±50",
    )
    validator.load_constraints("market_maker", [mm_constraint])

    return validator


@pytest.fixture
def test_positions():
    """Thread-safe position storage for testing."""
    positions: Dict[str, Dict[str, int]] = {}
    return positions


@pytest.fixture
def test_order_counts():
    """Order count tracking for testing."""
    order_counts: Dict[str, int] = {}
    return order_counts


@pytest.fixture
def service_context(
    role_fees, exchange, validator, test_positions, test_order_counts
):
    """Minimal context for service integration tests.

    Provides initialized services without threads or queues.
    """

    # Initialize position service with internal state
    position_service = PositionManagementService()

    # Copy test positions into the service
    for team_id, instruments in test_positions.items():
        position_service._positions[team_id] = instruments.copy()

    # Initialize services (rate limiting now handled internally)
    validation_service = OrderValidationService(
        validator=validator,
        exchange=exchange,
        position_service=position_service,
    )

    fee_service = TradingFeeService(role_fees)

    matching_service = OrderMatchingService(exchange)

    trade_service = TradeProcessingService(
        fee_service=fee_service,
        position_service=position_service,
        websocket_queue=Queue(),  # Dummy queue for service tests
    )

    return {
        "validation_service": validation_service,
        "matching_service": matching_service,
        "trade_service": trade_service,
        "fee_service": fee_service,
        "position_service": position_service,
        "exchange": exchange,
        "validator": validator,
        "positions": test_positions,
        "order_counts": test_order_counts,
        # get_positions removed - handled internally by PositionManagementService
        # get_order_count removed - handled internally by OrderValidationService
    }


@pytest.fixture
def test_team():
    """Create a test team for integration tests."""
    game_service = GameService()
    team = game_service.register_team("Test Market Maker", "market_maker")

    yield team

    # GameService instance will be garbage collected after test


# Pipeline-level fixtures (single thread with queues)


@pytest.fixture
def pipeline_context(service_context):
    """Single pipeline with queues for testing thread coordination.

    Provides a single processing thread with real queues but mocked
    dependencies for other components.
    """
    # Add queues to service context
    service_context["order_queue"] = Queue()
    service_context["validation_queue"] = Queue()
    service_context["match_queue"] = Queue()
    service_context["trade_queue"] = Queue()
    service_context["websocket_queue"] = Queue()

    return service_context


# API-level fixtures (full API with threads, defined in api/conftest.py)

# System-level fixtures (complete system, defined in system/conftest.py)
