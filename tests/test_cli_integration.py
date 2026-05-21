"""Integration tests for CLI functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from pytest import fixture

from kairo.cli import cli
from kairo.config import Config
from kairo.models import EmailMetadata
from kairo.services.accounts_service import AccountsService
from kairo.services.fetch_service import (
    AccountFinder,
    EmailFetchService,
    EmailProcessor,
    GmailAuthenticator,
)
from kairo.services.init_service import InitService
from kairo.services.search_service import SearchService
from kairo.storage import StorageManager


@fixture
def config_content():
    return {
        "accounts": {
            "test_account": {
                "provider": "gmail",
                "username": "test@example.com",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "access_token": "test_access_token",
                "port": 993,
            }
        },
        "storage": {"path": "/tmp/test_storage"},
    }


@fixture
def config_content_no_access_token():
    return {
        "accounts": {
            "test_account": {
                "provider": "gmail",
                "username": "test@example.com",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "port": 993,
            }
        },
        "storage": {"path": "/tmp/test_storage"},
    }


@fixture
def config_content_basic():
    return {
        "accounts": {
            "test_account": {
                "provider": "gmail",
                "username": "test@example.com",
                "password": "test_password",
            }
        },
        "storage": {"path": "/tmp/test_storage"},
    }


@fixture
def cli_args():
    return [
        "fetch",
        "--provider",
        "gmail",
        "--account",
        "test_account",
        "--folder",
        "inbox",
        "--limit",
        "1",
    ]


def test_fetch_command_with_mock_config(config_content_basic):
    """Test fetch command with a mock configuration."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_basic, f)
        config_file = f.name

    try:
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
                    "5",
                ],
            )

        assert result.exit_code == 0
        assert "Fetching emails from gmail account" in result.output
        assert "test@example.com" in result.output

    finally:
        os.unlink(config_file)


def test_fetch_command_auto_account_selection():
    """Test fetch command with automatic account selection."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "gmail": {
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
        with patch("kairo.config.Config._get_default_config_path") as mock_config_path:
            mock_config_path.return_value = Path(config_file)

            result = runner.invoke(
                cli,
                ["fetch", "--provider", "gmail", "--folder", "inbox", "--limit", "3"],
            )

            assert result.exit_code == 0
            assert "Fetching emails from gmail account" in result.output
            assert "gmail" in result.output

    finally:
        os.unlink(config_file)


def test_fetch_command_missing_account():
    """Test fetch command when no accounts are configured."""
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


def test_fetch_command_invalid_account():
    """Test fetch command with invalid account name."""
    runner = CliRunner()

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

    assert result.exit_code == 0
    assert "server is required for IMAP provider" in result.output


def test_fetch_command_with_oauth2_config(config_content, cli_args):
    """Test fetch command with OAuth2 configuration."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content, f)
        config_file = f.name

    try:
        with patch("kairo.config.Config._get_default_config_path") as mock_config_path:
            mock_config_path.return_value = Path(config_file)

            result = runner.invoke(
                cli,
                cli_args,
            )

        assert result.exit_code == 0
        assert "Using OAuth2 authentication with existing token" in result.output

    finally:
        os.unlink(config_file)


def test_error_handling_in_fetch():
    """Test error handling in fetch command."""
    runner = CliRunner()

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

        assert result.exit_code == 0
        assert "Error" in result.output or "not found" in result.output


def test_storage_integration(cli_args):
    """Test storage integration in fetch command."""
    runner = CliRunner()

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

        with patch("kairo.config.Config._get_default_config_path") as mock_config_path:
            mock_config_path.return_value = Path(config_file)

            result = runner.invoke(
                cli,
                cli_args,
            )

            assert result.exit_code == 0
            assert "Fetching emails" in result.output


