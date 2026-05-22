"""Pytest fixtures and helpers for kairo-fetch tests."""

from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from unittest.mock import patch

import pytest

from kairo.config import Config
from kairo.models import EmailMetadata
from kairo.retrievers.gmail import GmailRetriever


@pytest.fixture(autouse=True)
def reset_config():
    """Reset Config singleton before each test."""
    Config.reset()
    yield
    Config.reset()


# =============================================================================
# Fake Data Generators
# =============================================================================


class FakeEmailGenerator:
    """Generate fake email data for testing.

    Provides consistent, configurable test data for email-related tests.
    """

    @staticmethod
    def create_email_data(
        email_id: str = "1",
        subject: str = "Test Subject",
        from_addr: str = "sender@example.com",
        to_addrs: list[str] | None = None,
        has_attachments: bool = False,
        attachment_names: list[str] | None = None,
        folder: str = "INBOX",
        date: str = "Mon, 1 Jan 2024 12:00:00 +0000",
    ) -> dict[str, Any]:
        """Generate a fake email data dictionary.

        Args:
            email_id: Unique email identifier
            subject: Email subject line
            from_addr: Sender email address
            to_addrs: List of recipient email addresses
            has_attachments: Whether email has attachments
            attachment_names: List of attachment filenames
            folder: Email folder/label
            date: Email date string

        Returns:
            Dictionary matching the structure returned by GmailRetriever._parse_email
        """
        return {
            "email_id": email_id,
            "from_address": from_addr,
            "to_addresses": to_addrs or ["recipient@example.com"],
            "subject": subject,
            "date": date,
            "folder": folder,
            "attachments": attachment_names
            or ([] if not has_attachments else ["file.pdf"]),
            "has_attachments": has_attachments,
            "raw": f"From: {from_addr}\r\nSubject: {subject}\r\n\r\nTest body",
        }

    @staticmethod
    def create_mime_message(
        subject: str = "Test",
        from_addr: str = "sender@example.com",
        to_addr: str = "recipient@example.com",
        body: str = "Test body",
        has_attachment: bool = False,
        attachment_name: str = "doc.pdf",
        date: str = "Mon, 1 Jan 2024 12:00:00 +0000",
        folder: str = "INBOX",
    ) -> MIMEMultipart | Message:
        """Generate a fake MIME message.

        Args:
            subject: Email subject
            from_addr: Sender address
            to_addr: Recipient address
            body: Email body content
            has_attachment: Whether to include an attachment
            attachment_name: Name of the attachment file
            date: Email date header
            folder: Gmail folder label

        Returns:
            email.message.Message or MIMEMultipart object
        """
        if has_attachment:
            msg = MIMEMultipart()
            text_part = MIMEText(body)
            msg.attach(text_part)
            attachment = MIMEApplication(b"attachment content", _subtype="pdf")
            attachment.add_header(
                "Content-Disposition", "attachment", filename=attachment_name
            )
            msg.attach(attachment)
        else:
            msg = Message()
            msg.set_payload(body)

        msg["subject"] = subject
        msg["from"] = from_addr
        msg["to"] = to_addr
        msg["date"] = date
        msg["X-GM-LABELS"] = folder
        return msg


# =============================================================================
# Fixtures for Gmail Retriever Tests
# =============================================================================


@pytest.fixture
def email_example():
    """Provide example email data dictionary."""
    return FakeEmailGenerator.create_email_data()


@pytest.fixture
def email_metadata():
    """Provide an EmailMetadata instance for testing."""
    return EmailMetadata(
        email_id="12345",
        from_address="sender@example.com",
        to_addresses=["recipient@example.com"],
        subject="Test Subject",
        date="Mon, 1 Jan 2024 12:00:00 +0000",
        folder="INBOX",
        attachments=["document.pdf"],
        has_attachments=True,
    )


@pytest.fixture
def gmail_retriever_password():
    """Provide a GmailRetriever with password authentication."""
    return GmailRetriever(username="test@example.com", password="password123")


@pytest.fixture
def gmail_retriever_oauth():
    """Provide a GmailRetriever with OAuth2 authentication."""
    return GmailRetriever(username="test@example.com", access_token="token123")


@pytest.fixture
def gmail_retriever_no_creds():
    """Provide a GmailRetriever with no credentials."""
    return GmailRetriever(username="test@example.com")


@pytest.fixture
def mock_imap_connection():
    """Provide a mock IMAP connection with default success responses.

    Yields:
        tuple: (mock_imap_class, mock_instance) for configuring test behavior
    """
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_instance = mock_imap.return_value
        mock_instance.select.return_value = ("OK", [b"1"])
        mock_instance.search.return_value = ("OK", [b"1 2 3"])
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
        yield mock_imap, mock_instance


# =============================================================================
# Helper Functions
# =============================================================================


def assert_raises_on_connect(retriever_class, **kwargs):
    """Helper to test that a retriever raises an exception on connect."""
    with pytest.raises(ValueError):
        retriever = retriever_class(**kwargs)
        retriever.connect()


def setup_mock_imap_for_fetch(
    mock_imap,
    select_result: tuple = ("OK", [b"1"]),
    search_result: tuple = ("OK", [b"1 2 3"]),
    fetch_result: tuple | None = None,
):
    """Configure mock IMAP for fetch_emails tests.

    Args:
        mock_imap: The mock IMAP4_SSL class
        select_result: Result for select() call
        search_result: Result for search() call
        fetch_result: Result for fetch() call (optional)

    Returns:
        The mock IMAP instance for further configuration
    """
    mock_instance = mock_imap.return_value
    mock_instance.select.return_value = select_result
    mock_instance.search.return_value = search_result
    if fetch_result:
        mock_instance.fetch.return_value = fetch_result
    return mock_instance
