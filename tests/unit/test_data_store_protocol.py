"""Tests for DataStore protocol."""
import pytest


def test_data_store_is_protocol():
    from src.core.data_store import DataStore

    # Protocol classes have this attribute
    assert hasattr(DataStore, '__protocol_attrs__') or DataStore._is_protocol


def test_file_data_store_implements_protocol():
    import tempfile
    from src.core.data_store import DataStore, FileDataStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = FileDataStore(base_path=tmpdir)
        assert isinstance(store, DataStore)


def test_file_data_store_creates_directories():
    import tempfile
    from pathlib import Path
    from src.core.data_store import FileDataStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = FileDataStore(base_path=tmpdir)
        base = Path(tmpdir)

        assert (base / "prices").exists()
        assert (base / "fundamentals").exists()
        assert (base / "events").exists()
        assert (base / "state").exists()
        assert (base / "audit" / "decisions").exists()
        assert (base / "audit" / "orders").exists()
