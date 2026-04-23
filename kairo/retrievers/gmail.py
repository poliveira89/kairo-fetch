"""Gmail email retriever using IMAP."""

import email
import email.policy
import imaplib
from typing import Any, Dict, List

from ..models import EmailMetadata


class GmailRetriever:
    """Retrieve emails from Gmail using IMAP."""

    def __init__(
        self,
        username: str,
        password: str | None = None,
        access_token: str | None = None,
    ):
        """Initialize Gmail retriever.

        Args:
            username: Gmail username/email
            password: Gmail password (for basic auth)
            access_token: OAuth2 access token (for OAuth2 auth)
        """
        self.username = username
        self.password = password
        self.access_token = access_token
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993

    def connect(self) -> imaplib.IMAP4_SSL:
        """Connect to Gmail IMAP server."""
        imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)

        if self.access_token:
            # Use OAuth2 authentication
            auth_string = (
                f"user={self.username}\x01auth=Bearer {self.access_token}\x01\x01"
            )
            imap.authenticate("XOAUTH2", lambda x: auth_string.encode())
        else:
            # Use basic authentication
            if self.password:
                imap.login(self.username, self.password)
            else:
                raise ValueError("No password provided for basic authentication")

        return imap

    def fetch_emails(
        self, folder: str = "INBOX", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch emails from specified folder.

        Args:
            folder: Folder/label to fetch from
            limit: Maximum number of emails to fetch

        Returns:
            List of email data dictionaries
        """
        emails = []

        try:
            imap = self.connect()

            # Select the mailbox
            status, _ = imap.select(folder)
            if status != "OK":
                raise Exception(f"Failed to select folder: {folder}")

            # Search for all emails
            status, messages = imap.search(None, "ALL")
            if status != "OK":
                raise Exception("Failed to search emails")

            email_ids = messages[0].split()

            # Fetch the most recent emails (up to limit)
            for email_id in email_ids[-limit:]:
                status, msg_data = imap.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue

                if not msg_data or len(msg_data) == 0:
                    continue
                msg_part = msg_data[0]
                if not isinstance(msg_part, (list, tuple)) or len(msg_part) < 2:
                    continue
                raw_email = msg_part[1]
                if raw_email is None:
                    continue
                if isinstance(raw_email, bytes):
                    email_message = email.message_from_bytes(
                        raw_email, policy=email.policy.default
                    )
                else:
                    email_message = email.message_from_string(
                        str(raw_email), policy=email.policy.default
                    )

                email_data = self._parse_email(email_message, str(email_id))
                emails.append(email_data)

            imap.close()
            imap.logout()

        except Exception as e:
            print(f"Error fetching emails: {e}")
            raise

        return emails

    def _parse_email(self, email_message: Any, email_id: str) -> Dict[str, Any]:
        """Parse email message into structured data."""
        subject = email_message["subject"] or "No Subject"
        from_address = email_message["from"] or "Unknown Sender"
        to_addresses = email_message["to"] or ""
        date = email_message["date"] or "Unknown Date"

        # Parse to addresses
        if isinstance(to_addresses, str):
            to_addresses = [addr.strip() for addr in to_addresses.split(",")]

        # Check for attachments
        attachments = []
        has_attachments = False

        for part in email_message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            content_disposition = part.get("Content-Disposition")
            if content_disposition is None:
                continue

            filename = part.get_filename()
            if filename:
                attachments.append(filename)
                has_attachments = True

        return {
            "email_id": email_id,
            "from_address": from_address,
            "to_addresses": to_addresses,
            "subject": subject,
            "date": date,
            "folder": email_message["X-GM-LABELS"] or "INBOX",
            "attachments": attachments,
            "has_attachments": has_attachments,
            "raw": email_message.as_string(),
        }

    def get_email_metadata(self, email_data: Dict[str, Any]) -> EmailMetadata:
        """Convert email data to EmailMetadata model."""
        return EmailMetadata(
            email_id=email_data["email_id"],
            from_address=email_data["from_address"],
            to_addresses=email_data["to_addresses"],
            subject=email_data["subject"],
            date=email_data["date"],
            folder=email_data["folder"],
            attachments=email_data["attachments"],
            has_attachments=email_data["has_attachments"],
            processed=False,
        )
