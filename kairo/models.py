"""Data models for email-fetch."""

from typing import List, Dict, Any
from pydantic import BaseModel


class EmailAccount(BaseModel):
    """Email account configuration."""
    provider: str  # 'gmail' or 'imap'
    username: str
    password: str  # In real usage, consider more secure storage
    server: str = None  # For IMAP
    port: int = 993  # For IMAP


class EmailMetadata(BaseModel):
    """Email metadata for indexing."""
    email_id: str
    from_address: str
    to_addresses: List[str]
    subject: str
    date: str
    folder: str
    attachments: List[str] = []
    has_attachments: bool = False


class StorageConfig(BaseModel):
    """Storage configuration."""
    path: str
    structure: str = "flat"  # 'flat' or 'hierarchical'
