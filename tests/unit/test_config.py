"""Tests for configuration loading."""
import pytest
import tempfile
from pathlib import Path


SAMPLE_CONFIG = """
ibkr:
  host: "127.0.0.1"
  port: 7497
  client_id: 1

data_store:
  backend: "file"
  path: "./data"

collector:
  watchlist:
    - "AAPL"
    - "MSFT"
  fundamental_refresh_hours: 24

strategies:
  - name: "example_value"
    class_path: "src.strategies.example_value.ExampleValueStrategy"
    allocated_capital: 10000
    enabled: true
    params:
      min_market_cap: 1000000000
"""

MINIMAL_CONFIG = """
ibkr:
  host: "127.0.0.1"
  port: 7497
  client_id: 1

data_store:
  backend: "file"
  path: "./data"

collector:
  watchlist: []

strategies: []
"""


def test_load_config_from_file():
    from src.core.config import load_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()

        config = load_config(f.name)

    assert config.ibkr.host == "127.0.0.1"
    assert config.ibkr.port == 7497
    assert config.ibkr.client_id == 1


def test_config_data_store():
    from src.core.config import load_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()

        config = load_config(f.name)

    assert config.data_store.backend == "file"
    assert config.data_store.path == "./data"


def test_config_collector():
    from src.core.config import load_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()

        config = load_config(f.name)

    assert config.collector.watchlist == ["AAPL", "MSFT"]
    assert config.collector.fundamental_refresh_hours == 24


def test_config_strategies():
    from src.core.config import load_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()

        config = load_config(f.name)

    assert len(config.strategies) == 1
    strategy = config.strategies[0]
    assert strategy.name == "example_value"
    assert strategy.class_path == "src.strategies.example_value.ExampleValueStrategy"
    assert strategy.allocated_capital == 10000
    assert strategy.enabled is True
    assert strategy.params["min_market_cap"] == 1000000000


def test_config_missing_file():
    from src.core.config import load_config, ConfigError

    with pytest.raises(ConfigError, match="not found"):
        load_config("/nonexistent/config.yaml")


def test_config_invalid_yaml():
    from src.core.config import load_config, ConfigError

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content: [")
        f.flush()

        with pytest.raises(ConfigError, match="parse"):
            load_config(f.name)


def test_config_missing_required_section():
    from src.core.config import load_config, ConfigError

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("ibkr:\n  host: localhost\n")  # Missing other sections
        f.flush()

        with pytest.raises(ConfigError, match="required"):
            load_config(f.name)


def test_config_defaults():
    from src.core.config import load_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(MINIMAL_CONFIG)
        f.flush()

        config = load_config(f.name)

    assert config.collector.fundamental_refresh_hours == 24  # Default value


def test_config_strategy_disabled():
    from src.core.config import load_config

    config_with_disabled = """
ibkr:
  host: "127.0.0.1"
  port: 7497
  client_id: 1

data_store:
  backend: "file"
  path: "./data"

collector:
  watchlist: []

strategies:
  - name: "disabled_strategy"
    class_path: "src.strategies.example.Strategy"
    allocated_capital: 5000
    enabled: false
    params: {}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_with_disabled)
        f.flush()

        config = load_config(f.name)

    assert config.strategies[0].enabled is False


def test_config_get_enabled_strategies():
    from src.core.config import load_config

    config_mixed = """
ibkr:
  host: "127.0.0.1"
  port: 7497
  client_id: 1

data_store:
  backend: "file"
  path: "./data"

collector:
  watchlist: []

strategies:
  - name: "enabled_strategy"
    class_path: "src.strategies.example.Strategy1"
    allocated_capital: 5000
    enabled: true
    params: {}
  - name: "disabled_strategy"
    class_path: "src.strategies.example.Strategy2"
    allocated_capital: 5000
    enabled: false
    params: {}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_mixed)
        f.flush()

        config = load_config(f.name)

    enabled = config.get_enabled_strategies()
    assert len(enabled) == 1
    assert enabled[0].name == "enabled_strategy"
