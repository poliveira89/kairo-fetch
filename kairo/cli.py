"""CLI interface for email-fetch tool."""

import click

from .config import Config


@click.group()
@click.pass_context
def cli(ctx):
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
@click.option("--account", required=True, help="Account name/identifier")
@click.option("--folder", default="inbox", help="Folder/label to fetch from")
@click.option("--server", help="IMAP server address (required for IMAP)")
@click.option("--port", type=int, default=993, help="IMAP server port")
@click.pass_context
def fetch(ctx, provider, account, folder, server, port):
    """Fetch emails from specified provider and folder."""
    config = ctx.obj["config"]
    click.echo(f"Fetching emails from {provider} account '{account}' folder '{folder}'")

    if provider == "imap" and not server:
        click.echo("Error: --server is required for IMAP provider", err=True)
        return

    # TODO: Implement actual retrieval logic
    click.echo(f"Configuration loaded: {config}")
    click.echo("Feature not yet implemented. This is the basic CLI structure.")


@cli.command()
@click.option("--account", required=True, help="Account name to search")
@click.option("--query", required=True, help='Search query (e.g., "from:john")')
@click.pass_context
def search(ctx, account, query):
    """Search emails in index."""
    config = ctx.obj["config"]
    click.echo(f"Searching account '{account}' for query: {query}")
    click.echo(f"Configuration loaded: {config}")
    click.echo("Feature not yet implemented. This is the basic CLI structure.")


@cli.command()
@click.pass_context
def list_accounts(ctx):
    """List configured accounts."""
    config = ctx.obj["config"]
    click.echo("List of configured accounts:")
    click.echo(f"Configuration loaded: {config}")
    click.echo("Feature not yet implemented. This is the basic CLI structure.")


if __name__ == "__main__":
    cli()
