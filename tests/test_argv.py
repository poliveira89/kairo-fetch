"""Test CLI argument propagation when executed as a script."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def make_config(
    accounts: dict[str, Any] | None = None,
    storage_path: str | None = None,
) -> dict[str, Any]:
    """Generate test configuration data.

    Args:
        accounts: Dictionary of email accounts, defaults to empty dict.
        storage_path: Path for storage, defaults to /tmp/storage.

    Returns:
        Configuration dictionary.
    """
    return {
        "accounts": accounts or {},
        "storage": {"path": storage_path or "/tmp/storage"},
    }


@pytest.fixture
def kairo_dir(tmp_path: Path) -> Path:
    """Create a temporary kairo directory structure."""
    kairo_dir = tmp_path / ".kairo"
    kairo_dir.mkdir()
    storage_dir = kairo_dir / "storage"
    storage_dir.mkdir()
    config = make_config(storage_path=str(storage_dir))
    config_file = kairo_dir / "config.json"
    config_file.write_text(json.dumps(config))
    return tmp_path


def test_cli_entry_point_propagates_arguments(kairo_dir: Path) -> None:
    """Test that CLI entry point propagates system arguments correctly."""
    result = subprocess.run(
        [sys.executable, "-m", "kairo.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        env={"HOME": str(kairo_dir), "PYTHONPATH": str(Path(__file__).parent.parent)},
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert all(x in result.stdout for x in ["Usage:", "Email Fetch", "fetch"])


def test_cli_fetch_command_help(kairo_dir: Path) -> None:
    """Test that fetch command help works when executed as a module."""
    result = subprocess.run(
        [sys.executable, "-m", "kairo.cli", "fetch", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        env={"HOME": str(kairo_dir), "PYTHONPATH": str(Path(__file__).parent.parent)},
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert all(x in result.stdout for x in ["Fetch emails", "--provider"])


def test_cli_search_command_help(kairo_dir: Path) -> None:
    """Test that search command help works when executed as a module."""
    result = subprocess.run(
        [sys.executable, "-m", "kairo.cli", "search", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        env={"HOME": str(kairo_dir), "PYTHONPATH": str(Path(__file__).parent.parent)},
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert all(x in result.stdout for x in ["Search emails", "--account", "--query"])