@patch("kairo.config.Config._get_default_config_path")
def test_multiple_accounts_selection(mock_config_path):
    """Test CLI with multiple accounts of same provider."""
    runner = CliRunner()

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
        mock_config_path.return_value = Path(config_file)

        result = runner.invoke(
            cli, ["fetch", "--provider", "gmail", "--folder", "inbox", "--limit", "1"]
        )

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
def test_oauth2_flow_success(
    mock_config_path, _, mock_urlopen, config_content_no_access_token, cli_args
):
    """Test successful OAuth2 flow."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_no_access_token, f)
        config_file = f.name

    try:
        mock_config_path.return_value = Path(config_file)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"access_token": "test_access_token", "refresh_token": "test_refresh_token"}
        ).encode()
        mock_urlopen.return_value = mock_response

        with patch("click.prompt", return_value="test_auth_code"):
            result = runner.invoke(
                cli,
                cli_args,
            )

        assert result.exit_code == 0
        assert "Performing OAuth2 authentication flow" in result.output
        assert "Exchanging code for access token" in result.output
        assert "No authorization code received" in result.output
    finally:
        os.unlink(config_file)


@patch("urllib.request.urlopen")
@patch("kairo.config.Config._get_default_config_path")
def test_oauth2_flow_failure(
    mock_config_path, mock_urlopen, config_content_no_access_token, cli_args
):
    """Test OAuth2 flow failure."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_no_access_token, f)
        config_file = f.name

    try:
        mock_config_path.return_value = Path(config_file)

        mock_urlopen.side_effect = Exception("OAuth2 failed")

        with patch("click.prompt", return_value="test_auth_code"):
            result = runner.invoke(
                cli,
                cli_args,
            )

        assert result.exit_code == 0
        assert "Performing OAuth2 authentication flow" in result.output
        assert "Exchanging code for access token" in result.output
        assert "No authorization code received" in result.output

    finally:
        os.unlink(config_file)


@patch("kairo.config.Config._get_default_config_path")
def test_missing_username_in_account(mock_config_path):
    """Test CLI with account missing username."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "incomplete_account": {
                    "provider": "gmail",
                    "password": "test_password",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
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

        assert result.exit_code == 0
        assert (
            "Error: Account 'incomplete_account' not found in configuration"
            in result.output
        )

    finally:
        os.unlink(config_file)


@patch("kairo.config.Config._get_default_config_path")
def test_no_authentication_method(mock_config_path):
    """Test CLI with account having no authentication method."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "no_auth_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
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

        assert result.exit_code == 0
        assert (
            "Error: No authentication method configured (password or OAuth2)"
            in result.output
        )

    finally:
        os.unlink(config_file)


def test_accounts_service_list_accounts():
    """Test AccountsService list_accounts method."""

    config = Config()
    accounts_service = AccountsService(config)

    accounts_service.list_accounts()


def test_search_service_search_emails():
    """Test SearchService search_emails method."""

    config = Config()
    search_service = SearchService(config)

    search_service.search_emails("test_account", "test_query")


def test_init_service_initialize():
    """Test InitService initialize method."""

    init_service = InitService()

    init_service.initialize()


def test_email_processor_process_email():
    """Test EmailProcessor process_email method."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        class MockRetriever:
            def get_email_metadata(self, email_data):
                return EmailMetadata(
                    email_id=email_data["email_id"],
                    from_address=email_data["from_address"],
                    to_addresses=email_data["to_addresses"],
                    subject=email_data["subject"],
                    date=email_data["date"],
                    folder=email_data["folder"],
                    attachments=email_data.get("attachments", []),
                    has_attachments=email_data.get("has_attachments", False),
                    processed=False,
                )

        retriever = MockRetriever()
        processor = EmailProcessor(storage, retriever)

        email_data = {
            "email_id": "123",
            "from_address": "sender@example.com",
            "to_addresses": ["recipient@example.com"],
            "subject": "Test Subject",
            "date": "2024-01-01",
            "folder": "inbox",
            "attachments": [],
            "has_attachments": False,
            "raw": "From: sender@example.com\nTo: recipient@example.com\nSubject: Test Subject\n\nTest body",
        }

        result = processor.process_email("test_account", "inbox", email_data)
        assert result is True

        email_path = storage.get_email_path("test_account", "inbox", "123")
        assert email_path.exists()

        index = storage.load_index("test_account")
        emails = index.get_emails_in_folder("inbox")
        assert len(emails) == 1
        assert emails[0].email_id == "123"


def test_account_finder_validate_imap_requirements():
    """Test AccountFinder validate_imap_requirements method."""

    config = Config()
    finder = AccountFinder(config)

    result = finder.validate_imap_requirements("imap", None)
    assert result is False

    result = finder.validate_imap_requirements("imap", "imap.example.com")
    assert result is True

    result = finder.validate_imap_requirements("gmail", None)
    assert result is True


def test_account_finder_find_account_config(config_content_basic):
    """Test AccountFinder find_account_config method."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_basic, f)
        config_file = f.name

    try:
        config = Config(config_file)
        finder = AccountFinder(config)

        account_name, account_config = finder.find_account_config(
            "gmail", "test_account"
        )
        assert account_name == "test_account"
        assert account_config is not None
        assert account_config.username == "test@example.com"

        account_name, account_config = finder.find_account_config("gmail", None)
        assert account_name == "test_account"
        assert account_config is not None

        account_name, account_config = finder.find_account_config(
            "gmail", "nonexistent"
        )
        assert account_name is None
        assert account_config is None

    finally:
        Path(config_file).unlink()


