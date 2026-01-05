# Interactive Brokers TWS API: Complete Python Development Guide

The TWS API enables fully automated trading across all asset classes through a callback-based architecture. This guide covers everything needed to build production-ready trading bots, from connection handling to order management, using either the native `ibapi` library or the more developer-friendly `ib_async` wrapper. **Critical update:** The popular `ib_insync` library was archived in March 2024 and succeeded by `ib_async` under active maintenance.

---

## Core architecture: The EWrapper/EClient pattern

The TWS API uses a **request/response pattern** over TCP sockets with two fundamental classes working together. **EClient** handles all outgoing requests to TWS/IB Gateway—placing orders, requesting data, managing subscriptions. **EWrapper** processes all incoming responses through callback methods you override. This separation creates a clean but verbose architecture requiring careful message handling.

```python
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading

class TradingApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)  # Pass wrapper reference
        self.next_order_id = None
    
    def nextValidId(self, orderId: int):
        """Connection fully established when this fires"""
        self.next_order_id = orderId
        print(f"Connected - Next Order ID: {orderId}")
    
    def error(self, reqId, errorCode, errorString, advancedOrderReject=""):
        print(f"Error {errorCode}: {errorString}")

app = TradingApp()
app.connect("127.0.0.1", 7497, clientId=1)
threading.Thread(target=app.run, daemon=True).start()
```

The `run()` method blocks indefinitely processing the message queue, so it must execute in a separate thread. Python's implementation uses the standard `Queue` class rather than the EReaderSignal used in other languages. The EReader thread starts automatically upon connection.

### Connection configuration

| Application | Live Port | Paper Port | Best For |
|-------------|-----------|------------|----------|
| TWS | 7496 | 7497 | Development, visual confirmation |
| IB Gateway | 4001 | 4002 | Production, headless servers |

**IB Gateway** consumes approximately 40% less memory than TWS and provides better stability for 24/7 operation. Each connection requires a unique **clientId** (0-32 maximum), with clientId 0 acting as the "master client" receiving updates for all orders. The `nextValidId` callback signals that the connection handshake is complete—never send requests before receiving it.

### Thread-safe reconnection handling

Production systems require robust reconnection logic handling the inevitable disconnections:

```python
class RobustTradingApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self._connected = threading.Event()
        self._lock = threading.Lock()
    
    def connectionClosed(self):
        self._connected.clear()
        self._attempt_reconnect()
    
    def error(self, reqId, errorCode, errorString, advancedOrderReject=""):
        if errorCode == 1100:  # Connectivity lost
            self._attempt_reconnect()
        elif errorCode in [1101, 1102]:  # Connectivity restored
            self._resubscribe_market_data()
```

Error code **1100** indicates connectivity loss requiring reconnection and data resubscription. Codes **1101** (data lost) and **1102** (data maintained) signal restoration, with 1101 requiring you to resubmit all market data requests.

---

## Contract specifications across asset classes

Every API request requires a properly configured `Contract` object specifying the instrument. The **conId** (contract ID) provides the most precise identification—a permanent, unique integer that never changes.

### Stock contracts

```python
from ibapi.contract import Contract

# Recommended: SMART routing with primary exchange
contract = Contract()
contract.symbol = "AAPL"
contract.secType = "STK"
contract.exchange = "SMART"
contract.currency = "USD"
contract.primaryExchange = "NASDAQ"  # Prevents ambiguity

# Most precise: Using conId
contract = Contract()
contract.conId = 265598  # AAPL's permanent ID
contract.exchange = "SMART"
```

### Options and futures

```python
# Equity option
contract = Contract()
contract.symbol = "AAPL"
contract.secType = "OPT"
contract.exchange = "SMART"
contract.currency = "USD"
contract.lastTradeDateOrContractMonth = "20250321"
contract.strike = 180.0
contract.right = "C"  # Call
contract.multiplier = "100"

# E-mini S&P 500 future
contract = Contract()
contract.symbol = "ES"
contract.secType = "FUT"
contract.exchange = "CME"
contract.currency = "USD"
contract.lastTradeDateOrContractMonth = "202509"

# Forex pair
contract = Contract()
contract.symbol = "EUR"
contract.secType = "CASH"
contract.exchange = "IDEALPRO"
contract.currency = "USD"
```

The `reqContractDetails()` method validates contracts and returns complete specifications including trading hours, tick sizes, and valid exchanges. When multiple matches exist (common with options), use the returned conId for subsequent requests.

---

## Order management and execution

### Order types and construction

| Order Type | `orderType` Value | Key Fields |
|------------|-------------------|------------|
| Market | `"MKT"` | action, totalQuantity |
| Limit | `"LMT"` | lmtPrice |
| Stop | `"STP"` | auxPrice (trigger) |
| Stop-Limit | `"STP LMT"` | auxPrice, lmtPrice |
| Trailing Stop | `"TRAIL"` | auxPrice or trailingPercent |

