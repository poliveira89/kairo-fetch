"""Tests for the CLI interface."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from kairo.cli import cli
from kairo.config import Config


@pytest.fixture
def runner(tmp_path):
    """Provide a CliRunner instance with isolated filesystem and temp home for CLI tests."""
    Config.reset()

    with CliRunner().isolated_filesystem(temp_dir=str(tmp_path)):
        with patch("kairo.config.Path.home", return_value=tmp_path):
            yield CliRunner()


def test_cli_help(runner: CliRunner) -> None:
    """Test that CLI help works."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert all(
        x in result.output
        for x in ["Usage:", "Email Fetch", "fetch", "search", "list-accounts"]
    )


def test_fetch_command_help(runner: CliRunner) -> None:
    """Test fetch command help."""
    result = runner.invoke(cli, ["fetch", "--help"])
    assert result.exit_code == 0
    assert all(x in result.output for x in ["Fetch emails", "--provider", "--account"])


def test_search_command_help(runner: CliRunner) -> None:
    """Test search command help."""
    result = runner.invoke(cli, ["search", "--help"])
    assert result.exit_code == 0
    assert all(x in result.output for x in ["Search emails", "--account", "--query"])


def test_list_accounts_command_help(runner: CliRunner) -> None:
    """Test list-accounts command help."""
    result = runner.invoke(cli, ["list-accounts", "--help"])
    assert result.exit_code == 0
    assert "List configured accounts" in result.output


def test_fetch_command_requires_provider(runner: CliRunner) -> None:
    """Test that fetch command requires provider."""
    result = runner.invoke(cli, ["fetch", "--account", "test"])
    assert result.exit_code != 0
    assert any(x in result.output.lower() for x in ["required", "provider"])


def test_fetch_command_imap_requires_server(runner: CliRunner) -> None:
    """Test that IMAP provider requires server."""
    result = runner.invoke(cli, ["fetch", "--provider", "imap", "--account", "test"])
    assert result.exit_code == 0
    assert "server is required" in result.output.lower()


def test_search_command_execution(runner: CliRunner) -> None:
    """Test search command execution."""
    result = runner.invoke(
        cli, ["search", "--account", "test_account", "--query", "from:john"]
    )
    assert result.exit_code == 0
    assert all(
        x in result.output
        for x in [
            "Searching account 'test_account' for query: from:john",
            "Feature not yet implemented",
        ]
    )


def test_list_accounts_command_execution(runner: CliRunner) -> None:
    """Test list-accounts command execution."""
    result = runner.invoke(cli, ["list-accounts"])
    assert result.exit_code == 0
    assert all(
        x in result.output
        for x in ["List of configured accounts:", "Feature not yet implemented"]
    )


def test_init_command_execution(runner: CliRunner) -> None:
    """Test init command execution."""
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "Initialized kairo configuration and storage directories" in result.output


def test_fetch_command_missing_required_args(runner: CliRunner) -> None:
    """Test fetch command fails without required arguments."""
    result = runner.invoke(cli, ["fetch"])
    assert result.exit_code != 0
    assert any(
        x in result.output.lower()
        for x in ["required", "missing", "provider", "account"]
    )


def test_search_command_missing_required_args(runner: CliRunner) -> None:
    """Test search command fails without required arguments."""
    result = runner.invoke(cli, ["search"])
    assert result.exit_code != 0
    assert any(
        x in result.output.lower() for x in ["required", "missing", "account", "query"]
    )
