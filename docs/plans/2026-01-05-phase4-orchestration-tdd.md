# Phase 4: Orchestration - TDD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire all components together with config-driven startup and graceful shutdown

**Architecture:** YAML config → Orchestrator → Components lifecycle management

**Tech Stack:** Python 3.12+, pyyaml, argparse, signal handlers

---

## Task 1: Config Loader

**Files:**
- Create: `src/core/config.py`
- Create: `config/default.yaml`
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_config.py
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


def test_load_config_from_file():
    from src.core.config import load_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()

        config = load_config(f.name)

    assert config.ibkr.host == "127.0.0.1"
    assert config.ibkr.port == 7497
    assert config.collector.watchlist == ["AAPL", "MSFT"]


def test_config_validates_required_fields():
    from src.core.config import load_config, ConfigError

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("ibkr:\n  host: localhost\n")  # Missing required fields
        f.flush()

        with pytest.raises(ConfigError):
            load_config(f.name)


def test_config_strategy_loading():
    from src.core.config import load_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(SAMPLE_CONFIG)
        f.flush()

        config = load_config(f.name)

    assert len(config.strategies) == 1
    assert config.strategies[0].name == "example_value"
    assert config.strategies[0].allocated_capital == 10000
```

**Step 2-5:** Run test (fail), implement, run test (pass), commit.

---

## Task 2: Orchestrator

**Files:**
- Create: `src/core/orchestrator.py`
- Test: `tests/unit/test_orchestrator.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_orchestrator.py
import pytest
from unittest.mock import Mock, patch, MagicMock


def test_orchestrator_init():
    from src.core.orchestrator import Orchestrator
    from src.core.config import Config

    config = Mock(spec=Config)
    orchestrator = Orchestrator(config)

    assert orchestrator.config is config
    assert not orchestrator.is_running


def test_orchestrator_initializes_components():
    from src.core.orchestrator import Orchestrator

    with patch('src.core.orchestrator.FileDataStore') as MockStore:
        with patch('src.core.orchestrator.EventBus') as MockBus:
            config = create_mock_config()
            orchestrator = Orchestrator(config)
            orchestrator._initialize_components()

            MockStore.assert_called_once()
            MockBus.assert_called_once()


def test_orchestrator_loads_strategies():
    from src.core.orchestrator import Orchestrator

    config = create_mock_config()
    orchestrator = Orchestrator(config)
    orchestrator._initialize_components()
    orchestrator._load_strategies()

    assert len(orchestrator.strategies) == 1
```

**Step 2-5:** Run test (fail), implement, run test (pass), commit.

---

## Task 3: Main Entry Point

**Files:**
- Create: `src/__main__.py`
- Test: `tests/unit/test_main.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_main.py
import pytest
from unittest.mock import patch, MagicMock


def test_parse_args_default():
    from src.__main__ import parse_args

    args = parse_args([])

    assert args.config == "config/default.yaml"


def test_parse_args_custom_config():
    from src.__main__ import parse_args

    args = parse_args(["--config", "custom.yaml"])

    assert args.config == "custom.yaml"


def test_main_creates_orchestrator():
    from src.__main__ import main

    with patch('src.__main__.Orchestrator') as MockOrch:
        with patch('src.__main__.load_config') as MockConfig:
            mock_orch = MagicMock()
            MockOrch.return_value = mock_orch

            # Simulate immediate shutdown
            mock_orch.start.side_effect = KeyboardInterrupt

            main(["--config", "test.yaml"])

            MockConfig.assert_called_once()
            mock_orch.stop.assert_called_once()
```

**Step 2-5:** Run test (fail), implement, run test (pass), commit.

---

## Implementation Order

1. **Config Loader** - Foundation for all component initialization
2. **Orchestrator** - Wires components together
3. **Main Entry Point** - CLI interface

## Testing Strategy

- Config tests use temporary files
- Orchestrator tests mock all components
- Main tests mock orchestrator