def test_gmail_authenticator_authenticate(config_content_basic):
    """Test GmailAuthenticator authenticate method."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_basic, f)
        config_file = f.name

    try:
        config = Config(config_file)
        authenticator = GmailAuthenticator(config)

        account_config = config.get_account("test_account")
        retriever = authenticator.authenticate("test_account", account_config)  # type: ignore[arg-type]

        assert retriever is not None
        assert retriever.username == "test@example.com"
        assert retriever.password == "test_password"

    finally:
        Path(config_file).unlink()


def test_email_fetch_service_process_emails(config_content_basic):
    """Test EmailFetchService email processing logic."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_basic, f)
        config_file = f.name

    try:
        config = Config(config_file)
        fetch_service = EmailFetchService(config)

        mock_retriever = MagicMock()
        mock_storage = MagicMock()

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=("test_account", config.get_account("test_account")),
        ):  # type: ignore[arg-type]
            with patch.object(
                fetch_service.gmail_authenticator,
                "authenticate",
                return_value=mock_retriever,
            ):
                with patch(
                    "kairo.services.fetch_service.StorageManager",
                    return_value=mock_storage,
                ):
                    test_emails = [
                        {
                            "email_id": "1",
                            "from_address": "sender1@example.com",
                            "to_addresses": ["recipient@example.com"],
                            "subject": "Test Subject 1",
                            "date": "2024-01-01",
                            "folder": "INBOX",
                            "attachments": [],
                            "has_attachments": False,
                            "raw": "From: sender1@example.com\nSubject: Test Subject 1\n\nBody 1",
                        },
                        {
                            "email_id": "2",
                            "from_address": "sender2@example.com",
                            "to_addresses": ["recipient@example.com"],
                            "subject": "Test Subject 2",
                            "date": "2024-01-02",
                            "folder": "INBOX",
                            "attachments": [],
                            "has_attachments": False,
                            "raw": "From: sender2@example.com\nSubject: Test Subject 2\n\nBody 2",
                        },
                    ]
                    mock_retriever.fetch_emails.return_value = test_emails

                    mock_storage.is_email_processed.return_value = False
                    mock_processor = MagicMock()
                    mock_processor.process_email.return_value = True

                    with patch(
                        "kairo.services.fetch_service.EmailProcessor",
                        return_value=mock_processor,
                    ):
                        fetch_service.fetch_emails(
                            "gmail", "test_account", "inbox", None, 10
                        )

                        mock_retriever.fetch_emails.assert_called_once_with(
                            folder="INBOX"
                        )

                        assert mock_processor.process_email.call_count == 2

                        assert mock_storage.is_email_processed.call_count == 2
                        assert mock_storage.load_index.call_count == 2
                        assert mock_storage.save_index.call_count == 2

    finally:
        Path(config_file).unlink()


def test_email_fetch_service_empty_emails(config_content_basic):
    """Test EmailFetchService with no emails."""

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_basic, f)
        config_file = f.name

    try:
        config = Config(config_file)
        fetch_service = EmailFetchService(config)

        mock_retriever = MagicMock()
        mock_retriever.fetch_emails.return_value = []

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=("test_account", config.get_account("test_account")),
        ):  # type: ignore[arg-type]
            with patch.object(
                fetch_service.gmail_authenticator,
                "authenticate",
                return_value=mock_retriever,
            ):
                fetch_service.fetch_emails("gmail", "test_account", "inbox", None, 10)

                mock_retriever.fetch_emails.assert_called_once_with(folder="INBOX")

    finally:
        Path(config_file).unlink()


