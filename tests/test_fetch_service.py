"""Tests for fetch service functionality."""

from unittest.mock import MagicMock, patch

import pytest

from kairo.config import AccountConfig, Config, OAuthConfig
from kairo.retrievers.gmail import GmailRetriever
from kairo.services.fetch_service import GmailAuthenticator


@pytest.fixture
def mock_config():
    """Create a mock Config instance for testing."""
    config = MagicMock(spec=Config)
    config.oauth = OAuthConfig()
    return config


@pytest.fixture
def account_config():
    """Create a sample AccountConfig for testing."""
    return AccountConfig(
        provider="gmail",
        username="test@example.com",
        client_id="test_client_id",
        client_secret="test_client_secret",
        password=None,
        access_token=None,
    )


def test_gmail_authenticator_uses_oauth_config_token_url(mock_config):
    """Test that GmailAuthenticator uses token_url from config.oauth during OAuth exchange."""

    expected_url: str = mock_config.oauth.token_url
    authenticator = GmailAuthenticator(mock_config)

    account_config = AccountConfig(
        provider="gmail",
        username="test@example.com",
        client_id="test_client_id",
        client_secret="test_client_secret",
        password="test_password",
        access_token=None,
    )

    mock_automator_instance = MagicMock()
    mock_automator_instance.get_authorization_code.return_value = "test_auth_code"

    with (
        patch("kairo.services.fetch_service.click.echo"),
        patch("kairo.services.fetch_service.OAuthAutomator") as mock_automator_class,
        patch("kairo.services.fetch_service.Request") as mock_request,
        patch("kairo.services.fetch_service.urlopen") as mock_urlopen,
    ):
        mock_automator_class.return_value = mock_automator_instance

        mock_response = MagicMock()
        mock_response.read.return_value = (
            b'{"access_token": "test_token", "refresh_token": "refresh_token"}'
        )
        mock_urlopen.return_value = mock_response
        mock_request_instance = MagicMock()
        mock_request.return_value = mock_request_instance

        captured_url = None
        captured_data = None

        def capture_request(url, data=None, **_):
            nonlocal captured_url, captured_data
            captured_url = url
            captured_data = data
            return mock_request_instance

        mock_request.side_effect = capture_request

        result = authenticator.authenticate("test_account", account_config)

        assert isinstance(result, GmailRetriever)
        assert captured_url == expected_url
        assert captured_data is not None
        assert b"code=test_auth_code" in captured_data
        assert b"client_id=test_client_id" in captured_data
        assert b"client_secret=test_client_secret" in captured_data
        assert b"grant_type=authorization_code" in captured_data
