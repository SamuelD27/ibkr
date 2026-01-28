"""Orchestrator for wiring and managing all components."""
import asyncio
import importlib
import logging
from typing import Any

from src.core.config import Config, StrategyConfig
from src.core.data_store import FileDataStore
from src.core.event_bus import EventBus
from src.collectors.ibkr.connection import IBKRConnection
from src.collectors.ibkr.collector import IBKRCollector
from src.models import Event
from src.strategies.base import Strategy

logger = logging.getLogger(__name__)


class Orchestrator:
    """Wires all components together and manages lifecycle.

    Responsibilities:
    1. Initialize data store, event bus, and connection
    2. Load and wire strategies
    3. Subscribe strategies to events
    4. Manage startup and shutdown
    """

    def __init__(self, config: Config):
        """Initialize the orchestrator.

        Args:
            config: System configuration
        """
        self.config = config
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None

        # Initialize components
        self.event_bus = EventBus()
        self.data_store = FileDataStore(config.data_store.path)

        # Initialize IBKR connection
        self.connection = IBKRConnection(
            host=config.ibkr.host,
            port=config.ibkr.port,
            client_id=config.ibkr.client_id,
        )

        # Initialize collector (scans full S&P 500 universe)
        self.collector = IBKRCollector(
            connection=self.connection,
            event_bus=self.event_bus,
            data_store=self.data_store,
            market_symbol=config.collector.market_symbol,
            scan_interval_hours=config.collector.scan_interval_hours,
        )

        # Load strategies
        self.strategies: list[Strategy] = []
        self._load_strategies()

        # Wire strategies to event bus
        self._wire_strategies()

        logger.info("Orchestrator initialized")

    @property
    def is_running(self) -> bool:
        """Check if orchestrator is currently running."""
        return self._running

    def _load_strategies(self) -> None:
        """Load enabled strategies from configuration."""
        for strat_config in self.config.get_enabled_strategies():
            try:
                strategy = self._instantiate_strategy(strat_config)
                self.strategies.append(strategy)
                logger.info(f"Loaded strategy: {strat_config.name}")

                # Restore saved state if available
                saved_state = self.data_store.load_strategy_state(strat_config.name)
                if saved_state:
                    strategy.load_state(saved_state)
                    logger.info(f"Restored state for strategy: {strat_config.name}")

            except Exception as e:
                logger.error(f"Failed to load strategy {strat_config.name}: {e}")
                raise

    def _instantiate_strategy(self, config: StrategyConfig) -> Strategy:
        """Instantiate a strategy from its class path.

        Args:
            config: Strategy configuration

        Returns:
            Instantiated strategy object
        """
        # Parse class path
        module_path, class_name = config.class_path.rsplit(".", 1)

        # Import module
        module = importlib.import_module(module_path)

        # Get class
        strategy_class = getattr(module, class_name)

        # Instantiate with config
        strategy = strategy_class(
            allocated_capital=config.allocated_capital,
            **config.params,
        )

        return strategy

    def _wire_strategies(self) -> None:
        """Subscribe strategies to their event types."""
        for strategy in self.strategies:
            # Create event handler for this strategy
            def make_handler(strat: Strategy):
                def handler(event: Event) -> None:
                    decisions = strat.on_event(event)
                    for decision in decisions:
                        self.data_store.log_decision(strat.name, decision)
                        logger.info(
                            f"Strategy {strat.name} decision: {decision.action.value.upper()} "
                            f"{decision.symbol} (weight={decision.target_weight:.1%}, "
                            f"confidence={decision.confidence:.0%})"
                        )
                        # TODO: Send decision to execution engine

                return handler

            handler = make_handler(strategy)
            self.event_bus.subscribe(strategy.subscriptions, handler)
            logger.debug(f"Subscribed {strategy.name} to {strategy.subscriptions}")

    async def _run_async(self) -> None:
        """Run the orchestrator asynchronously."""
        logger.info("Connecting to IBKR...")

        # Connect to IBKR
        connected = await self.connection.connect(timeout=15.0)
        if not connected:
            logger.error("Failed to connect to IBKR. Is TWS/Gateway running on port 7497?")
            return

        logger.info("Starting data collector...")

        try:
            # Run the collector (this will collect data and publish events)
            await self.collector.run()
        except asyncio.CancelledError:
            logger.info("Orchestrator cancelled")
        finally:
            # Disconnect
            await self.connection.disconnect()

    def start(self) -> None:
        """Start the orchestrator and all components.

        This method blocks until stop() is called.
        """
        logger.info("Starting orchestrator...")
        self._running = True

        # Get or create event loop
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._run_async())
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self._running = False
            logger.info("Orchestrator stopped")

    def stop(self) -> None:
        """Stop the orchestrator and save state."""
        logger.info("Stopping orchestrator...")
        self._running = False

        # Stop the collector
        self.collector.stop()

        # Save strategy states
        for strategy in self.strategies:
            state = strategy.get_state()
            self.data_store.save_strategy_state(strategy.name, state)
            logger.info(f"Saved state for strategy: {strategy.name}")

        logger.info("Orchestrator stopped")

    def get_strategy(self, name: str) -> Strategy | None:
        """Get a strategy by name.

        Args:
            name: Strategy name

        Returns:
            Strategy if found, None otherwise
        """
        for strategy in self.strategies:
            if strategy.name == name:
                return strategy
        return None
