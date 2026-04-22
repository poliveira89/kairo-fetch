"""Accounts service for account management operations."""

import click

from ..config import Config


class AccountsService:
    """Service for handling account management operations."""

    def __init__(self, config: Config):
        self.config = config

    def list_accounts(self) -> None:
        """List configured accounts."""
        click.echo("List of configured accounts:")
        click.echo(f"Configuration loaded: {self.config}")
        click.echo("Feature not yet implemented. This is the basic CLI structure.")