```python
from ibapi.order import Order

order = Order()
order.action = "BUY"
order.orderType = "LMT"
order.totalQuantity = 100
order.lmtPrice = 150.00
order.tif = "GTC"  # Good-til-cancelled
```

### Bracket orders with take-profit and stop-loss

Bracket orders link three orders together: entry, take-profit, and stop-loss. The critical detail is setting `transmit = False` on all orders except the final child:

```python
def create_bracket_order(parent_id, action, qty, entry, tp_price, sl_price):
    parent = Order()
    parent.orderId = parent_id
    parent.action = action
    parent.orderType = "LMT"
    parent.totalQuantity = qty
    parent.lmtPrice = entry
    parent.transmit = False  # Hold until all orders ready
    
    take_profit = Order()
    take_profit.orderId = parent_id + 1
    take_profit.action = "SELL" if action == "BUY" else "BUY"
    take_profit.orderType = "LMT"
    take_profit.totalQuantity = qty
    take_profit.lmtPrice = tp_price
    take_profit.parentId = parent_id
    take_profit.transmit = False
    
    stop_loss = Order()
    stop_loss.orderId = parent_id + 2
    stop_loss.action = "SELL" if action == "BUY" else "BUY"
    stop_loss.orderType = "STP"
    stop_loss.auxPrice = sl_price
    stop_loss.totalQuantity = qty
    stop_loss.parentId = parent_id
    stop_loss.transmit = True  # Transmits entire bracket
    
    return [parent, take_profit, stop_loss]
```

### Order status flow

Orders progress through states: `ApiPending` → `PendingSubmit` → `PreSubmitted` → `Submitted` → `Filled`. The `orderStatus` callback delivers updates:

```python
def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, 
                permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
    print(f"Order {orderId}: {status}, Filled: {filled}/{filled + remaining}")
```

Modify orders by calling `placeOrder()` with the same orderId. Cancel with `cancelOrder(orderId)` or `reqGlobalCancel()` for all open orders.

---

## Real-time market data streaming

### Level 1 quotes with reqMktData

```python
# Streaming quotes with generic ticks for RTVolume and shortable status
self.reqMktData(1001, contract, "233,236", False, False, [])

# Callbacks receive price, size, and string data
def tickPrice(self, reqId, tickType, price, attrib):
    # tickType: 1=BID, 2=ASK, 4=LAST, 6=HIGH, 7=LOW
    pass

def tickSize(self, reqId, tickType, size):
    # tickType: 0=BID_SIZE, 3=ASK_SIZE, 5=LAST_SIZE, 8=VOLUME
    pass
```

**Important limitation:** Data arrives as aggregated snapshots approximately every 250ms, not true tick-by-tick. For actual tick data, use `reqTickByTickData()`, though subscriptions are limited to 5% of your market data lines.

### Market data subscription limits

Default allocation provides **100 concurrent streaming subscriptions**. The formula for your actual limit: `Max(100, Monthly Commissions ÷ 8, Equity × 100 ÷ $1,000,000)`. Quote Booster packs add 100 lines each ($30/month) up to 10 packs maximum.

---

## Historical data retrieval and pacing

### Request parameters

```python
self.reqHistoricalData(
    reqId=4001,
    contract=contract,
    endDateTime="",  # Empty = now
    durationStr="30 D",
    barSizeSetting="1 hour",
    whatToShow="TRADES",  # Also: MIDPOINT, BID, ASK, ADJUSTED_LAST
    useRTH=1,  # Regular trading hours only
    formatDate=1,
    keepUpToDate=False,
    chartOptions=[]
)
```

Valid bar sizes range from `"1 secs"` through `"1 month"`. Duration strings use format like `"30 D"`, `"4 W"`, `"6 M"`, or `"1 Y"` (maximum). Each request returns approximately **2000 bars maximum**.

### Avoiding pacing violations

Historical data requests face strict rate limits that cause the dreaded "pacing violation" error:

- No identical requests within **15 seconds**
- Maximum **6 requests** for same contract/exchange within **2 seconds**  
- Maximum **60 requests** per **10-minute** window
- **BID_ASK requests count as two** requests
- Maximum **50 simultaneous** open requests

```python
class HistoricalDataPacer:
    def __init__(self):
        self.request_times = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            # Clean requests older than 10 minutes
            self.request_times = [t for t in self.request_times if now - t < 600]
            
            # Enforce 60-per-10-minute limit
            if len(self.request_times) >= 55:
                sleep_time = 600 - (now - self.request_times[0])
                time.sleep(max(0, sleep_time) + 1)
            
            self.request_times.append(time.time())
```

---

## Account and position management

### Real-time account updates

```python
# Subscribe to account updates (updates every 3 minutes if changed)
self.reqAccountUpdates(subscribe=True, acctCode="U1234567")

def updateAccountValue(self, key, val, currency, accountName):
    # Key values: NetLiquidation, TotalCashValue, BuyingPower, 
    # UnrealizedPnL, InitMarginReq, MaintMarginReq, AvailableFunds
    pass

def updatePortfolio(self, contract, position, marketPrice, marketValue,
                    averageCost, unrealizedPNL, realizedPNL, accountName):
    pass
```

