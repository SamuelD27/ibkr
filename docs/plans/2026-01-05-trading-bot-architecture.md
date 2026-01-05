# IBKR Trading Bot Architecture Design

**Date:** 2026-01-05
**Status:** Approved
**Goal:** Long-term, fundamentals-driven trading bot for US equities with plugin-based architecture

---

## 1. Project Vision

### Trading Philosophy
- **Fundamentals-first:** Decisions based on financial data, not short-term price movements
- **Patient:** Hold positions over time, exit only when fundamentals deteriorate or risk constraints breach
- **Cash is valid:** No requirement to always be invested
- **Capital preservation:** Safety over returns

### Architectural Philosophy
- **Plugin-based:** Strategies and data collectors are interchangeable plugins
- **Future-proof:** Support new asset classes, markets, data sources without rewriting core
- **Simplicity:** Core system is minimal and stable; complexity lives in plugins
- **Explainability:** Every decision has a clear audit trail

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATOR                                   │
│                    (Config, Lifecycle, Wiring)                              │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ├──────────────────────┬──────────────────────┬──────────────────────┐
        ▼                      ▼                      ▼                      ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  IBKR         │      │  EVENT BUS    │      │  DATA STORE   │      │  EXECUTION    │
│  COLLECTOR    │─────►│               │      │               │      │  ENGINE       │
│               │      │  Routes       │      │  File/Postgres│      │               │
│  - Prices     │      │  events to    │◄────►│               │      │  Dumb pipe    │
│  - Fundamentals│      │  subscribers  │      │  - Bars       │      │  to IBKR      │
│  - Parse XML  │      │               │      │  - Fundamentals│      │               │
└───────────────┘      └───────┬───────┘      │  - Events     │      └───────▲───────┘
                               │              │  - State      │              │
                               ▼              │  - Audit logs │              │
        ┌──────────────────────────────────┐  └───────────────┘              │
        │           STRATEGIES             │                                 │
        │  ┌────────────────────────────┐  │                                 │
        │  │ Strategy A                 │  │                                 │
        │  │  ┌─────────┐               │  │                                 │
        │  │  │ Layer 1 │ Screen        │  │                                 │
        │  │  └────┬────┘               │  │                                 │
        │  │       ▼                    │  │         ┌───────┐               │
        │  │  ┌─────────┐               │──┼────────►│ Order │───────────────┘
        │  │  │ Layer 2 │ Analyze       │  │         └───────┘
        │  │  └────┬────┘               │  │
        │  │       ▼                    │  │
        │  │  ┌─────────┐               │  │
        │  │  │ Layer N │ Decide        │  │
        │  │  └─────────┘               │  │
        │  └────────────────────────────┘  │
        └──────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 Event Bus

Routes events from collectors to strategies. Pure infrastructure, no business logic.

```python
@dataclass
class Event:
    type: str              # "price_bar", "fundamental_data"
    symbol: str | None     # Ticker if applicable
    timestamp: datetime    # When event occurred
    ingested_at: datetime  # When we received it
    source: str            # "ibkr"
    payload: dict          # The actual data
```

**Event Types:**
- `price_bar` - OHLCV data
- `fundamental_data` - Parsed company fundamentals
- `contract_details` - Symbol metadata

### 3.2 Data Store

Persists all data. Backend-agnostic interface with two implementations:

| Backend | Use Case |
|---------|----------|
| **FileDataStore** | Development - Parquet for time-series, JSON for state |
| **PostgresDataStore** | Production - TimescaleDB for scale |

```python
class DataStore(Protocol):
    # Price data
    def write_bars(self, symbol: str, bars: list[PriceBar]) -> None: ...
    def read_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]: ...

    # Fundamental data
    def write_fundamental(self, symbol: str, data: FundamentalData) -> None: ...
    def read_fundamental(self, symbol: str, as_of: datetime | None = None) -> FundamentalData | None: ...

    # Events (for backtesting replay)
    def write_event(self, event: Event) -> None: ...
    def read_events(self, start: datetime, end: datetime, types: list[str] | None = None) -> list[Event]: ...

    # Strategy state
    def save_strategy_state(self, strategy_name: str, state: dict) -> None: ...
    def load_strategy_state(self, strategy_name: str) -> dict | None: ...

    # Audit trail
    def log_decision(self, strategy_name: str, decision: Decision) -> None: ...
    def log_order(self, strategy_name: str, order: Order, result: OrderResult) -> None: ...
```

### 3.3 Execution Engine

**Dumb pipe** - receives orders, submits to IBKR, reports results. No intelligence.

```python
@dataclass
class Order:
    strategy_name: str
    symbol: str
    action: str           # "BUY" or "SELL"
    quantity: int
    order_type: str       # "MARKET", "LIMIT"
    limit_price: float | None

@dataclass
class OrderResult:
    order_id: int
    status: str           # "submitted", "filled", "rejected", "cancelled"
    fill_price: float | None
    fill_quantity: int | None
    message: str | None

class ExecutionEngine(Protocol):
    def submit(self, order: Order) -> OrderResult: ...
    def cancel(self, order_id: int) -> bool: ...
    def get_order_status(self, order_id: int) -> OrderResult: ...
```

### 3.4 Orchestrator

Wires everything together. Manages lifecycle. Contains no business logic.

```python
@dataclass
class StrategyConfig:
    name: str
    class_path: str
    allocated_capital: float
    enabled: bool
    params: dict

class Orchestrator:
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def add_strategy(self, config: StrategyConfig) -> None: ...
    def remove_strategy(self, name: str) -> None: ...
```

