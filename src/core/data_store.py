"""Data store protocol and implementations."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable, Any

import pyarrow as pa
import pyarrow.parquet as pq

from src.models import Event, PriceBar, FundamentalData, Decision, Order, OrderResult

logger = logging.getLogger(__name__)


@runtime_checkable
class DataStore(Protocol):
    """Protocol for data persistence backends."""

    # Price data
    def write_bars(self, symbol: str, bars: list[PriceBar]) -> None:
        """Write price bars to storage."""
        ...

    def read_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        """Read price bars from storage within date range."""
        ...

    # Fundamental data
    def write_fundamental(self, symbol: str, data: FundamentalData) -> None:
        """Write fundamental data to storage."""
        ...

    def read_fundamental(self, symbol: str, as_of: datetime | None = None) -> FundamentalData | None:
        """Read fundamental data from storage. Returns latest if as_of is None."""
        ...

    # Events
    def write_event(self, event: Event) -> None:
        """Write event to storage."""
        ...

    def read_events(self, start: datetime, end: datetime, types: list[str] | None = None) -> list[Event]:
        """Read events from storage within date range, optionally filtered by type."""
        ...

    # Strategy state
    def save_strategy_state(self, strategy_name: str, state: dict) -> None:
        """Save strategy state to storage."""
        ...

    def load_strategy_state(self, strategy_name: str) -> dict | None:
        """Load strategy state from storage. Returns None if not found."""
        ...

    # Audit
    def log_decision(self, strategy_name: str, decision: Decision) -> None:
        """Log a strategy decision for audit trail."""
        ...

    def log_order(self, strategy_name: str, order: Order, result: OrderResult) -> None:
        """Log an order and its result for audit trail."""
        ...


class FileDataStore:
    """File-based implementation of DataStore using Parquet and JSON."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create directory structure if it doesn't exist."""
        dirs = [
            "prices",
            "fundamentals",
            "events",
            "state",
            "audit/decisions",
            "audit/orders",
        ]
        for d in dirs:
            (self.base_path / d).mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Price Bar Storage (Parquet)
    # =========================================================================

    def write_bars(self, symbol: str, bars: list[PriceBar]) -> None:
        """Write price bars to Parquet files, partitioned by month."""
        if not bars:
            return

        symbol_dir = self.base_path / "prices" / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)

        # Group bars by month
        bars_by_month: dict[str, list[PriceBar]] = {}
        for bar in bars:
            month_key = bar.date.strftime("%Y-%m")
            if month_key not in bars_by_month:
                bars_by_month[month_key] = []
            bars_by_month[month_key].append(bar)

        for month_key, month_bars in bars_by_month.items():
            file_path = symbol_dir / f"{month_key}.parquet"

            # Read existing data if file exists
            existing_bars: list[PriceBar] = []
            if file_path.exists():
                existing_bars = self._read_parquet_bars(file_path)

            # Merge and dedupe by date (newer data wins)
            all_bars = {b.date: b for b in existing_bars}
            for bar in month_bars:
                all_bars[bar.date] = bar

            # Sort and write
            sorted_bars = sorted(all_bars.values(), key=lambda b: b.date)
            self._write_parquet_bars(file_path, sorted_bars)
            logger.debug(f"Wrote {len(sorted_bars)} bars to {file_path}")

    def read_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        """Read price bars from Parquet files within date range."""
        symbol_dir = self.base_path / "prices" / symbol
        if not symbol_dir.exists():
            return []

        all_bars: list[PriceBar] = []
        for parquet_file in symbol_dir.glob("*.parquet"):
            bars = self._read_parquet_bars(parquet_file)
            all_bars.extend(bars)

        # Filter by date range
        filtered = [b for b in all_bars if start <= b.date <= end]
        return sorted(filtered, key=lambda b: b.date)

    def _write_parquet_bars(self, path: Path, bars: list[PriceBar]) -> None:
        """Write bars to a Parquet file."""
        table = pa.table({
            "symbol": [b.symbol for b in bars],
            "date": [b.date for b in bars],
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
        })
        pq.write_table(table, path)

    def _read_parquet_bars(self, path: Path) -> list[PriceBar]:
        """Read bars from a Parquet file."""
        table = pq.read_table(path)
        bars = []
        for i in range(table.num_rows):
            date_val = table["date"][i].as_py()
            # Handle both datetime and date objects from Parquet
            if hasattr(date_val, 'hour'):
                date_obj = date_val
            else:
                date_obj = datetime.combine(date_val, datetime.min.time())

            bars.append(PriceBar(
                symbol=table["symbol"][i].as_py(),
                date=date_obj,
                open=float(table["open"][i].as_py()),
                high=float(table["high"][i].as_py()),
                low=float(table["low"][i].as_py()),
                close=float(table["close"][i].as_py()),
                volume=int(table["volume"][i].as_py()),
            ))
        return bars

    # =========================================================================
    # Fundamental Data Storage (JSON)
    # =========================================================================

    def write_fundamental(self, symbol: str, data: FundamentalData) -> None:
        """Write fundamental data to JSON file, timestamped."""
        symbol_dir = self.base_path / "fundamentals" / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)

        # Use timestamp for filename to support historical queries
        filename = data.timestamp.strftime("%Y-%m-%d_%H%M%S") + ".json"
        file_path = symbol_dir / filename

        # Convert to dict for JSON serialization
        data_dict = {
            "symbol": data.symbol,
            "timestamp": data.timestamp.isoformat(),
            "company_name": data.company_name,
            "cik": data.cik,
            "employees": data.employees,
            "shares_outstanding": data.shares_outstanding,
            "float_shares": data.float_shares,
            "industry": data.industry,
            "category": data.category,
            "subcategory": data.subcategory,
            "raw_xml": data.raw_xml,
        }

        with open(file_path, "w") as f:
            json.dump(data_dict, f, indent=2)

        logger.debug(f"Wrote fundamental data to {file_path}")

    def read_fundamental(self, symbol: str, as_of: datetime | None = None) -> FundamentalData | None:
        """Read fundamental data from JSON. Returns latest if as_of is None."""
        symbol_dir = self.base_path / "fundamentals" / symbol
        if not symbol_dir.exists():
            return None

        # Get all JSON files
        json_files = sorted(symbol_dir.glob("*.json"), reverse=True)
        if not json_files:
            return None

        # If as_of specified, filter to files before that time
        if as_of is not None:
            as_of_str = as_of.strftime("%Y-%m-%d_%H%M%S")
            json_files = [f for f in json_files if f.stem <= as_of_str]
            if not json_files:
                return None

        # Read the latest file
        latest_file = json_files[0]
        with open(latest_file) as f:
            data_dict = json.load(f)

        return FundamentalData(
            symbol=data_dict["symbol"],
            timestamp=datetime.fromisoformat(data_dict["timestamp"]),
            company_name=data_dict["company_name"],
            cik=data_dict["cik"],
            employees=data_dict.get("employees"),
            shares_outstanding=data_dict.get("shares_outstanding"),
            float_shares=data_dict.get("float_shares"),
            industry=data_dict.get("industry"),
            category=data_dict.get("category"),
            subcategory=data_dict.get("subcategory"),
            raw_xml=data_dict["raw_xml"],
        )

    # =========================================================================
    # Event Storage (Parquet) - Not yet implemented
    # =========================================================================

    def write_event(self, event: Event) -> None:
        raise NotImplementedError("Event storage not yet implemented")

    def read_events(self, start: datetime, end: datetime, types: list[str] | None = None) -> list[Event]:
        raise NotImplementedError("Event storage not yet implemented")

    # =========================================================================
    # Strategy State Storage (JSON) - Not yet implemented
    # =========================================================================

    def save_strategy_state(self, strategy_name: str, state: dict) -> None:
        raise NotImplementedError("State storage not yet implemented")

    def load_strategy_state(self, strategy_name: str) -> dict | None:
        raise NotImplementedError("State storage not yet implemented")

    # =========================================================================
    # Audit Logging (JSONL) - Not yet implemented
    # =========================================================================

    def log_decision(self, strategy_name: str, decision: Decision) -> None:
        raise NotImplementedError("Audit logging not yet implemented")

    def log_order(self, strategy_name: str, order: Order, result: OrderResult) -> None:
        raise NotImplementedError("Audit logging not yet implemented")
