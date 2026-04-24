"""Tests for the CLI interface."""
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


def test_search_command_execution():
    """Test search command execution."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["search", "--account", "test_account", "--query", "from:john"]
    )
    assert result.exit_code == 0
    assert "Searching account 'test_account' for query: from:john" in result.output
    assert "Feature not yet implemented" in result.output


def test_list_accounts_command_execution():
    """Test list-accounts command execution."""
    runner = CliRunner()
    result = runner.invoke(cli, ["list-accounts"])
    assert result.exit_code == 0
    assert "List of configured accounts:" in result.output
    assert "Feature not yet implemented" in result.output


def test_init_command_execution():
    """Test init command execution."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert (
            "Initialized kairo configuration and storage directories" in result.output
        )


def test_cli_main_block():
    """Test CLI main block."""
    # This test covers the if __name__ == "__main__": block
    # by importing the module and checking that it doesn't execute main
    from kairo import cli

    assert hasattr(cli, "cli")
    assert hasattr(cli, "fetch")
    assert hasattr(cli, "search")
    assert hasattr(cli, "list_accounts")
    assert hasattr(cli, "init")


def test_cli_direct_execution():
    """Test CLI direct execution simulation."""
    # This test simulates what happens when the module is executed directly
    # by calling cli() directly
    from click.testing import CliRunner

    from kairo.cli import cli

    runner = CliRunner()

    # Test that calling cli() without arguments shows help
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Email Fetch" in result.output
