# Phase 1.4: File Data Store - TDD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement file-based data persistence for prices, fundamentals, events, state, and audit logs

**Architecture:** Protocol-based DataStore with FileDataStore implementation using Parquet for time-series and JSON/JSONL for documents

**Tech Stack:** Python 3.12+, pyarrow (Parquet), json, pathlib

---

## Task 1: DataStore Protocol

**Files:**
- Create: `src/core/data_store.py`
- Test: `tests/unit/test_data_store_protocol.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_data_store_protocol.py
from typing import Protocol, runtime_checkable
import pytest


def test_data_store_is_protocol():
    from src.core.data_store import DataStore

    assert hasattr(DataStore, '__protocol_attrs__') or hasattr(DataStore, '_is_protocol')


def test_file_data_store_implements_protocol():
    from src.core.data_store import DataStore, FileDataStore

    store = FileDataStore(base_path="/tmp/test_store")
    assert isinstance(store, DataStore)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_data_store_protocol.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/core/data_store.py
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from src.models import Event, PriceBar, FundamentalData, Decision, Order, OrderResult


@runtime_checkable
class DataStore(Protocol):
    """Protocol for data persistence backends."""

    # Price data
    def write_bars(self, symbol: str, bars: list[PriceBar]) -> None: ...
    def read_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]: ...

    # Fundamental data
    def write_fundamental(self, symbol: str, data: FundamentalData) -> None: ...
    def read_fundamental(self, symbol: str, as_of: datetime | None = None) -> FundamentalData | None: ...

    # Events
    def write_event(self, event: Event) -> None: ...
    def read_events(self, start: datetime, end: datetime, types: list[str] | None = None) -> list[Event]: ...

    # Strategy state
    def save_strategy_state(self, strategy_name: str, state: dict) -> None: ...
    def load_strategy_state(self, strategy_name: str) -> dict | None: ...

    # Audit
    def log_decision(self, strategy_name: str, decision: Decision) -> None: ...
    def log_order(self, strategy_name: str, order: Order, result: OrderResult) -> None: ...


class FileDataStore:
    """File-based implementation of DataStore."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create directory structure if it doesn't exist."""
        dirs = ["prices", "fundamentals", "events", "state", "audit/decisions", "audit/orders"]
        for d in dirs:
            (self.base_path / d).mkdir(parents=True, exist_ok=True)

    # Stub implementations for protocol compliance
    def write_bars(self, symbol: str, bars: list[PriceBar]) -> None:
        raise NotImplementedError

    def read_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        raise NotImplementedError

    def write_fundamental(self, symbol: str, data: FundamentalData) -> None:
        raise NotImplementedError

    def read_fundamental(self, symbol: str, as_of: datetime | None = None) -> FundamentalData | None:
        raise NotImplementedError

    def write_event(self, event: Event) -> None:
        raise NotImplementedError

    def read_events(self, start: datetime, end: datetime, types: list[str] | None = None) -> list[Event]:
        raise NotImplementedError

    def save_strategy_state(self, strategy_name: str, state: dict) -> None:
        raise NotImplementedError

    def load_strategy_state(self, strategy_name: str) -> dict | None:
        raise NotImplementedError

    def log_decision(self, strategy_name: str, decision: Decision) -> None:
        raise NotImplementedError

    def log_order(self, strategy_name: str, order: Order, result: OrderResult) -> None:
        raise NotImplementedError
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_data_store_protocol.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/data_store.py tests/unit/test_data_store_protocol.py
git commit -m "feat: add DataStore protocol and FileDataStore skeleton"
```

---

## Task 2: Price Bar Storage (Parquet)

**Files:**
- Modify: `src/core/data_store.py`
- Test: `tests/unit/test_file_data_store.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_file_data_store.py
from datetime import datetime
import tempfile
import pytest


@pytest.fixture
def temp_store():
    import tempfile
    from src.core.data_store import FileDataStore

    with tempfile.TemporaryDirectory() as tmpdir:
        yield FileDataStore(base_path=tmpdir)


def test_write_and_read_bars(temp_store):
    from src.models import PriceBar

    bars = [
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 5), open=150.0, high=152.0, low=149.0, close=151.0, volume=1000000),
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 6), open=151.0, high=153.0, low=150.0, close=152.0, volume=1100000),
    ]

    temp_store.write_bars("AAPL", bars)

    result = temp_store.read_bars("AAPL", datetime(2026, 1, 1), datetime(2026, 1, 31))

    assert len(result) == 2
    assert result[0].symbol == "AAPL"
    assert result[0].close == 151.0
    assert result[1].close == 152.0


def test_read_bars_with_date_filter(temp_store):
    from src.models import PriceBar

    bars = [
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 5), open=150.0, high=152.0, low=149.0, close=151.0, volume=1000000),
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 10), open=151.0, high=153.0, low=150.0, close=152.0, volume=1100000),
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 15), open=152.0, high=154.0, low=151.0, close=153.0, volume=1200000),
    ]

    temp_store.write_bars("AAPL", bars)

    result = temp_store.read_bars("AAPL", datetime(2026, 1, 8), datetime(2026, 1, 12))

    assert len(result) == 1
    assert result[0].date == datetime(2026, 1, 10)


def test_read_bars_empty_for_missing_symbol(temp_store):
    result = temp_store.read_bars("MISSING", datetime(2026, 1, 1), datetime(2026, 1, 31))
    assert result == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_file_data_store.py -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Implement price bar storage**

Add to FileDataStore class:

```python
import pyarrow as pa
import pyarrow.parquet as pq

