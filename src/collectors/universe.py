"""Universe providers for fetching stock constituents."""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol
import json

import aiohttp

logger = logging.getLogger(__name__)


class UniverseProvider(Protocol):
    """Protocol for universe data providers."""

    async def get_symbols(self) -> list[str]:
        """Get list of symbols in the universe."""
        ...


class SP500Provider:
    """Fetches S&P 500 constituents from Wikipedia.

    Caches the list locally to avoid repeated fetches.
    Falls back to a static list if fetch fails.
    """

    WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    CACHE_FILE = "data/universe/sp500.json"
    CACHE_TTL_HOURS = 24

    def __init__(self, cache_dir: str = "data/universe"):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "sp500.json"
        self._symbols: list[str] = []
        self._last_fetch: datetime | None = None

    async def get_symbols(self) -> list[str]:
        """Get S&P 500 symbols, using cache if fresh."""
        # Check cache first
        cached = self._load_cache()
        if cached:
            logger.info(f"Loaded {len(cached)} S&P 500 symbols from cache")
            self._symbols = cached
            return cached

        # Fetch from Wikipedia
        try:
            symbols = await self._fetch_from_wikipedia()
            if symbols:
                self._symbols = symbols
                self._save_cache(symbols)
                logger.info(f"Fetched {len(symbols)} S&P 500 symbols from Wikipedia")
                return symbols
        except Exception as e:
            logger.warning(f"Failed to fetch S&P 500 from Wikipedia: {e}")

        # Fall back to static list
        symbols = self._get_static_list()
        self._symbols = symbols
        logger.info(f"Using static S&P 500 list ({len(symbols)} symbols)")
        return symbols

    def _load_cache(self) -> list[str] | None:
        """Load symbols from cache if fresh."""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file) as f:
                data = json.load(f)

            # Check if cache is still fresh
            cached_at = datetime.fromisoformat(data["cached_at"])
            if datetime.now() - cached_at > timedelta(hours=self.CACHE_TTL_HOURS):
                logger.debug("Cache expired")
                return None

            return data["symbols"]
        except Exception as e:
            logger.debug(f"Error loading cache: {e}")
            return None

    def _save_cache(self, symbols: list[str]) -> None:
        """Save symbols to cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "cached_at": datetime.now().isoformat(),
            "count": len(symbols),
            "symbols": symbols,
        }

        with open(self.cache_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved {len(symbols)} symbols to cache")

    async def _fetch_from_wikipedia(self) -> list[str]:
        """Fetch S&P 500 symbols from Wikipedia."""
        logger.debug(
            "STEP: Fetching S&P 500 from Wikipedia",
            extra={
                "extra_data": {
                    "action": "fetch_sp500",
                    "source": "wikipedia",
                }
            },
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(self.WIKIPEDIA_URL, timeout=30) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                html = await response.text()

        # Parse the HTML table
        symbols = self._parse_wikipedia_html(html)

        logger.debug(
            "TRANSFORM: S&P 500 symbols parsed",
            extra={
                "extra_data": {
                    "action": "sp500_parsed",
                    "count": len(symbols),
                }
            },
        )

        return symbols

    def _parse_wikipedia_html(self, html: str) -> list[str]:
        """Parse S&P 500 table from Wikipedia HTML."""
        import re

        symbols = []

        # Find the first wikitable (constituents table)
        # Look for rows with stock symbols in the first column
        # Pattern matches: <td>SYMBOL</td> or <td><a...>SYMBOL</a></td>

        # First, find the constituents table
        table_match = re.search(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL)
        if not table_match:
            logger.warning("Could not find wikitable in Wikipedia HTML")
            return []

        table_html = table_match.group(1)

        # Extract symbols from first column of each row
        # Handles both plain text and linked symbols
        row_pattern = re.compile(r'<tr[^>]*>\s*<td[^>]*>(?:<a[^>]*>)?([A-Z]{1,5})(?:</a>)?</td>', re.MULTILINE)

        for match in row_pattern.finditer(table_html):
            symbol = match.group(1)
            if symbol and len(symbol) <= 5:  # Valid ticker symbols are 1-5 chars
                symbols.append(symbol)

        # Dedupe while preserving order
        seen = set()
        unique_symbols = []
        for s in symbols:
            if s not in seen:
                seen.add(s)
                unique_symbols.append(s)

        return unique_symbols

    def _get_static_list(self) -> list[str]:
        """Return a static S&P 500 list as fallback.

        This list is current as of January 2025.
        """
        return [
            "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "BRK.B", "UNH",
            "XOM", "LLY", "JPM", "JNJ", "V", "PG", "MA", "AVGO", "HD", "CVX",
            "MRK", "ABBV", "COST", "PEP", "ADBE", "KO", "WMT", "MCD", "CSCO", "CRM",
            "BAC", "PFE", "ACN", "TMO", "NFLX", "AMD", "LIN", "ABT", "DIS", "ORCL",
            "DHR", "CMCSA", "VZ", "INTC", "WFC", "PM", "TXN", "NKE", "COP", "NEE",
            "RTX", "UNP", "INTU", "HON", "IBM", "QCOM", "LOW", "SPGI", "CAT", "BA",
            "AMGN", "UPS", "GE", "DE", "ELV", "AMAT", "SBUX", "BMY", "NOW", "PLD",
            "MS", "GS", "BLK", "ISRG", "BKNG", "LMT", "AXP", "MDT", "GILD", "SYK",
            "MDLZ", "ADI", "TJX", "VRTX", "C", "ADP", "REGN", "LRCX", "CVS", "MMC",
            "TMUS", "SCHW", "CI", "ZTS", "ETN", "CB", "MO", "SO", "BDX", "PANW",
            "FI", "DUK", "BSX", "EOG", "CME", "SLB", "PGR", "AON", "NOC", "EQIX",
            "WM", "CL", "ITW", "MU", "CSX", "SNPS", "CDNS", "ICE", "SHW", "MCK",
            "ORLY", "HUM", "PNC", "APD", "FCX", "KLAC", "GD", "USB", "PYPL", "F",
            "EMR", "CMG", "MAR", "TGT", "MSI", "NSC", "EW", "ROP", "MCO", "CTAS",
            "FDX", "TT", "GM", "CARR", "AJG", "PH", "APH", "PSX", "HCA", "AZO",
            "TDG", "PSA", "SRE", "JCI", "ECL", "WELL", "PCAR", "AEP", "OXY", "AFL",
            "MET", "D", "CCI", "MCHP", "ADSK", "DXCM", "MNST", "KMB", "MSCI", "GWW",
            "KDP", "SPG", "HLT", "NEM", "FTNT", "O", "AIG", "ADM", "TRV", "MPC",
            "PAYX", "DHI", "TEL", "ALL", "CPRT", "VLO", "CNC", "BK", "ROST", "IDXX",
            "CHTR", "AMP", "KHC", "LHX", "DOW", "PRU", "DLR", "STZ", "YUM", "CTVA",
            "DD", "NXPI", "KMI", "PCG", "IQV", "COF", "OKE", "A", "EXC", "GIS",
            "ODFL", "FAST", "XEL", "PPG", "HSY", "CMI", "GEHC", "HAL", "WMB", "OTIS",
            "VRSK", "PEG", "CTSH", "HES", "DFS", "SYY", "BIIB", "ED", "EA", "BKR",
            "URI", "ROK", "VMC", "ACGL", "KEYS", "FANG", "NUE", "EIX", "MTD", "ANSS",
            "MLM", "ON", "IR", "AWK", "IT", "DVN", "WEC", "DAL", "RMD", "CBRE",
            "CAH", "GLW", "WST", "CDW", "WBD", "VICI", "ZBH", "EXR", "HPQ", "GPN",
            "XYL", "EBAY", "PWR", "APTV", "WTW", "GRMN", "TSCO", "LYB", "FTV", "DLTR",
            "TROW", "AVB", "SBAC", "EFX", "ES", "CHD", "RJF", "LEN", "ULTA", "IFF",
            "FSLR", "CSGP", "EQR", "DOV", "FITB", "WAB", "MPWR", "LUV", "HPE", "STT",
            "ETR", "MTB", "WY", "PPL", "BR", "BALL", "NTAP", "TDY", "DTE", "AEE",
            "FE", "HUBB", "STE", "K", "HOLX", "CBOE", "INVH", "COO", "CINF", "MOH",
            "VRSN", "TTWO", "TRGP", "MAA", "AXON", "RF", "WAT", "TYL", "CTRA", "IRM",
            "PTC", "ILMN", "CLX", "TSN", "HBAN", "ARE", "CNP", "DRI", "SWKS", "MKC",
            "AMCR", "LDOS", "CAG", "DGX", "EXPD", "ATO", "FDS", "CF", "ESS", "PKG",
            "SJM", "NTRS", "MRO", "BBY", "STLD", "J", "ZBRA", "NVR", "POOL", "TER",
            "IP", "KIM", "AKAM", "AVY", "BAX", "LKQ", "JBHT", "UAL", "EG", "BRO",
            "NDAQ", "LNT", "CFG", "L", "EXPE", "VTR", "OMC", "EVRG", "SNA", "CMS",
            "WRB", "TPR", "KEY", "VTRS", "HST", "RVTY", "JKHY", "GPC", "NI", "DPZ",
            "REG", "ALLE", "LH", "FFIV", "PFG", "BG", "TECH", "EMN", "BXP", "KMX",
            "WDC", "INCY", "TXT", "AES", "UDR", "AAL", "CPT", "CHRW", "CPB", "IEX",
            "PODD", "IPG", "NDSN", "ROL", "AOS", "HII", "RCL", "PAYC", "MGM", "CCL",
            "PEAK", "CTLT", "HRL", "AIZ", "PNR", "CE", "HAS", "GL", "EPAM", "BEN",
            "TAP", "JNPR", "WYNN", "HSIC", "FMC", "CRL", "SEE", "LW", "QRVO", "MOS",
            "BWA", "BBWI", "WHR", "ALB", "MTCH", "FRT", "PARA", "CZR", "GNRC", "IVZ",
            "MKTX", "RHI", "ETSY", "NWSA", "NWS", "RL", "ZION", "DVA", "BIO", "HWM",
            "FOXA", "FOX", "SEDG", "AAP", "CMA", "VFC", "XRAY", "NCLH", "MHK", "DXC",
        ]


class UniverseManager:
    """Manages multiple universe providers and combines them."""

    def __init__(self):
        self.providers: dict[str, UniverseProvider] = {}
        self._cache: dict[str, list[str]] = {}

    def register_provider(self, name: str, provider: UniverseProvider) -> None:
        """Register a universe provider."""
        self.providers[name] = provider
        logger.info(f"Registered universe provider: {name}")

    async def get_universe(self, name: str) -> list[str]:
        """Get symbols from a named universe."""
        if name not in self.providers:
            raise ValueError(f"Unknown universe: {name}")

        if name not in self._cache:
            self._cache[name] = await self.providers[name].get_symbols()

        return self._cache[name]

    async def refresh_universe(self, name: str) -> list[str]:
        """Force refresh a universe."""
        if name not in self.providers:
            raise ValueError(f"Unknown universe: {name}")

        self._cache[name] = await self.providers[name].get_symbols()
        return self._cache[name]
