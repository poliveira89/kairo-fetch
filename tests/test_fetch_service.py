"""Tests for fetch service functionality."""

from unittest.mock import MagicMock, patch

import pytest

from kairo.config import AccountConfig, Config, OAuthSettings
from kairo.retrievers.gmail import GmailRetriever
from kairo.services.fetch_service import GmailAuthenticator


@pytest.fixture
def mock_config():
    """Create a mock Config instance for testing."""
    config = MagicMock(spec=Config)
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


def test_gmail_authenticator_uses_oauth_settings_token_url(mock_config, account_config):
    """Test that GmailAuthenticator uses token_url from OAuthSettings during OAuth exchange."""

    expected_url: str = OAuthSettings().token_url

    with patch(
        "kairo.services.fetch_service.OAuthSettings",
        return_value=MagicMock(token_url=expected_url),
    ):
        authenticator = GmailAuthenticator(mock_config)

        with (
            patch("kairo.services.fetch_service.click.echo"),
            patch("kairo.services.fetch_service.click.prompt") as mock_prompt,
            patch("urllib.request.Request") as mock_request,
            patch("urllib.request.urlopen") as mock_urlopen,
        ):
            # Setup mocks
            mock_prompt.return_value = "test_auth_code"
            mock_response = MagicMock()
            mock_response.read.return_value = (
                b'{"access_token": "test_token", "refresh_token": "refresh_token"}'
            )
            mock_urlopen.return_value = mock_response
            mock_request_instance = MagicMock()
            mock_request.return_value = mock_request_instance

            # Track the URL and data passed to Request
            captured_url = None
            captured_data = None

            def capture_request(url, data=None, **_):
                nonlocal captured_url, captured_data
                captured_url = url
                captured_data = data
                return mock_request_instance

            mock_request.side_effect = capture_request

            # Call authenticate
            result = authenticator.authenticate("test_account", account_config)

            # Verify the result is a GmailRetriever instance
            assert result is not None
            assert isinstance(result, GmailRetriever)

            # Verify the custom token URL was used
            assert captured_url == expected_url
            assert captured_data is not None
            assert b"code=test_auth_code" in captured_data
            assert b"client_id=test_client_id" in captured_data
            assert b"client_secret=test_client_secret" in captured_data
            assert b"grant_type=authorization_code" in captured_data
