"""Data models for email-fetch."""

from pydantic import BaseModel


class EmailAccount(BaseModel):
    """Email account configuration."""

    provider: str  # 'gmail' or 'imap'
    username: str
    password: str | None = None  # For basic auth
    access_token: str | None = None  # For OAuth2
    client_id: str | None = None  # For OAuth2 client credentials
    client_secret: str | None = None  # For OAuth2 client credentials
    server: str | None = None  # For IMAP
    port: int = 993  # For IMAP


class EmailMetadata(BaseModel):
    """Email metadata for indexing."""

    email_id: str
    from_address: str
    to_addresses: list[str]
    subject: str
    date: str
    folder: str
    attachments: list[str] = []
    has_attachments: bool = False
    processed: bool = False
