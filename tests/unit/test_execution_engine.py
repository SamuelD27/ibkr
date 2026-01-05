"""Tests for Execution Engine."""
from unittest.mock import Mock, MagicMock, patch
import pytest


@pytest.fixture
def mock_connection():
    """Create a mock IBKR connection."""
    from src.collectors.ibkr.connection import IBKRConnection

    conn = Mock(spec=IBKRConnection)
    conn.is_connected.return_value = True
    conn._next_order_id = 100

    # Make next_order_id property work correctly
    order_id_counter = [100]

    def get_next_order_id():
        oid = order_id_counter[0]
        order_id_counter[0] += 1
        return oid

    type(conn).next_order_id = property(lambda self: get_next_order_id())

    return conn


def test_execution_engine_init(mock_connection):
    from src.core.execution_engine import ExecutionEngine

    engine = ExecutionEngine(connection=mock_connection)

    assert engine.connection is mock_connection


def test_submit_order(mock_connection):
    from src.core.execution_engine import ExecutionEngine
    from src.models import Order

    engine = ExecutionEngine(connection=mock_connection)

    order = Order(
        strategy_name="test_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MARKET",
    )

    result = engine.submit(order)

    assert result.order_id == 100
    assert result.status == "submitted"


def test_submit_order_increments_id(mock_connection):
    from src.core.execution_engine import ExecutionEngine
    from src.models import Order

    engine = ExecutionEngine(connection=mock_connection)

    order1 = Order(
        strategy_name="test_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MARKET",
    )
    order2 = Order(
        strategy_name="test_strategy",
        symbol="MSFT",
        action="BUY",
        quantity=50,
        order_type="MARKET",
    )

    result1 = engine.submit(order1)
    result2 = engine.submit(order2)

    assert result1.order_id == 100
    assert result2.order_id == 101


def test_submit_order_not_connected():
    from src.core.execution_engine import ExecutionEngine
    from src.collectors.ibkr.connection import IBKRConnection
    from src.models import Order

    conn = Mock(spec=IBKRConnection)
    conn.is_connected.return_value = False

    engine = ExecutionEngine(connection=conn)

    order = Order(
        strategy_name="test_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MARKET",
    )

    result = engine.submit(order)

    assert result.status == "rejected"
    assert "not connected" in result.message.lower()


def test_submit_limit_order(mock_connection):
    from src.core.execution_engine import ExecutionEngine
    from src.models import Order

    engine = ExecutionEngine(connection=mock_connection)

    order = Order(
        strategy_name="test_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="LIMIT",
        limit_price=150.50,
    )

    result = engine.submit(order)

    assert result.order_id == 100
    assert result.status == "submitted"


def test_cancel_order(mock_connection):
    from src.core.execution_engine import ExecutionEngine

    engine = ExecutionEngine(connection=mock_connection)

    result = engine.cancel(order_id=100)

    assert result is True


def test_cancel_order_not_connected():
    from src.core.execution_engine import ExecutionEngine
    from src.collectors.ibkr.connection import IBKRConnection

    conn = Mock(spec=IBKRConnection)
    conn.is_connected.return_value = False

    engine = ExecutionEngine(connection=conn)

    result = engine.cancel(order_id=100)

    assert result is False


def test_pending_orders_tracking(mock_connection):
    from src.core.execution_engine import ExecutionEngine
    from src.models import Order

    engine = ExecutionEngine(connection=mock_connection)

    order = Order(
        strategy_name="test_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MARKET",
    )

    result = engine.submit(order)

    assert result.order_id in engine.pending_orders
    assert engine.pending_orders[result.order_id] == order


def test_order_fill_callback(mock_connection):
    from src.core.execution_engine import ExecutionEngine
    from src.models import Order

    engine = ExecutionEngine(connection=mock_connection)
    fills = []

    engine.on_fill = lambda order_id, price, qty: fills.append((order_id, price, qty))

    order = Order(
        strategy_name="test_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MARKET",
    )

    result = engine.submit(order)

    # Simulate fill callback
    engine._on_order_filled(result.order_id, 150.25, 100)

    assert len(fills) == 1
    assert fills[0] == (100, 150.25, 100)
    assert result.order_id not in engine.pending_orders
