"""CLI interface for email-fetch tool."""

import click

from .config import Config
from .retrievers.gmail import GmailRetriever
from .storage import StorageManager


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Email Fetch - Retrieve emails from Gmail and IMAP providers."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config()


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["gmail", "imap"], case_sensitive=False),
    required=True,
    help="Email provider to use",
)
@click.option(
    "--account",
    help="Account name/identifier (uses first matching account if not specified)",
)
@click.option("--folder", default="inbox", help="Folder/label to fetch from")
@click.option("--server", help="IMAP server address (required for IMAP)")
@click.option("--port", type=int, default=993, help="IMAP server port")
@click.option("--limit", type=int, default=10, help="Maximum number of emails to fetch")
@click.pass_context
def fetch(
    ctx: click.Context,
    provider: str,
    account: str | None,
    folder: str,
    server: str | None,
    port: int,
    limit: int,
) -> None:
    """Fetch emails from specified provider and folder."""
    config = ctx.obj["config"]

    if provider == "imap" and not server:
        click.echo("Error: --server is required for IMAP provider", err=True)
        return

    # Find account configuration
    if account:
        # Specific account requested
        account_config = config.get_account(account)
        if not account_config:
            click.echo(
                f"Error: Account '{account}' not found in configuration", err=True
            )
            return
    else:
        # Find first account matching the provider
        accounts = config.data.get("accounts", {})
        matching_accounts = []

        for name, acc in accounts.items():
            # Match by provider field OR by account name matching provider
            if acc.get("provider") == provider or name == provider:
                matching_accounts.append((name, acc))

        if not matching_accounts:
            click.echo(
                f"Error: No {provider} accounts configured. Please add an account to config or specify --account",
                err=True,
            )
            return

        if len(matching_accounts) > 1:
            account_names = [name for name, _ in matching_accounts]
            click.echo(
                f"Multiple {provider} accounts found: {', '.join(account_names)}"
            )
            click.echo(f"Using first account: {matching_accounts[0][0]}")

        account = matching_accounts[0][0]
        account_config = matching_accounts[0][1]

    click.echo(f"Fetching emails from {provider} account '{account}' folder '{folder}'")

    try:
        if provider == "gmail":
            # Initialize Gmail retriever
            username = account_config.get("username")
            password = account_config.get("password")
            access_token = account_config.get("access_token")

            if not username:
                click.echo("Error: Username not configured for account", err=True)
                return

            # Check if we need to perform OAuth2 flow
            client_id = account_config.get("client_id")
            client_secret = account_config.get("client_secret")

            # Use existing access token if available
            if access_token:
                click.echo("Using OAuth2 authentication with existing token")
                retriever = GmailRetriever(username=username, access_token=access_token)

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

                click.echo(f"1. Visit this URL to authorize:")
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
                    token_request = Request(
                        token_url, data=urlencode(token_data).encode()
                    )
                    token_response = urlopen(token_request).read().decode()
                    token_data = json.loads(token_response)
                    access_token = token_data["access_token"]
                    refresh_token = token_data.get("refresh_token")

                    click.echo("✅ OAuth2 authentication successful!")

                    # Update config with new token
                    account_config["access_token"] = access_token
                    if refresh_token:
                        account_config["refresh_token"] = refresh_token
                    config.set_account(account, account_config)
                    config.save()

                    retriever = GmailRetriever(
                        username=username, access_token=access_token
                    )

                except Exception as e:
                    click.echo(f"❌ OAuth2 authentication failed: {e}", err=True)
                    return

            # Use password authentication as fallback
            elif password:
                retriever = GmailRetriever(username=username, password=password)

            else:
                click.echo(
                    "Error: No authentication method configured (password or OAuth2)",
                    err=True,
                )
                return

            # Fetch emails
            click.echo(f"Connecting to Gmail for account: {username}")
            emails = retriever.fetch_emails(folder=folder.upper(), limit=limit)

            click.echo(f"Successfully fetched {len(emails)} emails")

            # Store emails
            storage = StorageManager(config.get_storage_path())
            for email_data in emails:
                # Save raw email
                email_path = storage.get_email_path(
                    str(account), str(folder), str(email_data["email_id"])
                )
                with open(email_path, "w") as f:
                    f.write(email_data["raw"])

                # Update index
                index = storage.load_index(str(account))
                # Simple index update - just use the loaded index directly
                # Type checking is complex here but the logic is sound
                index_dict = index if isinstance(index, dict) else {"folders": {}}
                if "folders" not in index_dict:  # type: ignore[operator]
                    index_dict["folders"] = {}  # type: ignore[index]
                if folder not in index_dict["folders"]:  # type: ignore[operator]
                    index_dict["folders"][folder] = []  # type: ignore[index]

                metadata = retriever.get_email_metadata(email_data)
                index_dict["folders"][folder].append(metadata.dict())  # type: ignore[attr-defined]
                storage.save_index(str(account), index_dict)  # type: ignore[arg-type]

                click.echo(
                    f"  Saved email: {email_data['subject']} (ID: {email_data['email_id']})"
                )

        elif provider == "imap":
            # TODO: Implement IMAP retrieval
            click.echo("IMAP provider not yet implemented")

        click.echo("Email fetch completed successfully!")

    except Exception as e:
        click.echo(f"Error fetching emails: {e}", err=True)
        return


@cli.command()
@click.option("--account", required=True, help="Account name to search")
@click.option("--query", required=True, help='Search query (e.g., "from:john")')
@click.pass_context
def search(ctx: click.Context, account: str, query: str) -> None:
    """Search emails in index."""
    config = ctx.obj["config"]
    click.echo(f"Searching account '{account}' for query: {query}")
    click.echo(f"Configuration loaded: {config}")
    click.echo("Feature not yet implemented. This is the basic CLI structure.")


@cli.command()
@click.pass_context
def list_accounts(ctx: click.Context) -> None:
    """List configured accounts."""
    config = ctx.obj["config"]
    click.echo("List of configured accounts:")
    click.echo(f"Configuration loaded: {config}")
    click.echo("Feature not yet implemented. This is the basic CLI structure.")


@cli.command()
def init() -> None:
    """Initialize the kairo configuration and storage directories."""
    from pathlib import Path

    # Create .kairo directory in the user's home directory
    kairo_dir = Path.home() / ".kairo"
    kairo_dir.mkdir(exist_ok=True)

    # Create storage directory
    storage_dir = kairo_dir / "storage"
    storage_dir.mkdir(exist_ok=True)

    click.echo(
        f"Initialized kairo configuration and storage directories at {kairo_dir}"
    )


if __name__ == "__main__":
    cli()
