# Phase 1: Foundation - TDD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up Python project structure with data models, event bus, and file data store

**Architecture:** Event-driven system where collectors emit events through an event bus to strategies, with all data persisted to a file-based data store

**Tech Stack:** Python 3.12+, pytest, pyarrow, pyyaml, dataclasses

---

## Task 1: Project Structure

**Files:**
- Create: `src/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/collectors/__init__.py`
- Create: `src/strategies/__init__.py`
- Create: `src/models/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `pyproject.toml`
- Create: `requirements.txt`

**Step 1: Create directory structure**

```bash
mkdir -p src/core src/collectors src/strategies src/models
mkdir -p tests/unit tests/integration
```

**Step 2: Create __init__.py files**

Create empty `__init__.py` files in all directories.

**Step 3: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "ibkr-trading-bot"
version = "0.1.0"
description = "IBKR Trading Bot with fundamentals-driven strategies"
requires-python = ">=3.12"
dependencies = [
    "pyyaml>=6.0",
    "pyarrow>=14.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_ignores = true
```

**Step 4: Create requirements.txt**

```
pyyaml>=6.0
pyarrow>=14.0.0
pytest>=7.0
pytest-cov>=4.0
mypy>=1.0
```

**Step 5: Verify structure**

Run: `python -c "import src; print('OK')"`
Expected: OK

**Step 6: Commit**

```bash
git add .
git commit -m "feat: initialize project structure with packaging"
```

---

## Task 2: Event Model

**Files:**
- Create: `src/models/events.py`
- Test: `tests/unit/test_events.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_events.py
from datetime import datetime
import pytest


def test_event_creation():
    from src.models.events import Event

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5, 10, 0, 0),
        ingested_at=datetime(2026, 1, 5, 10, 0, 1),
        source="ibkr",
        payload={"open": 150.0, "close": 151.0}
    )

    assert event.type == "price_bar"
    assert event.symbol == "AAPL"
    assert event.source == "ibkr"
    assert event.payload["open"] == 150.0


def test_event_with_none_symbol():
    from src.models.events import Event

    event = Event(
        type="system_start",
        symbol=None,
        timestamp=datetime(2026, 1, 5, 10, 0, 0),
        ingested_at=datetime(2026, 1, 5, 10, 0, 0),
        source="system",
        payload={}
    )

    assert event.symbol is None


def test_event_to_dict():
    from src.models.events import Event

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5, 10, 0, 0),
        ingested_at=datetime(2026, 1, 5, 10, 0, 1),
        source="ibkr",
        payload={"open": 150.0}
    )

    d = event.to_dict()
    assert d["type"] == "price_bar"
    assert d["symbol"] == "AAPL"
    assert "timestamp" in d
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_events.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.models.events'"

**Step 3: Write minimal implementation**

```python
# src/models/events.py
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_events.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/models/events.py tests/unit/test_events.py
git commit -m "feat: add Event dataclass with serialization"
```

---

## Task 3: Market Data Models

**Files:**
- Create: `src/models/market_data.py`
- Test: `tests/unit/test_market_data.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_market_data.py
from datetime import datetime
import pytest


def test_price_bar_creation():
    from src.models.market_data import PriceBar

    bar = PriceBar(
        symbol="AAPL",
        date=datetime(2026, 1, 5),
        open=150.0,
        high=152.0,
        low=149.5,
        close=151.0,
        volume=1000000
    )

    assert bar.symbol == "AAPL"
    assert bar.open == 150.0
    assert bar.high == 152.0
    assert bar.low == 149.5
    assert bar.close == 151.0
    assert bar.volume == 1000000


def test_contract_info_creation():
    from src.models.market_data import ContractInfo

    info = ContractInfo(
        symbol="AAPL",
        con_id=265598,
        long_name="APPLE INC",
        industry="Technology",
        category="Computers",
        subcategory="Consumer Electronics",
        exchange="NASDAQ",
        currency="USD"
    )

    assert info.symbol == "AAPL"
    assert info.con_id == 265598
    assert info.long_name == "APPLE INC"


def test_price_bar_to_dict():
    from src.models.market_data import PriceBar

    bar = PriceBar(
        symbol="AAPL",
        date=datetime(2026, 1, 5),
        open=150.0,
        high=152.0,
        low=149.5,
        close=151.0,
        volume=1000000
    )

    d = bar.to_dict()
    assert d["symbol"] == "AAPL"
    assert d["close"] == 151.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_market_data.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/models/market_data.py
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class PriceBar:
    """OHLCV price bar data."""
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


