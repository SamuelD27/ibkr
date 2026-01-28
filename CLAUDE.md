# IBKR Trading Bot Project

## Strategy Plugin Architecture (CRITICAL)

**DO NOT MODIFY CORE INFRASTRUCTURE** when adding new trading strategies. Strategies are **plugins** that integrate through well-defined interfaces.

### Protected Core Files (DO NOT MODIFY)

```
src/core/               # ALL files in core are protected
├── event_bus.py        # Pub/sub message system
├── data_store.py       # Persistence layer
├── execution_engine.py # Order execution
├── config.py           # Configuration loading
└── orchestrator.py     # Component lifecycle

src/models/             # ALL data models are protected
├── events.py
├── market_data.py
├── fundamental_data.py
├── orders.py
└── strategy.py

src/collectors/         # ALL collectors are protected
└── ibkr/
    ├── connection.py
    ├── collector.py
    └── parsers.py

src/strategies/base.py     # Strategy protocol (protected)
src/strategies/pipeline.py # Pipeline framework (protected)
```

### Adding New Strategies (Plugin Pattern)

New strategies MUST be added as self-contained directories under `src/strategies/`:

```
src/strategies/
├── base.py           # Protocol definition (READ ONLY)
├── pipeline.py       # Pipeline utilities (READ ONLY)
├── example_value/    # Example strategy (reference)
└── your_strategy/    # <-- ADD YOUR STRATEGY HERE
    ├── __init__.py
    ├── strategy.py   # Implements Strategy protocol
    └── layers/       # Custom layers for your strategy
        ├── __init__.py
        └── your_filters.py
```

### Strategy Integration Points

1. **Implement the protocol** from `src/strategies/base.py`
2. **Use the pipeline** from `src/strategies/pipeline.py`
3. **Subscribe to events** via `subscriptions` attribute
4. **Register in config** at `config/default.yaml`

### What You CAN Modify

- Create new directories under `src/strategies/`
- Add new strategy config entries in `config/default.yaml`
- Add new tests under `tests/`

### What You CANNOT Modify

- Any file in `src/core/`
- Any file in `src/models/`
- Any file in `src/collectors/`
- `src/strategies/base.py` or `src/strategies/pipeline.py`
- `src/__main__.py`

If you need new functionality in core, discuss with the user first.

---

## API Selection: Client Portal Web API

This project uses the **IBKR Client Portal Web API** (not the TWS API). The Web API provides:
- RESTful HTTP endpoints for all trading operations
- WebSocket streaming for real-time market data, orders, and P&L
- Browser-based authentication via the Client Portal Gateway
- JSON response format (no XML parsing needed)

---

## Knowledge Base References

### Documentation
- **`base_knowledge.md`** - Comprehensive Client Portal Web API guide with architecture, endpoints, and best practices
- **`clientportal.gw/doc/GettingStarted.md`** - Official gateway setup instructions
- **`clientportal.gw/doc/RealtimeSubscription.md`** - WebSocket streaming documentation

### Client Portal Gateway Location
```
clientportal.gw/
├── bin/               # Startup scripts (run.sh, run.bat)
├── build/lib/runtime/ # Java dependencies
├── dist/              # Gateway JAR file
├── doc/               # Documentation
└── root/              # Configuration files
    ├── conf.yaml      # Main configuration
    └── webapps/demo/  # Demo web interface
```

### Official API Documentation
- **Swagger/OpenAPI Spec:** https://gdcdyn.interactivebrokers.com/portal.proxy/v1/portal/swagger/swagger?format=yaml
- **API Guide with test pages:** https://interactivebrokers.github.io/cpwebapi
- **ReDoc viewer:** https://rebilly.github.io/ReDoc/?url=https://gdcdyn.interactivebrokers.com/portal.proxy/v1/portal/swagger/swagger?format=yaml

---

## Client Portal Gateway Setup

### Requirements
- Java 1.8 update 192+ or OpenJDK 11+

### Starting the Gateway
```bash
cd clientportal.gw
bin/run.sh root/conf.yaml
```

Gateway listens on **https://localhost:5000** by default (SSL mode).

### Authentication
1. Open browser to https://localhost:5000
2. Login with IBKR credentials
3. Gateway confirms "Client login succeeds"
4. Close browser - gateway maintains session

### Configuration (`root/conf.yaml`)
```yaml
ip2loc: "US"
proxyRemoteSsl: true
proxyRemoteHost: "https://api.ibkr.com"
listenPort: 5000
listenSsl: true
svcEnvironment: "v1"
sslCert: "vertx.jks"
sslPwd: "mywebapi"
authDelay: 3000
cors:
    origin.allowed: "*"
    allowCredentials: false
ips:
  allow:
    - 127.0.0.1
    - 192.*
```

---

## Interactive Brokers Web API Knowledge

### Architecture
- **REST API:** All endpoints at `https://localhost:5000/v1/api/...`
- **WebSocket:** Real-time streaming at `wss://localhost:5000/v1/api/ws`
- **Authentication:** Browser-based login, session maintained by gateway
- **Data Format:** JSON for all requests and responses

### Key REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/iserver/auth/status` | GET | Check authentication status |
| `/iserver/reauthenticate` | POST | Refresh session |
| `/iserver/secdef/search` | POST | Search for contracts |
| `/iserver/contract/{conid}/info` | GET | Get contract details |
| `/iserver/marketdata/snapshot` | GET | Get market data snapshot |
| `/iserver/marketdata/history` | GET | Get historical data |
| `/iserver/account/orders` | GET | Get live orders |
| `/iserver/account/order` | POST | Place order |
| `/iserver/account/order/{orderId}` | DELETE | Cancel order |
| `/portfolio/accounts` | GET | Get account list |
| `/portfolio/{accountId}/positions/0` | GET | Get positions |
| `/portfolio/{accountId}/summary` | GET | Account summary |

