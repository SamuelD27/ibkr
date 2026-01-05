# IBKR Trading Bot Implementation Plan

**Date:** 2026-01-05
**Architecture:** See `2026-01-05-trading-bot-architecture.md`
**Goal:** Paper trading with fundamentals-driven strategies

---

## Overview

This plan breaks the architecture into implementable steps, ordered by dependencies. Each step produces working, testable code before moving to the next.

---

## Phase 1: Foundation (Core Infrastructure)

### 1.1 Project Structure

**Goal:** Set up Python project with proper packaging and tooling.

**Tasks:**
- Create directory structure:
  ```
  src/
  ├── core/
  ├── collectors/
  ├── strategies/
  ├── models/
  └── __init__.py
  tests/
  ├── unit/
  └── integration/
  ```
- Create `pyproject.toml` with dependencies:
  - `ibapi` (local wheel)
  - `ib_async` (optional, for simpler async patterns)
  - `pyyaml` (config)
  - `pyarrow` (Parquet storage)
  - `pytest` (testing)
- Configure `mypy` for type checking
- Create `requirements.txt` for venv setup

**Deliverable:** Runnable Python package with `python -m src` entry point.

---

### 1.2 Data Models

**Goal:** Define all dataclasses used across the system.

**File:** `src/models/`

**Tasks:**

#### `src/models/events.py`
```python
@dataclass
class Event:
    type: str              # "price_bar", "fundamental_data", etc.
    symbol: str | None     # Ticker (None for system events)
    timestamp: datetime    # When event occurred
    ingested_at: datetime  # When we received it
    source: str            # "ibkr", "file", etc.
    payload: dict          # Actual data
```

#### `src/models/market_data.py`
```python
@dataclass
class PriceBar:
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

@dataclass
class ContractInfo:
    symbol: str
    con_id: int
    long_name: str
    industry: str
    category: str
    subcategory: str
    exchange: str
    currency: str
```

#### `src/models/fundamental_data.py`
```python
@dataclass
class FundamentalData:
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

    # Raw data preserved
    raw_xml: str  # Keep original for debugging
```

#### `src/models/orders.py`
```python
class Action(Enum):
    HOLD = "hold"
    BUY = "buy"
    EXIT = "exit"

@dataclass
class Order:
    strategy_name: str
    symbol: str
    action: str           # "BUY" or "SELL"
    quantity: int
    order_type: str       # "MARKET", "LIMIT"
    limit_price: float | None = None

@dataclass
class OrderResult:
    order_id: int
    status: str           # "submitted", "filled", "rejected", "cancelled"
    fill_price: float | None = None
    fill_quantity: int | None = None
    message: str | None = None
```

#### `src/models/strategy.py`
```python
@dataclass
class LayerResult:
    passed: bool
    data: dict
    reasoning: str

@dataclass
class Decision:
    symbol: str
    action: Action
    target_weight: float  # 0.0 to 1.0
    confidence: float     # 0.0 to 1.0
    reasoning: str        # Full audit trail
```

**Deliverable:** All models importable from `src.models`.

---

### 1.3 Event Bus

**Goal:** Simple pub/sub system for routing events to strategies.

**File:** `src/core/event_bus.py`

**Interface:**
```python
class EventBus:
    def subscribe(self, event_types: list[str], callback: Callable[[Event], None]) -> None:
        """Register callback for specific event types."""

    def unsubscribe(self, callback: Callable[[Event], None]) -> None:
        """Remove callback from all subscriptions."""

    def publish(self, event: Event) -> None:
        """Send event to all subscribers of its type."""

    def publish_async(self, event: Event) -> None:
        """Non-blocking publish (queues event)."""
```

**Implementation notes:**
- Use `defaultdict(list)` for subscriptions by event type
- Support wildcard subscription (`*` for all events)
- Thread-safe with `threading.Lock`
- Optional async queue for non-blocking publish

**Deliverable:** Working event bus with unit tests.

---

### 1.4 File Data Store

**Goal:** Persist data to local files for development and backtesting.

**File:** `src/core/data_store.py`

**Interface:**
```python
class DataStore(Protocol):
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
```