@dataclass
class ContractInfo:
    """Contract details from IBKR."""
    symbol: str
    con_id: int
    long_name: str
    industry: str
    category: str
    subcategory: str
    exchange: str
    currency: str
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_market_data.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/models/market_data.py tests/unit/test_market_data.py
git commit -m "feat: add PriceBar and ContractInfo dataclasses"
```

---

## Task 4: Fundamental Data Model

**Files:**
- Create: `src/models/fundamental_data.py`
- Test: `tests/unit/test_fundamental_data.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_fundamental_data.py
from datetime import datetime
import pytest


def test_fundamental_data_creation():
    from src.models.fundamental_data import FundamentalData

    data = FundamentalData(
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
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

    assert data.symbol == "AAPL"
    assert data.company_name == "Apple Inc"
    assert data.employees == 166000


def test_fundamental_data_with_none_fields():
    from src.models.fundamental_data import FundamentalData

    data = FundamentalData(
        symbol="NEWCO",
        timestamp=datetime(2026, 1, 5),
        company_name="New Company Inc",
        cik="0001234567",
        employees=None,
        shares_outstanding=None,
        float_shares=None,
        industry=None,
        category=None,
        subcategory=None,
        raw_xml="<incomplete/>"
    )

    assert data.employees is None
    assert data.shares_outstanding is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_fundamental_data.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/models/fundamental_data.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FundamentalData:
    """Parsed fundamental data from IBKR XML."""
    symbol: str
    timestamp: datetime

    # Company info
    company_name: str
    cik: str
    employees: int | None

    # Share data
    shares_outstanding: float | None
    float_shares: float | None

    # Classification
    industry: str | None
    category: str | None
    subcategory: str | None

    # Raw data preserved for debugging
    raw_xml: str
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_fundamental_data.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/models/fundamental_data.py tests/unit/test_fundamental_data.py
git commit -m "feat: add FundamentalData dataclass"
```

---

## Task 5: Order Models

**Files:**
- Create: `src/models/orders.py`
- Test: `tests/unit/test_orders.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_orders.py
import pytest


def test_action_enum():
    from src.models.orders import Action

    assert Action.HOLD.value == "hold"
    assert Action.BUY.value == "buy"
    assert Action.EXIT.value == "exit"


def test_order_creation():
    from src.models.orders import Order

    order = Order(
        strategy_name="value_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MARKET",
        limit_price=None
    )

    assert order.strategy_name == "value_strategy"
    assert order.symbol == "AAPL"
    assert order.action == "BUY"
    assert order.quantity == 100


def test_order_with_limit():
    from src.models.orders import Order

    order = Order(
        strategy_name="value_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="LIMIT",
        limit_price=150.50
    )

    assert order.order_type == "LIMIT"
    assert order.limit_price == 150.50


def test_order_result():
    from src.models.orders import OrderResult

    result = OrderResult(
        order_id=123,
        status="filled",
        fill_price=150.25,
        fill_quantity=100,
        message=None
    )

    assert result.order_id == 123
    assert result.status == "filled"
    assert result.fill_price == 150.25
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_orders.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/models/orders.py
from dataclasses import dataclass
from enum import Enum


class Action(Enum):
    """Strategy decision actions."""
    HOLD = "hold"
    BUY = "buy"
    EXIT = "exit"


@dataclass
class Order:
    """Order to be submitted to execution engine."""
    strategy_name: str
    symbol: str
    action: str           # "BUY" or "SELL"
    quantity: int
    order_type: str       # "MARKET", "LIMIT"
    limit_price: float | None = None


@dataclass
class OrderResult:
    """Result of order submission."""
    order_id: int
    status: str           # "submitted", "filled", "rejected", "cancelled"
    fill_price: float | None = None
    fill_quantity: int | None = None
    message: str | None = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_orders.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/models/orders.py tests/unit/test_orders.py
git commit -m "feat: add Action enum and Order/OrderResult dataclasses"
```

---

## Task 6: Strategy Models

**Files:**
- Create: `src/models/strategy.py`
- Test: `tests/unit/test_strategy_models.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_strategy_models.py
import pytest


def test_layer_result_creation():
    from src.models.strategy import LayerResult

    result = LayerResult(
        passed=True,
        data={"market_cap": 3000000000000},
        reasoning="Market cap $3T exceeds minimum threshold"
    )

    assert result.passed is True
    assert result.data["market_cap"] == 3000000000000
    assert "threshold" in result.reasoning


def test_layer_result_failure():
    from src.models.strategy import LayerResult

    result = LayerResult(
        passed=False,
        data={"market_cap": 500000000},
        reasoning="Market cap $500M below minimum $1B threshold"
    )

    assert result.passed is False


def test_decision_creation():
    from src.models.strategy import Decision
    from src.models.orders import Action

    decision = Decision(
        symbol="AAPL",
        action=Action.BUY,
        target_weight=0.05,
        confidence=0.8,
        reasoning="Strong fundamentals, passes all screens"
    )

    assert decision.symbol == "AAPL"
    assert decision.action == Action.BUY
    assert decision.target_weight == 0.05
    assert decision.confidence == 0.8
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_strategy_models.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/models/strategy.py
from dataclasses import dataclass
from typing import Any

from src.models.orders import Action


@dataclass
class LayerResult:
    """Result from a strategy layer."""
    passed: bool
    data: dict[str, Any]
    reasoning: str


@dataclass
class Decision:
    """Final decision from a strategy."""
    symbol: str
    action: Action
    target_weight: float  # 0.0 to 1.0
    confidence: float     # 0.0 to 1.0
    reasoning: str        # Full audit trail
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_strategy_models.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/models/strategy.py tests/unit/test_strategy_models.py
git commit -m "feat: add LayerResult and Decision dataclasses"
```

---

## Task 7: Models Package Export

**Files:**
- Modify: `src/models/__init__.py`
- Test: `tests/unit/test_models_package.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_models_package.py
import pytest


def test_all_models_importable():
    from src.models import (
        Event,
        PriceBar,
        ContractInfo,
        FundamentalData,
        Action,
        Order,
        OrderResult,
        LayerResult,
        Decision,
    )

    assert Event is not None
    assert PriceBar is not None
    assert ContractInfo is not None
    assert FundamentalData is not None
    assert Action is not None
    assert Order is not None
    assert OrderResult is not None
    assert LayerResult is not None
    assert Decision is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models_package.py -v`
Expected: FAIL with "ImportError: cannot import name 'Event'"

**Step 3: Write minimal implementation**

```python
# src/models/__init__.py
"""Data models for IBKR Trading Bot."""

from src.models.events import Event
from src.models.market_data import PriceBar, ContractInfo
from src.models.fundamental_data import FundamentalData
from src.models.orders import Action, Order, OrderResult
from src.models.strategy import LayerResult, Decision

__all__ = [
    "Event",
    "PriceBar",
    "ContractInfo",
    "FundamentalData",
    "Action",
    "Order",
    "OrderResult",
    "LayerResult",
    "Decision",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_models_package.py -v`
Expected: PASS (1 test)

**Step 5: Commit**

```bash
git add src/models/__init__.py tests/unit/test_models_package.py
git commit -m "feat: export all models from package"
```

---

## Task 8: Event Bus - Core Subscribe/Publish

**Files:**
- Create: `src/core/event_bus.py`
- Test: `tests/unit/test_event_bus.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_event_bus.py
from datetime import datetime
import pytest


def test_subscribe_and_publish():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    def handler(event: Event):
        received.append(event)

    bus.subscribe(["price_bar"], handler)

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received) == 1
    assert received[0].symbol == "AAPL"


def test_subscriber_not_called_for_other_types():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    def handler(event: Event):
        received.append(event)

    bus.subscribe(["price_bar"], handler)

    event = Event(
        type="fundamental_data",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received) == 0


def test_multiple_subscribers():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received_a = []
    received_b = []

    bus.subscribe(["price_bar"], lambda e: received_a.append(e))
    bus.subscribe(["price_bar"], lambda e: received_b.append(e))

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received_a) == 1
    assert len(received_b) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_event_bus.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/core/event_bus.py
