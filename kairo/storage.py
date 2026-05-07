"""Storage management for email-fetch."""

import json
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel

from kairo import log


class IndexEmailMetadata(BaseModel):
    """Email metadata stored in index."""

    email_id: str
    from_address: str
    to_addresses: List[str]
    subject: str
    date: str
    folder: str
    attachments: List[str]
    has_attachments: bool
    processed: bool


class IndexFolderData(BaseModel):
    """Folder data stored in index."""

    emails: List[IndexEmailMetadata]


class IndexData(BaseModel):
    """Complete index data structure."""

    folders: Dict[str, List[IndexEmailMetadata]]


class IndexManager:
    """OOP abstraction for managing email index."""

    def __init__(self, index_data: IndexData):
        self._index_data = index_data

    @classmethod
    def create_empty(cls) -> "IndexManager":
        """Create empty IndexManager with default structure."""
        return cls(IndexData(folders={}))

    @classmethod
    def load_from_dict(cls, index_dict: dict) -> "IndexManager":
        """Create IndexManager from raw dictionary."""
        if "folders" not in index_dict:
            index_dict["folders"] = {}

        # Convert old format to new format for backward compatibility
        validated_folders = {}
        for folder_name, emails in index_dict["folders"].items():
            validated_emails = []
            for email_data in emails:
                if not isinstance(email_data, dict):
                    log.warning(
                        f"Skip invalid email: non-dict type {type(email_data).__name__}"
                    )
                    continue

                try:
                    validated_email = IndexEmailMetadata(
                        email_id=email_data.get("email_id", ""),
                        from_address=email_data.get("from_address", ""),
                        to_addresses=email_data.get("to_addresses", []),
                        subject=email_data.get("subject", ""),
                        date=email_data.get("date", ""),
                        folder=email_data.get("folder", folder_name),
                        attachments=email_data.get("attachments", []),
                        has_attachments=email_data.get("has_attachments", False),
                        processed=email_data.get("processed", False),
                    )
                    validated_emails.append(validated_email)
                except Exception as e:
                    from_address = email_data.get("from_address", "")
                    log.exception(f"Skip invalid email: {from_address}")
                    continue
            validated_folders[folder_name] = validated_emails

        index_data = IndexData(folders=validated_folders)
        return cls(index_data)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return self._index_data.dict()

    def get_emails_in_folder(self, folder: str) -> List[IndexEmailMetadata]:
        """Get all emails in a specific folder."""
        return self._index_data.folders.get(folder, [])

    def email_exists(self, folder: str, email_id: str) -> bool:
        """Check if email with given ID exists in folder."""
        folder_emails = self.get_emails_in_folder(folder)
        return any(email.email_id == email_id for email in folder_emails)

    def is_email_processed(self, folder: str, email_id: str) -> bool:
        """Check if email is marked as processed."""
        folder_emails = self.get_emails_in_folder(folder)
        for email_metadata in folder_emails:
            if email_metadata.email_id == email_id:
                return email_metadata.processed
        return False

    def add(self, folder: str, email_metadata: IndexEmailMetadata) -> None:
        """Add or update email in index."""
        self.ensure_folder_exists(folder)

        existing_emails = self._index_data.folders[folder]
        email_already_in_index = False
        for i, existing_email in enumerate(existing_emails):
            if existing_email.email_id == email_metadata.email_id:
                existing_emails[i] = email_metadata
                email_already_in_index = True
                break

        if not email_already_in_index:
            existing_emails.append(email_metadata)

    def mark_email_as_processed(self, folder: str, email_id: str) -> bool:
        """Mark email as processed. Returns True if found and updated."""
        folder_emails = self.get_emails_in_folder(folder)
        for email_metadata in folder_emails:
            if email_metadata.email_id == email_id:
                email_metadata.processed = True
                return True
        return False

    def get_unprocessed_emails(self, folder: str) -> List[IndexEmailMetadata]:
        """Get only unprocessed emails from a folder."""
        return [
            email for email in self.get_emails_in_folder(folder) if not email.processed
        ]

    def ensure_folder_exists(self, folder: str) -> None:
        """Ensure folder exists in index, create if not."""
        if folder not in self._index_data.folders:
            self._index_data.folders[folder] = []

    def get_folders(self):
        return self._index_data.folders

    def get_folder(self, folder: str):
        self.ensure_folder_exists(folder)
        return self._index_data.folders[folder]


class StorageManager:
    """Handles email and attachment storage."""

    def __init__(self, base_path: str):
        self.base_path: Path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_account_path(self, account_name: str) -> Path:
        """Get path for specific account."""
        account_path = self.base_path / account_name
        account_path.mkdir(exist_ok=True)
        return account_path

    def get_email_path(self, account_name: str, folder: str, email_id: str) -> Path:
        """Get path for specific email."""
        account_path = self.get_account_path(account_name)
        folder_path = account_path / "emails" / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path / f"{email_id}.eml"

    def is_email_processed(self, account_name: str, folder: str, email_id: str) -> bool:
        """Check if email is marked as processed in index."""
        index_manager = self.load_index(account_name)
        return index_manager.is_email_processed(folder, email_id)

    def get_attachment_path(
        self, account_name: str, attachment_id: str, original_filename: str
    ) -> Path:
        """Get path for specific attachment."""
        account_path = self.get_account_path(account_name)
        attachments_path = account_path / "attachments"
        attachments_path.mkdir(exist_ok=True)
        safe_filename = self._sanitize_filename(original_filename)
        return attachments_path / f"{attachment_id}_{safe_filename}"

    def get_index_path(self, account_name: str) -> Path:
        """Get path for account index file."""
        account_path = self.get_account_path(account_name)
        return account_path / "index.json"

    def load_index(self, account_name: str) -> IndexManager:
        """Load index for account."""
        index_path = self.get_index_path(account_name)
        try:
            with open(index_path, "r") as f:
                index_dict = json.load(f)
                return IndexManager.load_from_dict(index_dict)
        except (FileNotFoundError, json.JSONDecodeError):
            return IndexManager.create_empty()

    def save_index(self, account_name: str, index_manager: IndexManager) -> None:
        """Save index for account."""
        index_path = self.get_index_path(account_name)
        with open(index_path, "w") as f:
            json.dump(index_manager.to_dict(), f, indent=2)

    def _sanitize_filename(self, filename: str) -> str:
        """Make filename safe for storage."""
        safe_chars = "-_.() []{}"
        sanitized = "".join(
            c if c.isalnum() or c in safe_chars else "_" for c in filename
        )
        return sanitized if sanitized else "attachment"

    def __repr__(self) -> str:
        return f"StorageManager(base_path={self.base_path})"
