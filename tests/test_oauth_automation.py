"""Tests for OAuth2 automation with Playwright."""

from unittest.mock import AsyncMock, patch

import pytest

from kairo.services.oauth_automation import OAuthAutomator


@pytest.fixture
def oauth_automator():
    """Create an OAuthAutomator instance for testing."""
    return OAuthAutomator(
        client_id="test_client_id",
        client_secret="test_client_secret",
        username="test@example.com",
        password="test_password",
    )


class TestOAuthAutomatorInit:
    """Tests for OAuthAutomator initialization."""

    def test_init_with_required_params(self, oauth_automator):
        """Test initialization with required parameters."""
        assert oauth_automator.client_id == "test_client_id"
        assert oauth_automator.client_secret == "test_client_secret"
        assert oauth_automator.username == "test@example.com"
        assert oauth_automator.password == "test_password"

    def test_init_with_custom_scope(self):
        """Test initialization with custom scope."""
        automator = OAuthAutomator(
            client_id="test_client_id",
            client_secret="test_client_secret",
            username="test@example.com",
            password="test_password",
            scope="https://www.googleapis.com/auth/drive",
        )
        assert automator.scope == "https://www.googleapis.com/auth/drive"

    def test_init_with_custom_redirect_uri(self):
        """Test initialization with custom redirect URI."""
        automator = OAuthAutomator(
            client_id="test_client_id",
            client_secret="test_client_secret",
            username="test@example.com",
            password="test_password",
            redirect_uri="http://localhost:8000/callback",
        )
        assert automator.redirect_uri == "http://localhost:8000/callback"


class TestBuildAuthUrl:
    """Tests for _build_auth_url method."""

    def test_build_auth_url_basic(self, oauth_automator):
        """Test building basic auth URL."""
        url = oauth_automator._build_auth_url()
        assert "https://accounts.google.com/o/oauth2/auth" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob" in url
        assert "scope=https%3A%2F%2Fmail.google.com%2F" in url
        assert "response_type=code" in url

    def test_build_auth_url_with_custom_params(self):
        """Test building auth URL with custom scope and redirect URI."""
        automator = OAuthAutomator(
            client_id="my_client",
            client_secret="my_secret",
            username="user@test.com",
            password="pass",
            scope="custom:scope",
            redirect_uri="http://myapp.com/callback",
        )
        url = automator._build_auth_url()
        assert "scope=custom%3Ascope" in url
        assert "redirect_uri=http%3A%2F%2Fmyapp.com%2Fcallback" in url


class TestExtractAuthCode:
    """Tests for _extract_auth_code method."""

    def test_extract_auth_code_from_urn_url(self, oauth_automator):
        """Test extracting auth code from urn:ietf:wg:oauth:2.0:oob URL."""
        url = "urn:ietf:wg:oauth:2.0:oob?code=test_auth_code_123"
        code = oauth_automator._extract_auth_code(url)
        assert code == "test_auth_code_123"

    def test_extract_auth_code_from_https_url(self, oauth_automator):
        """Test extracting auth code from HTTPS redirect URL."""
        url = "https://example.com/callback?code=abc123&state=xyz"
        code = oauth_automator._extract_auth_code(url)
        assert code == "abc123"

    def test_extract_auth_code_not_found(self, oauth_automator):
        """Test extracting auth code when not present."""
        url = "https://example.com/no-code-here"
        code = oauth_automator._extract_auth_code(url)
        assert code is None

    def test_extract_auth_code_empty(self, oauth_automator):
        """Test extracting auth code when code is empty."""
        url = "https://example.com?code="
        code = oauth_automator._extract_auth_code(url)
        assert code == ""


class TestGetAuthorizationCode:
    """Tests for get_authorization_code method."""

    @patch("kairo.services.oauth_automation.asyncio.run")
    def test_get_authorization_code_calls_async_flow(self, mock_run, oauth_automator):
        """Test that get_authorization_code calls the async flow."""
        mock_run.return_value = "test_code"
        result = oauth_automator.get_authorization_code()
        assert result == "test_code"
        mock_run.assert_called_once()

    @patch("kairo.services.oauth_automation.asyncio.run")
    def test_get_authorization_code_handles_import_error(
        self, mock_run, oauth_automator
    ):
        """Test handling of ImportError for asyncio."""
        mock_run.side_effect = ImportError("No module named 'playwright'")
        result = oauth_automator.get_authorization_code()
        assert result is None

    @patch("kairo.services.oauth_automation.asyncio.run")
    def test_get_authorization_code_handles_generic_error(
        self, mock_run, oauth_automator
    ):
        """Test handling of generic exceptions."""
        mock_run.side_effect = Exception("Some error")
        result = oauth_automator.get_authorization_code()
        assert result is None


