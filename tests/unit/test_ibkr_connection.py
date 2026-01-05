"""Tests for IBKR Connection Manager."""
from unittest.mock import Mock, patch, MagicMock
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


def test_connection_default_values():
    from src.collectors.ibkr.connection import IBKRConnection

    conn = IBKRConnection()

    assert conn.host == "127.0.0.1"
    assert conn.port == 7497
    assert conn.client_id == 0


def test_next_order_id_not_available_before_connect():
    from src.collectors.ibkr.connection import IBKRConnection

    conn = IBKRConnection()

    with pytest.raises(RuntimeError, match="not connected"):
        _ = conn.next_order_id


def test_connection_callbacks_registered():
    """Test that connection has callback mechanism for nextValidId."""
    from src.collectors.ibkr.connection import IBKRConnection

    conn = IBKRConnection()

    # Simulate receiving nextValidId callback
    conn._on_next_valid_id(500)

    assert conn._next_order_id == 500


def test_connection_status_tracking():
    from src.collectors.ibkr.connection import IBKRConnection

    conn = IBKRConnection()

    assert not conn.is_connected()

    conn._set_connected(True)
    assert conn.is_connected()

    conn._set_connected(False)
    assert not conn.is_connected()


def test_error_callback():
    from src.collectors.ibkr.connection import IBKRConnection

    conn = IBKRConnection()
    errors = []

    conn.on_error = lambda code, msg: errors.append((code, msg))

    conn._on_error(200, "Contract not found")

    assert len(errors) == 1
    assert errors[0] == (200, "Contract not found")
