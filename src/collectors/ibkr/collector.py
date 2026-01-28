"""IBKR market data collector using ib_async.

Scans the full S&P 500 universe and publishes data to the event bus.
Strategy layers handle filtering and elimination.
"""
import asyncio
import logging
import time
from datetime import datetime, date
from typing import Any
from pathlib import Path
import json

from ib_async import IB, Stock, BarDataList, util

from src.collectors.ibkr.connection import IBKRConnection
from src.collectors.universe import SP500Provider
from src.core.data_store import DataStore
from src.core.event_bus import EventBus
from src.models import Event, PriceBar, FundamentalData

logger = logging.getLogger(__name__)


# IBKR Rate Limits: 50 messages/second
# Using 20/sec to leave margin for other operations
REQUESTS_PER_SECOND = 20
REQUEST_INTERVAL = 1.0 / REQUESTS_PER_SECOND  # 0.05 seconds


class IBKRCollector:
    """Collects market data from IBKR for the full S&P 500 universe.

    The collector fetches data for all stocks and publishes events.
    Strategy pipeline layers handle filtering and elimination.
    """

    def __init__(
        self,
        connection: IBKRConnection,
        event_bus: EventBus,
        data_store: DataStore,
        market_symbol: str = "SPY",
        bar_size: str = "1 day",
        history_duration: str = "1 Y",
        scan_interval_hours: float = 24.0,
    ):
        self.connection = connection
        self.event_bus = event_bus
        self.data_store = data_store
        self.market_symbol = market_symbol
        self.bar_size = bar_size
        self.history_duration = history_duration
        self.scan_interval_hours = scan_interval_hours

        # Universe provider
        self._universe_provider = SP500Provider()
        self._universe: list[str] = []

        # State tracking
        self._running = False
        self._contracts: dict[str, Stock] = {}
        self._scan_progress_file = Path("data/state/scan_progress.json")
        self._last_full_scan: datetime | None = None

        # Rate limiting
        self._last_request_time = 0.0
        self._request_count = 0

        logger.debug(
            "INIT: IBKRCollector initialized",
            extra={
                "extra_data": {
                    "action": "collector_init",
                    "market_symbol": market_symbol,
                    "requests_per_second": REQUESTS_PER_SECOND,
                }
            },
        )

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def ib(self) -> IB:
        return self.connection.ib

    def stop(self) -> None:
        self._running = False
        self._save_scan_progress()
        logger.info("Collector stopped")

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self._last_request_time

        if elapsed < REQUEST_INTERVAL:
            await asyncio.sleep(REQUEST_INTERVAL - elapsed)

        self._last_request_time = time.time()
        self._request_count += 1

    def _load_scan_progress(self) -> dict:
        """Load scan progress from file."""
        if not self._scan_progress_file.exists():
            return {}

        try:
            with open(self._scan_progress_file) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading scan progress: {e}")
            return {}

    def _save_scan_progress(self, data: dict = None) -> None:
        """Save scan progress to file."""
        self._scan_progress_file.parent.mkdir(parents=True, exist_ok=True)

        if data is None:
            data = {}

        data["saved_at"] = datetime.now().isoformat()
        data["last_full_scan"] = self._last_full_scan.isoformat() if self._last_full_scan else None

        with open(self._scan_progress_file, "w") as f:
            json.dump(data, f, indent=2)

    async def _load_universe(self) -> None:
        """Load the S&P 500 universe."""
        logger.info("Loading S&P 500 universe...")
        self._universe = await self._universe_provider.get_symbols()
        logger.info(f"Loaded {len(self._universe)} symbols")

    async def _qualify_contract(self, symbol: str) -> Stock | None:
        """Qualify a single contract."""
        if symbol in self._contracts:
            return self._contracts[symbol]

        await self._rate_limit()

        ib_symbol = symbol.replace(".", " ")
        contract = Stock(ib_symbol, "SMART", "USD")

        try:
            qualified = await self.ib.qualifyContractsAsync(contract)
            if qualified:
                self._contracts[symbol] = qualified[0]
                return qualified[0]
            return None
        except Exception as e:
            logger.debug(f"Error qualifying {symbol}: {e}")
            return None

    async def _fetch_contract_details(self, symbol: str) -> dict | None:
        """Fetch contract details for a symbol."""
        contract = await self._qualify_contract(symbol)
        if not contract:
            return None

        await self._rate_limit()

        try:
            details_list = await self.ib.reqContractDetailsAsync(contract)
            if not details_list:
                return None

            details = details_list[0]

            return {
                "symbol": symbol,
                "company_name": details.longName or symbol,
                "industry": details.industry or "",
                "category": details.category or "",
                "subcategory": details.subcategory or "",
            }

        except Exception as e:
            logger.debug(f"Error fetching details for {symbol}: {e}")
            return None

    async def _fetch_historical_bars(self, symbol: str) -> list[PriceBar]:
        """Fetch historical bar data for a symbol."""
        if symbol not in self._contracts:
            return []

        contract = self._contracts[symbol]
        await self._rate_limit()

        try:
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr=self.history_duration,
                barSizeSetting=self.bar_size,
                whatToShow="ADJUSTED_LAST",
                useRTH=True,
                formatDate=1,
            )

            if not bars:
                return []

            return [
                PriceBar(
                    symbol=symbol,
                    date=bar.date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=int(bar.volume),
                )
                for bar in bars
            ]

        except Exception as e:
            logger.warning(f"Error fetching history for {symbol}: {e}")
            return []

    def _publish_price_bars(self, symbol: str, bars: list[PriceBar]) -> None:
        """Publish price bar events for a symbol."""
        for bar in bars:
            event = Event(
                type="price_bar",
                symbol=bar.symbol,
                timestamp=bar.date if isinstance(bar.date, datetime) else datetime.now(),
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

    def _publish_market_bars(self, bars: list[PriceBar]) -> None:
        """Publish market benchmark bar events."""
        for bar in bars:
            event = Event(
                type="market_bar",
                symbol=bar.symbol,
                timestamp=bar.date if isinstance(bar.date, datetime) else datetime.now(),
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

    def _publish_fundamental_data(self, symbol: str, details: dict) -> None:
        """Publish fundamental data event."""
        event = Event(
            type="fundamental_data",
            symbol=symbol,
            timestamp=datetime.now(),
            ingested_at=datetime.now(),
            source="ibkr",
            payload={
                "company_name": details.get("company_name", symbol),
                "industry": details.get("industry", ""),
                "category": details.get("category", ""),
                "subcategory": details.get("subcategory", ""),
            },
        )
        self.event_bus.publish(event)

    async def _run_full_scan(self) -> None:
        """Run a full scan of the S&P 500 universe.

        Fetches data for all stocks and publishes events.
        Strategy layers handle filtering and elimination.
        """
        logger.info("=" * 60)
        logger.info("STARTING FULL S&P 500 SCAN")
        logger.info("=" * 60)

        await self._load_universe()
        total_symbols = len(self._universe)

        # =========================================================
        # Step 1: Fetch market benchmark data
        # =========================================================
        logger.info(f"Fetching market benchmark ({self.market_symbol})...")

        market_contract = await self._qualify_contract(self.market_symbol)
        if not market_contract:
            logger.error(f"Failed to qualify market benchmark {self.market_symbol}!")
            return

        market_bars = await self._fetch_historical_bars(self.market_symbol)
        if market_bars:
            self._publish_market_bars(market_bars)
            logger.info(f"Published {len(market_bars)} market bars")
        else:
            logger.error("Failed to fetch market benchmark!")
            return

        # =========================================================
        # Step 2: Scan all stocks in the universe
        # =========================================================
        logger.info(f"Scanning {total_symbols} stocks...")

        start_time = time.time()
        success_count = 0

        for i, symbol in enumerate(self._universe):
            if not self._running:
                break

            # Fetch contract details
            details = await self._fetch_contract_details(symbol)
            if not details:
                continue

            # Fetch historical bars
            bars = await self._fetch_historical_bars(symbol)
            if not bars:
                continue

            # Publish fundamental data first
            self._publish_fundamental_data(symbol, details)

            # Then publish price bars (triggers strategy analysis)
            self._publish_price_bars(symbol, bars)

            # Store to disk
            self.data_store.write_bars(symbol, bars)
            success_count += 1

            # Progress every 50 symbols
            if (i + 1) % 50 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                remaining = (total_symbols - i - 1) / rate
                logger.info(
                    f"Progress: {i+1}/{total_symbols} "
                    f"({success_count} success, {rate:.1f}/sec, ~{remaining:.0f}s remaining)"
                )

        # =========================================================
        # Scan complete
        # =========================================================
        elapsed = time.time() - start_time
        self._last_full_scan = datetime.now()
        self._save_scan_progress({
            "total_universe": total_symbols,
            "successful": success_count,
            "elapsed_seconds": elapsed,
        })

        logger.info("=" * 60)
        logger.info(f"SCAN COMPLETE: {success_count}/{total_symbols} stocks in {elapsed:.1f}s")
        logger.info("=" * 60)

    async def run(self) -> None:
        """Run the collector continuously."""
        if not self.connection.is_connected():
            logger.error("Cannot run collector: not connected")
            return

        self._running = True
        logger.info("Collector started - scanning S&P 500 universe")

        try:
            while self._running:
                await self._run_full_scan()

                if not self._running:
                    break

                logger.info(f"Next scan in {self.scan_interval_hours} hours")

                # Sleep in 1-minute intervals for clean shutdown
                wait_seconds = self.scan_interval_hours * 3600
                waited = 0
                while waited < wait_seconds and self._running:
                    await asyncio.sleep(60)
                    waited += 60

        except asyncio.CancelledError:
            logger.info("Collector cancelled")
        except Exception as e:
            logger.error(f"Collector error: {e}")
            raise
        finally:
            self._running = False
            self._save_scan_progress()
            logger.info("Collector stopped")
