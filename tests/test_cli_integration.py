"""Integration tests for CLI functionality."""

import json
import re
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from faker import Faker

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
from tests.conftest import save_config

fake = Faker()


class MockGmailRetriever:
    """Custom mock for GmailRetriever with tracking capabilities."""

    def __init__(
        self,
        username: str,
        password: str | None = None,
        access_token: str | None = None,
        emails: list | None = None,
    ):
        self.username = username
        self.password = password
        self.access_token = access_token
        self.emails = emails or []
        self.fetch_emails_calls: list[dict] = []
        self.get_email_metadata_calls: list[dict] = []

    def fetch_emails(self, folder: str, limit: int = 10) -> list:
        """Mock fetch_emails method."""
        self.fetch_emails_calls.append({"folder": folder, "limit": limit})
        return self.emails

    def get_email_metadata(self, email_data: dict) -> EmailMetadata:
        """Mock get_email_metadata method."""
        self.get_email_metadata_calls.append(email_data)
        return EmailMetadata(
            email_id=email_data.get("email_id", ""),
            from_address=email_data.get("from_address", ""),
            to_addresses=email_data.get("to_addresses", []),
            subject=email_data.get("subject", ""),
            date=email_data.get("date", ""),
            folder=email_data.get("folder", ""),
            attachments=email_data.get("attachments", []),
            has_attachments=email_data.get("has_attachments", False),
            processed=False,
        )


class MockIMAPRetriever:
    """Custom mock for IMAP retriever."""

    def __init__(self, server: str, username: str, password: str):
        self.server = server
        self.username = username
        self.password = password
        self.fetch_emails_calls: list[dict] = []

    def fetch_emails(self, folder: str, limit: int = 10) -> list:
        """Mock fetch_emails method."""
        self.fetch_emails_calls.append({"folder": folder, "limit": limit})
        return []


@pytest.fixture
def fake_email_data():
    """Generate a single fake email dict."""
    return {
        "email_id": str(fake.uuid4()),
        "from_address": fake.email(),
        "to_addresses": [fake.email() for _ in range(fake.pyint(1, 3))],
        "subject": fake.sentence(nb_words=4),
        "date": fake.date_this_year().isoformat(),
        "folder": fake.word().upper(),
        "attachments": [fake.file_name() for _ in range(fake.pyint(0, 3))],
        "has_attachments": fake.pybool(),
        "raw": (
            f"From: {fake.email()}\n"
            f"To: {fake.email()}\n"
            f"Subject: {fake.sentence()}\n\n"
            f"{fake.text()}"
        ),
    }


@pytest.fixture
def fake_emails_data(batch_size=5):
    """Generate multiple fake emails."""
    emails = []
    for _ in range(batch_size):
        emails.append(
            {
                "email_id": str(fake.uuid4()),
                "from_address": fake.email(),
                "to_addresses": [fake.email() for _ in range(fake.pyint(1, 3))],
                "subject": fake.sentence(nb_words=4),
                "date": fake.date_this_year().isoformat(),
                "folder": fake.word().upper(),
                "attachments": [fake.file_name() for _ in range(fake.pyint(0, 3))],
                "has_attachments": fake.pybool(),
                "raw": (
                    f"From: {fake.email()}\n"
                    f"To: {fake.email()}\n"
                    f"Subject: {fake.sentence()}\n\n"
                    f"{fake.text()}"
                ),
            }
        )
    return emails


