"""Fetch service for email retrieval operations."""

from typing import Any, Dict, List, Tuple

import click

from ..config import AccountConfig, Config
from ..retrievers.gmail import GmailRetriever
from ..storage import StorageManager


class EmailProcessor:
    """Handles processing of individual emails."""

    def __init__(self, storage: StorageManager, retriever: Any):
        self.storage = storage
        self.retriever = retriever

    def process_email(
        self, account_name: str, folder: str, email_data: Dict[str, Any]
    ) -> bool:
        """Process a single email and return True if successful."""
        email_id = str(email_data["email_id"])

        email_path = self.storage.get_email_path(
            str(account_name), str(folder), email_id
        )
        with open(email_path, "w") as f:
            f.write(email_data["raw"])

        index = self.storage.load_index(str(account_name))

        metadata = self.retriever.get_email_metadata(email_data)

        email_already_in_index = index.is_email_processed(folder, email_id)
        if not email_already_in_index:
            index.add(folder, metadata)

        self.storage.save_index(str(account_name), index)

        click.echo(f"  Saved email: {email_data['subject']} (ID: {email_id})")

        return True


class AccountFinder:
    """Handles finding and validating account configurations."""

    def __init__(self, config: Config):
        self.config = config

    def validate_imap_requirements(self, provider: str, server: str | None) -> bool:
        """Validate IMAP provider requirements."""
        if provider == "imap" and not server:
            click.echo("Error: --server is required for IMAP provider", err=True)
            return False
        return True

    def find_account_config(
        self, provider: str, account: str | None
    ) -> Tuple[str | None, AccountConfig | None]:
        """Find account configuration based on provider and account name."""
        if account:
            account_config = self.config.get_account(account)
            if not account_config:
                click.echo(
                    f"Error: Account '{account}' not found in configuration", err=True
                )
                return None, None
            return account, account_config
        else:
            accounts = self.config.data.accounts
            matching_accounts: List[Tuple[str, AccountConfig]] = []

            for name, acc in accounts.items():
                if acc.provider == provider or name == provider:
                    matching_accounts.append((name, acc))

            if not matching_accounts:
                click.echo(
                    f"Error: No {provider} accounts configured. Please add an account to config or specify --account",
                    err=True,
                )
                return None, None

            if len(matching_accounts) > 1:
                account_names = [name for name, _ in matching_accounts]
                click.echo(
                    f"Multiple {provider} accounts found: {', '.join(account_names)}"
                )
                click.echo(f"Using first account: {matching_accounts[0][0]}")

            return matching_accounts[0][0], matching_accounts[0][1]


class GmailAuthenticator:
    """Handles Gmail authentication."""

    def __init__(self, config: Config):
        self.config = config

    def authenticate(
        self, account: str, account_config: AccountConfig
    ) -> GmailRetriever | None:
        """Handle Gmail authentication and return retriever."""
        username = account_config.username
        password = account_config.password
        access_token = account_config.access_token

        if not username:
            click.echo("Error: Username not configured for account", err=True)
            return None

        client_id = account_config.client_id
        client_secret = account_config.client_secret

        if access_token:
            click.echo("Using OAuth2 authentication with existing token")
            return GmailRetriever(username=username, access_token=access_token)

        elif client_id and client_secret and not access_token:
            click.echo("Performing OAuth2 authentication flow...")

            import json
            from urllib.parse import urlencode
            from urllib.request import Request, urlopen

            auth_url = "https://accounts.google.com/o/oauth2/auth?" + urlencode(
                {
                    "client_id": client_id,
                    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                    "scope": "https://mail.google.com/",
                    "response_type": "code",
                }
            )

            click.echo("1. Visit this URL to authorize:")
            click.echo(f"   {auth_url}")

            auth_code = click.prompt("2. Paste the authorization code")

            click.echo("3. Exchanging code for access token...")

            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": auth_code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                "grant_type": "authorization_code",
            }

            try:
                token_request = Request(token_url, data=urlencode(token_data).encode())
                token_response = urlopen(token_request).read().decode()
                token_data = json.loads(token_response)
                access_token = token_data["access_token"]
                refresh_token = token_data.get("refresh_token")

                click.echo("✅ OAuth2 authentication successful!")

                # Create a new account config with updated tokens
                updated_account_config = AccountConfig(
                    provider=account_config.provider,
                    username=account_config.username,
                    password=account_config.password,
                    access_token=access_token,
                    client_id=account_config.client_id,
                    client_secret=account_config.client_secret,
                    server=account_config.server,
                    refresh_token=refresh_token or account_config.refresh_token,
                    port=account_config.port,
                )
                self.config.set_account(account, updated_account_config)
                self.config.save()

                return GmailRetriever(username=username, access_token=access_token)

            except Exception as e:
                click.echo(f"❌ OAuth2 authentication failed: {e}", err=True)
                return None

        elif password:
            return GmailRetriever(username=username, password=password)

        else:
            click.echo(
                "Error: No authentication method configured (password or OAuth2)",
                err=True,
            )
            return None


class EmailFetchService:
    """Service for handling email fetch operations."""

    def __init__(self, config: Config):
        self.config = config
        self.account_finder = AccountFinder(config)
        self.gmail_authenticator = GmailAuthenticator(config)

    def fetch_emails(
        self,
        provider: str,
        account: str | None,
        folder: str,
        server: str | None,
        limit: int,
    ) -> None:
        """Main fetch emails method."""
        if not self.account_finder.validate_imap_requirements(provider, server):
            return

        account_name, account_config = self.account_finder.find_account_config(
            provider, account
        )
        if not account_name or not account_config:
            return

        click.echo(
            f"Fetching emails from {provider} account '{account_name}' folder '{folder}'"
        )

        try:
            if provider == "gmail":
                retriever = self.gmail_authenticator.authenticate(
                    account_name, account_config
                )
                if not retriever:
                    return

                storage = StorageManager(self.config.get_storage_path())
                email_processor = EmailProcessor(storage, retriever)
                processed_count = 0

                click.echo(
                    f"Connecting to Gmail for account: {account_config.username}"
                )

                emails = retriever.fetch_emails(folder=folder.upper())

                if not emails:
                    return

                click.echo(
                    f"Fetched {len(emails)} emails, looking for unprocessed ones..."
                )

                for email_data in emails:
                    email_id = str(email_data["email_id"])

                    is_processed = storage.is_email_processed(
                        str(account_name), str(folder), email_id
                    )

                    if is_processed:
                        click.echo(f"  Skipping already processed email ID: {email_id}")
                        continue

                    if processed_count >= limit:
                        break

                    email_processor.process_email(account_name, folder, email_data)

                    index = storage.load_index(str(account_name))
                    if index.mark_email_as_processed(folder, email_id):
                        storage.save_index(str(account_name), index)

                    processed_count += 1

                click.echo(f"Processed {processed_count} emails (limit: {limit})")
            elif provider == "imap":
                # TODO: Implement IMAP retrieval
                click.echo("IMAP provider not yet implemented")

            click.echo("Email fetch completed successfully!")

        except Exception as e:
            click.echo(f"Error fetching emails: {e}", err=True)


# Main service class for backward compatibility
class FetchService(EmailFetchService):
    """Service for handling email fetch operations."""

    pass
