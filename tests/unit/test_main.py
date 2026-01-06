"""Tests for main entry point."""
import pytest
from unittest.mock import patch, MagicMock
import tempfile


def test_parse_args_default():
    from src.__main__ import parse_args

    args = parse_args([])

    assert args.config == "config/default.yaml"
    assert args.log_level == "INFO"


def test_parse_args_custom_config():
    from src.__main__ import parse_args

    args = parse_args(["--config", "custom.yaml"])

    assert args.config == "custom.yaml"


def test_parse_args_debug_level():
    from src.__main__ import parse_args

    args = parse_args(["--log-level", "DEBUG"])

    assert args.log_level == "DEBUG"


def test_parse_args_short_flags():
    from src.__main__ import parse_args

    args = parse_args(["-c", "test.yaml", "-l", "WARNING"])

    assert args.config == "test.yaml"
    assert args.log_level == "WARNING"


def test_setup_logging():
    from src.__main__ import setup_logging
    import logging

    # Just verify setup_logging runs without error for all valid levels
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        setup_logging(level)  # Should not raise

    # Verify a handler was added
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0


def test_main_loads_config():
    from src.__main__ import main

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
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
""")
        f.flush()

        with patch('src.__main__.Orchestrator') as MockOrch:
            mock_orch = MagicMock()
            MockOrch.return_value = mock_orch
            mock_orch.start.side_effect = KeyboardInterrupt

            result = main(["--config", f.name])

            MockOrch.assert_called_once()
            mock_orch.stop.assert_called_once()


def test_main_handles_keyboard_interrupt():
    from src.__main__ import main

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
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
""")
        f.flush()

        with patch('src.__main__.Orchestrator') as MockOrch:
            mock_orch = MagicMock()
            MockOrch.return_value = mock_orch
            mock_orch.start.side_effect = KeyboardInterrupt

            # Should not raise, should return 0
            result = main(["--config", f.name])

            assert result == 0
            mock_orch.stop.assert_called_once()


def test_main_returns_error_on_config_error():
    from src.__main__ import main

    # Non-existent config file
    result = main(["--config", "/nonexistent/config.yaml"])

    assert result == 1


def test_main_returns_error_on_exception():
    from src.__main__ import main

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
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
""")
        f.flush()

        with patch('src.__main__.Orchestrator') as MockOrch:
            MockOrch.side_effect = RuntimeError("Test error")

            result = main(["--config", f.name])

            assert result == 1
