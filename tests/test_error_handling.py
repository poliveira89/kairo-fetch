"""Tests for error handling in the application."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from kairo.cli import cli
from kairo.config import Config
from kairo.models import EmailMetadata
from kairo.retrievers.gmail import GmailRetriever
from kairo.storage import StorageManager
from tests.conftest import assert_raises_on_connect


def test_config_file_not_found():
    """Test handling of missing config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "nonexistent.json"

        Config.reset()
        config = Config(str(config_path))
        assert config.config_path == str(config_path)
        assert config.data.accounts == {}
        assert config.data.storage.path == str(Path.home() / ".kairo" / "storage")


def test_config_file_invalid_json():
    """Test handling of invalid JSON in config file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write("invalid json content {")
        config_file = f.name

    try:
        Config.reset()
        config = Config(config_file)
        assert config.data.accounts == {}
        assert config.data.storage.path == str(Path.home() / ".kairo" / "storage")
    finally:
        os.unlink(config_file)


def test_gmail_retriever_missing_username():
    """Test Gmail retriever with missing username."""
    with pytest.raises(TypeError):
        GmailRetriever()  # Missing required username parameter  # type: ignore[call-arg]


def test_gmail_retriever_connection_failure():
    """Test Gmail retriever connection failure handling."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap.side_effect = Exception("Connection failed")

        retriever = GmailRetriever(username="test@example.com", password="password")

        with pytest.raises(Exception):
            retriever.connect()


def test_gmail_retriever_authentication_failure():
    """Test Gmail retriever authentication failure handling."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.login.side_effect = Exception("Authentication failed")

        retriever = GmailRetriever(
            username="test@example.com", password="wrong_password"
        )

        with pytest.raises(Exception):
            retriever.connect()


def test_gmail_retriever_fetch_emails_error():
    """Test Gmail retriever fetch emails error handling."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.side_effect = Exception("Folder not found")

        retriever = GmailRetriever(username="test@example.com", password="password")

        with pytest.raises(Exception):
            retriever.fetch_emails()


def test_cli_missing_provider():
    """Test CLI with missing provider parameter."""
    runner = CliRunner()

    result = runner.invoke(cli, ["fetch", "--account", "test"])

    assert result.exit_code != 0
    assert "required" in result.output.lower() or "provider" in result.output.lower()


def test_cli_invalid_provider():
    """Test CLI with invalid provider."""
    runner = CliRunner()

    result = runner.invoke(cli, ["fetch", "--provider", "invalid", "--account", "test"])

    assert result.exit_code != 0
    assert (
        "invalid choice" in result.output.lower() or "invalid" in result.output.lower()
    )


def test_cli_missing_account_when_required():
    """Test CLI with missing account when it's required."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {"accounts": {}, "storage": {"path": "/tmp/test_storage"}}
        json.dump(config_content, f)
        config_file = f.name

    try:
        with patch("kairo.config.Config._get_default_config_path") as mock_config_path:
            mock_config_path.return_value = Path(config_file)

            result = runner.invoke(
                cli, ["fetch", "--provider", "gmail", "--folder", "inbox"]
            )

        assert result.exit_code == 0
        assert "No gmail accounts configured" in result.output

    finally:
        os.unlink(config_file)


def test_storage_invalid_path():
    """Test storage with invalid path."""
    with pytest.raises(TypeError):
        StorageManager(None)  # type: ignore[arg-type]


def test_storage_permission_error():
    """Test storage with permission error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        no_write_dir = Path(temp_dir) / "no_write"
        no_write_dir.mkdir(mode=0o444)  # Read-only

        try:
            with pytest.raises(PermissionError):
                StorageManager(str(no_write_dir / "subdir"))
        finally:
            no_write_dir.chmod(0o755)
            no_write_dir.rmdir()


def test_config_invalid_account_data():
    """Test config with invalid account data."""
    config = Config()

    result = config.get_account("nonexistent")
    assert result is None

    invalid_data = {"invalid": "data"}
    config.set_account("test", invalid_data)  # type: ignore[arg-type]
    retrieved = config.get_account("test")
    assert retrieved == invalid_data


def test_email_metadata_validation():
    """Test EmailMetadata validation."""

    with pytest.raises(ValidationError):
        EmailMetadata(
            from_address="test@example.com",
            to_addresses=[],
            subject="Test",
            date="2024-01-01",
            folder="inbox",
        )  # type: ignore[call-arg]

    metadata = EmailMetadata(
        email_id="123",
        from_address="test@example.com",
        to_addresses=[],
        subject="Test",
        date="2024-01-01",
        folder="inbox",
    )
    assert metadata.email_id == "123"


def test_cli_error_output():
    """Test CLI error output formatting."""
    runner = CliRunner()

    result = runner.invoke(cli, ["nonexistent_command"])
    assert result.exit_code != 0
    assert "No such command" in result.output

    result = runner.invoke(cli, ["fetch", "--invalid-option"])
    assert result.exit_code != 0
    assert "no such option" in result.output.lower()


def test_gmail_retriever_empty_username():
    """Test empty username raises ValueError."""
    assert_raises_on_connect(GmailRetriever, username="")


def test_gmail_retriever_long_username():
    """Test long username is stored correctly."""
    long_username = "a" * 300 + "@example.com"
    retriever = GmailRetriever(username=long_username, password="password")
    assert retriever.username == long_username


def test_storage_edge_cases():
    """Test storage edge cases."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        account_path = storage.get_account_path("")
        assert str(account_path).endswith("")

        account_path = storage.get_account_path("test@account.com")
        assert "test@account.com" in str(account_path)

        long_email_id = "a" * 300
        email_path = storage.get_email_path("test", "inbox", long_email_id)
        assert long_email_id in str(email_path)

        assert storage.base_path == Path(temp_dir)  # nosec
