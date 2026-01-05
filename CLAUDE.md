# IBKR Trading Bot Project

## Knowledge Base References

### Documentation
- **`base_knowledge.md`** - Comprehensive TWS API guide with architecture explanations, code patterns, and best practices
- **`IBKR_api/IBJts/source/README.md`** - Official installation and setup instructions

### Source Code References (API v10.37.02)
When writing TWS API code, consult these files for accurate method signatures and parameters:

| File | Location | Use For |
|------|----------|---------|
| `client.py` | `IBKR_api/IBJts/source/pythonclient/ibapi/` | All EClient request methods (4,891 lines) |
| `wrapper.py` | `IBKR_api/IBJts/source/pythonclient/ibapi/` | EWrapper callback signatures (885 lines) |
| `contract.py` | `IBKR_api/IBJts/source/pythonclient/ibapi/` | Contract, ComboLeg, DeltaNeutralContract classes |
| `order.py` | `IBKR_api/IBJts/source/pythonclient/ibapi/` | Order class with 100+ fields |
| `order_condition.py` | `IBKR_api/IBJts/source/pythonclient/ibapi/` | PriceCondition, TimeCondition, etc. |
| `execution.py` | `IBKR_api/IBJts/source/pythonclient/ibapi/` | Execution class for trade fills |
| `ticktype.py` | `IBKR_api/IBJts/source/pythonclient/ibapi/` | Tick type constants (BID, ASK, LAST, etc.) |

### Sample Code References
**Location:** `IBKR_api/IBJts/samples/Python/Testbed/`

| File | Use For |
|------|---------|
| `Program.py` (97 KB) | Complete feature demonstrations - check here first |
| `OrderSamples.py` (55 KB) | 100+ order type examples (bracket, algo, conditional) |
| `ContractSamples.py` (20 KB) | All contract types (STK, OPT, FUT, CASH, CRYPTO) |
| `AvailableAlgoParams.py` (14 KB) | Algorithmic order parameters |

## Local API Installation

```bash
cd IBKR_api/IBJts/source/pythonclient
python setup.py bdist_wheel
pip install dist/ibapi-10.37.02-py3-none-any.whl
```

**Dependency:** `protobuf==5.29.3`

## Interactive Brokers TWS API Knowledge

**Architecture:**
- EWrapper receives callbacks, EClient sends requests
- Always wait for `nextValidId` callback before any requests
- Use `threading.Thread(target=app.run, daemon=True).start()` for message processing
- Ports: TWS 7496/7497 (live/paper), Gateway 4001/4002

**Libraries:**
- `ibapi` (local): Official API v10.37.02 - use for latest features
- `ib_async` (pip install): Recommended wrapper for simpler async-style code, Python 3.10+

**Contracts:**
- Always specify `primaryExchange` for SMART-routed stocks to avoid ambiguity
- Use `conId` for precise identification after initial lookup
- secTypes: STK, OPT, FUT, CASH (forex), CRYPTO

**Rate Limits:**
- 50 messages/second max to TWS
- Historical data: 60 requests/10 minutes, no identical requests within 15 seconds
- Market data: Limited by subscription lines (default 100)

**Critical Error Codes:**
- 1100: Connection lost (reconnect needed)
- 1101/1102: Connection restored (resubscribe data for 1101)
- 200: Contract not found
- 201: Order rejected
- 354: No market data subscription

**Order Patterns:**
- Get order ID from `nextValidId`, increment locally
- Bracket orders: Set `transmit=False` on all except last child
- Modify orders: Same orderId with `placeOrder()`
- OCA groups: Same `ocaGroup` string on related orders

**Best Practices:**
- Use IB Gateway (not TWS) for production
- Implement exponential backoff reconnection
- Cache historical data locally
- Paper trade first (port 7497/4002)

## IBKR Data Formats (Verified 2026-01-05)

### Contract Details
- **Format:** Python object (ContractDetails)
- **Access:** Dot notation
- **Key fields:** `.longName`, `.industry`, `.category`, `.subcategory`, `.contract.conId`

```python
details = ib.reqContractDetails(contract)
print(details[0].longName)  # "APPLE INC"
print(details[0].industry)  # "Technology"
```

### Historical Bars (OHLCV)
- **Format:** List of BarData objects
- **Access:** Dot notation
- **Key fields:** `.date`, `.open`, `.high`, `.low`, `.close`, `.volume`

```python
bars = ib.reqHistoricalData(contract, endDateTime='', durationStr='5 D', ...)
for bar in bars:
    print(f"{bar.date}: O={bar.open} H={bar.high} L={bar.low} C={bar.close}")
```

### Fundamental Data
- **Format:** Raw XML string (requires parsing)
- **Size:** ~10,000+ characters per report
- **Report types:** `ReportSnapshot`, `ReportsFinSummary`, `ReportsFinStatements`
- **Note:** Some reports require Reuters fundamental data subscription

**XML Structure (ReportSnapshot example):**
```xml
<ReportSnapshot>
  <CoIDs>
    <CoID Type="CompanyName">Apple Inc</CoID>
    <CoID Type="CIKNo">0000320193</CoID>
  </CoIDs>
  <CoGeneralInfo>
    <Employees>166000</Employees>
    <SharesOut TotalFloat="14525947723.0">14776353000.0</SharesOut>
  </CoGeneralInfo>
  <Ratios>...</Ratios>
</ReportSnapshot>
```

### Additional Error Codes (from testing)
- 430: Fundamental data not available (subscription required)
- 366: No historical data query found (timing/market hours)
- 10089: Market data requires API subscription (delayed available)

## Code Writing Guidelines

1. **Before writing any TWS API code**, check the corresponding source file in `IBKR_api/IBJts/source/pythonclient/ibapi/` for exact method signatures
2. **For order examples**, reference `OrderSamples.py` in the Testbed
3. **For contract definitions**, reference `ContractSamples.py` in the Testbed
4. **For complete feature usage**, reference `Program.py` in the Testbed
5. **For fundamental data**, parse XML using ElementTree and convert to structured dataclasses