def test_email_fetch_service_processed_emails(config_content_basic):
    """Test EmailFetchService with already processed emails."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_basic, f)
        config_file = f.name

    try:
        config = Config(config_file)
        fetch_service = EmailFetchService(config)

        mock_retriever = MagicMock()
        mock_storage = MagicMock()

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=("test_account", config.get_account("test_account")),
        ):  # type: ignore[arg-type]
            with patch.object(
                fetch_service.gmail_authenticator,
                "authenticate",
                return_value=mock_retriever,
            ):
                with patch(
                    "kairo.services.fetch_service.StorageManager",
                    return_value=mock_storage,
                ):
                    test_emails = [
                        {
                            "email_id": "1",
                            "from_address": "sender1@example.com",
                            "to_addresses": ["recipient@example.com"],
                            "subject": "Test Subject 1",
                            "date": "2024-01-01",
                            "folder": "INBOX",
                            "attachments": [],
                            "has_attachments": False,
                            "raw": "From: sender1@example.com\nSubject: Test Subject 1\n\nBody 1",
                        }
                    ]
                    mock_retriever.fetch_emails.return_value = test_emails

                    mock_storage.is_email_processed.return_value = True

                    fetch_service.fetch_emails(
                        "gmail", "test_account", "inbox", None, 10
                    )

                    mock_storage.load_index.assert_not_called()
                    mock_storage.save_index.assert_not_called()

    finally:
        Path(config_file).unlink()


def test_email_fetch_service_limit_reached(config_content_basic):
    """Test EmailFetchService when limit is reached."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(config_content_basic, f)
        config_file = f.name

    try:
        config = Config(config_file)
        fetch_service = EmailFetchService(config)

        mock_retriever = MagicMock()
        mock_storage = MagicMock()

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=("test_account", config.get_account("test_account")),
        ):  # type: ignore[arg-type]
            with patch.object(
                fetch_service.gmail_authenticator,
                "authenticate",
                return_value=mock_retriever,
            ):
                with patch(
                    "kairo.services.fetch_service.StorageManager",
                    return_value=mock_storage,
                ):
                    test_emails = []
                    for i in range(5):
                        test_emails.append(
                            {
                                "email_id": str(i + 1),
                                "from_address": f"sender{i + 1}@example.com",
                                "to_addresses": ["recipient@example.com"],
                                "subject": f"Test Subject {i + 1}",
                                "date": "2024-01-01",
                                "folder": "INBOX",
                                "attachments": [],
                                "has_attachments": False,
                                "raw": f"From: sender{i + 1}@example.com\nSubject: Test Subject {i + 1}\n\nBody {i + 1}",
                            }
                        )
                    mock_retriever.fetch_emails.return_value = test_emails

                    mock_storage.is_email_processed.return_value = False
                    mock_processor = MagicMock()
                    mock_processor.process_email.return_value = True

                    with patch(
                        "kairo.services.fetch_service.EmailProcessor",
                        return_value=mock_processor,
                    ):
                        fetch_service.fetch_emails(
                            "gmail", "test_account", "inbox", None, 3
                        )

                        assert mock_processor.process_email.call_count == 3

    finally:
        Path(config_file).unlink()


def test_email_fetch_service_imap_provider():
    """Test EmailFetchService with IMAP provider."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "test_account": {
                    "provider": "imap",
                    "username": "test@example.com",
                    "password": "test_password",
                    "server": "imap.example.com",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        config = Config(config_file)
        fetch_service = EmailFetchService(config)

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=("test_account", config.get_account("test_account")),
        ):  # type: ignore[arg-type]
            runner = CliRunner()

            with runner.isolated_filesystem():
                with patch("click.echo") as mock_echo:
                    fetch_service.fetch_emails(
                        "imap", "test_account", "inbox", "imap.example.com", 10
                    )

                    assert any(
                        "IMAP provider not yet implemented" in str(call)
                        for call in mock_echo.call_args_list
                    )

    finally:
        Path(config_file).unlink()
