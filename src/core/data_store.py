"""Data store protocol and implementations."""
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable, Any

from src.models import Event, PriceBar, FundamentalData, Decision, Order, OrderResult


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

    # Stub implementations for protocol compliance - will be implemented in subsequent tasks
    def write_bars(self, symbol: str, bars: list[PriceBar]) -> None:
        raise NotImplementedError("Price bar storage not yet implemented")

    def read_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        raise NotImplementedError("Price bar storage not yet implemented")

    def write_fundamental(self, symbol: str, data: FundamentalData) -> None:
        raise NotImplementedError("Fundamental storage not yet implemented")

    def read_fundamental(self, symbol: str, as_of: datetime | None = None) -> FundamentalData | None:
        raise NotImplementedError("Fundamental storage not yet implemented")

    def write_event(self, event: Event) -> None:
        raise NotImplementedError("Event storage not yet implemented")

    def read_events(self, start: datetime, end: datetime, types: list[str] | None = None) -> list[Event]:
        raise NotImplementedError("Event storage not yet implemented")

    def save_strategy_state(self, strategy_name: str, state: dict) -> None:
        raise NotImplementedError("State storage not yet implemented")

    def load_strategy_state(self, strategy_name: str) -> dict | None:
        raise NotImplementedError("State storage not yet implemented")

    def log_decision(self, strategy_name: str, decision: Decision) -> None:
        raise NotImplementedError("Audit logging not yet implemented")

    def log_order(self, strategy_name: str, order: Order, result: OrderResult) -> None:
        raise NotImplementedError("Audit logging not yet implemented")
