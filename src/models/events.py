"""Event model for IBKR Trading Bot."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class Event:
    """Base event type for all system events."""
    type: str              # "price_bar", "fundamental_data", etc.
    symbol: str | None     # Ticker (None for system events)
    timestamp: datetime    # When event occurred
    ingested_at: datetime  # When we received it
    source: str            # "ibkr", "file", etc.
    payload: dict[str, Any]  # Actual data

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        d["ingested_at"] = self.ingested_at.isoformat()
        return d
