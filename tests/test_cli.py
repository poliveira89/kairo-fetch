"""Tests for the CLI interface."""
import pytest
from click.testing import CliRunner

from kairo.cli import cli


def test_cli_help():
    """Test that CLI help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Email Fetch" in result.output
    assert "fetch" in result.output
    assert "search" in result.output
    assert "list-accounts" in result.output


def test_fetch_command_help():
    """Test fetch command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["fetch", "--help"])
    assert result.exit_code == 0
    assert "Fetch emails" in result.output
    assert "--provider" in result.output
    assert "--account" in result.output


def test_search_command_help():
    """Test search command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--help"])
    assert result.exit_code == 0
    assert "Search emails" in result.output
    assert "--account" in result.output
    assert "--query" in result.output


def test_list_accounts_command_help():
    """Test list-accounts command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["list-accounts", "--help"])
    assert result.exit_code == 0
    assert "List configured accounts" in result.output


def test_fetch_command_requires_provider():
    """Test that fetch command requires provider."""
    runner = CliRunner()
    result = runner.invoke(cli, ["fetch", "--account", "test"])
    assert result.exit_code != 0
    assert "required" in result.output.lower() or "provider" in result.output.lower()


def test_fetch_command_imap_requires_server():
    """Test that IMAP provider requires server."""
    runner = CliRunner()
    result = runner.invoke(cli, ["fetch", "--provider", "imap", "--account", "test"])
    assert result.exit_code == 0  # Should show error message but exit 0
    assert "server is required" in result.output.lower()
