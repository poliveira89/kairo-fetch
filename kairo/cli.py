"""CLI interface for email-fetch tool."""

from sys import argv

import click

from .config import Config
from .logging import setup_logging
from .services.accounts_service import AccountsService
from .services.fetch_service import FetchService
from .services.init_service import InitService
from .services.search_service import SearchService


@click.group()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output (DEBUG level logging).",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Enable quiet mode (WARNING level logging).",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Email Fetch - Retrieve emails from Gmail and IMAP providers."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config()

    verbose = ctx.params.get("verbose", False)
    quiet = ctx.params.get("quiet", False)

    if verbose:
        log_level = "DEBUG"
    elif quiet:
        log_level = "WARNING"
    else:
        log_level = "INFO"

    setup_logging(log_level)


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
@click.option("--limit", type=int, default=10, help="Maximum number of emails to fetch")
@click.pass_context
def fetch(
    ctx: click.Context,
    provider: str,
    account: str | None,
    folder: str,
    server: str | None,
    limit: int,
) -> None:
    """Fetch emails from specified provider and folder."""
    config = ctx.obj["config"]
    fetch_service = FetchService(config)
    fetch_service.fetch_emails(provider, account, folder, server, limit)


@cli.command()
@click.option("--account", required=True, help="Account name to search")
@click.option("--query", required=True, help='Search query (e.g., "from:john")')
@click.pass_context
def search(ctx: click.Context, account: str, query: str) -> None:
    """Search emails in index."""
    config = ctx.obj["config"]
    search_service = SearchService(config)
    search_service.search_emails(account, query)


@cli.command()
@click.pass_context
def list_accounts(ctx: click.Context) -> None:
    """List configured accounts."""
    config = ctx.obj["config"]
    accounts_service = AccountsService(config)
    accounts_service.list_accounts()


@cli.command()
def init() -> None:
    """Initialize the kairo configuration and storage directories."""
    init_service = InitService()
    init_service.initialize()


if __name__ == "__main__":
    cli(argv[1:])
