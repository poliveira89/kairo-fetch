"""Configuration management for email-fetch."""

import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration manager for email-fetch tool."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._get_default_config_path()
        self.data = self._load_config()

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        config_dir = Path.home() / ".email_fetch"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "config.json"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return default empty config
            return {"accounts": {}, "storage": {"path": str(Path.cwd() / "storage")}}

    def save(self):
        """Save configuration to file."""
        with open(self.config_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_account(self, account_name: str) -> Dict[str, Any]:
        """Get account configuration."""
        return self.data.get("accounts", {}).get(account_name, {})

    def set_account(self, account_name: str, account_data: Dict[str, Any]):
        """Set account configuration."""
        if "accounts" not in self.data:
            self.data["accounts"] = {}
        self.data["accounts"][account_name] = account_data

    def get_storage_path(self) -> str:
        """Get storage path."""
        return self.data.get("storage", {}).get("path", str(Path.cwd() / "storage"))

    def __repr__(self):
        return f"Config(config_path={self.config_path}, accounts={list(self.data.get('accounts', {}).keys())})"
