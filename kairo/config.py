"""Configuration management for email-fetch."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


@dataclass
class AccountConfig(TypedDict):
    """Type for account configuration."""

    provider: str
    username: str
    password: str | None
    access_token: str | None
    client_id: str | None
    client_secret: str | None
    server: str | None
    refresh_token: str | None
    port: int


class StorageConfig(TypedDict):
    """Type for storage configuration."""

    path: str


@dataclass
class ConfigData(TypedDict):
    """Type for configuration data."""

    accounts: dict[str, AccountConfig]
    storage: StorageConfig


class Config:
    """Configuration manager for email-fetch tool."""

    def __init__(self, config_path: str | None = None):
        self.config_path: str = config_path or str(self._get_default_config_path())
        self.data: ConfigData = self._load_config()

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        config_dir = Path.home() / ".kairo"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "config.json"

    def _load_config(self) -> ConfigData:
        """Load configuration from file."""
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
                return ConfigData(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            default_storage_path = str(Path.home() / ".kairo" / "storage")
            return {"accounts": {}, "storage": {"path": default_storage_path}}

    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_account(self, account_name: str) -> AccountConfig | None:
        """Get account configuration."""
        accounts = self.data.get("accounts", {})
        account_data = accounts.get(account_name)
        return account_data if account_data is not None else None

    def set_account(self, account_name: str, account_data: AccountConfig) -> None:
        """Set account configuration."""
        if "accounts" not in self.data:
            self.data["accounts"] = {}
        self.data["accounts"][account_name] = account_data

    def get_storage_path(self) -> str:
        """Get storage path."""
        return self.data.get("storage", {}).get(
            "path", str(Path.home() / ".kairo" / "storage")
        )

    def __repr__(self) -> str:
        return f"Config(config_path={self.config_path}, accounts={list(self.data.get('accounts', {}).keys())})"
