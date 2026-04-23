"""Integration tests for CLI functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kairo.cli import cli
from kairo.config import Config


def test_fetch_command_with_mock_config():
    """Test fetch command with a mock configuration."""
    runner = CliRunner()

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Mock the config to use our test file
        with patch("kairo.config.Config._get_default_config_path") as mock_config_path:
            mock_config_path.return_value = Path(config_file)

            # Test with explicit account
            result = runner.invoke(
                cli,
                [
                    "fetch",
                    "--provider",
                    "gmail",
                    "--account",
                    "test_account",
                    "--folder",
                    "inbox",
                    "--limit",
                    "5",
                ],
            )

        # Should fail with authentication error (expected since we're using test credentials)
        assert result.exit_code == 0  # CLI handles errors gracefully
        assert "Fetching emails from gmail account" in result.output
        assert "test@example.com" in result.output

    finally:
        os.unlink(config_file)


def test_fetch_command_auto_account_selection():
    """Test fetch command with automatic account selection."""
    runner = CliRunner()

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "gmail": {  # Account name matches provider
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Test without specifying account (should auto-select)
        result = runner.invoke(
            cli, ["fetch", "--provider", "gmail", "--folder", "inbox", "--limit", "3"]
        )

        # Should automatically select the gmail account
        assert result.exit_code == 0
        assert "Fetching emails from gmail account" in result.output
        assert "gmail" in result.output  # Account name

    finally:
        os.unlink(config_file)


def test_fetch_command_missing_account():
    """Test fetch command when no accounts are configured."""
    runner = CliRunner()

    # Create a temporary config file with no accounts
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {"accounts": {}, "storage": {"path": "/tmp/test_storage"}}
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Mock the config to use our test file
        with patch("kairo.config.Config._get_default_config_path") as mock_config_path:
            mock_config_path.return_value = Path(config_file)

            result = runner.invoke(
                cli, ["fetch", "--provider", "gmail", "--folder", "inbox"]
            )

        # Should show error about no accounts configured
        assert result.exit_code == 0
        assert "No gmail accounts configured" in result.output

    finally:
        os.unlink(config_file)


def test_fetch_command_invalid_account():
    """Test fetch command with invalid account name."""
    runner = CliRunner()

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "valid_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Test with non-existent account
        result = runner.invoke(
            cli,
            [
                "fetch",
                "--provider",
                "gmail",
                "--account",
                "invalid_account",
                "--folder",
                "inbox",
            ],
        )

        # Should show error about account not found
        assert result.exit_code == 0
        assert "Account 'invalid_account' not found in configuration" in result.output

    finally:
        os.unlink(config_file)


def test_fetch_command_imap_requires_server():
    """Test that IMAP provider requires server parameter."""
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "fetch",
            "--provider",
            "imap",
            "--account",
            "test_account",
            "--folder",
            "inbox",
        ],
    )

    # Should show error about missing server
    assert result.exit_code == 0
    assert "server is required for IMAP provider" in result.output


def test_fetch_command_with_oauth2_config():
    """Test fetch command with OAuth2 configuration."""
    runner = CliRunner()

    # Create a temporary config file with OAuth2 credentials
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Mock the config to use our test file
        with patch("kairo.config.Config._get_default_config_path") as mock_config_path:
            mock_config_path.return_value = Path(config_file)

            # This would normally trigger OAuth2 flow, but we'll just test the setup
            result = runner.invoke(
                cli,
                [
                    "fetch",
                    "--provider",
                    "gmail",
                    "--account",
                    "test_account",
                    "--folder",
                    "inbox",
                    "--limit",
                    "1",
                ],
            )

        # Should attempt OAuth2 flow (will fail without real credentials)
        assert result.exit_code == 0
        assert "Performing OAuth2 authentication flow" in result.output

    finally:
        os.unlink(config_file)


def test_error_handling_in_fetch():
    """Test error handling in fetch command."""
    runner = CliRunner()

    # Test with no config file (should create default)
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "fetch",
                "--provider",
                "gmail",
                "--account",
                "nonexistent",
                "--folder",
                "inbox",
            ],
        )

        # Should handle missing config gracefully
        assert result.exit_code == 0
        # Should show appropriate error message
        assert "Error" in result.output or "not found" in result.output


def test_storage_integration():
    """Test storage integration in fetch command."""
    runner = CliRunner()

    # Create a temporary config and storage directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, "config.json")
        storage_dir = os.path.join(temp_dir, "storage")

        with open(config_file, "w") as f:
            config_content = {
                "accounts": {
                    "test_account": {
                        "provider": "gmail",
                        "username": "test@example.com",
                        "password": "test_password",
                    }
                },
                "storage": {"path": storage_dir},
            }
            json.dump(config_content, f)

        # Mock the config to use our test file
        with patch("kairo.config.Config._get_default_config_path") as mock_config_path:
            mock_config_path.return_value = Path(config_file)

            result = runner.invoke(
                cli,
                [
                    "fetch",
                    "--provider",
                    "gmail",
                    "--account",
                    "test_account",
                    "--folder",
                    "inbox",
                    "--limit",
                    "1",
                ],
            )

            # Should attempt to fetch (will fail with auth error)
            assert result.exit_code == 0
            assert "Fetching emails" in result.output


@patch("kairo.config.Config._get_default_config_path")
def test_multiple_accounts_selection(mock_config_path):
    """Test CLI with multiple accounts of same provider."""
    runner = CliRunner()

    # Create a temporary config with multiple gmail accounts
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "work_gmail": {
                    "provider": "gmail",
                    "username": "work@example.com",
                    "password": "work_password",
                },
                "personal_gmail": {
                    "provider": "gmail",
                    "username": "personal@example.com",
                    "password": "personal_password",
                },
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Mock the config to use our test file
        mock_config_path.return_value = Path(config_file)

        result = runner.invoke(
            cli, ["fetch", "--provider", "gmail", "--folder", "inbox", "--limit", "1"]
        )

        # Should show multiple accounts found message
        assert result.exit_code == 0
        assert "Multiple gmail accounts found" in result.output
        assert "work_gmail" in result.output
        assert "personal_gmail" in result.output
        assert "Using first account: work_gmail" in result.output

    finally:
        os.unlink(config_file)


@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
@patch("kairo.config.Config._get_default_config_path")
def test_oauth2_flow_success(mock_config_path, mock_request, mock_urlopen):
    """Test successful OAuth2 flow."""
    runner = CliRunner()

    # Create a temporary config with OAuth2 credentials
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Mock the config to use our test file
        mock_config_path.return_value = Path(config_file)

        # Mock OAuth2 responses
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"access_token": "test_access_token", "refresh_token": "test_refresh_token"}
        ).encode()
        mock_urlopen.return_value = mock_response

        # Mock user input for auth code
        with patch("click.prompt", return_value="test_auth_code"):
            result = runner.invoke(
                cli,
                [
                    "fetch",
                    "--provider",
                    "gmail",
                    "--account",
                    "test_account",
                    "--folder",
                    "inbox",
                    "--limit",
                    "1",
                ],
            )

        # Should show successful OAuth2 flow
        assert result.exit_code == 0
        assert "Performing OAuth2 authentication flow" in result.output
        assert "Visit this URL to authorize" in result.output
        assert "Exchanging code for access token" in result.output
        assert "✅ OAuth2 authentication successful!" in result.output

        # Verify token was saved to config
        config = Config(config_file)
        account_config = config.get_account("test_account")
        assert account_config["access_token"] == "test_access_token"
        assert account_config["refresh_token"] == "test_refresh_token"  # type: ignore[index]

    finally:
        os.unlink(config_file)


@patch("urllib.request.urlopen")
@patch("kairo.config.Config._get_default_config_path")
def test_oauth2_flow_failure(mock_config_path, mock_urlopen):
    """Test OAuth2 flow failure."""
    runner = CliRunner()

    # Create a temporary config with OAuth2 credentials
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Mock the config to use our test file
        mock_config_path.return_value = Path(config_file)

        # Mock OAuth2 failure
        mock_urlopen.side_effect = Exception("OAuth2 failed")

        # Mock user input for auth code
        with patch("click.prompt", return_value="test_auth_code"):
            result = runner.invoke(
                cli,
                [
                    "fetch",
                    "--provider",
                    "gmail",
                    "--account",
                    "test_account",
                    "--folder",
                    "inbox",
                    "--limit",
                    "1",
                ],
            )

        # Should show OAuth2 failure
        assert result.exit_code == 0
        assert "Performing OAuth2 authentication flow" in result.output
        assert "❌ OAuth2 authentication failed" in result.output
        assert "OAuth2 failed" in result.output

    finally:
        os.unlink(config_file)


@patch("kairo.config.Config._get_default_config_path")
def test_missing_username_in_account(mock_config_path):
    """Test CLI with account missing username."""
    runner = CliRunner()

    # Create a temporary config with account missing username
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "incomplete_account": {
                    "provider": "gmail",
                    "password": "test_password"
                    # Missing username
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Mock the config to use our test file
        mock_config_path.return_value = Path(config_file)

        result = runner.invoke(
            cli,
            [
                "fetch",
                "--provider",
                "gmail",
                "--account",
                "incomplete_account",
                "--folder",
                "inbox",
                "--limit",
                "1",
            ],
        )

        # Should show error about missing username
        assert result.exit_code == 0
        assert "Error: Username not configured for account" in result.output

    finally:
        os.unlink(config_file)


@patch("kairo.config.Config._get_default_config_path")
def test_no_authentication_method(mock_config_path):
    """Test CLI with account having no authentication method."""
    runner = CliRunner()

    # Create a temporary config with account missing both password and OAuth2
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "no_auth_account": {
                    "provider": "gmail",
                    "username": "test@example.com"
                    # Missing password and OAuth2 credentials
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        # Mock the config to use our test file
        mock_config_path.return_value = Path(config_file)

        result = runner.invoke(
            cli,
            [
                "fetch",
                "--provider",
                "gmail",
                "--account",
                "no_auth_account",
                "--folder",
                "inbox",
                "--limit",
                "1",
            ],
        )

        # Should show error about no authentication method
        assert result.exit_code == 0
        assert (
            "Error: No authentication method configured (password or OAuth2)"
            in result.output
        )

    finally:
        os.unlink(config_file)
