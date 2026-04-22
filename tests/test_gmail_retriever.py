"""Tests for Gmail retriever functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from kairo.models import EmailMetadata
from kairo.retrievers.gmail import GmailRetriever


def test_gmail_retriever_initialization():
    """Test GmailRetriever initialization with different auth methods."""
    # Test password authentication
    retriever = GmailRetriever(username="test@example.com", password="password123")
    assert retriever.username == "test@example.com"
    assert retriever.password == "password123"
    assert retriever.access_token is None

    # Test OAuth2 authentication
    retriever_oauth = GmailRetriever(
        username="test@example.com", access_token="token123"
    )
    assert retriever_oauth.username == "test@example.com"
    assert retriever_oauth.access_token == "token123"
    assert retriever_oauth.password is None


def test_gmail_retriever_missing_credentials():
    """Test GmailRetriever with missing credentials."""
    # Should not raise error during initialization
    retriever = GmailRetriever(username="test@example.com")
    assert retriever.username == "test@example.com"
    assert retriever.password is None
    assert retriever.access_token is None

    # Should raise error when trying to connect without credentials
    with pytest.raises(ValueError):
        retriever.connect()


@patch("imaplib.IMAP4_SSL")
def test_gmail_connect_password(mock_imap):
    """Test Gmail connection with password authentication."""
    mock_imap_instance = mock_imap.return_value

    retriever = GmailRetriever(username="test@example.com", password="password123")
    retriever.connect()

    # Verify IMAP connection was made
    mock_imap.assert_called_once_with("imap.gmail.com", 993)
    mock_imap_instance.login.assert_called_once_with("test@example.com", "password123")


@patch("imaplib.IMAP4_SSL")
def test_gmail_connect_oauth2(mock_imap):
    """Test Gmail connection with OAuth2 authentication."""
    mock_imap_instance = mock_imap.return_value

    retriever = GmailRetriever(username="test@example.com", access_token="token123")
    retriever.connect()

    # Verify IMAP connection was made with OAuth2
    mock_imap.assert_called_once_with("imap.gmail.com", 993)
    # OAuth2 authentication uses authenticate method
    mock_imap_instance.authenticate.assert_called_once()


@patch("imaplib.IMAP4_SSL")
def test_gmail_fetch_emails(mock_imap):
    """Test fetching emails from Gmail."""
    # Mock IMAP instance
    mock_imap_instance = mock_imap.return_value
    mock_imap_instance.select.return_value = ("OK", [b"1"])
    mock_imap_instance.search.return_value = ("OK", [b"1 2 3"])

    # Mock email data
    mock_email_bytes = b"From: test@example.com\r\nSubject: Test\r\n\r\nTest body"
    mock_imap_instance.fetch.return_value = (
        "OK",
        [(b"1", (b"RFC822", mock_email_bytes))],
    )

    retriever = GmailRetriever(username="test@example.com", password="password123")

    # Mock the _parse_email method to avoid complex email parsing
    with patch.object(retriever, "_parse_email") as mock_parse:
        mock_parse.return_value = {
            "email_id": "1",
            "from_address": "test@example.com",
            "to_addresses": ["recipient@example.com"],
            "subject": "Test Subject",
            "date": "Mon, 1 Jan 2024 12:00:00 +0000",
            "folder": "INBOX",
            "attachments": [],
            "has_attachments": False,
            "raw": "test email content",
        }

        emails = retriever.fetch_emails(folder="INBOX", limit=1)

        # Verify we got one email
        assert len(emails) == 1
        assert emails[0]["subject"] == "Test Subject"

        # Verify IMAP methods were called
        mock_imap_instance.select.assert_called_once_with("INBOX")
        mock_imap_instance.search.assert_called_once()
        mock_imap_instance.fetch.assert_called_once()


@patch("imaplib.IMAP4_SSL")
def test_gmail_fetch_emails_error_handling(mock_imap):
    """Test error handling in email fetching."""
    # Mock IMAP instance that raises an error
    mock_imap_instance = mock_imap.return_value
    mock_imap_instance.select.side_effect = Exception("Connection failed")

    retriever = GmailRetriever(username="test@example.com", password="password123")

    # Should handle the error gracefully
    with pytest.raises(Exception):
        retriever.fetch_emails(folder="INBOX", limit=1)


def test_parse_email_metadata():
    """Test email metadata conversion."""
    retriever = GmailRetriever(username="test@example.com", password="password123")

    # Sample email data
    email_data = {
        "email_id": "12345",
        "from_address": "sender@example.com",
        "to_addresses": ["recipient@example.com"],
        "subject": "Test Subject",
        "date": "Mon, 1 Jan 2024 12:00:00 +0000",
        "folder": "INBOX",
        "attachments": ["document.pdf"],
        "has_attachments": True,
    }

    metadata = retriever.get_email_metadata(email_data)

    # Verify metadata conversion
    assert isinstance(metadata, EmailMetadata)
    assert metadata.email_id == "12345"
    assert metadata.subject == "Test Subject"
    assert metadata.from_address == "sender@example.com"
    assert metadata.has_attachments is True
    assert len(metadata.attachments) == 1


@patch("imaplib.IMAP4_SSL")
def test_gmail_connection_error(mock_imap):
    """Test connection error handling."""
    mock_imap.side_effect = Exception("Connection failed")

    retriever = GmailRetriever(username="test@example.com", password="password123")

    with pytest.raises(Exception):
        retriever.connect()
