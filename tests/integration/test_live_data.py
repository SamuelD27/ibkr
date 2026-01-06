"""Integration tests for live market data collection."""
import pytest
from ib_async import IB, Stock, Contract

from src.collectors.ibkr.parsers import parse_report_snapshot


pytestmark = pytest.mark.asyncio


async def test_request_contract_details(ib_connection):
    """Test requesting contract details for AAPL."""
    contract = Stock("AAPL", "SMART", "USD")

    details = await ib_connection.reqContractDetailsAsync(contract)

    assert len(details) > 0
    detail = details[0]
    assert detail.contract.symbol == "AAPL"
    assert detail.longName is not None
    assert "APPLE" in detail.longName.upper()


async def test_request_historical_bars(ib_connection):
    """Test requesting historical price bars."""
    contract = Stock("AAPL", "SMART", "USD")

    bars = await ib_connection.reqHistoricalDataAsync(
        contract,
        endDateTime="",
        durationStr="5 D",
        barSizeSetting="1 day",
        whatToShow="TRADES",
        useRTH=True,
    )

    assert len(bars) > 0
    bar = bars[0]
    assert bar.open > 0
    assert bar.high >= bar.low
    assert bar.close > 0
    assert bar.volume >= 0


async def test_request_multiple_contracts(ib_connection):
    """Test requesting details for multiple symbols."""
    symbols = ["AAPL", "MSFT", "GOOGL"]
    contracts = [Stock(s, "SMART", "USD") for s in symbols]

    for contract in contracts:
        details = await ib_connection.reqContractDetailsAsync(contract)
        assert len(details) > 0
        assert details[0].contract.symbol == contract.symbol


async def test_contract_has_industry_info(ib_connection):
    """Test that contract details include industry information."""
    contract = Stock("AAPL", "SMART", "USD")

    details = await ib_connection.reqContractDetailsAsync(contract)

    detail = details[0]
    # Industry info may or may not be populated depending on subscription
    # Just verify the fields exist
    assert hasattr(detail, "industry")
    assert hasattr(detail, "category")


async def test_historical_bars_have_correct_structure(ib_connection):
    """Test that historical bars match expected structure."""
    contract = Stock("MSFT", "SMART", "USD")

    bars = await ib_connection.reqHistoricalDataAsync(
        contract,
        endDateTime="",
        durationStr="1 D",
        barSizeSetting="1 hour",
        whatToShow="TRADES",
        useRTH=True,
    )

    assert len(bars) > 0

    for bar in bars:
        # Verify OHLCV structure
        assert hasattr(bar, "date")
        assert hasattr(bar, "open")
        assert hasattr(bar, "high")
        assert hasattr(bar, "low")
        assert hasattr(bar, "close")
        assert hasattr(bar, "volume")

        # Price sanity checks
        assert bar.high >= bar.low
        assert bar.high >= bar.open
        assert bar.high >= bar.close
        assert bar.low <= bar.open
        assert bar.low <= bar.close


async def test_request_fundamental_data(ib_connection):
    """Test requesting fundamental data (ReportSnapshot).

    Note: This may fail with error 430 if no fundamental data subscription.
    """
    contract = Stock("AAPL", "SMART", "USD")

    # First qualify the contract to get conId
    await ib_connection.qualifyContractsAsync(contract)

    try:
        xml_data = await ib_connection.reqFundamentalDataAsync(
            contract, "ReportSnapshot"
        )

        if xml_data:
            assert "<ReportSnapshot>" in xml_data or len(xml_data) > 100
    except Exception as e:
        # Error 430 means no subscription - that's acceptable
        if "430" in str(e) or "fundamental" in str(e).lower():
            pytest.skip("Fundamental data subscription not available")
        raise


async def test_parse_live_fundamental_data(ib_connection):
    """Test parsing actual fundamental data from IBKR."""
    contract = Stock("AAPL", "SMART", "USD")
    await ib_connection.qualifyContractsAsync(contract)

    try:
        xml_data = await ib_connection.reqFundamentalDataAsync(
            contract, "ReportSnapshot"
        )

        if not xml_data:
            pytest.skip("No fundamental data returned")

        # Parse with our parser
        result = parse_report_snapshot(xml_data, "AAPL")

        assert result.symbol == "AAPL"
        # Verify we extracted something meaningful
        assert result.raw_xml == xml_data

    except Exception as e:
        if "430" in str(e) or "fundamental" in str(e).lower():
            pytest.skip("Fundamental data subscription not available")
        raise
