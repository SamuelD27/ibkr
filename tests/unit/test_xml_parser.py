"""Tests for IBKR XML fundamental data parser."""
import pytest

SAMPLE_REPORT_SNAPSHOT = '''<?xml version="1.0" encoding="UTF-8"?>
<ReportSnapshot>
  <CoIDs>
    <CoID Type="CompanyName">Apple Inc</CoID>
    <CoID Type="CIKNo">0000320193</CoID>
  </CoIDs>
  <CoGeneralInfo>
    <Employees>166000</Employees>
    <SharesOut TotalFloat="14525947723.0">14776353000.0</SharesOut>
  </CoGeneralInfo>
</ReportSnapshot>
'''

SAMPLE_REPORT_SNAPSHOT_MINIMAL = '''<?xml version="1.0" encoding="UTF-8"?>
<ReportSnapshot>
  <CoIDs>
    <CoID Type="CompanyName">Test Corp</CoID>
  </CoIDs>
</ReportSnapshot>
'''

SAMPLE_REPORT_SNAPSHOT_WITH_INDUSTRY = '''<?xml version="1.0" encoding="UTF-8"?>
<ReportSnapshot>
  <CoIDs>
    <CoID Type="CompanyName">Microsoft Corporation</CoID>
    <CoID Type="CIKNo">0000789019</CoID>
  </CoIDs>
  <CoGeneralInfo>
    <Employees>221000</Employees>
    <SharesOut TotalFloat="7430000000.0">7433000000.0</SharesOut>
  </CoGeneralInfo>
  <TextInfo>
    <Text Type="Business Summary">Microsoft develops software products.</Text>
  </TextInfo>
  <peerInfo>
    <IndustryInfo>
      <Industry type="TRBC">Technology</Industry>
      <Industry type="TRBCCode">57</Industry>
    </IndustryInfo>
  </peerInfo>
</ReportSnapshot>
'''


def test_parse_report_snapshot():
    from src.collectors.ibkr.parsers import parse_report_snapshot

    result = parse_report_snapshot(SAMPLE_REPORT_SNAPSHOT, "AAPL")

    assert result.symbol == "AAPL"
    assert result.company_name == "Apple Inc"
    assert result.cik == "0000320193"
    assert result.employees == 166000
    assert result.shares_outstanding == 14776353000.0
    assert result.float_shares == 14525947723.0


def test_parse_report_snapshot_minimal():
    from src.collectors.ibkr.parsers import parse_report_snapshot

    result = parse_report_snapshot(SAMPLE_REPORT_SNAPSHOT_MINIMAL, "TEST")

    assert result.symbol == "TEST"
    assert result.company_name == "Test Corp"
    assert result.cik is None
    assert result.employees is None
    assert result.shares_outstanding is None
    assert result.float_shares is None


def test_parse_report_snapshot_stores_raw_xml():
    from src.collectors.ibkr.parsers import parse_report_snapshot

    result = parse_report_snapshot(SAMPLE_REPORT_SNAPSHOT, "AAPL")

    assert result.raw_xml == SAMPLE_REPORT_SNAPSHOT


def test_parse_report_snapshot_with_industry():
    from src.collectors.ibkr.parsers import parse_report_snapshot

    result = parse_report_snapshot(SAMPLE_REPORT_SNAPSHOT_WITH_INDUSTRY, "MSFT")

    assert result.symbol == "MSFT"
    assert result.company_name == "Microsoft Corporation"
    assert result.employees == 221000
    assert result.industry == "Technology"


def test_parse_report_snapshot_invalid_xml():
    from src.collectors.ibkr.parsers import parse_report_snapshot

    with pytest.raises(ValueError, match="Invalid XML"):
        parse_report_snapshot("not valid xml <>>", "TEST")


def test_parse_report_snapshot_empty_xml():
    from src.collectors.ibkr.parsers import parse_report_snapshot

    with pytest.raises(ValueError, match="Invalid XML"):
        parse_report_snapshot("", "TEST")
