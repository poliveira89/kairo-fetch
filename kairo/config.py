"""Configuration management for email-fetch."""

import json
from pathlib import Path
from typing import Dict

from pydantic import BaseModel

from kairo import log


class AccountConfig(BaseModel):
    """Account configuration."""

    provider: str | None = None
    username: str
    password: str | None = None
    access_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    server: str | None = None
    refresh_token: str | None = None
    port: int = 993


class StorageConfig(BaseModel):
    """Storage configuration."""

    path: str


class ConfigData(BaseModel):
    """Complete configuration data."""

    accounts: Dict[str, AccountConfig]
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
                # Handle backward compatibility with old config format
                if "accounts" not in data:
                    data["accounts"] = {}
                if "storage" not in data:
                    data["storage"] = {"path": str(Path.home() / ".kairo" / "storage")}

                # Validate and convert accounts to proper format
                validated_accounts = {}
                for account_name, account_data in data["accounts"].items():
                    try:
                        validated_accounts[account_name] = AccountConfig(**account_data)
                    except Exception as e:
                        log.exception(f"Skipping invalid account: {account_name}")
                        continue
                data["accounts"] = validated_accounts

                return ConfigData(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            default_storage_path = str(Path.home() / ".kairo" / "storage")
            return ConfigData(
                accounts={}, storage=StorageConfig(path=default_storage_path)
            )

    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, "w") as f:
            # Convert Pydantic model to dict for JSON serialization
            data_dict = self.data.dict()
            json.dump(data_dict, f, indent=2)

    def get_account(self, account_name: str) -> AccountConfig | None:
        """Get account configuration."""
        accounts = self.data.accounts
        account_data = accounts.get(account_name)
        return account_data if account_data is not None else None

    def set_account(self, account_name: str, account_data: AccountConfig) -> None:
        """Set account configuration."""
        self.data.accounts[account_name] = account_data

    def get_storage_path(self) -> str:
        """Get storage path."""
        return self.data.storage.path

    def __repr__(self) -> str:
        return f"Config(config_path={self.config_path}, accounts={list(self.data.accounts.keys())})"