### WebSocket Streaming

Connect to `wss://localhost:5000/v1/api/ws` after authentication.

**Message Format:** `TOPIC+{ARGUMENTS}`
- `s` prefix = subscribe
- `u` prefix = unsubscribe

| Topic | Description | Example |
|-------|-------------|---------|
| `smd+conid` | Subscribe market data | `smd+265598+{"fields":["31","83"]}` |
| `umd+conid` | Unsubscribe market data | `umd+265598+{}` |
| `sor` | Subscribe live orders | `sor+{}` |
| `uor` | Unsubscribe orders | `uor+{}` |
| `spl` | Subscribe P&L | `spl+{}` |
| `upl` | Unsubscribe P&L | `upl+{}` |
| `ech+hb` | Heartbeat (send every 60s) | `ech+hb` |

**Unsolicited Messages (received automatically):**
- `system` - Connection status, heartbeats
- `sts` - Authentication status
- `ntf` - Notifications
- `blt` - Bulletins

### Market Data Fields (for WebSocket `smd`)

| Field | Description |
|-------|-------------|
| 31 | Last price |
| 83 | Change % |
| 84 | Bid price |
| 85 | Ask size |
| 86 | Ask price |
| 87 | Bid size |
| 88 | Volume |
| 7295 | Open price |
| 7296 | High price |
| 7297 | Low price |
| 7331 | Close price |

### Contract Lookup

```python
import requests

# Search for AAPL
response = requests.post(
    "https://localhost:5000/v1/api/iserver/secdef/search",
    json={"symbol": "AAPL"},
    verify=False  # Self-signed cert
)
contracts = response.json()
conid = contracts[0]["conid"]  # 265598 for AAPL
```

### Historical Data

```python
response = requests.get(
    "https://localhost:5000/v1/api/iserver/marketdata/history",
    params={
        "conid": 265598,
        "period": "1d",
        "bar": "1min",
    },
    verify=False
)
bars = response.json()["data"]
# Each bar: {"o": open, "h": high, "l": low, "c": close, "v": volume, "t": timestamp}
```

### Placing Orders

```python
response = requests.post(
    "https://localhost:5000/v1/api/iserver/account/order",
    json={
        "acctId": "DU1234567",
        "conid": 265598,
        "orderType": "LMT",
        "side": "BUY",
        "quantity": 100,
        "price": 150.00,
        "tif": "GTC"
    },
    verify=False
)
```

### Rate Limits
- No official rate limit documentation
- Recommend: ~10 requests/second for REST endpoints
- WebSocket: Real-time streaming, no pacing needed
- Historical data: Use reasonable intervals between requests

### Session Management
- Sessions expire after ~24 hours of inactivity
- Use `/iserver/auth/status` to check session validity
- Use `/iserver/reauthenticate` to refresh (may require re-login)
- Keep WebSocket heartbeat (`ech+hb`) every 60 seconds

### Common HTTP Status Codes
- 200: Success
- 401: Not authenticated (need to login via browser)
- 500: Server error (often means invalid parameters)

### Best Practices
- Always verify SSL certificates in production (use proper certs)
- Implement session monitoring with `/iserver/auth/status`
- Use WebSocket for real-time data instead of polling REST
- Cache contract info (conid) - it's permanent per instrument
- Handle order confirmations via `/iserver/reply/{replyId}`

---

## Data Response Formats

### Contract Search Response
```json
[{
  "conid": 265598,
  "companyHeader": "APPLE INC - NASDAQ",
  "companyName": "APPLE INC",
  "symbol": "AAPL",
  "description": "NASDAQ",
  "restricted": null,
  "fop": null,
  "opt": null,
  "war": null,
  "sections": [...]
}]
```

### Market Data Snapshot Response
```json
{
  "265598": {
    "31": "189.84",
    "83": "-0.42",
    "84": "189.83",
    "85": "100",
    "86": "189.85",
    "87": "200",
    "88": "52341234",
    "conid": 265598,
    "server_id": "q0"
  }
}
```

### Historical Data Response
```json
{
  "data": [
    {"t": 1704067200000, "o": 185.2, "h": 186.1, "l": 184.8, "c": 185.9, "v": 1234567},
    {"t": 1704153600000, "o": 186.0, "h": 187.2, "l": 185.5, "c": 186.8, "v": 2345678}
  ],
  "points": 2,
  "mktDataDelay": 0
}
```

### Order Status WebSocket Response
```json
{
  "topic": "sor",
  "args": [{
    "acct": "DU1234",
    "conid": 265598,
    "orderId": 922048212,
    "orderDesc": "Buy 100 Limit 372.00 GTC",
    "ticker": "AAPL",
    "secType": "STK",
    "remainingQuantity": 100.0,
    "filledQuantity": 0.0,
    "status": "Submitted",
    "orderType": "Limit",
    "side": "BUY",
    "price": 372
  }]
}
```

---

## Code Writing Guidelines

1. **Use the `requests` library** for REST API calls
2. **Use `websockets` library** for WebSocket streaming
3. **Always handle SSL** - gateway uses self-signed certs by default
4. **Check authentication** before making requests
5. **Implement heartbeat** for WebSocket connections (every 60s)
6. **Parse JSON responses** - no XML parsing needed with Web API
7. **Reference official Swagger spec** for complete endpoint documentation