**File structure:**
```
data/
├── prices/
│   └── AAPL/
│       ├── 2026-01.parquet
│       └── 2026-02.parquet
├── fundamentals/
│   └── AAPL/
│       └── 2026-01-05.json
├── events/
│   └── 2026-01-05.parquet
├── state/
│   └── value_strategy.json
└── audit/
    ├── decisions/
    │   └── 2026-01-05.jsonl
    └── orders/
        └── 2026-01-05.jsonl
```

**Implementation notes:**
- Use `pyarrow` for Parquet read/write
- Partition by month for prices, day for events
- JSONL (JSON Lines) for append-only audit logs
- Create directories on first write

**Deliverable:** Working file data store with unit tests.

---

## Phase 2: IBKR Integration

### 2.1 IBKR Connection Manager

**Goal:** Reliable connection to TWS/Gateway with auto-reconnect.

**File:** `src/collectors/ibkr/connection.py`

**Interface:**
```python
class IBKRConnection:
    def __init__(self, host: str, port: int, client_id: int): ...

    def connect(self) -> None:
        """Connect and wait for nextValidId."""

    def disconnect(self) -> None:
        """Graceful disconnect."""

    def is_connected(self) -> bool: ...

    def get_client(self) -> EClient:
        """Get underlying client for API calls."""

    @property
    def next_order_id(self) -> int:
        """Get and increment order ID."""
```

**Implementation notes:**
- Wrap `EClient` and `EWrapper`
- Wait for `nextValidId` before returning from `connect()`
- Auto-reconnect with exponential backoff on disconnect
- Thread-safe order ID management
- Log all connection state changes

**Deliverable:** Reliable connection that survives TWS restarts.

---

### 2.2 XML Parser for Fundamental Data

**Goal:** Parse IBKR's XML fundamental data into `FundamentalData` dataclass.

**File:** `src/collectors/ibkr/parsers.py`

**Interface:**
```python
def parse_report_snapshot(xml_string: str, symbol: str) -> FundamentalData:
    """Parse ReportSnapshot XML into FundamentalData."""

def parse_financial_statements(xml_string: str, symbol: str) -> dict:
    """Parse ReportsFinStatements XML into structured dict."""
```

**Implementation notes:**
- Use `xml.etree.ElementTree` (stdlib, no dependencies)
- Handle missing fields gracefully (None values)
- Preserve raw XML in dataclass for debugging
- Log parse errors but don't crash

**XML fields to extract (ReportSnapshot):**
- `CoIDs/CoID[@Type='CompanyName']` → company_name
- `CoIDs/CoID[@Type='CIKNo']` → cik
- `CoGeneralInfo/Employees` → employees
- `CoGeneralInfo/SharesOut` → shares_outstanding
- `CoGeneralInfo/SharesOut/@TotalFloat` → float_shares

**Deliverable:** Parser with tests against sample XML.

---

### 2.3 IBKR Collector

**Goal:** Continuous data collection from IBKR, emitting events.

**File:** `src/collectors/ibkr/collector.py`

**Interface:**
```python
class IBKRCollector:
    def __init__(
        self,
        connection: IBKRConnection,
        event_bus: EventBus,
        data_store: DataStore,
        watchlist: list[str],
    ): ...

    async def run(self) -> None:
        """Run forever, fetching data and emitting events."""

    def stop(self) -> None:
        """Signal to stop."""
```

**Responsibilities:**
1. Subscribe to market data for watchlist symbols
2. Poll fundamental data periodically (respect rate limits)
3. Parse all data into dataclasses
4. Persist to data store
5. Emit events to event bus

**Rate limit handling:**
- Fundamental data: Max 1 request per symbol per hour
- Historical data: 60 requests / 10 minutes
- Market data: Limited by subscription lines

**Implementation notes:**
- Use `asyncio` for concurrent data fetching
- Maintain internal state of last fetch times
- Queue requests to stay under rate limits
- Emit events immediately on data arrival

**Deliverable:** Collector that runs continuously and emits events.

---

### 2.4 Execution Engine

**Goal:** Submit orders to IBKR and report results.

**File:** `src/core/execution_engine.py`

