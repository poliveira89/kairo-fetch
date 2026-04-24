"""Tests for storage functionality."""

import tempfile
from pathlib import Path

from kairo.models import EmailMetadata
from kairo.storage import IndexEmailMetadata, IndexManager, StorageManager


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

        index_manager = storage.load_index("test_account")

        # Should return default empty index
        assert isinstance(index_manager, IndexManager)
        assert index_manager.to_dict() == {"folders": {}}


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
                        "to_addresses": [],
                        "date": "",
                        "folder": "inbox",
                        "attachments": [],
                        "has_attachments": False,
                        "processed": False,
                    }
                ]
            }
        }

        import json

        with open(index_path, "w") as f:
            json.dump(test_index, f)

        # Load the index
        loaded_index_manager = storage.load_index("test_account")

        assert isinstance(loaded_index_manager, IndexManager)
        assert loaded_index_manager.to_dict() == test_index
        assert (
            loaded_index_manager.to_dict()["folders"]["inbox"][0]["subject"]
            == "Test Email"
        )


def test_save_index():
    """Test saving index."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Create test index data
        test_index_dict = {
            "folders": {
                "inbox": [
                    {
                        "email_id": "123",
                        "subject": "Test Email",
                        "from_address": "test@example.com",
                        "to_addresses": [],
                        "date": "",
                        "folder": "inbox",
                        "attachments": [],
                        "has_attachments": False,
                        "processed": False,
                    }
                ]
            }
        }
        test_index_manager = IndexManager.load_from_dict(test_index_dict)

        # Save the index
        storage.save_index("test_account", test_index_manager)

        # Verify it was saved
        index_path = storage.get_index_path("test_account")
        assert index_path.exists()

        # Load and verify
        import json

        with open(index_path, "r") as f:
            saved_index = json.load(f)

        assert saved_index == test_index_dict


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
            processed=False,
        )

        # Test saving and loading metadata
        test_index_dict = {"folders": {"inbox": [metadata.dict()]}}
        test_index_manager = IndexManager.load_from_dict(test_index_dict)

        storage.save_index("test_account", test_index_manager)
        loaded_index_manager = storage.load_index("test_account")

        assert (
            loaded_index_manager.to_dict()["folders"]["inbox"][0]["email_id"]
            == "test123"
        )
        assert (
            loaded_index_manager.to_dict()["folders"]["inbox"][0]["subject"]
            == "Test Subject"
        )
        assert (
            loaded_index_manager.to_dict()["folders"]["inbox"][0]["has_attachments"]
            is True
        )
        assert (
            loaded_index_manager.to_dict()["folders"]["inbox"][0]["processed"] is False
        )


def test_is_email_processed():
    """Test checking if email is processed."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Create test index with processed and unprocessed emails
        test_index_dict = {
            "folders": {
                "inbox": [
                    {
                        "email_id": "123",
                        "subject": "Processed Email",
                        "from_address": "test@example.com",
                        "processed": True,
                    },
                    {
                        "email_id": "456",
                        "subject": "Unprocessed Email",
                        "from_address": "test@example.com",
                        "processed": False,
                    },
                ]
            }
        }
        test_index_manager = IndexManager.load_from_dict(test_index_dict)

        storage.save_index("test_account", test_index_manager)

        # Test checking processed status
        assert storage.is_email_processed("test_account", "inbox", "123") is True
        assert storage.is_email_processed("test_account", "inbox", "456") is False
        assert storage.is_email_processed("test_account", "inbox", "999") is False
        assert storage.is_email_processed("test_account", "sent", "123") is False


