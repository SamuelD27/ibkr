# IBKR Trading Bot - Repository Structure

## Overview

An event-driven algorithmic trading system built for Interactive Brokers TWS/Gateway. The architecture follows a modular design with clear separation between data collection, strategy execution, and order management.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orchestrator                             │
│  (Wires components, manages lifecycle, loads strategies)        │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Collector  │─────▶│  Event Bus  │◀─────│  Strategies │
│  (IBKR API) │      │  (Pub/Sub)  │      │  (Layers)   │
└─────────────┘      └─────────────┘      └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Connection │      │  Data Store │      │  Execution  │
│  Manager    │      │  (Parquet)  │      │  Engine     │
└─────────────┘      └─────────────┘      └─────────────┘
```

## Directory Structure

```
ibkr/
├── src/                    # Main application code
│   ├── __main__.py         # CLI entry point
│   ├── core/               # Core infrastructure
│   ├── collectors/         # Data collection (IBKR)
│   ├── strategies/         # Trading strategies
│   └── models/             # Data models
├── tests/                  # Test suites
│   ├── unit/               # Unit tests (124 tests)
│   └── integration/        # Integration tests (19 tests)
├── config/                 # Configuration files
│   └── default.yaml        # Default configuration
├── data/                   # Runtime data storage
└── docs/                   # Documentation & plans
```

## Core Components

### 1. Entry Point (`src/__main__.py`)

The CLI that boots the system:

```bash
python -m src --config config/default.yaml --log-level INFO
```

- Parses command-line arguments
- Sets up logging
- Loads configuration
- Creates and starts the Orchestrator
- Handles graceful shutdown (SIGINT/SIGTERM)

### 2. Orchestrator (`src/core/orchestrator.py`)

Central coordinator that wires all components:

```python
orchestrator = Orchestrator(config)
orchestrator.start()  # Blocks until stopped
orchestrator.stop()   # Saves state, cleanup
```

**Responsibilities:**
- Initialize EventBus, DataStore, Connection
- Load and instantiate strategies from config
- Subscribe strategies to relevant event types
- Restore strategy state on startup
- Save strategy state on shutdown

### 3. Event Bus (`src/core/event_bus.py`)

Pub/sub system for decoupled communication:

```python
event_bus = EventBus()
event_bus.subscribe(["price_bar", "fundamental_data"], handler)
event_bus.publish(event)
```

Events flow: `Collector → EventBus → Strategies`

### 4. Data Store (`src/core/data_store.py`)

Persistent storage with type-appropriate formats:

| Data Type | Format | Location |
|-----------|--------|----------|
| Price bars | Parquet | `data/prices/{symbol}.parquet` |
| Fundamentals | JSON | `data/fundamentals/{symbol}.json` |
| Strategy state | JSON | `data/strategies/{name}_state.json` |
| Decisions | JSONL | `data/decisions/{name}.jsonl` |

### 5. Configuration (`src/core/config.py`)

YAML-based configuration with dataclass validation:

```yaml
ibkr:
  host: "127.0.0.1"
  port: 7497
  client_id: 1

strategies:
  - name: "my_strategy"
    class_path: "src.strategies.my_strategy.MyStrategy"
    allocated_capital: 10000
    enabled: true
    params:
      threshold: 0.5
```

## Data Collection

### IBKR Connection (`src/collectors/ibkr/connection.py`)

Manages TWS/Gateway connection:

```python
connection = IBKRConnection(host="127.0.0.1", port=7497, client_id=1)
order_id = connection.next_order_id  # Auto-incrementing
```

### IBKR Collector (`src/collectors/ibkr/collector.py`)

Collects market data and publishes events:

```python
collector = IBKRCollector(connection, event_bus, data_store, watchlist)
collector.add_symbol("AAPL")
await collector.run()
```

### XML Parser (`src/collectors/ibkr/parsers.py`)

Parses IBKR fundamental data XML:

```python
fundamental = parse_report_snapshot(xml_string, "AAPL")
# Returns FundamentalData with company_name, shares_outstanding, etc.
```

## Strategy Framework

### Strategy Protocol (`src/strategies/base.py`)

All strategies implement this interface:

```python
class Strategy(Protocol):
    name: str
    subscriptions: list[str]  # Event types to receive
    allocated_capital: float

    def on_event(self, event: Event) -> list[Decision]: ...
    def get_positions(self) -> dict[str, Position]: ...
    def get_state(self) -> dict: ...
    def load_state(self, state: dict) -> None: ...