**Interface:**
```python
class ExecutionEngine:
    def __init__(self, connection: IBKRConnection): ...

    def submit(self, order: Order) -> OrderResult:
        """Submit order to IBKR, return result."""

    def cancel(self, order_id: int) -> bool:
        """Cancel pending order."""

    def get_order_status(self, order_id: int) -> OrderResult:
        """Check status of submitted order."""
```

**Implementation notes:**
- Map `Order` to IBKR `Contract` + `Order` objects
- Handle order ID management via connection
- Wait for fill confirmation (with timeout)
- Log all orders and results
- No position tracking (strategy's responsibility)

**Deliverable:** Working execution engine tested with paper trading.

---

## Phase 3: Strategy Framework

### 3.1 Strategy Base Classes

**Goal:** Define protocols/base classes for strategies and layers.

**File:** `src/strategies/base.py`

**Interface:**
```python
class StrategyLayer(Protocol):
    """Single layer in a strategy pipeline."""

    name: str

    def process(self, symbol: str, data: dict) -> LayerResult:
        """
        Analyze data, return whether to pass to next layer.
        Mutate data dict to add analysis results.
        """
        ...

class Strategy(Protocol):
    """Multi-layer strategy pipeline."""

    name: str
    subscriptions: list[str]  # Event types to subscribe to
    allocated_capital: float

    def on_event(self, event: Event) -> list[Decision]:
        """Process event through layer pipeline."""
        ...

    def get_positions(self) -> dict[str, Position]:
        """Current positions held by this strategy."""
        ...

    def get_state(self) -> dict:
        """Serializable state for persistence."""
        ...

    def load_state(self, state: dict) -> None:
        """Restore from saved state."""
        ...
```

**Deliverable:** Base classes with documentation.

---

### 3.2 Layer Pipeline Runner

**Goal:** Run events through strategy layers, accumulate reasoning.

**File:** `src/strategies/pipeline.py`

**Interface:**
```python
class StrategyPipeline:
    def __init__(self, layers: list[StrategyLayer]): ...

    def run(self, symbol: str, initial_data: dict) -> tuple[bool, dict, str]:
        """
        Run data through all layers.
        Returns: (passed_all, final_data, accumulated_reasoning)
        """
```

**Implementation notes:**
- Stop at first layer that returns `passed=False`
- Accumulate reasoning from each layer
- Pass enriched data dict through layers
- Log each layer's decision

**Deliverable:** Pipeline runner with unit tests.

---

### 3.3 Example Strategy

**Goal:** Simple working strategy for end-to-end testing.

**File:** `src/strategies/example_value/`

**Structure:**
```
example_value/
├── __init__.py
├── strategy.py
└── layers/
    ├── __init__.py
    ├── liquidity_screen.py
    └── decision.py
```

**Layers:**
1. `LiquidityScreen`: Pass if market cap > threshold (from fundamental data)
2. `DecisionLayer`: Always return HOLD (no actual trading logic)

**Purpose:** Validate the full pipeline works before building real strategies.

**Deliverable:** Working example strategy that processes events.

---

## Phase 4: Orchestration

### 4.1 Config Loader

**Goal:** Load system configuration from YAML.

**File:** `src/core/config.py`

**Config schema:**
```yaml
ibkr:
  host: "127.0.0.1"
  port: 7497
  client_id: 1

data_store:
  backend: "file"  # or "postgres"
  path: "./data"

collector:
  watchlist:
    - "AAPL"
    - "MSFT"
    - "GOOGL"
  fundamental_refresh_hours: 24

strategies:
  - name: "example_value"
    class_path: "src.strategies.example_value.ExampleValueStrategy"
    allocated_capital: 10000
    enabled: true
    params: {}
```

**Implementation notes:**
- Use `pydantic` for validation (optional)
- Support environment variable overrides
- Validate strategy class paths exist

**Deliverable:** Config loader with validation.

---

### 4.2 Orchestrator

**Goal:** Wire all components together and manage lifecycle.

**File:** `src/core/orchestrator.py`

**Interface:**
```python
class Orchestrator:
    def __init__(self, config_path: str): ...

    def start(self) -> None:
        """
        1. Load config
        2. Initialize data store
        3. Connect to IBKR
        4. Start collector
        5. Load and wire strategies
        6. Begin processing
        """

    def stop(self) -> None:
        """
        1. Stop collector
        2. Save strategy states
        3. Disconnect from IBKR
        """

    def add_strategy(self, config: StrategyConfig) -> None:
        """Hot-add strategy at runtime."""

    def remove_strategy(self, name: str) -> None:
        """Hot-remove strategy."""
```

**Implementation notes:**
- Use signal handlers for graceful shutdown (SIGINT, SIGTERM)
- Save strategy states periodically (not just on shutdown)
- Log all lifecycle events

**Deliverable:** Working orchestrator that runs the system.

---

### 4.3 Main Entry Point

**Goal:** CLI to run the trading bot.

**File:** `src/__main__.py`

**Usage:**
```bash
# Run with default config
python -m src

# Run with custom config
python -m src --config path/to/config.yaml

# Run in backtest mode (future)
python -m src --backtest --start 2025-01-01 --end 2025-12-31
```

**Implementation notes:**
- Use `argparse` for CLI
- Setup logging configuration
- Handle keyboard interrupt gracefully

**Deliverable:** Working CLI entry point.

---

## Phase 5: Testing & Validation

### 5.1 Unit Tests

**Goal:** Test each component in isolation.

**Tests to write:**
- `tests/unit/test_event_bus.py` - Pub/sub functionality
- `tests/unit/test_data_store.py` - File read/write
- `tests/unit/test_xml_parser.py` - XML parsing with sample data
- `tests/unit/test_pipeline.py` - Layer pipeline execution
- `tests/unit/test_models.py` - Dataclass serialization

**Deliverable:** >80% code coverage on core components.

---

### 5.2 Integration Tests

**Goal:** Test component interactions with mock IBKR.

**File:** `tests/integration/`

**Tests:**
- Collector → Event Bus → Strategy flow
- Strategy → Execution Engine flow
- Full config load → start → stop cycle

**Mock IBKR:**
- Create `MockIBKRConnection` that returns canned data
- Simulate market data callbacks
- Simulate order fills

**Deliverable:** Integration tests that run without live IBKR.

---

### 5.3 Paper Trading Test

**Goal:** Validate system works with real TWS paper account.

**Manual test checklist:**
- [ ] Connect to TWS paper trading (port 7497)
- [ ] Receive market data for watchlist
- [ ] Receive fundamental data
- [ ] Events flow through to strategy
- [ ] Strategy decisions are logged
- [ ] Orders submit correctly (with example that actually trades)
- [ ] Graceful shutdown preserves state

**Deliverable:** Documented test run with logs.

---

## Dependency Graph

```
Phase 1:
  1.1 Project Structure
   └─► 1.2 Data Models
        └─► 1.3 Event Bus
             └─► 1.4 File Data Store

Phase 2:
  1.2 ──────────────────────────────────────┐
  1.3 ──────────────────────────────────────┤
  1.4 ──────────────────────────────────────┤
       └─► 2.1 IBKR Connection              │
            ├─► 2.2 XML Parser              │
            │    └─► 2.3 IBKR Collector ◄───┘
            └─► 2.4 Execution Engine

Phase 3:
  1.2 ─► 3.1 Strategy Base
          └─► 3.2 Pipeline Runner
               └─► 3.3 Example Strategy

Phase 4:
  All Phase 1-3 ─► 4.1 Config
                   └─► 4.2 Orchestrator
                        └─► 4.3 Main Entry

Phase 5:
  All ─► 5.1 Unit Tests
         └─► 5.2 Integration Tests
              └─► 5.3 Paper Trading Test
```

---

## First Milestone

**Goal:** Data flowing from IBKR to console output.

**Steps:** 1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 2.3

**Validation:** Run collector, see events printed to console with parsed fundamental data.

---

## Second Milestone

**Goal:** Strategy receives events and logs decisions.

**Steps:** + 1.4 → 3.1 → 3.2 → 3.3 → 4.1 → 4.2 → 4.3

**Validation:** Run full system, see strategy layer reasoning in logs.

---

## Third Milestone

**Goal:** End-to-end paper trading.

**Steps:** + 2.4 → 5.x

**Validation:** Submit test order to paper account, confirm fill.
