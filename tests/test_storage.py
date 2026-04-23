"""Tests for storage functionality."""

import os
import tempfile
from pathlib import Path

from kairo.models import EmailMetadata
from kairo.storage import StorageManager


def test_storage_manager_initialization():
    """Test StorageManager initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)
        assert storage.base_path == Path(temp_dir)
        assert storage.base_path.exists()


def test_get_account_path():
    """Test getting account path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        account_path = storage.get_account_path("test_account")
        expected_path = Path(temp_dir) / "test_account"

        assert account_path == expected_path
        assert account_path.exists()


def test_get_email_path():
    """Test getting email path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        email_path = storage.get_email_path("test_account", "inbox", "email123")
        expected_path = (
            Path(temp_dir) / "test_account" / "emails" / "inbox" / "email123.eml"
        )

        assert email_path == expected_path
        assert email_path.parent.exists()  # Parent directory should be created


def test_get_attachment_path():
    """Test getting attachment path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        attachment_path = storage.get_attachment_path(
            "test_account", "attach123", "document.pdf"
        )
        expected_path = (
            Path(temp_dir) / "test_account" / "attachments" / "attach123_document.pdf"
        )

        assert attachment_path == expected_path
        assert attachment_path.parent.exists()


def test_get_index_path():
    """Test getting index path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        index_path = storage.get_index_path("test_account")
        expected_path = Path(temp_dir) / "test_account" / "index.json"

        assert index_path == expected_path


def test_load_index_empty():
    """Test loading index when file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        index = storage.load_index("test_account")

        # Should return default empty index
        assert isinstance(index, dict)
        assert "folders" in index
        assert index["folders"] == {}


def test_load_index_existing():
    """Test loading existing index."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Create a test index file
        index_path = storage.get_index_path("test_account")
        test_index = {
            "folders": {
                "inbox": [
                    {
                        "email_id": "123",
                        "subject": "Test Email",
                        "from_address": "test@example.com",
                    }
                ]
            }
        }

        import json

        with open(index_path, "w") as f:
            json.dump(test_index, f)

        # Load the index
        loaded_index = storage.load_index("test_account")

        assert loaded_index == test_index
        assert loaded_index["folders"]["inbox"][0]["subject"] == "Test Email"


def test_save_index():
    """Test saving index."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Create test index data
        test_index = {
            "folders": {
                "inbox": [
                    {
                        "email_id": "123",
                        "subject": "Test Email",
                        "from_address": "test@example.com",
                    }
                ]
            }
        }

        # Save the index
        storage.save_index("test_account", test_index)  # type: ignore[arg-type]  # type: ignore[arg-type]

        # Verify it was saved
        index_path = storage.get_index_path("test_account")
        assert index_path.exists()

        # Load and verify
        import json

        with open(index_path, "r") as f:
            saved_index = json.load(f)

        assert saved_index == test_index


def test_sanitize_filename():
    """Test filename sanitization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Test various problematic filenames
        test_cases = [
            ("normal_file.pdf", "normal_file.pdf"),
            ("file with spaces.txt", "file with spaces.txt"),  # Spaces are allowed
            ("file/with/slashes.pdf", "file_with_slashes.pdf"),
            ("file:with:colons.txt", "file_with_colons.txt"),
            ("file*with*asterisks.pdf", "file_with_asterisks.pdf"),
            ("file?with?questions.txt", "file_with_questions.txt"),
            ("", "attachment"),  # Empty filename
            ("   ", "   "),  # Whitespace only - sanitize preserves whitespace
        ]

        for input_filename, expected_output in test_cases:
            sanitized = storage._sanitize_filename(input_filename)
            assert sanitized == expected_output


def test_storage_with_metadata():
    """Test storage with EmailMetadata objects."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Create test metadata
        metadata = EmailMetadata(
            email_id="test123",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            date="2024-01-01",
            folder="inbox",
            attachments=["document.pdf"],
            has_attachments=True,
        )

        # Test saving and loading metadata
        test_index = {"folders": {"inbox": [metadata.dict()]}}

        storage.save_index("test_account", test_index)  # type: ignore[arg-type]
        loaded_index = storage.load_index("test_account")

        assert loaded_index["folders"]["inbox"][0]["email_id"] == "test123"
        assert loaded_index["folders"]["inbox"][0]["subject"] == "Test Subject"
        assert loaded_index["folders"]["inbox"][0]["has_attachments"] is True


def test_email_storage_and_retrieval():
    """Test storing and retrieving email content."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Test email content
        email_content = """From: sender@example.com
To: recipient@example.com
Subject: Test Email

This is a test email body.
"""

        # Store email
        email_path = storage.get_email_path("test_account", "inbox", "email123")
        with open(email_path, "w") as f:
            f.write(email_content)

        # Retrieve email
        with open(email_path, "r") as f:
            retrieved_content = f.read()

        assert retrieved_content == email_content
        assert email_path.exists()


def test_attachment_storage():
    """Test storing attachments."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Test attachment content
        attachment_content = b"This is a test attachment content"

        # Store attachment
        attachment_path = storage.get_attachment_path(
            "test_account", "attach123", "document.pdf"
        )
        with open(attachment_path, "wb") as f:
            f.write(attachment_content)

        # Retrieve attachment
        with open(attachment_path, "rb") as f:
            retrieved_content = f.read()

        assert retrieved_content == attachment_content
        assert attachment_path.exists()