```

### Layer Pipeline (`src/strategies/pipeline.py`)

Strategies use composable layers:

```python
pipeline = StrategyPipeline([
    LiquidityScreen(min_market_cap=1_000_000_000),
    ValuationFilter(max_pe=20),
    DecisionLayer(),
])

passed, data, reasoning = pipeline.run("AAPL", initial_data)
```

Each layer returns `LayerResult(passed, data, reasoning)`.

### Example Strategy (`src/strategies/example_value/`)

```
example_value/
├── __init__.py
├── strategy.py           # Main strategy class
└── layers/
    ├── liquidity_screen.py  # Market cap filter
    └── decision.py          # Final decision logic
```

## Data Models (`src/models/`)

| Model | Purpose |
|-------|---------|
| `Event` | Base event with type, symbol, timestamp, payload |
| `PriceBar` | OHLCV data |
| `FundamentalData` | Company fundamentals (shares, industry, etc.) |
| `Decision` | Trading signal (symbol, action, confidence) |
| `Order` | Order specification |
| `OrderResult` | Execution result |
| `Position` | Current holding |
| `LayerResult` | Pipeline layer output |

## Execution Engine (`src/core/execution_engine.py`)

Submits and manages orders:

```python
engine = ExecutionEngine(connection)
result = engine.submit(order)
engine.cancel(order_id)
```

## Running the System

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with paper trading (TWS on port 7497)
python -m src --config config/default.yaml
```

### Configuration

1. Copy `config/default.yaml` to `config/local.yaml`
2. Adjust IBKR connection settings
3. Add/configure strategies
4. Run: `python -m src -c config/local.yaml`

## Creating a New Strategy

1. Create directory: `src/strategies/my_strategy/`

2. Implement layers:
```python
# layers/my_filter.py
class MyFilter:
    name = "my_filter"

    def process(self, symbol: str, data: dict) -> LayerResult:
        passed = data["price"] > 100
        return LayerResult(passed=passed, data=data, reasoning="...")
```

3. Implement strategy:
```python
# strategy.py
class MyStrategy:
    name = "my_strategy"
    subscriptions = ["price_bar", "fundamental_data"]

    def __init__(self, allocated_capital: float, **params):
        self.allocated_capital = allocated_capital
        self.pipeline = StrategyPipeline([MyFilter(), DecisionLayer()])

    def on_event(self, event: Event) -> list[Decision]:
        # Process event, run pipeline, return decisions
        ...
```

4. Add to config:
```yaml
strategies:
  - name: "my_strategy"
    class_path: "src.strategies.my_strategy.MyStrategy"
    allocated_capital: 50000
    enabled: true
```

## Test Coverage

```
143 tests | 96% coverage
├── Unit Tests (124)
│   ├── Models
│   ├── Core (EventBus, DataStore, Config, Orchestrator)
│   ├── Collectors (Parser, Connection, Collector)
│   └── Strategies (Base, Pipeline, ExampleValue)
└── Integration Tests (19)
    ├── IBKR Connection (5)
    ├── Live Data Collection (7)
    └── End-to-End Flow (7)
```

## Key Design Decisions

1. **Event-Driven**: Decoupled components communicate via EventBus
2. **Protocol-Based**: Strategies implement protocols, not inherit classes
3. **Layer Pipeline**: Composable, testable strategy logic
4. **Type-Appropriate Storage**: Parquet for time-series, JSON for documents
5. **State Persistence**: Strategies restore state across restarts
6. **Graceful Shutdown**: Signal handlers ensure clean cleanup