@pytest.fixture(
    params=[
        "basic_password",
        "oauth2_with_token",
        "oauth2_no_token",
        "imap_full",
        "multiple_gmail_accounts",
        "empty_accounts",
    ]
)
def config_variant(request, tmp_path):
    """Parameterized fixture providing different config variations."""
    variants = {
        "basic_password": {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        },
        "oauth2_with_token": {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "access_token": "test_access_token",
                    "refresh_token": "test_refresh_token",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        },
        "oauth2_no_token": {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        },
        "imap_full": {
            "accounts": {
                "test_account": {
                    "provider": "imap",
                    "username": "test@example.com",
                    "password": "test_password",
                    "server": "imap.example.com",
                    "port": 993,
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        },
        "multiple_gmail_accounts": {
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
            "storage": {"path": str(tmp_path / "storage")},
        },
        "empty_accounts": {
            "accounts": {},
            "storage": {"path": str(tmp_path / "storage")},
        },
    }
    return variants[request.param]


@pytest.fixture
def config_file(tmp_path, config_variant):
    """Create a temporary config file from variant."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config_variant, f)
    return config_path


@pytest.fixture
def config_file_basic(tmp_path):
    """Create a basic config file with password auth."""
    config_path = tmp_path / "config.json"
    config = {
        "accounts": {
            "test_account": {
                "provider": "gmail",
                "username": "test@example.com",
                "password": "test_password",
            }
        },
        "storage": {"path": str(tmp_path / "storage")},
    }
    save_config(config_path, config)
    return config_path


@pytest.fixture
def config_file_oauth2(tmp_path):
    """Create a config file with OAuth2."""
    config_path = tmp_path / "config.json"
    config = {
        "accounts": {
            "test_account": {
                "provider": "gmail",
                "username": "test@example.com",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "access_token": "test_access_token",
            }
        },
        "storage": {"path": str(tmp_path / "storage")},
    }
    save_config(config_path, config)
    return config_path


@pytest.fixture
def mock_config_path(tmp_path):
    """Mock the config path to use test config."""
    with patch("kairo.config.Config._get_default_config_path") as mock_path:
        mock_path.return_value = tmp_path / "config.json"
        yield mock_path


@pytest.fixture
def runner():
    """Provide a CliRunner instance."""
    return CliRunner()


@pytest.fixture
def config_path(tmp_path):
    config = {
        "accounts": {
            "test_account": {
                "provider": "gmail",
                "username": "test@example.com",
                "password": "test_password",
            }
        },
        "storage": {"path": str(tmp_path / "storage")},
    }
    config_path = tmp_path / "config.json"
    save_config(config_path, config)
    return config_path


@pytest.fixture
def empty_config(tmp_path):
    config = {
        "accounts": {},
        "storage": {"path": str(tmp_path / "storage")},
    }
    config_path = tmp_path / "config.json"
    save_config(config_path, config)
    return config_path


def assert_contains_in_order(output: str, *strings: str) -> None:
    """Assert that all strings appear in output in the specified order."""
    indices = []
    for s in strings:
        idx = output.find(s)
        if idx == -1:
            pytest.fail(f"String '{s}' not found in output")
        indices.append(idx)

    for i in range(len(indices) - 1):
        if indices[i] > indices[i + 1]:
            pytest.fail(
                f"Strings not in order: '{strings[i]}' at {indices[i]} "
                f"comes after '{strings[i + 1]}' at {indices[i + 1]}"
            )


def assert_matches_regex(output: str, pattern: str) -> None:
    """Assert that output matches the given regex pattern."""
    if not re.search(pattern, output):
        pytest.fail(f"Output does not match pattern: {pattern}\nOutput: {output}")


class TestFetchCommandBasic:
    """Tests for basic fetch command functionality."""

    def test_fetch_with_password_auth(self, runner, config_path, mock_config_path):
        """Test fetch command with password authentication."""

        mock_config_path.return_value = config_path

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
        assert_contains_in_order(
            result.output,
            "Fetching emails from gmail account",
            "test@example.com",
        )

    def test_fetch_auto_account_selection(self, runner, tmp_path, mock_config_path):
        """Test fetch command with automatic account selection."""
        config = {
            "accounts": {
                "gmail_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

        result = runner.invoke(
            cli,
            ["fetch", "--provider", "gmail", "--folder", "inbox", "--limit", "3"],
        )

        assert result.exit_code == 0
        assert_contains_in_order(
            result.output,
            "Fetching emails from gmail account",
        )

    @pytest.mark.parametrize(
        "provider,expected_message",
        [
            ("gmail", "Fetching emails from gmail account"),
            ("imap", "server is required for IMAP provider"),
        ],
    )
    def test_fetch_provider_messages(
        self,
        runner,
        tmp_path,
        provider,
        expected_message,
        mock_config_path,
    ):
        """Test fetch command with different providers."""
        config = {
            "accounts": {
                "test_account": {
                    "provider": provider,
                    "username": "test@example.com",
                    "password": "test_password",
                    "server": "imap.example.com" if provider == "imap" else None,
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        if provider == "gmail":
            config["accounts"]["test_account"].pop("server", None)

        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

        result = runner.invoke(
            cli,
            [
                "fetch",
                "--provider",
                provider,
                "--account",
                "test_account",
                "--folder",
                "inbox",
            ],
        )

        assert result.exit_code == 0
        assert expected_message in result.output


class TestFetchCommandAccounts:
    """Tests for fetch command account handling."""

    def test_missing_account(self, runner, tmp_path, mock_config_path):
        """Test fetch command when no accounts are configured."""
        config = {"accounts": {}, "storage": {"path": str(tmp_path / "storage")}}
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

        result = runner.invoke(
            cli,
            ["fetch", "--provider", "gmail", "--folder", "inbox"],
        )

        assert result.exit_code == 0
        assert "No gmail accounts configured" in result.output

    def test_invalid_account_name(self, runner, tmp_path, mock_config_path):
        """Test fetch command with invalid account name."""
        config = {
            "accounts": {
                "valid_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

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
        assert "Account 'invalid_account' not found" in result.output

    def test_multiple_accounts_selection(self, runner, tmp_path, mock_config_path):
        """Test CLI with multiple accounts of same provider."""
        config = {
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
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

        result = runner.invoke(
            cli,
            ["fetch", "--provider", "gmail", "--folder", "inbox", "--limit", "1"],
        )

        assert result.exit_code == 0
        assert "Multiple gmail accounts found" in result.output
        assert "work_gmail" in result.output
        assert "personal_gmail" in result.output
        assert "Using first account: work_gmail" in result.output


class TestFetchCommandOAuth2:
    """Tests for OAuth2 authentication flow."""

    def test_oauth2_with_existing_token(self, runner, tmp_path, mock_config_path):
        """Test fetch command with existing OAuth2 token."""
        config = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "access_token": "test_access_token",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

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

        assert result.exit_code == 0
        assert "Using OAuth2 authentication with existing token" in result.output

    def test_oauth2_flow_success(self, runner, tmp_path, mock_config_path):
        """Test successful OAuth2 flow when token is missing."""
        config = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            }
        ).encode()

        with patch("click.prompt", return_value="test_auth_code"):
            with patch("urllib.request.Request"):
                with patch("urllib.request.urlopen", return_value=mock_response):
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

        assert result.exit_code == 0
        assert_contains_in_order(
            result.output,
            "Performing OAuth2 authentication flow",
            "Exchanging code for access token",
        )

    def test_oauth2_flow_failure(self, runner, tmp_path, mock_config_path):
        """Test OAuth2 flow failure."""
        config = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

        with patch("click.prompt", return_value="test_auth_code"):
            with patch("urllib.request.Request"):
                with patch(
                    "urllib.request.urlopen",
                    side_effect=Exception("OAuth2 failed"),
                ):
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

        assert result.exit_code == 0
        assert "Performing OAuth2 authentication flow" in result.output


class TestFetchCommandErrors:
    """Tests for error handling in fetch command."""

    def test_missing_username(self, runner, tmp_path, mock_config_path):
        """Test CLI with account missing username."""
        config = {
            "accounts": {
                "incomplete_account": {
                    "provider": "gmail",
                    "password": "test_password",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

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
        assert "Account 'incomplete_account' not found" in result.output

    def test_no_authentication_method(self, runner, tmp_path, mock_config_path):
        """Test CLI with account having no authentication method."""
        config = {
            "accounts": {
                "no_auth_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

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
        assert "No authentication method configured" in result.output

    def test_imap_requires_server(self, runner, tmp_path, mock_config_path):
        """Test that IMAP provider requires server parameter."""
        config = {
            "accounts": {
                "test_account": {
                    "provider": "imap",
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

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

    def test_network_error_handling(self, runner, config_path, mock_config_path):
        """Test fetch command with network failure."""

        mock_config_path.return_value = config_path

        with patch("kairo.services.fetch_service.GmailRetriever") as mock_retriever:
            mock_retriever.side_effect = ConnectionError("Network failed")

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
                ],
            )

            assert result.exit_code == 0
            assert "Error" in result.output or "Network failed" in result.output

    def test_invalid_folder(self, runner, config_path, mock_config_path):
        """Test fetch command with invalid folder."""

        mock_config_path.return_value = config_path

        with patch("kairo.services.fetch_service.GmailRetriever") as mock_retriever:
            mock_instance = MagicMock()
            mock_instance.fetch_emails.side_effect = ValueError("Invalid folder")
            mock_retriever.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "fetch",
                    "--provider",
                    "gmail",
                    "--account",
                    "test_account",
                    "--folder",
                    "invalid_folder_xyz",
                ],
            )

            assert result.exit_code == 0
            assert "Error" in result.output or "invalid" in result.output.lower()


class TestStorageIntegration:
    """Tests for storage integration in fetch command."""

    def test_storage_creation(self, runner, tmp_path, mock_config_path):
        """Test that storage directory is created during fetch."""
        storage_dir = tmp_path / "storage"
        config = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": str(storage_dir)},
        }
        config_path = tmp_path / "config.json"
        save_config(config_path, config)
        mock_config_path.return_value = config_path

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

        assert result.exit_code == 0
        assert storage_dir.exists()

    def test_email_storage(self, fake_email_data, tmp_path):
        """Test that emails are stored correctly."""
        storage = StorageManager(str(tmp_path / "storage"))
        processor = EmailProcessor(storage, MockGmailRetriever("test", "pass"))

        result = processor.process_email("test_account", "inbox", fake_email_data)

        assert result is True
        email_path = storage.get_email_path(
            "test_account", "inbox", fake_email_data["email_id"]
        )
        assert email_path.exists()

        index = storage.load_index("test_account")
        emails = index.get_emails_in_folder("inbox")
        assert len(emails) == 1
        assert emails[0].email_id == fake_email_data["email_id"]
        assert emails[0].from_address == fake_email_data["from_address"]
        assert emails[0].subject == fake_email_data["subject"]


class TestAccountFinder:
    """Tests for AccountFinder service."""

    def test_validate_imap_requirements(self, empty_config):
        """Test IMAP requirements validation."""

        config_obj = Config(str(empty_config))
        finder = AccountFinder(config_obj)

        assert finder.validate_imap_requirements("imap", None) is False
        assert finder.validate_imap_requirements("imap", "") is False

        assert finder.validate_imap_requirements("imap", "imap.example.com") is True

        assert finder.validate_imap_requirements("gmail", None) is True

    def test_find_account_config(self, config_path):
        """Test finding account configuration."""

        config_obj = Config(str(config_path))
        finder = AccountFinder(config_obj)

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


class TestGmailAuthenticator:
    """Tests for GmailAuthenticator service."""

    def test_authenticate_with_password(self, config_path):
        """Test authentication with password."""

        config_obj = Config(str(config_path))
        authenticator = GmailAuthenticator(config_obj)

        account_config = config_obj.get_account("test_account")
        assert account_config is not None

        retriever = authenticator.authenticate("test_account", account_config)

        assert retriever is not None
        assert retriever.username == "test@example.com"
        assert retriever.password == "test_password"


class TestEmailFetchService:
    """Tests for EmailFetchService."""

    def test_process_emails_with_fake_data(
        self, tmp_path, config_path, fake_emails_data
    ):
        """Test processing multiple emails with fake data."""

        config_obj = Config(str(config_path))
        fetch_service = EmailFetchService(config_obj)

        mock_retriever = MockGmailRetriever(
            username="test@example.com",
            password="test_password",
            emails=fake_emails_data,
        )
        mock_storage = StorageManager(str(tmp_path / "storage"))

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=(
                "test_account",
                config_obj.get_account("test_account"),
            ),
        ):
            with patch.object(
                fetch_service.gmail_authenticator,
                "authenticate",
                return_value=mock_retriever,
            ):
                with patch(
                    "kairo.services.fetch_service.StorageManager",
                    return_value=mock_storage,
                ):
                    mock_processor = MagicMock()
                    mock_processor.process_email.return_value = True

                    with patch(
                        "kairo.services.fetch_service.EmailProcessor",
                        return_value=mock_processor,
                    ):
                        fetch_service.fetch_emails(
                            "gmail", "test_account", "inbox", None, 10
                        )

                        assert len(mock_retriever.fetch_emails_calls) == 1
                        assert mock_retriever.fetch_emails_calls[0]["folder"] == "INBOX"
                        assert mock_processor.process_email.call_count == len(
                            fake_emails_data
                        )

    def test_empty_emails(self, config_path):
        """Test processing with no emails."""

        config_obj = Config(str(config_path))
        fetch_service = EmailFetchService(config_obj)

        mock_retriever = MockGmailRetriever(
            username="test@example.com",
            password="test_password",
            emails=[],
        )

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=(
                "test_account",
                config_obj.get_account("test_account"),
            ),
        ):
            with patch.object(
                fetch_service.gmail_authenticator,
                "authenticate",
                return_value=mock_retriever,
            ):
                fetch_service.fetch_emails("gmail", "test_account", "inbox", None, 10)

                assert len(mock_retriever.fetch_emails_calls) == 1
                assert mock_retriever.fetch_emails_calls[0]["folder"] == "INBOX"

    def test_processed_emails_skipped(self, config_path, fake_emails_data):
        """Test that already processed emails are skipped."""

        config_obj = Config(str(config_path))
        fetch_service = EmailFetchService(config_obj)

        mock_retriever = MockGmailRetriever(
            username="test@example.com",
            password="test_password",
            emails=fake_emails_data,
        )
        mock_storage = MagicMock()
        mock_storage.is_email_processed.return_value = True

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=(
                "test_account",
                config_obj.get_account("test_account"),
            ),
        ):
            with patch.object(
                fetch_service.gmail_authenticator,
                "authenticate",
                return_value=mock_retriever,
            ):
                with patch(
                    "kairo.services.fetch_service.StorageManager",
                    return_value=mock_storage,
                ):
                    fetch_service.fetch_emails(
                        "gmail", "test_account", "inbox", None, 10
                    )

                    mock_storage.load_index.assert_not_called()
                    mock_storage.save_index.assert_not_called()

    def test_limit_reached(self, config_path):
        """Test that processing stops when limit is reached."""

        config_obj = Config(str(config_path))
        fetch_service = EmailFetchService(config_obj)

        emails = [
            {
                "email_id": str(i),
                "from_address": f"sender{i}@example.com",
                "to_addresses": ["recipient@example.com"],
                "subject": f"Subject {i}",
                "date": "2024-01-01",
                "folder": "INBOX",
                "attachments": [],
                "has_attachments": False,
                "raw": f"Body {i}",
            }
            for i in range(10)
        ]
        mock_retriever = MockGmailRetriever(
            username="test@example.com",
            password="test_password",
            emails=emails,
        )
        mock_storage = MagicMock()
        mock_storage.is_email_processed.return_value = False

        mock_processor = MagicMock()
        mock_processor.process_email.return_value = True

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=(
                "test_account",
                config_obj.get_account("test_account"),
            ),
        ):
            with patch.object(
                fetch_service.gmail_authenticator,
                "authenticate",
                return_value=mock_retriever,
            ):
                with patch(
                    "kairo.services.fetch_service.StorageManager",
                    return_value=mock_storage,
                ):
                    with patch(
                        "kairo.services.fetch_service.EmailProcessor",
                        return_value=mock_processor,
                    ):
                        fetch_service.fetch_emails(
                            "gmail", "test_account", "inbox", None, 3
                        )

                        assert mock_processor.process_email.call_count == 3

    def test_imap_provider_not_implemented(self, tmp_path):
        """Test IMAP provider returns not implemented message."""
        config_path = tmp_path / "config_imap.json"
        config = {
            "accounts": {
                "imap_account": {
                    "provider": "imap",
                    "username": "test@example.com",
                    "password": "test_password",
                    "server": "imap.example.com",
                }
            },
            "storage": {"path": str(tmp_path / "storage")},
        }
        with open(config_path, "w") as f:
            json.dump(config, f)

        config = Config(str(config_path))
        fetch_service = EmailFetchService(config)

        with patch.object(
            fetch_service.account_finder,
            "find_account_config",
            return_value=("imap_account", config.get_account("imap_account")),
        ):
            with patch("click.echo") as mock_echo:
                fetch_service.fetch_emails(
                    "imap", "imap_account", "inbox", "imap.example.com", 10
                )

                assert any(
                    "IMAP provider not yet implemented" in str(call)
                    for call in mock_echo.call_args_list
                )


class TestAccountsService:
    """Tests for AccountsService."""

    def test_list_accounts(self, empty_config):
        """Test listing accounts."""

        config_obj = Config(str(empty_config))
        accounts_service = AccountsService(config_obj)
        accounts_service.list_accounts()


class TestSearchService:
    """Tests for SearchService."""

    def test_search_emails(self, empty_config):
        """Test searching emails."""

        config_obj = Config(str(empty_config))
        search_service = SearchService(config_obj)
        search_service.search_emails("test_account", "test_query")


class TestInitService:
    """Tests for InitService."""

    def test_initialize(self):
        """Test initialization."""
        init_service = InitService()
        init_service.initialize()
