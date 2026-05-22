"""Tests for Gmail retriever functionality."""

from unittest.mock import patch

import pytest

from kairo.models import EmailMetadata
from kairo.retrievers.gmail import GmailRetriever
from tests.conftest import (
    FakeEmailGenerator,
    assert_raises_on_connect,
    setup_mock_imap_for_fetch,
)


class TestGmailRetrieverAuthentication:
    """Tests for GmailRetriever authentication initialization and connection."""

    def test_basic_auth_initialization(self) -> None:
        """Test GmailRetriever initialization with username and password."""
        retriever = GmailRetriever(username="test@example.com", password="password123")
        assert retriever.username == "test@example.com"
        assert retriever.password == "password123"
        assert retriever.access_token is None

    def test_oauth2_initialization(self) -> None:
        """Test GmailRetriever initialization with username and access token."""
        retriever = GmailRetriever(username="test@example.com", access_token="token123")
        assert retriever.username == "test@example.com"
        assert retriever.access_token == "token123"
        assert retriever.password is None

    def test_missing_credentials_initialization(self) -> None:
        """Test GmailRetriever with missing credentials."""
        retriever = GmailRetriever(username="test@example.com")
        assert retriever.username == "test@example.com"
        assert retriever.password is None
        assert retriever.access_token is None

        with pytest.raises(ValueError):
            retriever.connect()

    def test_empty_username_raises_error(self) -> None:
        """Test empty username raises ValueError on connect."""
        assert_raises_on_connect(GmailRetriever, username="")

    def test_long_username_stored_correctly(self) -> None:
        """Test long username is stored correctly."""
        long_username = "a" * 300 + "@example.com"
        retriever = GmailRetriever(username=long_username, password="password")
        assert retriever.username == long_username

    @patch("imaplib.IMAP4_SSL")
    def test_connect_password_auth(self, mock_imap) -> None:
        """Test Gmail connection with password authentication."""
        retriever = GmailRetriever(username="test@example.com", password="password123")
        retriever.connect()

        mock_imap.assert_called_once_with("imap.gmail.com", 993)
        mock_imap.return_value.login.assert_called_once_with(
            "test@example.com", "password123"
        )

    @patch("imaplib.IMAP4_SSL")
    def test_connect_oauth2_auth(self, mock_imap) -> None:
        """Test Gmail connection with OAuth2 authentication."""
        retriever = GmailRetriever(username="test@example.com", access_token="token123")
        retriever.connect()

        mock_imap.assert_called_once_with("imap.gmail.com", 993)
        mock_imap.return_value.authenticate.assert_called_once()

    @patch("imaplib.IMAP4_SSL")
    def test_connection_error(self, mock_imap) -> None:
        """Test connection error handling."""
        mock_imap.side_effect = Exception("Connection failed")

        retriever = GmailRetriever(username="test@example.com", password="password123")

        with pytest.raises(Exception):
            retriever.connect()


class TestGmailRetrieverMetadata:
    """Tests for email metadata conversion."""

    def test_get_email_metadata(self, gmail_retriever_password) -> None:
        """Test email metadata conversion from email data."""
        email_data = FakeEmailGenerator.create_email_data(
            email_id="12345",
            from_addr="sender@example.com",
            to_addrs=["recipient@example.com"],
            subject="Test Subject",
            has_attachments=True,
            attachment_names=["document.pdf"],
        )

        metadata = gmail_retriever_password.get_email_metadata(email_data)

        assert isinstance(metadata, EmailMetadata)
        assert metadata.email_id == "12345"
        assert metadata.subject == "Test Subject"
        assert metadata.from_address == "sender@example.com"
        assert metadata.has_attachments is True
        assert len(metadata.attachments) == 1


class TestGmailRetrieverParsing:
    """Tests for email parsing functionality."""

    def test_parse_email_no_content_disposition(self, gmail_retriever_password) -> None:
        """Test email parsing with no Content-Disposition header."""
        msg = FakeEmailGenerator.create_mime_message(
            subject="Test Subject",
            from_addr="sender@example.com",
            to_addr="recipient@example.com",
            has_attachment=False,
        )

        email_data = gmail_retriever_password._parse_email(msg, "123")

        assert email_data["attachments"] == []
        assert email_data["has_attachments"] is False

    def test_parse_email_with_attachments(self, gmail_retriever_password) -> None:
        """Test email parsing with attachments."""
        msg = FakeEmailGenerator.create_mime_message(
            subject="Test Subject with Attachment",
            from_addr="sender@example.com",
            to_addr="recipient@example.com",
            has_attachment=True,
            attachment_name="document.pdf",
        )

        email_data = gmail_retriever_password._parse_email(msg, "123")

        assert len(email_data["attachments"]) == 1
        assert "document.pdf" in email_data["attachments"]
        assert email_data["has_attachments"] is True

    def test_parse_multipart_without_attachment(self, gmail_retriever_password) -> None:
        """Test email parsing with multipart but no attachments."""
        msg = FakeEmailGenerator.create_mime_message(
            subject="Test Subject",
            has_attachment=False,
        )

        email_data = gmail_retriever_password._parse_email(msg, "123")

        assert email_data["attachments"] == []
        assert email_data["has_attachments"] is False


