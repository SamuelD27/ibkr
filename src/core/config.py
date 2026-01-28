"""Configuration loading and validation."""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid."""

    pass


@dataclass
class IBKRConfig:
    """IBKR connection configuration."""

    host: str
    port: int
    client_id: int


@dataclass
class DataStoreConfig:
    """Data store configuration."""

    backend: str
    path: str


@dataclass
class CollectorConfig:
    """Collector configuration."""

    market_symbol: str = "SPY"
    scan_interval_hours: float = 24.0
    fundamental_refresh_hours: int = 24


@dataclass
class StrategyConfig:
    """Strategy configuration."""

    name: str
    class_path: str
    allocated_capital: float
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """Main configuration container."""

    ibkr: IBKRConfig
    data_store: DataStoreConfig
    collector: CollectorConfig
    strategies: list[StrategyConfig]

    def get_enabled_strategies(self) -> list[StrategyConfig]:
        """Get list of enabled strategies."""
        return [s for s in self.strategies if s.enabled]


def load_config(path: str) -> Config:
    """Load configuration from YAML file.

    Args:
        path: Path to YAML configuration file

    Returns:
        Config object with validated configuration

    Raises:
        ConfigError: If file not found, invalid YAML, or missing required fields
    """
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML: {e}") from e

    if raw is None:
        raise ConfigError("Configuration file is empty")

    # Validate required sections
    required_sections = ["ibkr", "data_store", "collector", "strategies"]
    for section in required_sections:
        if section not in raw:
            raise ConfigError(f"Missing required configuration section: {section}")

    # Parse IBKR config
    ibkr_raw = raw["ibkr"]
    ibkr = IBKRConfig(
        host=ibkr_raw.get("host", "127.0.0.1"),
        port=ibkr_raw.get("port", 7497),
        client_id=ibkr_raw.get("client_id", 0),
    )

    # Parse data store config
    ds_raw = raw["data_store"]
    data_store = DataStoreConfig(
        backend=ds_raw.get("backend", "file"),
        path=ds_raw.get("path", "./data"),
    )

    # Parse collector config
    coll_raw = raw["collector"]
    collector = CollectorConfig(
        market_symbol=coll_raw.get("market_symbol", "SPY"),
        scan_interval_hours=coll_raw.get("scan_interval_hours", 24.0),
        fundamental_refresh_hours=coll_raw.get("fundamental_refresh_hours", 24),
    )

    # Parse strategies
    strategies = []
    for strat_raw in raw.get("strategies", []):
        strategy = StrategyConfig(
            name=strat_raw["name"],
            class_path=strat_raw["class_path"],
            allocated_capital=strat_raw["allocated_capital"],
            enabled=strat_raw.get("enabled", True),
            params=strat_raw.get("params", {}),
        )
        strategies.append(strategy)

    config = Config(
        ibkr=ibkr,
        data_store=data_store,
        collector=collector,
        strategies=strategies,
    )

    logger.info(f"Loaded configuration from {path}")
    logger.debug(f"IBKR: {ibkr.host}:{ibkr.port}")
    logger.debug(f"Collector: market={collector.market_symbol}, scan_interval={collector.scan_interval_hours}h")
    logger.debug(f"Strategies: {[s.name for s in strategies]}")

    return config
