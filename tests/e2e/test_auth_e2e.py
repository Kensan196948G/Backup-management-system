"""
E2E Tests: Authentication Flow

Tests the login/logout UI flow using Playwright against a live Flask server.
"""

import re

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e


class TestLoginPage:
    """Login page rendering and accessibility tests."""

    def test_login_page_loads(self, page: Page, live_server, _seed_test_user):
        """Login page should display the login form with username/password fields."""
        page.goto(f"{live_server}/auth/login")

        # Page title contains the login keyword
        expect(page).to_have_title(re.compile("ログイン"))

        # Username and password inputs are visible
        expect(page.locator("#username")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()

        # Submit button is present
        expect(page.locator("#loginBtn")).to_be_visible()

    def test_login_with_valid_credentials(
        self, page: Page, live_server, _seed_test_user
    ):
        """Successful login should redirect to the dashboard."""
        page.goto(f"{live_server}/auth/login")

        page.fill("#username", "e2e_admin")
        page.fill("#password", "E2eTest123!")
        page.click("#loginBtn")

        # Should navigate away from login page to dashboard
        page.wait_for_url(f"{live_server}/**", timeout=5000)

        # URL should no longer be the login page
        assert "/auth/login" not in page.url

    def test_login_with_invalid_credentials(
        self, page: Page, live_server, _seed_test_user
    ):
        """Invalid credentials should show an error message on the login page."""
        page.goto(f"{live_server}/auth/login")

        page.fill("#username", "e2e_admin")
        page.fill("#password", "WrongPassword!")
        page.click("#loginBtn")

        # Should stay on the login page
        page.wait_for_load_state("networkidle")

        # An error message should be visible (flash messages use .alert with
        # contextual class like alert-danger, alert-info, etc.)
        error_alert = page.locator("[class*='alert-danger']")
        expect(error_alert.first).to_be_visible()

    def test_logout_flow(self, page: Page, live_server, _seed_test_user):
        """After logout, the user should be redirected back to the login page."""
        # Login first
        page.goto(f"{live_server}/auth/login")
        page.fill("#username", "e2e_admin")
        page.fill("#password", "E2eTest123!")
        page.click("#loginBtn")
        page.wait_for_url(f"{live_server}/**", timeout=5000)

        # Navigate to logout
        page.goto(f"{live_server}/auth/logout")
        page.wait_for_load_state("networkidle")

        # Should end up on the login page
        assert "/auth/login" in page.url or page.url.rstrip("/") == live_server
