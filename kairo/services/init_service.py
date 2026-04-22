"""Init service for initialization operations."""

import click
from pathlib import Path


class InitService:
    """Service for handling initialization operations."""

    def initialize(self) -> None:
        """Initialize the kairo configuration and storage directories."""
        # Create .kairo directory in the user's home directory
        kairo_dir = Path.home() / ".kairo"
        kairo_dir.mkdir(exist_ok=True)

        # Create storage directory
        storage_dir = kairo_dir / "storage"
        storage_dir.mkdir(exist_ok=True)

        click.echo(
            f"Initialized kairo configuration and storage directories at {kairo_dir}"
        )
