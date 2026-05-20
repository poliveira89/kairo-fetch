"""OAuth2 automation service using Playwright for Google OAuth flow."""

import asyncio
import re
from typing import Optional
from urllib.parse import urlencode

import click
from playwright.async_api import Browser, Page, Playwright, async_playwright

from ..logging import log

ALLOW_CONTINUE_PATTERN = re.compile(r"Allow|Continue", re.IGNORECASE)


class OAuthAutomator:
    """Automates OAuth2 authorization code retrieval using Playwright.

    This class handles the complete OAuth2 authorization code flow for Google,
    including: navigating to auth URL, handling login, consent, and extracting
    the authorization code from the redirect URL.
    """

    AUTH_URL_BASE = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    NAVIGATION_TIMEOUT = 30000  # 30 seconds
    ACTION_TIMEOUT = 10000  # 10 seconds
    CHROME_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        scope: str = "https://mail.google.com/",
        redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob",
    ):
        """Initialize OAuthAutomator.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            username: Google account email/username
            password: Google account password
            scope: OAuth2 scope (default: Gmail access)
            redirect_uri: OAuth2 redirect URI (default: out-of-band)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.scope = scope
        self.redirect_uri = redirect_uri

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    def get_authorization_code(self) -> Optional[str]:
        """Run the complete OAuth2 flow and return the authorization code.

        This is the main entry point. It runs the async flow synchronously
        and returns the authorization code, or None if the flow failed.

        Returns:
            The authorization code as a string, or None if automation failed.
        """
        try:
            return asyncio.run(self._run_auth_flow())
        except ImportError as e:
            log.warning(f"Playwright not available: {e}")
            return None
        except Exception as e:
            log.warning(f"OAuth automation failed: {e}")
            return None

    async def _run_auth_flow(self) -> Optional[str]:
        """Run the async OAuth2 authorization flow.

        Returns:
            Authorization code or None if failed.
        """
        playwright = None
        browser = None
        page = None

        try:
            playwright = await async_playwright().start()
            self._playwright = playwright

            browser = await playwright.chromium.launch(
                headless=False,
                timeout=self.NAVIGATION_TIMEOUT,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                ],
            )
            self._browser = browser

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=self.CHROME_USER_AGENT,
            )

            page = await context.new_page()

            auth_url = self._build_auth_url()
            log.info(f"Navigating to OAuth auth URL: {auth_url}")
            await page.goto(auth_url, timeout=self.NAVIGATION_TIMEOUT)

            await page.wait_for_load_state("networkidle", timeout=self.ACTION_TIMEOUT)

            login_result = await self._handle_login(page)
            if login_result is False:
                return None
            if isinstance(login_result, str):
                return login_result

            if not await self._handle_consent(page):
                return None

            current_url = page.url
            log.debug(f"Current URL after auth flow: {current_url}")

            auth_code = self._extract_auth_code(current_url)

            if not auth_code:
                auth_code = await self._extract_auth_code_from_page(page)

            if auth_code:
                click.echo("✅ Successfully retrieved authorization code via automation")
                return auth_code
            else:
                log.warning(f"Could not extract auth code from URL: {current_url}")
                return None
        except Exception as e:
            log.warning(f"Error during OAuth automation: {e}")
            return None
        finally:
            if page:
                await page.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
            self._playwright = None
            self._browser = None

    def _build_auth_url(self) -> str:
        """Build the Google OAuth2 authorization URL.

        Returns:
            Complete OAuth2 authorization URL.
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        return self.AUTH_URL_BASE + "?" + urlencode(params)

    async def _handle_login(self, page: Page) -> str:
        """Handle Google login if the login page is detected.

        Args:
            page: Playwright Page object

        Returns:
            True if login succeeded or wasn't needed, False otherwise.
        """
        if "accounts.google.com" not in page.url:
            return ""

        try:
            email_input = page.get_by_role("textbox", name="Email")
            if await email_input.count() > 0:
                log.debug("Email input field detected, filling login form")
                await email_input.first.fill(self.username)

            next_button = page.get_by_role("button", name="Next")
            if await next_button.count() > 0:
                await next_button.first.click()
            else:
                await email_input.first.press("Enter")

            await page.get_by_text(self.username, exact=True).wait_for(
                timeout=self.ACTION_TIMEOUT
            )
            password_input = page.get_by_role("textbox", name="Password")
            if await password_input.count() > 0:
                await password_input.first.fill(self.password)

            next_button = page.get_by_role("button", name="Next")
            if await next_button.count() > 0:
                await next_button.first.click()
            else:
                await password_input.first.press("Enter")

            await page.get_by_text(
                "Google hasn’t verified this app", exact=True
            ).wait_for(timeout=self.ACTION_TIMEOUT)
            await page.get_by_role("button", name="Continue").first.click()

            await page.get_by_text("Make sure you trust Kairos", exact=True).wait_for(
                timeout=self.ACTION_TIMEOUT
            )
            await page.get_by_role("button", name="Continue").first.click()

            await page.get_by_text("Authorization code", exact=True).wait_for(
                timeout=self.ACTION_TIMEOUT
            )
            authorization_code = await page.locator("//textarea").first.text_content()
            log.info(f"Authorizode code is {authorization_code}")

            if authorization_code:
                return authorization_code

            return ""
        except Exception as e:
            log.warning(f"Error during login handling: {e}")
            return ""

    async def _handle_consent(self, page: Page) -> bool:
        """Handle the OAuth consent page.

        Args:
            page: Playwright Page object

        Returns:
            True if consent was handled successfully, False otherwise.
        """
        try:
            await page.wait_for_timeout(1000)

            allow_button = page.get_by_role("button", name=ALLOW_CONTINUE_PATTERN).first
            if await allow_button.count() > 0:
                log.debug("Consent page detected, clicking Allow")
                await allow_button.click()
                await page.wait_for_load_state(
                    "networkidle", timeout=self.ACTION_TIMEOUT
                )
                return True

            return True

        except Exception as e:
            log.warning(f"Error during consent handling: {e}")
            return False

    def _extract_auth_code(self, url: str) -> Optional[str]:
        """Extract the authorization code from a redirect URL.

        The redirect URL for out-of-band flow is:
        urn:ietf:wg:oauth:2.0:oob?code=AUTH_CODE

        Args:
            url: The complete redirect URL

        Returns:
            The authorization code or None if not found.
        """
        match = re.search(r"[?&]code=([^&]*)", url)
        if match:
            return match.group(1)

        return None

    async def _extract_auth_code_from_page(self, page: Page) -> Optional[str]:
        """Extract auth code from page content if not in URL.

        For out-of-band flow, Google may display the code on a page
        instead of redirecting.

        Args:
            page: Playwright Page object

        Returns:
            Authorization code or None.
        """
        try:
            title = await page.title()
            match = re.search(r"code=([A-Za-z0-9_-]+)", title)
            if match:
                return match.group(1)

            body_text = await page.locator("body").text_content()
            if body_text is not None:
                match = re.search(r"code=([A-Za-z0-9_-]+)", body_text)
                if match:
                    return match.group(1)

                match = re.search(r"[A-Za-z0-9_-]{20,}", body_text)
                if match:
                    codes = re.findall(r"[A-Za-z0-9_-]{20,}", body_text)
                    if codes:
                        for code in codes:
                            if 30 <= len(code) <= 100:
                                return code

            return None
        except Exception as e:
            log.warning(f"Error extracting code from page: {e}")
            return None
