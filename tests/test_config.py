"""Tests for configuration module."""

from kairo.config import Config


def test_config_initialization():
    """Test that Config can be initialized."""
    config = Config()
    assert config is not None


def test_config_has_expected_attributes():
    """Test that Config has expected attributes."""
    config = Config()
    # Add assertions for expected attributes once they're defined
    # For now, just test that it initializes successfully
    assert hasattr(config, "__dict__")


def test_config_repr():
    """Test Config __repr__ method."""
    config = Config()
    repr_str = repr(config)
    assert "Config(" in repr_str
    assert "config_path=" in repr_str
    assert "accounts=" in repr_str
    assert ")" in repr_str


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
        config = Config(config_file)
        repr_str = repr(config)
        assert "Config(" in repr_str
        assert "config_path=" in repr_str
        assert "accounts=['test_account']" in repr_str
        assert ")" in repr_str
    finally:
        Path(config_file).unlink()
