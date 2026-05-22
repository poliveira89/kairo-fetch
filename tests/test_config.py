"""Tests for configuration module."""

from kairo.config import Config


def test_config_initialization():
    """Test that Config can be initialized."""
    Config.reset()
    config = Config()
    assert config is not None


def test_config_has_expected_attributes():
    """Test that Config has expected attributes."""
    Config.reset()
    config = Config()

    assert hasattr(config, "__dict__")


def test_config_repr():
    """Test Config __repr__ method."""
    Config.reset()
    config = Config()
    repr_str = repr(config)
    assert "Config(" in repr_str
    assert "config_path=" in repr_str
    assert "accounts=" in repr_str
    assert ")" in repr_str


# Config OAuth tests


def test_config_oauth_default_token_url():
    """Test that Config provides the correct default token_url for Google OAuth."""
    Config.reset()
    config = Config()
    assert config.oauth.token_url == "https://oauth2.googleapis.com/token"


def test_config_oauth_custom_token_url():
    """Test that Config can use a custom OAuthConfig with custom token_url."""
    import json
    import tempfile
    from pathlib import Path

    custom_url = "https://custom.oauth.token.url/token"

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {},
            "storage": {"path": "/tmp/test_storage"},
            "oauth": {"token_url": custom_url},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        Config.reset()
        config = Config(config_file)
        assert config.oauth.token_url == custom_url
    finally:
        Path(config_file).unlink()
        Config.reset()


def test_config_oauth_access():
    """Test that Config exposes OAuthConfig via oauth attribute."""
    Config.reset()
    config = Config()
    assert hasattr(config, "oauth")
    assert config.oauth.token_url == "https://oauth2.googleapis.com/token"


def test_config_singleton():
    """Test that Config is a singleton."""
    Config.reset()
    config1 = Config()
    config2 = Config()
    assert config1 is config2
    Config.reset()


def test_config_reset():
    """Test that Config.reset() allows creating a new instance."""
    Config.reset()
    config1 = Config()
    Config.reset()
    config2 = Config()

    assert config1 is not config2
    Config.reset()


def test_config_repr_with_accounts():
    """Test Config __repr__ method with accounts."""
    import json
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_content = {
            "accounts": {
                "test_account": {
                    "provider": "gmail",
                    "username": "test@example.com",
                    "password": "test_password",
                }
            },
            "storage": {"path": "/tmp/test_storage"},
        }
        json.dump(config_content, f)
        config_file = f.name

    try:
        Config.reset()
        config = Config(config_file)
        repr_str = repr(config)
        assert "Config(" in repr_str
        assert "config_path=" in repr_str
        assert "accounts=['test_account']" in repr_str
        assert ")" in repr_str
    finally:
        Path(config_file).unlink()
        Config.reset()
