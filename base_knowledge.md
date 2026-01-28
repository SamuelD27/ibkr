# Interactive Brokers Client Portal Web API: Complete Python Development Guide

The Client Portal Web API enables fully automated trading across all asset classes through a RESTful HTTP interface with WebSocket streaming. This guide covers everything needed to build production-ready trading bots using the Web API gateway.

---

## Core Architecture: Gateway + REST + WebSocket

The Web API uses a **local gateway** that authenticates with IBKR and provides both REST endpoints and WebSocket streaming. Unlike the TWS API's callback-based architecture, the Web API uses standard HTTP request/response patterns and WebSocket pub/sub.

```
┌─────────────────┐     HTTPS/WSS      ┌──────────────────┐     HTTPS     ┌────────────────┐
│  Your Python    │ ←────────────────→ │  Client Portal   │ ←───────────→ │  IBKR Servers  │
│  Application    │   localhost:5000   │  Gateway (Java)  │  api.ibkr.com │                │
└─────────────────┘                    └──────────────────┘               └────────────────┘
```

### Key Components

1. **Client Portal Gateway** - Java application running locally, handles authentication
2. **REST API** - Standard HTTP endpoints for requests/orders/account data
3. **WebSocket API** - Real-time streaming for market data, orders, P&L

### Basic Connection Flow

```python
import requests
import ssl

# Disable SSL warnings for self-signed cert (dev only)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://localhost:5000/v1/api"

def check_auth():
    """Check if gateway session is authenticated."""
    response = requests.get(
        f"{BASE_URL}/iserver/auth/status",
        verify=False
    )
    data = response.json()
    return data.get("authenticated", False)

# Authentication requires browser login to https://localhost:5000
# After login, the gateway maintains the session
```

---

## Gateway Setup and Configuration

### Starting the Gateway

```bash
cd clientportal.gw
bin/run.sh root/conf.yaml
```

Output when ready: `Server listening on port 5000`

### Configuration Options (`root/conf.yaml`)

```yaml
# Network settings
listenPort: 5000          # Gateway port
listenSsl: true           # Use HTTPS (recommended)
sslCert: "vertx.jks"      # SSL certificate
sslPwd: "mywebapi"        # Certificate password

# IBKR connection
proxyRemoteHost: "https://api.ibkr.com"
proxyRemoteSsl: true

# CORS (for web frontends)
cors:
    origin.allowed: "*"
    allowCredentials: false

# IP whitelist
ips:
  allow:
    - 127.0.0.1
    - 192.*
  deny:
    - 212.90.324.10
```

### Authentication Process

1. Start gateway: `bin/run.sh root/conf.yaml`
2. Open browser: `https://localhost:5000`
3. Login with IBKR credentials
4. Wait for "Client login succeeds" message
5. Close browser - gateway maintains session

**Session Duration:** ~24 hours of inactivity before expiration

---

## Contract Identification

Every instrument has a unique **conId** (contract ID) that's permanent and never changes. Always resolve symbols to conIds before trading.

### Symbol Search

```python
def search_contract(symbol: str) -> list[dict]:
    """Search for contracts by symbol."""
    response = requests.post(
        f"{BASE_URL}/iserver/secdef/search",
        json={"symbol": symbol},
        verify=False
    )
    return response.json()

# Example: AAPL
contracts = search_contract("AAPL")
# Returns: [{"conid": 265598, "companyName": "APPLE INC", ...}]
```

### Contract Types

| Type | Description | Example |
|------|-------------|---------|
| STK | Stock | AAPL, MSFT |
| OPT | Option | AAPL calls/puts |
| FUT | Future | ES, NQ |
| CASH | Forex | EUR.USD |
| CRYPTO | Cryptocurrency | BTC |

### Get Contract Details

```python
def get_contract_info(conid: int) -> dict:
    """Get detailed contract information."""
    response = requests.get(
        f"{BASE_URL}/iserver/contract/{conid}/info",
        verify=False
    )
    return response.json()
```

---

## Market Data

### REST Snapshots

