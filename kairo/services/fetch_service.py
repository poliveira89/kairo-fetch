"""Fetch service for email retrieval operations."""

from typing import Any, Dict, List, Tuple

import click

from ..config import AccountConfig, Config
from ..retrievers.gmail import GmailRetriever
from ..storage import StorageManager


class FetchService:
    """Service for handling email fetch operations."""

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
    ) -> Tuple[str | None, AccountConfig | dict[str, object] | None]:
        """Find account configuration based on provider and account name."""
        if account:
            # Specific account requested
            account_config = self.config.get_account(account)
            if not account_config:
                click.echo(
                    f"Error: Account '{account}' not found in configuration", err=True
                )
                return None, None
            return account, account_config
        else:
            # Find first account matching the provider
            accounts = self.config.data.get("accounts", {})
            matching_accounts: List[Tuple[str, AccountConfig | dict[str, object]]] = []

            for name, acc in accounts.items():
                # Match by provider field OR by account name matching provider
                if acc.get("provider") == provider or name == provider:
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

    def handle_gmail_authentication(
        self, account: str, account_config: Dict[str, Any]
    ) -> GmailRetriever | None:
        """Handle Gmail authentication and return retriever."""
        username = account_config.get("username")
        password = account_config.get("password")
        access_token = account_config.get("access_token")

        if not username:
            click.echo("Error: Username not configured for account", err=True)
            return None

        # Check if we need to perform OAuth2 flow
        client_id = account_config.get("client_id")
        client_secret = account_config.get("client_secret")

        # Use existing access token if available
        if access_token:
            click.echo("Using OAuth2 authentication with existing token")
            return GmailRetriever(username=username, access_token=access_token)

        # Perform OAuth2 flow if we have client credentials but no token
        elif client_id and client_secret and not access_token:
            click.echo("Performing OAuth2 authentication flow...")

            # Import OAuth2 modules
            import json
            from urllib.parse import urlencode
            from urllib.request import Request, urlopen

            # Step 1: Generate authorization URL
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

            # Step 2: Get authorization code
            auth_code = click.prompt("2. Paste the authorization code")

            # Step 3: Exchange for access token
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

                # Update config with new token
                account_config["access_token"] = access_token
                if refresh_token:
                    account_config["refresh_token"] = refresh_token
                self.config.set_account(account, account_config)  # type: ignore[arg-type]
                self.config.save()

                return GmailRetriever(username=username, access_token=access_token)

            except Exception as e:
                click.echo(f"❌ OAuth2 authentication failed: {e}", err=True)
                return None

        # Use password authentication as fallback
        elif password:
            return GmailRetriever(username=username, password=password)

        else:
            click.echo(
                "Error: No authentication method configured (password or OAuth2)",
                err=True,
            )
            return None

    def fetch_emails(
        self,
        provider: str,
        account: str | None,
        folder: str,
        server: str | None,
        port: int,
        limit: int,
    ) -> None:
        """Main fetch emails method."""
        # Validate requirements
        if not self.validate_imap_requirements(provider, server):
            return

        # Find account configuration
        account_name, account_config = self.find_account_config(provider, account)
        if not account_name or not account_config:
            return

        click.echo(
            f"Fetching emails from {provider} account '{account_name}' folder '{folder}'"
        )

        try:
            if provider == "gmail":
                # Handle Gmail authentication
                retriever = self.handle_gmail_authentication(
                    account_name, account_config  # type: ignore[arg-type]
                )
                if not retriever:
                    return

                # Fetch emails
                click.echo(
                    f"Connecting to Gmail for account: {account_config.get('username')}"
                )
                emails = retriever.fetch_emails(folder=folder.upper(), limit=limit)

                click.echo(f"Successfully fetched {len(emails)} emails")

                # Store emails
                storage = StorageManager(self.config.get_storage_path())
                for email_data in emails:
                    email_id = str(email_data["email_id"])

                    # Check if email is already processed
                    is_processed = storage.is_email_processed(
                        str(account_name), str(folder), email_id
                    )

                    if is_processed:
                        click.echo(f"  Skipping already processed email ID: {email_id}")
                        continue

                    # Save raw email (overwrite if exists - this is the tradeoff)
                    email_path = storage.get_email_path(
                        str(account_name), str(folder), email_id
                    )
                    with open(email_path, "w") as f:
                        f.write(email_data["raw"])

                    # Update index but don't mark as processed yet
                    index = storage.load_index(str(account_name))
                    # Simple index update - just use the loaded index directly
                    # Type checking is complex here but the logic is sound
                    index_dict = index if isinstance(index, dict) else {"folders": {}}
                    if "folders" not in index_dict:  # type: ignore[operator]
                        index_dict["folders"] = {}  # type: ignore[index]
                    if folder not in index_dict["folders"]:  # type: ignore[operator]
                        index_dict["folders"][folder] = []  # type: ignore[index]

                    metadata = retriever.get_email_metadata(email_data)
                    # Set processed=False initially
                    metadata_dict = metadata.dict()
                    metadata_dict["processed"] = False

                    # Check if email already exists in index (partial processing case)
                    existing_emails = index_dict["folders"][folder]  # type: ignore[index]
                    email_already_in_index = False
                    for i, existing_email in enumerate(existing_emails):
                        if existing_email.get("email_id") == email_id:
                            # Overwrite existing entry (tradeoff: force overwrite)
                            existing_emails[i] = metadata_dict
                            email_already_in_index = True
                            break

                    if not email_already_in_index:
                        existing_emails.append(metadata_dict)

                    storage.save_index(str(account_name), index_dict)  # type: ignore[arg-type]

                    click.echo(
                        f"  Saved email: {email_data['subject']} (ID: {email_id})"
                    )

                    # Mark this email as processed immediately after successful processing
                    index = storage.load_index(str(account_name))
                    if "folders" in index and folder in index["folders"]:
                        for email_metadata in index["folders"][folder]:
                            if email_metadata.get("email_id") == email_id:
                                email_metadata["processed"] = True
                                break
                    storage.save_index(str(account_name), index)  # type: ignore[arg-type]
            elif provider == "imap":
                # TODO: Implement IMAP retrieval
                click.echo("IMAP provider not yet implemented")

            click.echo("Email fetch completed successfully!")

        except Exception as e:
            click.echo(f"Error fetching emails: {e}", err=True)
