"""Tests for Gmail retriever functionality."""

from unittest.mock import patch

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


def test_gmail_retriever_edge_cases():
    """Test Gmail retriever edge cases."""

    # Test with empty username
    with pytest.raises(ValueError):
        retriever = GmailRetriever(username="")
        retriever.connect()

    # Test with very long username
    long_username = "a" * 300 + "@example.com"
    retriever = GmailRetriever(username=long_username, password="password")
    assert retriever.username == long_username


def test_gmail_fetch_emails_error_conditions():
    """Test Gmail retriever error conditions in fetch_emails."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        mock_imap_instance.search.return_value = ("OK", [b"1 2 3"])

        # Test case where msg_data is empty
        mock_imap_instance.fetch.return_value = ("OK", [])

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should handle empty msg_data gracefully
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
            assert len(emails) == 0  # Should skip empty msg_data


def test_gmail_fetch_emails_invalid_msg_part():
    """Test Gmail retriever with invalid msg_part structure."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        mock_imap_instance.search.return_value = ("OK", [b"1"])

        # Test case where msg_part is not a list/tuple or has wrong length
        mock_imap_instance.fetch.return_value = ("OK", ["invalid_structure"])

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should handle invalid msg_part gracefully
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
            assert len(emails) == 0  # Should skip invalid msg_part


def test_parse_email_no_content_disposition():
    """Test email parsing with no Content-Disposition."""
    retriever = GmailRetriever(username="test@example.com", password="password123")

    # Create a mock email message
    from email.message import Message

    msg = Message()
    msg["subject"] = "Test Subject"
    msg["from"] = "sender@example.com"
    msg["to"] = "recipient@example.com"
    msg["date"] = "Mon, 1 Jan 2024 12:00:00 +0000"
    msg["X-GM-LABELS"] = "INBOX"
    msg.set_payload("Test body")

    # Parse the email
    email_data = retriever._parse_email(msg, "123")

    # Should have no attachments when no Content-Disposition
    assert email_data["attachments"] == []
    assert email_data["has_attachments"] is False


def test_gmail_fetch_emails_select_folder_failure():
    """Test Gmail retriever when folder selection fails."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        # Mock select to return non-OK status
        mock_imap_instance.select.return_value = ("NO", [b"Folder does not exist"])

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should raise exception when folder selection fails
        with pytest.raises(Exception) as exc_info:
            retriever.fetch_emails(folder="NONEXISTENT", limit=1)

        assert "Failed to select folder: NONEXISTENT" in str(exc_info.value)


def test_gmail_fetch_emails_search_failure():
    """Test Gmail retriever when email search fails."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        # Mock search to return non-OK status
        mock_imap_instance.search.return_value = ("NO", [b"Search failed"])

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should raise exception when search fails
        with pytest.raises(Exception) as exc_info:
            retriever.fetch_emails(folder="INBOX", limit=1)

        assert "Failed to search emails" in str(exc_info.value)


def test_gmail_fetch_emails_fetch_failure():
    """Test Gmail retriever when email fetch fails."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        mock_imap_instance.search.return_value = ("OK", [b"1"])
        # Mock fetch to return non-OK status
        mock_imap_instance.fetch.return_value = ("NO", [b"Fetch failed"])

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should handle fetch failure gracefully (continue to next email)
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
            # Should skip the failed fetch and return empty list
            assert len(emails) == 0
            mock_parse.assert_not_called()


def test_gmail_fetch_emails_empty_msg_data():
    """Test Gmail retriever with empty msg_data."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        mock_imap_instance.search.return_value = ("OK", [b"1"])
        # Mock fetch to return empty msg_data
        mock_imap_instance.fetch.return_value = ("OK", [])

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should handle empty msg_data gracefully
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
            # Should skip empty msg_data and return empty list
            assert len(emails) == 0
            mock_parse.assert_not_called()


def test_gmail_fetch_emails_invalid_msg_part_structure():
    """Test Gmail retriever with invalid msg_part structure."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        mock_imap_instance.search.return_value = ("OK", [b"1"])
        # Mock fetch to return msg_part that's not a list/tuple or too short
        mock_imap_instance.fetch.return_value = ("OK", ["invalid_structure"])

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should handle invalid msg_part structure gracefully
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
            # Should skip invalid msg_part and return empty list
            assert len(emails) == 0
            mock_parse.assert_not_called()


def test_gmail_fetch_emails_string_raw_email():
    """Test Gmail retriever with string raw_email (non-bytes)."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        mock_imap_instance.search.return_value = ("OK", [b"1"])
        # Mock fetch to return string raw_email (not bytes)
        mock_imap_instance.fetch.return_value = (
            "OK",
            [(b"1", (b"RFC822", "string email content"))],
        )

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should handle string raw_email by converting to string
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
            # Should process the string email
            assert len(emails) == 1
            mock_parse.assert_called_once()


def test_parse_email_with_attachments():
    """Test email parsing with attachments."""
    retriever = GmailRetriever(username="test@example.com", password="password123")

    # Create a mock email message with attachments
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # Create multipart message
    msg = MIMEMultipart()
    msg["subject"] = "Test Subject with Attachment"
    msg["from"] = "sender@example.com"
    msg["to"] = "recipient@example.com"
    msg["date"] = "Mon, 1 Jan 2024 12:00:00 +0000"
    msg["X-GM-LABELS"] = "INBOX"

    # Add text part
    text_part = MIMEText("Test body")
    msg.attach(text_part)

    # Add attachment
    attachment = MIMEApplication(b"attachment content", _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename="document.pdf")
    msg.attach(attachment)

    # Parse the email
    email_data = retriever._parse_email(msg, "123")

    # Should detect the attachment
    assert len(email_data["attachments"]) == 1
    assert "document.pdf" in email_data["attachments"]
    assert email_data["has_attachments"] is True


def test_parse_email_multipart_without_attachment():
    """Test email parsing with multipart but no attachments."""
    retriever = GmailRetriever(username="test@example.com", password="password123")

    # Create a mock email message with multipart but no attachments
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # Create multipart message
    msg = MIMEMultipart()
    msg["subject"] = "Test Subject"
    msg["from"] = "sender@example.com"
    msg["to"] = "recipient@example.com"
    msg["date"] = "Mon, 1 Jan 2024 12:00:00 +0000"
    msg["X-GM-LABELS"] = "INBOX"

    # Add text part
    text_part = MIMEText("Test body")
    msg.attach(text_part)

    # Parse the email
    email_data = retriever._parse_email(msg, "123")

    # Should have no attachments when multipart has no Content-Disposition
    assert email_data["attachments"] == []
    assert email_data["has_attachments"] is False


def test_gmail_fetch_emails_bytes_raw_email():
    """Test Gmail retriever with bytes raw_email."""
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
        mock_imap_instance.search.return_value = ("OK", [b"1"])
        # Mock fetch to return bytes raw_email (normal case)
        mock_email_bytes = b"From: test@example.com\r\nSubject: Test\r\n\r\nTest body"
        mock_imap_instance.fetch.return_value = (
            "OK",
            [(b"1", (b"RFC822", mock_email_bytes))],
        )

        retriever = GmailRetriever(username="test@example.com", password="password123")

        # Should handle bytes raw_email correctly
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
            # Should process the bytes email
            assert len(emails) == 1
            mock_parse.assert_called_once()