```python
def get_market_snapshot(conids: list[int], fields: list[str] = None) -> dict:
    """Get market data snapshot for multiple contracts."""
    params = {"conids": ",".join(str(c) for c in conids)}
    if fields:
        params["fields"] = ",".join(fields)

    response = requests.get(
        f"{BASE_URL}/iserver/marketdata/snapshot",
        params=params,
        verify=False
    )
    return response.json()

# Common fields
# 31: Last price, 83: Change %, 84: Bid, 86: Ask, 88: Volume
snapshot = get_market_snapshot([265598], ["31", "84", "86", "88"])
```

### Historical Data

```python
def get_historical_data(
    conid: int,
    period: str = "1d",
    bar: str = "1min",
    outside_rth: bool = False
) -> dict:
    """Get historical price bars.

    Args:
        conid: Contract ID
        period: Duration (1d, 1w, 1m, 3m, 6m, 1y, 2y, 3y, 5y)
        bar: Bar size (1min, 2min, 5min, 15min, 30min, 1h, 2h, 4h, 1d, 1w, 1m)
        outside_rth: Include outside regular trading hours
    """
    response = requests.get(
        f"{BASE_URL}/iserver/marketdata/history",
        params={
            "conid": conid,
            "period": period,
            "bar": bar,
            "outsideRth": str(outside_rth).lower()
        },
        verify=False
    )
    return response.json()

# Example
bars = get_historical_data(265598, period="5d", bar="1h")
for bar in bars.get("data", []):
    print(f"Time: {bar['t']}, O: {bar['o']}, H: {bar['h']}, L: {bar['l']}, C: {bar['c']}, V: {bar['v']}")
```

### WebSocket Streaming

For real-time data, use WebSocket instead of polling REST endpoints.

```python
import asyncio
import websockets
import json

async def stream_market_data(conids: list[int], fields: list[str]):
    """Stream real-time market data via WebSocket."""
    uri = "wss://localhost:5000/v1/api/ws"

    async with websockets.connect(uri, ssl=ssl.SSLContext()) as ws:
        # Subscribe to market data for each contract
        for conid in conids:
            message = f'smd+{conid}+{json.dumps({"fields": fields})}'
            await ws.send(message)

        # Start heartbeat task
        async def heartbeat():
            while True:
                await asyncio.sleep(55)
                await ws.send("ech+hb")

        heartbeat_task = asyncio.create_task(heartbeat())

        try:
            async for message in ws:
                data = json.loads(message)
                print(f"Received: {data}")
        finally:
            heartbeat_task.cancel()

# Subscribe to AAPL (265598) with last price and volume
# asyncio.run(stream_market_data([265598], ["31", "88"]))
```

### Market Data Fields Reference

| Field | Description |
|-------|-------------|
| 31 | Last price |
| 83 | Change % |
| 84 | Bid price |
| 85 | Ask size |
| 86 | Ask price |
| 87 | Bid size |
| 88 | Volume |
| 7295 | Open |
| 7296 | High |
| 7297 | Low |
| 7331 | Prior close |

---

## Order Management

### Account Selection

```python
def get_accounts() -> list[dict]:
    """Get list of accounts."""
    response = requests.get(
        f"{BASE_URL}/portfolio/accounts",
        verify=False
    )
    return response.json()

accounts = get_accounts()
account_id = accounts[0]["accountId"]  # e.g., "DU1234567"
```

### Placing Orders

```python
def place_order(
    account_id: str,
    conid: int,
    side: str,
    quantity: int,
    order_type: str = "MKT",
    price: float = None,
    tif: str = "DAY"
) -> dict:
    """Place an order.

    Args:
        account_id: IBKR account ID
        conid: Contract ID
        side: "BUY" or "SELL"
        quantity: Number of shares/contracts
        order_type: "MKT", "LMT", "STP", "STP_LIMIT"
        price: Limit price (required for LMT orders)
        tif: Time in force ("DAY", "GTC", "IOC", "OPG")
    """
    order = {
        "acctId": account_id,
        "conid": conid,
        "side": side,
        "quantity": quantity,
        "orderType": order_type,
        "tif": tif
    }

    if price and order_type in ["LMT", "STP_LIMIT"]:
        order["price"] = price

    response = requests.post(
        f"{BASE_URL}/iserver/account/orders",
        json={"orders": [order]},
        verify=False
    )
    return response.json()
```