def write_bars(self, symbol: str, bars: list[PriceBar]) -> None:
    """Write price bars to Parquet file."""
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
        existing_bars = []
        if file_path.exists():
            existing_bars = self._read_parquet_bars(file_path)

        # Merge and dedupe by date
        all_bars = {b.date: b for b in existing_bars}
        for bar in month_bars:
            all_bars[bar.date] = bar

        # Sort and write
        sorted_bars = sorted(all_bars.values(), key=lambda b: b.date)
        self._write_parquet_bars(file_path, sorted_bars)

def read_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
    """Read price bars from Parquet files."""
    symbol_dir = self.base_path / "prices" / symbol
    if not symbol_dir.exists():
        return []

    all_bars = []
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
        bars.append(PriceBar(
            symbol=table["symbol"][i].as_py(),
            date=table["date"][i].as_py(),
            open=table["open"][i].as_py(),
            high=table["high"][i].as_py(),
            low=table["low"][i].as_py(),
            close=table["close"][i].as_py(),
            volume=table["volume"][i].as_py(),
        ))
    return bars
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_file_data_store.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/data_store.py tests/unit/test_file_data_store.py
git commit -m "feat: add Parquet storage for price bars"
```

---

## Task 3: Fundamental Data Storage (JSON)

**Step 1: Write the failing test**

Add to `tests/unit/test_file_data_store.py`:

```python
def test_write_and_read_fundamental(temp_store):
    from src.models import FundamentalData

    data = FundamentalData(
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5, 10, 0, 0),
        company_name="Apple Inc",
        cik="0000320193",
        employees=166000,
        shares_outstanding=14776353000.0,
        float_shares=14525947723.0,
        industry="Technology",
        category="Computers",
        subcategory="Consumer Electronics",
        raw_xml="<test/>"
    )

    temp_store.write_fundamental("AAPL", data)

    result = temp_store.read_fundamental("AAPL")

    assert result is not None
    assert result.symbol == "AAPL"
    assert result.company_name == "Apple Inc"
    assert result.employees == 166000


def test_read_fundamental_returns_latest(temp_store):
    from src.models import FundamentalData

    old_data = FundamentalData(
        symbol="AAPL", timestamp=datetime(2026, 1, 1),
        company_name="Apple Inc", cik="123", employees=160000,
        shares_outstanding=None, float_shares=None,
        industry=None, category=None, subcategory=None, raw_xml=""
    )

    new_data = FundamentalData(
        symbol="AAPL", timestamp=datetime(2026, 1, 5),
        company_name="Apple Inc", cik="123", employees=166000,
        shares_outstanding=None, float_shares=None,
        industry=None, category=None, subcategory=None, raw_xml=""
    )

    temp_store.write_fundamental("AAPL", old_data)
    temp_store.write_fundamental("AAPL", new_data)

    result = temp_store.read_fundamental("AAPL")
    assert result.employees == 166000


def test_read_fundamental_missing_returns_none(temp_store):
    result = temp_store.read_fundamental("MISSING")
    assert result is None
```

**Step 2-5: Implement, test, commit**

---

## Task 4: Strategy State Storage (JSON)

**Step 1: Write the failing test**

```python
def test_save_and_load_strategy_state(temp_store):
    state = {
        "positions": {"AAPL": 100, "MSFT": 50},
        "cash": 10000.0,
        "last_updated": "2026-01-05T10:00:00"
    }

    temp_store.save_strategy_state("value_strategy", state)

    result = temp_store.load_strategy_state("value_strategy")

    assert result == state


def test_load_strategy_state_missing_returns_none(temp_store):
    result = temp_store.load_strategy_state("missing_strategy")
    assert result is None
```

---

## Task 5: Audit Log Storage (JSONL)

**Step 1: Write the failing test**

```python
def test_log_decision(temp_store):
    from src.models import Decision, Action

    decision = Decision(
        symbol="AAPL",
        action=Action.BUY,
        target_weight=0.05,
        confidence=0.8,
        reasoning="Strong fundamentals"
    )

    temp_store.log_decision("value_strategy", decision)

    # Verify file exists and contains the decision
    log_file = temp_store.base_path / "audit" / "decisions" / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    assert log_file.exists()


def test_log_order(temp_store):
    from src.models import Order, OrderResult

    order = Order(
        strategy_name="value_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MARKET"
    )

    result = OrderResult(
        order_id=123,
        status="filled",
        fill_price=150.25,
        fill_quantity=100,
        message=None
    )

    temp_store.log_order("value_strategy", order, result)

    log_file = temp_store.base_path / "audit" / "orders" / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    assert log_file.exists()
```

---

## Checkpoint: Phase 1.4 Complete

At this point you should have:

- [ ] DataStore protocol definition
- [ ] FileDataStore with Parquet price bar storage
- [ ] FileDataStore with JSON fundamental data storage
- [ ] FileDataStore with JSON strategy state storage
- [ ] FileDataStore with JSONL audit logging
- [ ] 100% test coverage on data store
- [ ] Clean git history with atomic commits

**Next:** Continue to Phase 2 (IBKR Integration)