"""Event bus for routing events to subscribers."""

import logging
from collections import defaultdict
from typing import Callable

from src.models import Event

logger = logging.getLogger(__name__)


class EventBus:
    """Simple pub/sub event bus for routing events to strategies."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, event_types: list[str], callback: Callable[[Event], None]) -> None:
        """Register callback for specific event types."""
        for event_type in event_types:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed {callback.__name__} to {event_type}")

    def publish(self, event: Event) -> None:
        """Send event to all subscribers of its type."""
        callbacks = self._subscribers.get(event.type, [])
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in subscriber {callback.__name__}: {e}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_event_bus.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/core/event_bus.py tests/unit/test_event_bus.py
git commit -m "feat: add EventBus with subscribe/publish"
```

---

## Task 9: Event Bus - Unsubscribe and Wildcard

**Files:**
- Modify: `src/core/event_bus.py`
- Modify: `tests/unit/test_event_bus.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_event_bus.py`:

```python
def test_unsubscribe():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    def handler(event: Event):
        received.append(event)

    bus.subscribe(["price_bar"], handler)
    bus.unsubscribe(handler)

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received) == 0


def test_wildcard_subscription():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    bus.subscribe(["*"], lambda e: received.append(e))

    bus.publish(Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    ))

    bus.publish(Event(
        type="fundamental_data",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    ))

    assert len(received) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_event_bus.py::test_unsubscribe -v`
Expected: FAIL with "AttributeError: 'EventBus' object has no attribute 'unsubscribe'"

**Step 3: Update implementation**

Add to `src/core/event_bus.py`:

```python
def unsubscribe(self, callback: Callable[[Event], None]) -> None:
    """Remove callback from all subscriptions."""
    for event_type in list(self._subscribers.keys()):
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed {callback.__name__} from {event_type}")
```

Update `publish` method:

```python
def publish(self, event: Event) -> None:
    """Send event to all subscribers of its type."""
    # Get specific type subscribers + wildcard subscribers
    callbacks = self._subscribers.get(event.type, []) + self._subscribers.get("*", [])
    for callback in callbacks:
        try:
            callback(event)
        except Exception as e:
            logger.error(f"Error in subscriber {callback.__name__}: {e}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_event_bus.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/core/event_bus.py tests/unit/test_event_bus.py
git commit -m "feat: add unsubscribe and wildcard support to EventBus"
```

---

## Task 10: Event Bus - Thread Safety

**Files:**
- Modify: `src/core/event_bus.py`
- Modify: `tests/unit/test_event_bus.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_event_bus.py`:

```python
import threading
import time


def test_thread_safe_publish():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []
    lock = threading.Lock()

    def handler(event: Event):
        with lock:
            received.append(event)

    bus.subscribe(["price_bar"], handler)

    def publish_events():
        for i in range(100):
            bus.publish(Event(
                type="price_bar",
                symbol=f"SYM{i}",
                timestamp=datetime(2026, 1, 5),
                ingested_at=datetime(2026, 1, 5),
                source="test",
                payload={"i": i}
            ))

    threads = [threading.Thread(target=publish_events) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(received) == 500
```

**Step 2: Run test to verify it fails (or passes - this is defensive)**

Run: `pytest tests/unit/test_event_bus.py::test_thread_safe_publish -v`
Expected: May pass or fail depending on race conditions

**Step 3: Update implementation for thread safety**

Update `src/core/event_bus.py`:

```python
import logging
import threading
from collections import defaultdict
from typing import Callable

from src.models import Event

logger = logging.getLogger(__name__)


class EventBus:
    """Thread-safe pub/sub event bus for routing events to strategies."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_types: list[str], callback: Callable[[Event], None]) -> None:
        """Register callback for specific event types."""
        with self._lock:
            for event_type in event_types:
                self._subscribers[event_type].append(callback)
                logger.debug(f"Subscribed {callback.__name__} to {event_type}")

    def unsubscribe(self, callback: Callable[[Event], None]) -> None:
        """Remove callback from all subscriptions."""
        with self._lock:
            for event_type in list(self._subscribers.keys()):
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"Unsubscribed {callback.__name__} from {event_type}")

    def publish(self, event: Event) -> None:
        """Send event to all subscribers of its type."""
        with self._lock:
            callbacks = list(self._subscribers.get(event.type, []) + self._subscribers.get("*", []))

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in subscriber {callback.__name__}: {e}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_event_bus.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add src/core/event_bus.py tests/unit/test_event_bus.py
git commit -m "feat: add thread safety to EventBus"
```

---

## Task 11: Run All Tests

**Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 2: Check coverage**

Run: `pytest tests/ --cov=src --cov-report=term-missing`
Expected: >80% coverage on implemented modules

**Step 3: Commit any fixes**

```bash
git add .
git commit -m "test: ensure all Phase 1 tests pass"
```

---

## Checkpoint: Phase 1 Complete

At this point you should have:

- [ ] Project structure with `pyproject.toml`
- [ ] All data models: Event, PriceBar, ContractInfo, FundamentalData, Order, OrderResult, LayerResult, Decision
- [ ] EventBus with subscribe, unsubscribe, publish, wildcard support, thread safety
- [ ] 100% test coverage on models and event bus
- [ ] Clean git history with atomic commits

**Next:** Continue to Phase 1.4 (File Data Store) in `2026-01-05-phase1-datastore-tdd.md`
