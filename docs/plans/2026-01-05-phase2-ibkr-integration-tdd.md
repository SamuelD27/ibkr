# Phase 2: IBKR Integration - TDD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect to IBKR TWS/Gateway, collect market and fundamental data, execute orders

**Architecture:** Connection manager handles reconnection, collector emits events, execution engine submits orders

**Tech Stack:** Python 3.12+, ibapi (local wheel), ib_async (optional), xml.etree.ElementTree

---

## Task 1: XML Parser for Fundamental Data

**Files:**
- Create: `src/collectors/ibkr/parsers.py`
- Test: `tests/unit/test_xml_parser.py`

**Why first:** No dependencies, can be tested with sample XML without live connection.

**Step 1: Write the failing test**

```python
# tests/unit/test_xml_parser.py
import pytest

SAMPLE_REPORT_SNAPSHOT = '''<?xml version="1.0" encoding="UTF-8"?>
<ReportSnapshot>
  <CoIDs>
    <CoID Type="CompanyName">Apple Inc</CoID>
    <CoID Type="CIKNo">0000320193</CoID>
  </CoIDs>
  <CoGeneralInfo>
    <Employees>166000</Employees>
    <SharesOut TotalFloat="14525947723.0">14776353000.0</SharesOut>
  </CoGeneralInfo>
</ReportSnapshot>
'''

def test_parse_report_snapshot():
    from src.collectors.ibkr.parsers import parse_report_snapshot

    result = parse_report_snapshot(SAMPLE_REPORT_SNAPSHOT, "AAPL")

    assert result.symbol == "AAPL"
    assert result.company_name == "Apple Inc"
    assert result.cik == "0000320193"
    assert result.employees == 166000
    assert result.shares_outstanding == 14776353000.0
    assert result.float_shares == 14525947723.0
```

**Step 2-5:** Run test (fail), implement, run test (pass), commit.

---

## Task 2: IBKR Connection Manager

**Files:**
- Create: `src/collectors/ibkr/__init__.py`
- Create: `src/collectors/ibkr/connection.py`
- Test: `tests/unit/test_ibkr_connection.py`

**Step 1: Write the failing test (with mock)**

```python
# tests/unit/test_ibkr_connection.py
from unittest.mock import Mock, patch
import pytest


def test_connection_manager_init():
    from src.collectors.ibkr.connection import IBKRConnection

    conn = IBKRConnection(host="127.0.0.1", port=7497, client_id=1)

    assert conn.host == "127.0.0.1"
    assert conn.port == 7497
    assert conn.client_id == 1
    assert not conn.is_connected()


def test_next_order_id_increments():
    from src.collectors.ibkr.connection import IBKRConnection

    conn = IBKRConnection(host="127.0.0.1", port=7497, client_id=1)
    conn._next_order_id = 100

    assert conn.next_order_id == 100
    assert conn.next_order_id == 101
    assert conn.next_order_id == 102
```

---

## Task 3: Execution Engine

**Files:**
- Create: `src/core/execution_engine.py`
- Test: `tests/unit/test_execution_engine.py`

**Interface:**
```python
class ExecutionEngine:
    def __init__(self, connection: IBKRConnection): ...
    def submit(self, order: Order) -> OrderResult: ...
    def cancel(self, order_id: int) -> bool: ...
```

---

## Task 4: IBKR Collector

**Files:**
- Create: `src/collectors/ibkr/collector.py`
- Test: `tests/unit/test_ibkr_collector.py`

**Interface:**
```python
class IBKRCollector:
    def __init__(self, connection, event_bus, data_store, watchlist): ...
    async def run(self) -> None: ...
    def stop(self) -> None: ...
```

---

## Implementation Order

1. **XML Parser** - No dependencies, pure function
2. **Connection Manager** - Foundation for collector and execution
3. **Execution Engine** - Uses connection manager
4. **IBKR Collector** - Uses all above components

## Testing Strategy

- Unit tests use mocks for IBKR API
- Integration tests require TWS paper trading (manual)
- Sample XML data for parser tests