### Order Confirmation Flow

Orders may require confirmation. Handle the reply flow:

```python
def confirm_order(reply_id: str, confirmed: bool = True) -> dict:
    """Confirm or reject an order that requires confirmation."""
    response = requests.post(
        f"{BASE_URL}/iserver/reply/{reply_id}",
        json={"confirmed": confirmed},
        verify=False
    )
    return response.json()

# Example order flow
result = place_order("DU1234567", 265598, "BUY", 100, "LMT", 150.00)

# Check if confirmation needed
if result.get("id"):
    # Order placed successfully
    order_id = result["id"]
elif result.get("replyId"):
    # Confirmation required
    confirm_result = confirm_order(result["replyId"])
```

### Get Orders

```python
def get_live_orders() -> dict:
    """Get all live orders."""
    response = requests.get(
        f"{BASE_URL}/iserver/account/orders",
        verify=False
    )
    return response.json()

def get_order_status(order_id: str) -> dict:
    """Get status of a specific order."""
    response = requests.get(
        f"{BASE_URL}/iserver/account/order/status/{order_id}",
        verify=False
    )
    return response.json()
```

### Cancel Orders

```python
def cancel_order(account_id: str, order_id: str) -> dict:
    """Cancel an order."""
    response = requests.delete(
        f"{BASE_URL}/iserver/account/{account_id}/order/{order_id}",
        verify=False
    )
    return response.json()
```

### Modify Orders

```python
def modify_order(
    account_id: str,
    order_id: str,
    conid: int,
    quantity: int,
    price: float
) -> dict:
    """Modify an existing order."""
    response = requests.post(
        f"{BASE_URL}/iserver/account/{account_id}/order/{order_id}",
        json={
            "conid": conid,
            "quantity": quantity,
            "price": price
        },
        verify=False
    )
    return response.json()
```

### Order Types

| Order Type | `orderType` Value | Required Fields |
|------------|-------------------|-----------------|
| Market | `"MKT"` | side, quantity |
| Limit | `"LMT"` | side, quantity, price |
| Stop | `"STP"` | side, quantity, auxPrice |
| Stop-Limit | `"STP_LIMIT"` | side, quantity, price, auxPrice |

---

## Account and Portfolio

### Account Summary

```python
def get_account_summary(account_id: str) -> dict:
    """Get account summary with balances."""
    response = requests.get(
        f"{BASE_URL}/portfolio/{account_id}/summary",
        verify=False
    )
    return response.json()
```

### Positions

```python
def get_positions(account_id: str) -> list[dict]:
    """Get all positions for an account."""
    response = requests.get(
        f"{BASE_URL}/portfolio/{account_id}/positions/0",
        verify=False
    )
    return response.json()
```

### P&L Streaming (WebSocket)

```python
async def stream_pnl():
    """Stream real-time P&L updates."""
    uri = "wss://localhost:5000/v1/api/ws"

    async with websockets.connect(uri, ssl=ssl.SSLContext()) as ws:
        await ws.send("spl+{}")  # Subscribe to P&L

        async for message in ws:
            data = json.loads(message)
            if data.get("topic") == "spl":
                pnl = data.get("args", {})
                print(f"Daily P&L: {pnl.get('dpl')}, Unrealized: {pnl.get('upl')}")
```

---

## WebSocket Topics Reference

### Solicited (Request/Subscribe)

| Topic | Format | Description |
|-------|--------|-------------|
| `smd` | `smd+{conid}+{"fields":[...]}` | Subscribe market data |
| `umd` | `umd+{conid}+{}` | Unsubscribe market data |
| `sor` | `sor+{}` | Subscribe live orders |
| `uor` | `uor+{}` | Unsubscribe orders |
| `spl` | `spl+{}` | Subscribe P&L |
| `upl` | `upl+{}` | Unsubscribe P&L |
| `ech` | `ech+hb` | Heartbeat (send every 60s) |

### Unsolicited (Received)

| Topic | Description |
|-------|-------------|
| `system` | Connection status, periodic heartbeat |
| `sts` | Authentication status |
| `ntf` | Notifications (trading info) |
| `blt` | Bulletins (urgent messages) |

