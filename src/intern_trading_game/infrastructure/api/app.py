"""FastAPI application setup and lifecycle management."""

import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...data.messaging.queues import create_queues
from ...data.state.managers import (
    create_shared_state,
    get_team_order_count,
    get_team_positions,
)
from ...domain.exchange.book.matching_engine import ContinuousMatchingEngine
from ...domain.exchange.core.instrument import Instrument
from ...domain.exchange.validation.order_validator import (
    ConstraintBasedOrderValidator,
    ConstraintConfig,
    ConstraintType,
)
from ...domain.exchange.venue import ExchangeVenue
from ...infrastructure.config.fee_config import (
    get_hardcoded_fee_schedules,
)
from ...infrastructure.threads.matcher import matching_thread
from ...infrastructure.threads.publisher import trade_publisher_thread
from ...infrastructure.threads.validator import validator_thread
from ...infrastructure.threads.websocket import websocket_thread
from ...services.order_validation import OrderValidationService
from .endpoints import create_endpoints


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns
    -------
    FastAPI
        Configured FastAPI application instance
    """
    # Create shared state and queues
    queues = create_queues()
    state = create_shared_state()

    # Game components
    exchange = ExchangeVenue(ContinuousMatchingEngine())
    validator = ConstraintBasedOrderValidator()

    # Service instances
    validation_service: Optional[OrderValidationService] = None

    # Thread instances
    threads = {}

    async def startup():
        """Initialize the game components on startup.

        This function handles all startup logic including:
        - Initializing services
        - Starting processing threads
        - Configuring market maker constraints
        - Listing trading instruments

        Follows Single Responsibility Principle by focusing only on startup tasks.
        """
        nonlocal validation_service, threads

        # Initialize services
        validation_service = OrderValidationService(
            validator=validator,
            exchange=exchange,
            get_positions_func=lambda team_id: get_team_positions(
                team_id, state["positions"], state["positions_lock"]
            ),
            get_order_count_func=lambda team_id: get_team_order_count(
                team_id, state["orders_this_second"], state["orders_lock"]
            ),
        )

        # Create and start processing threads
        threads["validator"] = threading.Thread(
            target=validator_thread,
            args=(
                queues["order_queue"],
                queues["match_queue"],
                queues["websocket_queue"],
                validation_service,
                state["orders_this_second"],
                state["orders_lock"],
                state["pending_orders"],
                state["order_responses"],
            ),
            daemon=True,
        )

        threads["matcher"] = threading.Thread(
            target=matching_thread,
            args=(
                queues["match_queue"],
                queues["trade_queue"],
                queues["websocket_queue"],
                exchange,
                state["pending_orders"],
                state["order_responses"],
            ),
            daemon=True,
        )

        threads["publisher"] = threading.Thread(
            target=trade_publisher_thread,
            args=(
                queues["trade_queue"],
                queues["websocket_queue"],
                {
                    "roles": {
                        name: {
                            "fees": {
                                "maker_rebate": schedule.maker_rebate,
                                "taker_fee": schedule.taker_fee,
                            }
                        }
                        for name, schedule in get_hardcoded_fee_schedules().items()
                    }
                },
                state["positions"],
                state["positions_lock"],
                state["pending_orders"],
                state["order_responses"],
            ),
            daemon=True,
        )

        threads["websocket"] = threading.Thread(
            target=websocket_thread,
            args=(queues["websocket_queue"],),
            daemon=True,
        )

        # Start all threads
        for thread in threads.values():
            thread.start()

        # Setup market maker constraints
        mm_constraint = ConstraintConfig(
            constraint_type=ConstraintType.POSITION_LIMIT,
            parameters={"max_position": 50, "symmetric": True},
            error_code="MM_POS_LIMIT",
            error_message="Position exceeds ±50",
        )
        validator.load_constraints("market_maker", [mm_constraint])

        # List instruments
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

        print(
            f"✓ API started with {len(instruments)} instruments and 4 processing threads"
        )

    async def shutdown():
        """Cleanup resources on shutdown.

        This function handles all cleanup logic including:
        - Sending shutdown signals to threads
        - Waiting for threads to complete

        Follows Single Responsibility Principle by focusing only on cleanup tasks.
        """
        # Send shutdown signals to threads
        for queue_name in [
            "order_queue",
            "match_queue",
            "trade_queue",
            "websocket_queue",
        ]:
            queues[queue_name].put(None)

        # Wait for threads to finish
        for thread in threads.values():
            thread.join(timeout=1)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage the application lifecycle.

        This context manager handles startup and shutdown events for the FastAPI
        application, replacing the deprecated @app.on_event decorators.

        The lifespan pattern ensures proper resource management and follows
        SOLID principles by delegating to separate startup/shutdown functions.
        """
        await startup()
        yield
        await shutdown()

    # Initialize FastAPI app with lifespan management
    app = FastAPI(
        title="Intern Trading Game API",
        description="REST API for algorithmic trading simulation",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create and register endpoints
    create_endpoints(
        app,
        queues["order_queue"],
        state["positions"],
        state["positions_lock"],
        state["orders_this_second"],
        state["orders_lock"],
        state["pending_orders"],
        state["order_responses"],
        queues["websocket_queue"],
    )

    return app
