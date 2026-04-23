"""Storage management for email-fetch."""

import json
from pathlib import Path
from typing import Any, TypedDict


class IndexData(TypedDict):
    """Type for index data."""

    folders: dict[str, list[dict[str, Any]]]


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
        index = self.load_index(account_name)
        if "folders" not in index:
            return False

        folder_emails = index["folders"].get(folder, [])
        for email_metadata in folder_emails:
            if email_metadata.get("email_id") == email_id:
                return email_metadata.get("processed", False)
        return False

    def get_attachment_path(
        self, account_name: str, attachment_id: str, original_filename: str
    ) -> Path:
        """Get path for specific attachment."""
        account_path = self.get_account_path(account_name)
        attachments_path = account_path / "attachments"
        attachments_path.mkdir(exist_ok=True)
        # Use original filename but ensure it's safe
        safe_filename = self._sanitize_filename(original_filename)
        return attachments_path / f"{attachment_id}_{safe_filename}"

    def get_index_path(self, account_name: str) -> Path:
        """Get path for account index file."""
        account_path = self.get_account_path(account_name)
        return account_path / "index.json"

    def load_index(self, account_name: str) -> IndexData:
        """Load index for account."""
        index_path = self.get_index_path(account_name)
        try:
            with open(index_path, "r") as f:
                return json.load(f)  # type: ignore[return-value]
        except (FileNotFoundError, json.JSONDecodeError):
            return {"folders": {}}

    def save_index(self, account_name: str, index_data: IndexData) -> None:
        """Save index for account."""
        index_path = self.get_index_path(account_name)
        with open(index_path, "w") as f:
            json.dump(index_data, f, indent=2)

    def _sanitize_filename(self, filename: str) -> str:
        """Make filename safe for storage."""
        # Remove invalid characters
        safe_chars = "-_.() []{}"
        sanitized = "".join(
            c if c.isalnum() or c in safe_chars else "_" for c in filename
        )
        # Ensure it's not empty
        return sanitized if sanitized else "attachment"

    def __repr__(self) -> str:
        return f"StorageManager(base_path={self.base_path})"