class TestAsyncAuthFlow:
    """Tests for the async _run_auth_flow method."""

    @pytest.mark.asyncio
    @patch("kairo.services.oauth_automation.async_playwright")
    async def test_run_auth_flow_success(self, mock_playwright):
        """Test successful OAuth flow."""
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()

        class MockPage:
            def __init__(self):
                self.url = "urn:ietf:wg:oauth:2.0:oob?code=success_code"
                self.goto = AsyncMock(return_value=None)
                self.wait_for_load_state = AsyncMock(return_value=None)
                self.close = AsyncMock(return_value=None)

        mock_page = MockPage()

        mock_playwright.return_value.start = AsyncMock(
            return_value=mock_playwright_instance
        )
        mock_playwright_instance.chrome.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock(return_value=None)
        mock_playwright_instance.stop = AsyncMock(return_value=None)

        automator = OAuthAutomator(
            client_id="test",
            client_secret="test",
            username="test@test.com",
            password="pass",
        )

        with patch.object(
            automator, "_handle_login", new_callable=AsyncMock
        ) as mock_login:
            with patch.object(
                automator, "_handle_consent", new_callable=AsyncMock
            ) as mock_consent:
                with patch.object(
                    automator, "_extract_auth_code", return_value="success_code"
                ) as mock_extract:
                    mock_login.return_value = True
                    mock_consent.return_value = True

                    result = await automator._run_auth_flow()

        assert result == "success_code"
        mock_extract.assert_called_once()

    @pytest.mark.asyncio
    @patch("kairo.services.oauth_automation.async_playwright")
    async def test_run_auth_flow_login_failure(self, mock_playwright):
        """Test flow when login fails."""
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
        mock_playwright_instance.chrome.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        mock_page.url = "https://accounts.google.com/login"
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        automator = OAuthAutomator(
            client_id="test",
            client_secret="test",
            username="test@test.com",
            password="pass",
        )

        with patch.object(
            automator, "_handle_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = False

            result = await automator._run_auth_flow()

        assert result is None

    @pytest.mark.asyncio
    @patch("kairo.services.oauth_automation.async_playwright")
    async def test_run_auth_flow_consent_failure(self, mock_playwright):
        """Test flow when consent handling fails."""
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
        mock_playwright_instance.chrome.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        mock_page.url = "https://accounts.google.com/oauth/consent"
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        automator = OAuthAutomator(
            client_id="test",
            client_secret="test",
            username="test@test.com",
            password="pass",
        )

        with patch.object(
            automator, "_handle_login", new_callable=AsyncMock
        ) as mock_login:
            with patch.object(
                automator, "_handle_consent", new_callable=AsyncMock
            ) as mock_consent:
                mock_login.return_value = True
                mock_consent.return_value = False

                result = await automator._run_auth_flow()

        assert result is None


class TestHandleConsent:
    """Tests for _handle_consent method."""

    @pytest.mark.asyncio
    async def test_handle_consent_no_allow_button(self):
        """Test when no allow button is found."""
        from unittest.mock import MagicMock

        automator = OAuthAutomator(
            client_id="test",
            client_secret="test",
            username="test@test.com",
            password="pass",
        )
        mock_page = AsyncMock()

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_locator.first = mock_locator
        mock_page.get_by_role = MagicMock(return_value=mock_locator)
        mock_page.wait_for_timeout.return_value = None

        result = await automator._handle_consent(mock_page)
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_consent_allow_button_found(self):
        """Test when allow button is found and clicked."""
        from unittest.mock import MagicMock

        automator = OAuthAutomator(
            client_id="test",
            client_secret="test",
            username="test@test.com",
            password="pass",
        )
        mock_page = AsyncMock()

        mock_allow_button = AsyncMock()
        mock_allow_button.count = AsyncMock(return_value=1)
        mock_allow_button.click = AsyncMock()

        mock_locator = MagicMock()
        mock_locator.first = mock_allow_button
        mock_page.get_by_role = MagicMock(return_value=mock_locator)

        mock_page.wait_for_timeout.return_value = None
        mock_page.wait_for_load_state.return_value = None

        result = await automator._handle_consent(mock_page)

        assert result is True
        mock_allow_button.click.assert_called_once()


class TestExtractAuthCodeFromPage:
    """Tests for _extract_auth_code_from_page method."""

    @pytest.mark.asyncio
    async def test_extract_from_page_title(self, oauth_automator):
        """Test extracting code from page title."""
        mock_page = AsyncMock()
        mock_page.title.return_value = "Auth Code: abc123"

        with patch.object(oauth_automator, "_extract_auth_code", return_value=None):
            result = await oauth_automator._extract_auth_code_from_page(mock_page)

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_from_page_body(self, oauth_automator):
        """Test extracting code from page body."""
        mock_page = AsyncMock()
        mock_page.title.return_value = "Page Title"
        mock_locator = AsyncMock()
        mock_page.locator.return_value = mock_locator
        mock_locator.text_content.return_value = "Authorization code: test_code_123"

        result = await oauth_automator._extract_auth_code_from_page(mock_page)
        assert result is None
