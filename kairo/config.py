"""Configuration management for email-fetch."""

import json
from pathlib import Path
from typing import ClassVar, Dict, Optional

from pydantic import BaseModel

from .logging import log


class OAuthConfig(BaseModel):
    """OAuth configuration settings."""

    token_url: str = "https://oauth2.googleapis.com/token"


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
    oauth: OAuthConfig = OAuthConfig()


class Config:
    """Configuration manager for email-fetch tool - singleton pattern."""

    _instance: ClassVar[Optional["Config"]] = None

    def __new__(cls, config_path: str | None = None):
        """Ensure singleton pattern by returning existing instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._config_path_arg = None

        if config_path != cls._instance._config_path_arg:
            cls._instance._config_path_arg = config_path
            cls._instance._initialized = False

        if not cls._instance._initialized:
            cls._instance._init(config_path)
        return cls._instance

    def _init(self, config_path: str | None = None):
        """Initialize the config instance."""
        self.config_path: str = config_path or str(self._get_default_config_path())
        self.data: ConfigData = self._load_config()
        self.oauth: OAuthConfig = self.data.oauth
        self._initialized = True
        self._config_path_arg = config_path

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        if cls._instance is not None:
            cls._instance._initialized = False
            cls._instance._config_path_arg = None
        cls._instance = None

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        config_dir = Path.home() / ".kairo"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "config.json"

    def _load_config(self) -> ConfigData:
        """Load configuration from file with backward compatibility."""
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
                if "accounts" not in data:
                    data["accounts"] = {}
                if "storage" not in data:
                    data["storage"] = {"path": str(Path.home() / ".kairo" / "storage")}
                if "oauth" not in data:
                    data["oauth"] = {}

                validated_accounts = {}
                for account_name, account_data in data["accounts"].items():
                    try:
                        validated_accounts[account_name] = AccountConfig(**account_data)
                    except Exception:
                        log.exception(f"Skipping invalid account: {account_name}")
                        continue
                data["accounts"] = validated_accounts

                return ConfigData(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            default_storage_path = str(Path.home() / ".kairo" / "storage")
            return ConfigData(
                accounts={},
                storage=StorageConfig(path=default_storage_path),
                oauth=OAuthConfig(),
            )

    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, "w") as f:
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
