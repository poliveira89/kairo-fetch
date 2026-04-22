"""Search service for email search operations."""

import click

from ..config import Config


class SearchService:
    """Service for handling email search operations."""

    def __init__(self, config: Config):
        self.config = config

    def search_emails(self, account: str, query: str) -> None:
        """Search emails in index."""
        click.echo(f"Searching account '{account}' for query: {query}")
        click.echo(f"Configuration loaded: {self.config}")
        click.echo("Feature not yet implemented. This is the basic CLI structure.")