class TestGmailRetrieverFetch:
    """Tests for email fetching functionality."""

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_emails_success(
        self, mock_imap, gmail_retriever_password, email_example
    ) -> None:
        """Test fetching emails from Gmail successfully."""
        mock_instance = mock_imap.return_value
        mock_instance.select.return_value = ("OK", [b"1"])
        mock_instance.search.return_value = ("OK", [b"1"])
        mock_instance.fetch.return_value = (
            "OK",
            [
                (
                    b"1",
                    (
                        b"RFC822",
                        b"From: test@example.com\r\nSubject: Test\r\n\r\nTest body",
                    ),
                )
            ],
        )

        with patch.object(gmail_retriever_password, "_parse_email") as mock_parse:
            mock_parse.return_value = email_example
            emails = gmail_retriever_password.fetch_emails(folder="INBOX", limit=1)

            assert len(emails) == 1
            assert emails[0]["subject"] == "Test Subject"

            mock_instance.select.assert_called_once_with("INBOX")
            mock_instance.search.assert_called_once()
            mock_instance.fetch.assert_called_once()

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_emails_error_handling(
        self, mock_imap, gmail_retriever_password
    ) -> None:
        """Test error handling in email fetching when connection fails."""
        mock_instance = mock_imap.return_value
        mock_instance.select.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            gmail_retriever_password.fetch_emails(folder="INBOX", limit=1)

    @pytest.mark.parametrize("raw_email_type", ["bytes", "string"])
    @patch("imaplib.IMAP4_SSL")
    def test_fetch_emails_raw_email_types(
        self,
        mock_imap,
        gmail_retriever_password,
        raw_email_type: str,
    ) -> None:
        """Test fetching emails with different raw email content types."""
        mock_instance = setup_mock_imap_for_fetch(mock_imap)

        if raw_email_type == "bytes":
            raw_content = b"From: test@example.com\r\nSubject: Test\r\n\r\nTest body"
        else:
            raw_content = "From: test@example.com\r\nSubject: Test\r\n\r\nTest body"

        mock_instance.fetch.return_value = (
            "OK",
            [(b"1", (b"RFC822", raw_content))],
        )

        with patch.object(gmail_retriever_password, "_parse_email") as mock_parse:
            mock_parse.return_value = FakeEmailGenerator.create_email_data()
            emails = gmail_retriever_password.fetch_emails(folder="INBOX", limit=1)

            assert len(emails) == 1
            mock_parse.assert_called_once()

    @pytest.mark.parametrize(
        "fetch_result,expected_count",
        [
            (("OK", []), 0),
            (
                ("OK", ["invalid_structure"]),
                0,
            ),
            (("OK", [(b"1", None)]), 0),
        ],
    )
    @patch("imaplib.IMAP4_SSL")
    def test_fetch_emails_edge_cases(
        self,
        mock_imap,
        gmail_retriever_password,
        fetch_result: tuple,
        expected_count: int,
    ) -> None:
        """Test Gmail retriever edge cases in fetch_emails."""
        setup_mock_imap_for_fetch(
            mock_imap,
            fetch_result=fetch_result,
        )

        with patch.object(gmail_retriever_password, "_parse_email") as mock_parse:
            mock_parse.return_value = FakeEmailGenerator.create_email_data()

            emails = gmail_retriever_password.fetch_emails(folder="INBOX", limit=1)
            assert len(emails) == expected_count

            if expected_count == 0:
                mock_parse.assert_not_called()

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_emails_select_folder_failure(
        self, mock_imap, gmail_retriever_password
    ) -> None:
        """Test Gmail retriever when folder selection fails."""
        setup_mock_imap_for_fetch(
            mock_imap,
            select_result=("NO", [b"Folder does not exist"]),
        )

        with pytest.raises(Exception) as exc_info:
            gmail_retriever_password.fetch_emails(folder="NONEXISTENT", limit=1)

        assert "Failed to select folder: NONEXISTENT" in str(exc_info.value)

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_emails_search_failure(
        self, mock_imap, gmail_retriever_password
    ) -> None:
        """Test Gmail retriever when email search fails."""
        setup_mock_imap_for_fetch(
            mock_imap,
            search_result=("NO", [b"Search failed"]),
        )

        with pytest.raises(Exception) as exc_info:
            gmail_retriever_password.fetch_emails(folder="INBOX", limit=1)

        assert "Failed to search emails" in str(exc_info.value)

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_emails_fetch_failure(
        self, mock_imap, gmail_retriever_password
    ) -> None:
        """Test Gmail retriever when email fetch fails."""
        setup_mock_imap_for_fetch(
            mock_imap,
            fetch_result=("NO", [b"Fetch failed"]),
        )

        with patch.object(gmail_retriever_password, "_parse_email") as mock_parse:
            mock_parse.return_value = FakeEmailGenerator.create_email_data()

            emails = gmail_retriever_password.fetch_emails(folder="INBOX", limit=1)
            assert len(emails) == 0
            mock_parse.assert_not_called()