---

## 4. Plugin Components

### 4.1 Data Collectors (Plugin Type 1)

Continuously fetch data, parse into structured objects, emit events.

```python
class DataCollector(Protocol):
    name: str
    emits: list[str]  # Event types

    async def run(self, store: DataStore, bus: EventBus) -> Never: ...
```

**IBKR Collector** wraps the TWS API:
- Maintains connection (reconnect on failure)
- Subscribes to market data for watchlist
- Polls fundamental data (respecting rate limits)
- Parses XML → Python dataclasses
- Emits clean events

**Parsed Data Types:**

```python
@dataclass
class FundamentalData:
    symbol: str
    company_name: str
    cik: str
    employees: int
    shares_outstanding: float
    float_shares: float
    industry: str
    category: str
    # ... additional fields parsed from XML

@dataclass
class PriceBar:
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
```

### 4.2 Strategies (Plugin Type 2)

Multi-layer pipelines that progressively filter and analyze data.

```python
class Action(Enum):
    HOLD = "hold"
    BUY = "buy"
    EXIT = "exit"

@dataclass
class LayerResult:
    passed: bool
    data: dict
    reasoning: str

@dataclass
class Decision:
    symbol: str
    action: Action
    target_weight: float
    confidence: float
    reasoning: str

class StrategyLayer(Protocol):
    name: str
    def process(self, symbol: str, data: dict) -> LayerResult: ...

class Strategy(Protocol):
    name: str
    subscriptions: list[str]
    layers: list[StrategyLayer]
    allocated_capital: float

    def on_event(self, event: Event) -> list[Decision]: ...
```

**Pipeline Flow:**

```
Event arrives
    │
    ▼
┌─────────────┐
│  Layer 1    │ ──reject──► Stop processing
│  (Screen)   │
└─────┬───────┘
      │ pass (enriched data)
      ▼
┌─────────────┐
│  Layer 2    │ ──reject──► Stop processing
│  (Analyze)  │
└─────┬───────┘
      │ pass (enriched data)
      ▼
┌─────────────┐
│  Layer N    │ ──► Decision (BUY/HOLD/EXIT)
│  (Decide)   │
└─────────────┘
```

**Strategy Responsibilities:**
- Position tracking (knows its current holdings)
- Capital management (stays within allocated amount)
- Order generation (full control over what orders to submit)
- State management (save/restore for backtesting)

---

## 5. Data Flow

### 5.1 Live Trading Flow

```
1. IBKR Collector fetches data continuously
2. Collector parses XML → dataclasses
3. Collector emits Event to Event Bus
4. Event Bus routes to subscribed Strategies
5. Strategy runs event through layer pipeline
6. If all layers pass → Strategy generates Order
7. Strategy submits Order to Execution Engine
8. Execution Engine calls IBKR API
9. Execution Engine returns OrderResult
10. Strategy updates its position tracking
```

### 5.2 Backtesting Flow

```
1. Load historical Events from Data Store
2. Replay events in timestamp order through Event Bus
3. Strategies process exactly as in live mode
4. Orders go to MockExecutionEngine (simulates fills)
5. Compare results across strategy variants
```

---

## 6. Configuration

```yaml
# config.yaml
ibkr:
  host: "127.0.0.1"
  port: 7497          # Paper trading
  client_id: 1

data_store:
  backend: "file"     # or "postgres"
  path: "./data"

strategies:
  - name: "value_investor"
    class_path: "strategies.value.ValueStrategy"
    allocated_capital: 50000
    enabled: true
    params:
      max_positions: 10

  - name: "quality_growth"
    class_path: "strategies.growth.QualityGrowthStrategy"
    allocated_capital: 30000
    enabled: true
    params:
      min_roe: 0.15
```

---

## 7. Directory Structure

```
ibkr/
├── config.yaml
├── CLAUDE.md
├── docs/
│   └── plans/
│       └── 2026-01-05-trading-bot-architecture.md
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── event_bus.py
│   │   ├── data_store.py
│   │   ├── execution_engine.py
│   │   └── orchestrator.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── ibkr_collector.py
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── example_value/
│   │       ├── __init__.py
│   │       ├── strategy.py
│   │       └── layers/
│   │           ├── screen.py
│   │           ├── analyze.py
│   │           └── decide.py
│   └── models/
│       ├── __init__.py
│       ├── events.py
│       ├── market_data.py
│       ├── fundamental_data.py
│       └── orders.py
├── tests/
│   ├── unit/
│   └── integration/
└── data/           # Local file store (gitignored)
```

---

## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Event-driven architecture | Clean backtesting (replay events), decoupled components |
| Strategies own positions | Full autonomy per strategy, no central interference |
| Multi-layer strategy pipeline | Progressive filtering, strategy-specific depth |
| Parsed data (not raw XML) | Strategies never deal with IBKR formats |
| Dumb execution engine | Single responsibility, strategies have full control |
| File + Postgres backends | Simple development, scalable production |
| IBKR-only data source (initially) | Minimize dependencies for paper trading phase |

---

## 9. Future Extensions

Enabled by plugin architecture:

- **New data sources:** Add Polygon, SEC EDGAR, alternative data collectors
- **New asset classes:** Options, futures, crypto (new contract types in collector)
- **New strategies:** Drop in new strategy folders
- **ML integration:** Strategy layers can call ML models
- **Multi-account:** Execution engine routes to different IBKR accounts
- **Live risk overlay:** Add portfolio-level risk manager when moving to live trading
