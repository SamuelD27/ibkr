"""XML parsers for IBKR fundamental data."""
import xml.etree.ElementTree as ET
from datetime import datetime

from src.models import FundamentalData


def parse_report_snapshot(xml_string: str, symbol: str) -> FundamentalData:
    """Parse IBKR ReportSnapshot XML into FundamentalData.

    Args:
        xml_string: Raw XML string from IBKR fundamentalData callback
        symbol: Stock symbol this data belongs to

    Returns:
        FundamentalData object populated from the XML

    Raises:
        ValueError: If XML is invalid or cannot be parsed
    """
    if not xml_string or not xml_string.strip():
        raise ValueError("Invalid XML: empty string")

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}") from e

    # Parse company identifiers
    company_name = None
    cik = None
    for co_id in root.findall(".//CoID"):
        id_type = co_id.get("Type")
        if id_type == "CompanyName":
            company_name = co_id.text
        elif id_type == "CIKNo":
            cik = co_id.text

    # Parse general info
    employees = None
    shares_outstanding = None
    float_shares = None

    employees_elem = root.find(".//Employees")
    if employees_elem is not None and employees_elem.text:
        employees = int(employees_elem.text)

    shares_out_elem = root.find(".//SharesOut")
    if shares_out_elem is not None:
        if shares_out_elem.text:
            shares_outstanding = float(shares_out_elem.text)
        total_float = shares_out_elem.get("TotalFloat")
        if total_float:
            float_shares = float(total_float)

    # Parse industry info
    industry = None
    for industry_elem in root.findall(".//Industry"):
        if industry_elem.get("type") == "TRBC":
            industry = industry_elem.text
            break

    return FundamentalData(
        symbol=symbol,
        timestamp=datetime.now(),
        company_name=company_name,
        cik=cik,
        employees=employees,
        shares_outstanding=shares_outstanding,
        float_shares=float_shares,
        industry=industry,
        category=None,
        subcategory=None,
        raw_xml=xml_string,
    )
