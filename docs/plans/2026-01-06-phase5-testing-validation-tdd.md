# Phase 5: Testing & Validation - TDD Plan

## Overview
Integration tests with live IBKR connection to validate the full system works correctly.

## Prerequisites
- TWS or IB Gateway running on port 7497 (paper trading)
- API connections enabled in TWS settings

## Task 1: IBKR Connection Integration Test
**Goal:** Verify real connection to TWS/Gateway works

### Tests to Write:
1. `test_connect_to_tws` - Establish connection, verify `nextValidId` received
2. `test_disconnect_cleanly` - Connect then disconnect without errors
3. `test_connection_provides_valid_order_id` - Order ID > 0 after connection
4. `test_reconnect_after_disconnect` - Can reconnect after clean disconnect

### Implementation:
- Use real `ib_async` connection
- Timeout handling for CI environments without TWS
- Skip decorator for environments without live connection

---

## Task 2: Live Data Collection Test
**Goal:** Verify market data and fundamental data retrieval

### Tests to Write:
1. `test_request_contract_details` - Get AAPL contract details
2. `test_request_historical_bars` - Get recent price bars
3. `test_request_fundamental_data` - Get fundamental XML (if subscribed)
4. `test_parse_live_fundamental_data` - Parse actual IBKR XML response

### Implementation:
- Request real market data for AAPL
- Verify data structures match our models
- Handle subscription limitations gracefully

---

## Task 3: End-to-End System Test
**Goal:** Verify full system startup and data flow

### Tests to Write:
1. `test_orchestrator_with_live_connection` - Start orchestrator, receive events
2. `test_strategy_receives_live_data` - Strategy processes real price data
3. `test_graceful_shutdown_with_live_connection` - Clean shutdown preserves state

### Implementation:
- Use real config with live connection
- Verify event bus receives real market events
- Test signal handling for graceful shutdown

---

## Test Markers
```python
@pytest.mark.integration  # Requires live IBKR connection
@pytest.mark.slow        # Takes > 1 second
```

## Running Integration Tests
```bash
# Run only integration tests (requires TWS running)
pytest tests/integration/ -v -m integration

# Skip integration tests in CI
pytest tests/ -v -m "not integration"
```
