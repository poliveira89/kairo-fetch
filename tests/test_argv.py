"""Test CLI argument propagation when executed as a script."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def get_temp_kairo_dir():
    """Create a temporary kairo directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    kairo_dir = temp_dir / ".kairo"
    kairo_dir.mkdir(exist_ok=True)
    storage_dir = kairo_dir / "storage"
    storage_dir.mkdir(exist_ok=True)

    config_file = kairo_dir / "config.json"
    config_file.write_text(
        '{"accounts": {}, "storage": {"path": "' + str(storage_dir) + '"}}'
    )

    return temp_dir


def test_cli_entry_point_propagates_arguments():
    """Test that CLI entry point propagates system arguments correctly."""
    temp_dir = get_temp_kairo_dir()

    result = subprocess.run(
        [sys.executable, "-m", "kairo.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        env={"HOME": str(temp_dir), "PYTHONPATH": str(Path(__file__).parent.parent)},
    )

    shutil.rmtree(temp_dir, ignore_errors=True)

    assert result.returncode == 0, f"CLI --help failed with: {result.stderr}"
    assert (
        "Usage:" in result.stdout
    ), f"Expected 'Usage:' in output, got: {result.stdout}"
    assert (
        "Email Fetch" in result.stdout
    ), f"Expected 'Email Fetch' in output, got: {result.stdout}"
    assert (
        "fetch" in result.stdout
    ), f"Expected 'fetch' command in output, got: {result.stdout}"


def test_cli_fetch_command_help():
    """Test that fetch command help works when executed as a module."""
    temp_dir = get_temp_kairo_dir()

    result = subprocess.run(
        [sys.executable, "-m", "kairo.cli", "fetch", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        env={"HOME": str(temp_dir), "PYTHONPATH": str(Path(__file__).parent.parent)},
    )

    shutil.rmtree(temp_dir, ignore_errors=True)

    assert result.returncode == 0, f"fetch --help failed with: {result.stderr}"
    assert (
        "Fetch emails" in result.stdout
    ), f"Expected 'Fetch emails' in output, got: {result.stdout}"
    assert (
        "--provider" in result.stdout
    ), f"Expected '--provider' in output, got: {result.stdout}"


def test_cli_search_command_help():
    """Test that search command help works when executed as a module."""
    temp_dir = get_temp_kairo_dir()

    result = subprocess.run(
        [sys.executable, "-m", "kairo.cli", "search", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        env={"HOME": str(temp_dir), "PYTHONPATH": str(Path(__file__).parent.parent)},
    )

    shutil.rmtree(temp_dir, ignore_errors=True)

    assert result.returncode == 0, f"search --help failed with: {result.stderr}"
    assert (
        "Search emails" in result.stdout
    ), f"Expected 'Search emails' in output, got: {result.stdout}"
    assert (
        "--account" in result.stdout
    ), f"Expected '--account' in output, got: {result.stdout}"
    assert (
        "--query" in result.stdout
    ), f"Expected '--query' in output, got: {result.stdout}"