---

## Session Management

### Check Authentication

```python
def check_auth_status() -> dict:
    """Check current authentication status."""
    response = requests.get(
        f"{BASE_URL}/iserver/auth/status",
        verify=False
    )
    return response.json()
    # Returns: {"authenticated": true, "competing": false, ...}
```

### Keep Session Alive

```python
def tickle() -> dict:
    """Keep session alive / refresh authentication."""
    response = requests.post(
        f"{BASE_URL}/tickle",
        verify=False
    )
    return response.json()
```

### Reauthenticate

```python
def reauthenticate() -> dict:
    """Attempt to reauthenticate session."""
    response = requests.post(
        f"{BASE_URL}/iserver/reauthenticate",
        verify=False
    )
    return response.json()
    # May require browser re-login if session expired
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad request | Check parameters |
| 401 | Not authenticated | Login via browser |
| 500 | Server error | Check request format |

### Common Issues

1. **"Not authenticated"** - Session expired, need browser login
2. **SSL Certificate errors** - Use `verify=False` for dev or add gateway cert
3. **Empty response** - Market may be closed or contract invalid
4. **Order rejected** - Check account permissions, buying power

---

## Production Deployment

### Security Recommendations

1. **Use proper SSL certificates** in production (not self-signed)
2. **Restrict gateway IP whitelist** to only your application servers
3. **Implement session monitoring** with `/iserver/auth/status`
4. **Use environment variables** for configuration, not hardcoded values

### High Availability

```python
class WebAPIClient:
    """Production-ready Web API client with session management."""

    def __init__(self, base_url: str = "https://localhost:5000/v1/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = False  # Configure properly in production

    def ensure_authenticated(self) -> bool:
        """Check and attempt to restore authentication."""
        status = self.check_auth()
        if status.get("authenticated"):
            return True

        # Try tickle to refresh
        self.session.post(f"{self.base_url}/tickle")

        # Recheck
        status = self.check_auth()
        if status.get("authenticated"):
            return True

        # Session truly expired - need manual re-login
        raise RuntimeError("Session expired - browser login required")

    def check_auth(self) -> dict:
        return self.session.get(f"{self.base_url}/iserver/auth/status").json()
```

### Monitoring

- Check `/iserver/auth/status` every 5-10 minutes
- Monitor WebSocket connection with heartbeats
- Log all order submissions and confirmations
- Alert on authentication failures

---

## Comparison: Web API vs TWS API

| Feature | Web API | TWS API |
|---------|---------|---------|
| Protocol | REST + WebSocket | TCP Socket |
| Authentication | Browser login | TWS/Gateway GUI |
| Data Format | JSON | Binary/Callback |
| Libraries | requests, websockets | ibapi, ib_async |
| Setup | Java gateway | TWS or IB Gateway |
| Complexity | Lower | Higher |
| Rate Limits | Less documented | Well documented |
| Historical Data | Simpler | More options |

**When to use Web API:**
- Simpler integration requirements
- JSON/REST experience
- Web-based applications
- Lower latency requirements

**When to use TWS API:**
- Complex order types
- High-frequency needs
- Full API feature access
- Established codebase

---

## Quick Reference

### Essential Endpoints

```
GET  /iserver/auth/status          - Check authentication
POST /iserver/secdef/search        - Search contracts
GET  /iserver/marketdata/snapshot  - Market data snapshot
GET  /iserver/marketdata/history   - Historical data
POST /iserver/account/orders       - Place orders
GET  /iserver/account/orders       - Get live orders
DELETE /iserver/account/{acct}/order/{id} - Cancel order
GET  /portfolio/accounts           - List accounts
GET  /portfolio/{acct}/positions/0 - Get positions
POST /tickle                       - Keep session alive
```

### WebSocket Quick Start

```python
# Connect: wss://localhost:5000/v1/api/ws
# Subscribe to AAPL market data:
ws.send('smd+265598+{"fields":["31","84","86","88"]}')
# Subscribe to orders:
ws.send('sor+{}')
# Heartbeat every 60s:
ws.send('ech+hb')
```
