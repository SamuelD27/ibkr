"""Integration tests for IBKR connection."""
import pytest
from ib_async import IB


pytestmark = pytest.mark.asyncio


async def test_connect_to_tws():
    """Test establishing connection to TWS."""
    ib = IB()

    await ib.connectAsync("127.0.0.1", 7497, clientId=100)

    assert ib.isConnected()

    ib.disconnect()


async def test_disconnect_cleanly():
    """Test clean disconnection from TWS."""
    ib = IB()
    await ib.connectAsync("127.0.0.1", 7497, clientId=101)

    assert ib.isConnected()

    ib.disconnect()

    assert not ib.isConnected()


async def test_connection_provides_valid_order_id(ib_connection):
    """Test that connection provides valid order ID."""
    # ib_async automatically receives nextValidId on connect
    # We can access it via the client
    next_id = ib_connection.client.getReqId()

    assert next_id is not None
    assert next_id > 0


async def test_reconnect_after_disconnect():
    """Test reconnecting after clean disconnect."""
    ib = IB()

    # First connection
    await ib.connectAsync("127.0.0.1", 7497, clientId=102)
    assert ib.isConnected()

    # Disconnect
    ib.disconnect()
    assert not ib.isConnected()

    # Reconnect
    await ib.connectAsync("127.0.0.1", 7497, clientId=102)
    assert ib.isConnected()

    # Cleanup
    ib.disconnect()


async def test_multiple_clients_connect(ib_connection):
    """Test that multiple client IDs can connect simultaneously."""
    # ib_connection uses clientId=99
    assert ib_connection.isConnected()

    # Connect second client
    ib2 = IB()
    await ib2.connectAsync("127.0.0.1", 7497, clientId=103)

    assert ib2.isConnected()
    assert ib_connection.isConnected()

    ib2.disconnect()
