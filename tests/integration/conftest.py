"""Fixtures for integration tests."""
import asyncio
import pytest
import pytest_asyncio
from ib_async import IB


def is_tws_available(host: str = "127.0.0.1", port: int = 7497) -> bool:
    """Check if TWS/Gateway is available for connection."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# Skip all tests in this module if TWS not available
pytestmark = pytest.mark.skipif(
    not is_tws_available(),
    reason="TWS/Gateway not available on port 7497"
)


@pytest_asyncio.fixture
async def ib_connection():
    """Provide a connected IB instance for tests."""
    ib = IB()
    await ib.connectAsync("127.0.0.1", 7497, clientId=99)
    yield ib
    if ib.isConnected():
        ib.disconnect()


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