### Position tracking

```python
self.reqPositions()  # Request all positions across accounts

def position(self, account, contract, position, avgCost):
    print(f"{contract.symbol}: {position} shares @ ${avgCost:.2f}")

def positionEnd(self):
    print("Initial position snapshot complete")
```

### Real-time P&L streaming

```python
self.reqPnL(reqId=17001, account="U1234567", modelCode="")

def pnl(self, reqId, dailyPnL, unrealizedPnL, realizedPnL):
    # Updates approximately every second
    print(f"Daily: ${dailyPnL:.2f}, Unrealized: ${unrealizedPnL:.2f}")
```

---

## Python library choice: Native ibapi vs ib_async

### Critical update on ib_insync

The widely-used `ib_insync` library was **archived on March 14, 2024** following the passing of its creator Ewald de Wit. The community has forked and actively maintains it as **ib_async** under the ib-api-reloaded organization, with version 2.0.1 released in June 2025.

### Native ibapi (Official)

- **Installation:** Download from interactivebrokers.github.io (NOT available via pip)
- **Python requirement:** 3.11.0 minimum
- **Architecture:** Callback-based requiring explicit threading
- **Best for:** Institutional requirements, official support needs

### ib_async (Recommended for most use cases)

```bash
pip install ib_async
```

```python
from ib_async import IB, Stock, LimitOrder

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# Synchronous-style code (async handled internally)
contract = Stock('AAPL', 'SMART', 'USD')
bars = ib.reqHistoricalData(contract, endDateTime='', 
                            durationStr='30 D', barSizeSetting='1 day',
                            whatToShow='TRADES', useRTH=True)

order = LimitOrder('BUY', 100, 150.00)
trade = ib.placeOrder(contract, order)
ib.sleep(2)  # Process events while waiting

ib.disconnect()
```

**Key advantages:** Linear synchronous-style programming, excellent Jupyter support, built-in reconnection logic, cleaner API. Implements the IBKR binary protocol directly—does not require the ibapi package.

---

## Production deployment considerations

### IB Gateway for 24/7 operation

Use IB Gateway rather than TWS for production bots. Configure with **IBC (IB Controller)** for headless operation and automatic restarts. Key settings:

- Memory allocation: **4096 MB minimum**
- Enable "ActiveX and Socket Clients"
- Enable "Download open orders on connection"
- Restrict to localhost connections for security

### Error handling priorities

| Code | Meaning | Action Required |
|------|---------|-----------------|
| 1100 | Connectivity lost | Reconnect, resubscribe data |
| 1101 | Restored (data lost) | Resubmit all data requests |
| 100 | Rate limit exceeded | Implement pacing; 3 violations = disconnect |
| 200 | Contract not found | Check contract parameters |
| 201 | Order rejected | Review order parameters, permissions |
| 354 | No market data subscription | Subscribe or use delayed data |

### Rate limiting implementation

The API enforces **50 messages per second** maximum. Implement a pacer:

```python
from collections import deque
import time

class RequestPacer:
    def __init__(self, max_per_second=45):
        self.timestamps = deque()
        self.max_per_second = max_per_second
    
    def throttle(self):
        now = time.time()
        # Remove timestamps older than 1 second
        while self.timestamps and self.timestamps[0] < now - 1:
            self.timestamps.popleft()
        
        if len(self.timestamps) >= self.max_per_second:
            time.sleep(0.05)
        
        self.timestamps.append(time.time())
```

---

## Recent API changes (2024-2025)

**TWS API 10.33 (December 2024):**
- `EWrapper.error()` now includes `errorTime` parameter with epoch timestamp
- All "commissions" fields renamed to "commissionAndFees"
- `cancelOrder()` second argument changed from string to `OrderCancel` object

**TWS API 10.34.01 (February 2025):**
- New `EClient.reqCurrentTimeInMillis()` for millisecond-precision timestamps
- Added `Submitter` field in Order and Execution objects

**March 2025 requirement:** Minimum supported TWS/IB Gateway version is **10.30**. Older versions will be blocked from connecting.

**Deprecated and removed:** `EtradeOnly`, `firmQuoteOnly`, and `nbboPriceCap` order attributes were removed in TWS 983+.

---

## Conclusion

Building robust TWS API trading bots requires mastering the callback architecture, implementing proper pacing to avoid rate limits, and choosing the right Python library for your use case. **ib_async provides the smoothest development experience** for most scenarios, while the native ibapi offers official support for institutional requirements. 

Key success factors: always wait for `nextValidId` before sending requests, use conId for precise contract identification, implement reconnection logic with data resubscription, and respect the historical data pacing rules. Paper trading on port 7497 provides a safe environment for testing before deploying to production with IB Gateway.

---

