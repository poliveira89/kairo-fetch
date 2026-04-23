"""Init service for initialization operations."""

from pathlib import Path

import click


class InitService:
    """Service for handling initialization operations."""

    def initialize(self) -> None:
        """Initialize the kairo configuration and storage directories."""
        kairo_dir = Path.home() / ".kairo"
        kairo_dir.mkdir(exist_ok=True)

        storage_dir = kairo_dir / "storage"
        storage_dir.mkdir(exist_ok=True)

        click.echo(
            f"Initialized kairo configuration and storage directories at {kairo_dir}"
        )