def test_email_exists():
    """Test checking if email exists in index."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)

        # Create test index
        test_index_dict = {
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
        test_index_manager = IndexManager.load_from_dict(test_index_dict)
        storage.save_index("test_account", test_index_manager)

        # Test email existence
        assert test_index_manager.email_exists("inbox", "123") is True
        assert test_index_manager.email_exists("inbox", "999") is False
        assert test_index_manager.email_exists("sent", "123") is False


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


def test_index_manager_to_dict():
    """Test IndexManager to_dict method."""
    index_manager = IndexManager.create_empty()
    index_dict = index_manager.to_dict()
    assert index_dict == {"folders": {}}


def test_index_manager_load_from_dict():
    """Test IndexManager load_from_dict method."""
    index_dict = {
        "folders": {
            "inbox": [
                {
                    "email_id": "123",
                    "subject": "Test Email",
                    "from_address": "test@example.com",
                    "to_addresses": ["recipient@example.com"],
                    "date": "2024-01-01",
                    "folder": "inbox",
                    "attachments": [],
                    "has_attachments": False,
                    "processed": False,
                }
            ]
        }
    }
    index_manager = IndexManager.load_from_dict(index_dict)
    assert index_manager.to_dict() == index_dict


def test_index_manager_add_update():
    """Test IndexManager add method updates existing email."""
    index_manager = IndexManager.create_empty()

    # Add initial email
    email_metadata: IndexEmailMetadata = IndexEmailMetadata(
        email_id="123",
        subject="Original Subject",
        from_address="test@example.com",
        to_addresses=["recipient@example.com"],
        date="2024-01-01",
        folder="inbox",
        attachments=[],
        has_attachments=False,
        processed=False,
    )
    index_manager.add("inbox", email_metadata)

    # Update the same email
    updated_metadata: IndexEmailMetadata = IndexEmailMetadata(
        email_id="123",
        subject="Updated Subject",
        from_address="test@example.com",
        to_addresses=["recipient@example.com"],
        date="2024-01-01",
        folder="inbox",
        attachments=[],
        has_attachments=False,
        processed=True,
    )
    index_manager.add("inbox", updated_metadata)

    # Verify update
    emails = index_manager.get_emails_in_folder("inbox")
    assert len(emails) == 1
    assert emails[0].subject == "Updated Subject"
    assert emails[0].processed is True


def test_index_manager_mark_email_as_processed():
    """Test IndexManager mark_email_as_processed method."""
    index_manager = IndexManager.create_empty()

    # Add email
    email_metadata: IndexEmailMetadata = IndexEmailMetadata(
        email_id="123",
        subject="Test Email",
        from_address="test@example.com",
        to_addresses=["recipient@example.com"],
        date="2024-01-01",
        folder="inbox",
        attachments=[],
        has_attachments=False,
        processed=False,
    )
    index_manager.add("inbox", email_metadata)

    # Mark as processed
    result = index_manager.mark_email_as_processed("inbox", "123")
    assert result is True

    # Verify it was marked as processed
    emails = index_manager.get_emails_in_folder("inbox")
    assert emails[0].processed is True


def test_index_manager_mark_nonexistent_email():
    """Test IndexManager mark_email_as_processed with non-existent email."""
    index_manager = IndexManager.create_empty()
    result = index_manager.mark_email_as_processed("inbox", "999")
    assert result is False


def test_index_manager_get_unprocessed_emails():
    """Test IndexManager get_unprocessed_emails method."""
    index_manager = IndexManager.create_empty()

    # Add processed and unprocessed emails
    processed_email: IndexEmailMetadata = IndexEmailMetadata(
        email_id="123",
        subject="Processed Email",
        from_address="test@example.com",
        to_addresses=["recipient@example.com"],
        date="2024-01-01",
        folder="inbox",
        attachments=[],
        has_attachments=False,
        processed=True,
    )
    unprocessed_email: IndexEmailMetadata = IndexEmailMetadata(
        email_id="456",
        subject="Unprocessed Email",
        from_address="test@example.com",
        to_addresses=["recipient@example.com"],
        date="2024-01-01",
        folder="inbox",
        attachments=[],
        has_attachments=False,
        processed=False,
    )
    index_manager.add("inbox", processed_email)
    index_manager.add("inbox", unprocessed_email)

    # Get unprocessed emails
    unprocessed = index_manager.get_unprocessed_emails("inbox")
    assert len(unprocessed) == 1
    assert unprocessed[0].email_id == "456"
    assert unprocessed[0].processed is False


def test_index_manager_ensure_folder_exists():
    """Test IndexManager ensure_folder_exists method."""
    index_manager = IndexManager.create_empty()

    # Ensure folder exists
    index_manager.ensure_folder_exists("new_folder")
    assert "new_folder" in index_manager.to_dict()["folders"]
    assert index_manager.to_dict()["folders"]["new_folder"] == []


def test_index_manager_get_folders():
    """Test IndexManager get_folders method."""
    index_manager = IndexManager.create_empty()

    # Add emails to different folders
    index_manager.add(
        "inbox",
        IndexEmailMetadata(
            email_id="123",
            subject="Test",
            from_address="test@example.com",
            to_addresses=[],
            date="2024-01-01",
            folder="inbox",
            attachments=[],
            has_attachments=False,
            processed=False,
        ),
    )

    folders = index_manager.get_folders()
    assert "inbox" in folders
    assert len(folders["inbox"]) == 1


def test_index_manager_get_folder():
    """Test IndexManager get_folder method."""
    index_manager = IndexManager.create_empty()

    # Get folder that doesn't exist (should create it)
    folder = index_manager.get_folder("new_folder")
    assert folder == []
    assert "new_folder" in index_manager.to_dict()["folders"]


def test_storage_manager_repr():
    """Test StorageManager __repr__ method."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = StorageManager(temp_dir)
        repr_str = repr(storage)
        assert "StorageManager(" in repr_str
        assert "base_path=" in repr_str
        assert ")" in repr_str


def test_index_manager_load_from_dict_with_missing_folders():
    """Test IndexManager.load_from_dict with missing folders key."""
    # Test the case where index_dict doesn't have 'folders' key
    index_dict = {}  # Missing 'folders' key
    index_manager = IndexManager.load_from_dict(index_dict)

    # Should create empty folders dict
    assert index_manager.to_dict() == {"folders": {}}
