"""IBKR market data collector."""
import logging
from datetime import datetime
from typing import Any

from src.collectors.ibkr.connection import IBKRConnection
from src.core.data_store import DataStore
from src.core.event_bus import EventBus
from src.models import Event, PriceBar, FundamentalData

logger = logging.getLogger(__name__)


class IBKRCollector:
    """Collects market data from IBKR and publishes events.

    Subscribes to market data for symbols in the watchlist,
    publishes events to the event bus, and writes data to storage.
    """

    def __init__(
        self,
        connection: IBKRConnection,
        event_bus: EventBus,
        data_store: DataStore,
        watchlist: list[str],
    ):
        """Initialize the collector.

        Args:
            connection: IBKR connection manager
            event_bus: Event bus for publishing events
            data_store: Data store for persistence
            watchlist: List of symbols to collect data for
        """
        self.connection = connection
        self.event_bus = event_bus
        self.data_store = data_store
        self.watchlist = list(watchlist)

        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if collector is currently running."""
        return self._running

    def stop(self) -> None:
        """Stop the collector."""
        self._running = False
        logger.info("Collector stopped")

    def add_symbol(self, symbol: str) -> None:
        """Add a symbol to the watchlist.

        Args:
            symbol: Symbol to add
        """
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            logger.info(f"Added {symbol} to watchlist")

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from the watchlist.

        Args:
            symbol: Symbol to remove
        """
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            logger.info(f"Removed {symbol} from watchlist")

    def _on_price_bar(self, bar: PriceBar) -> None:
        """Handle incoming price bar data.

        Args:
            bar: Price bar to process
        """
        # Write to data store
        self.data_store.write_bars(bar.symbol, [bar])

        # Publish event
        event = Event(
            type="price_bar",
            symbol=bar.symbol,
            timestamp=bar.date,
            ingested_at=datetime.now(),
            source="ibkr",
            payload={
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            },
        )
        self.event_bus.publish(event)

        logger.debug(f"Processed price bar for {bar.symbol}")

    def _on_fundamental_data(self, data: FundamentalData) -> None:
        """Handle incoming fundamental data.

        Args:
            data: Fundamental data to process
        """
        # Write to data store
        self.data_store.write_fundamental(data.symbol, data)

        # Publish event
        event = Event(
            type="fundamental_data",
            symbol=data.symbol,
            timestamp=data.timestamp,
            ingested_at=datetime.now(),
            source="ibkr",
            payload={
                "company_name": data.company_name,
                "cik": data.cik,
                "employees": data.employees,
                "shares_outstanding": data.shares_outstanding,
                "float_shares": data.float_shares,
                "industry": data.industry,
            },
        )
        self.event_bus.publish(event)

        logger.debug(f"Processed fundamental data for {data.symbol}")

    async def run(self) -> None:
        """Run the collector (subscribes to data and processes messages).

        This method is intended to be run in an async context.
        """
        if not self.connection.is_connected():
            logger.error("Cannot run collector: not connected")
            return

        self._running = True
        logger.info(f"Collector started with watchlist: {self.watchlist}")

        # In a full implementation, this would:
        # 1. Subscribe to market data for all watchlist symbols
        # 2. Subscribe to fundamental data updates
        # 3. Process incoming callbacks
        # For now, this is a stub that the actual IBKR integration will fill in
