"""Orchestrator for wiring and managing all components."""
import importlib
import logging
from typing import Any

from src.core.config import Config, StrategyConfig
from src.core.data_store import FileDataStore
from src.core.event_bus import EventBus
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

        # Initialize components
        self.event_bus = EventBus()
        self.data_store = FileDataStore(config.data_store.path)

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
                        logger.debug(f"Strategy {strat.name} decision: {decision.action} {decision.symbol}")

                return handler

            handler = make_handler(strategy)
            self.event_bus.subscribe(strategy.subscriptions, handler)
            logger.debug(f"Subscribed {strategy.name} to {strategy.subscriptions}")

    def start(self) -> None:
        """Start the orchestrator and all components.

        This method blocks until stop() is called.
        """
        logger.info("Starting orchestrator...")
        self._running = True

        # In a full implementation, this would:
        # 1. Connect to IBKR
        # 2. Start the collector
        # 3. Begin processing events
        # For now, this is a placeholder

        logger.info("Orchestrator started")

    def stop(self) -> None:
        """Stop the orchestrator and save state."""
        logger.info("Stopping orchestrator...")
        self._running = False

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
