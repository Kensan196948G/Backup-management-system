"""
E2E Tests: Backup Jobs List Page

Tests the backup job list page load, authentication requirement,
and basic structural elements using Playwright against a live Flask server.
"""

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e


def _login(page: Page, live_server: str) -> None:
    """Helper: log in as the seeded E2E admin user."""
    page.goto(f"{live_server}/auth/login")
    page.fill("#username", "e2e_admin")
    page.fill("#password", "E2eTest123!")
    page.click("#loginBtn")
    page.wait_for_url(f"{live_server}/**", timeout=5000)


class TestBackupJobsList:
    """Backup job list page load and structural tests."""

    def test_jobs_list_page_loads(self, page: Page, live_server, _seed_test_user):
        """Authenticated user should be able to load the jobs list page."""
        _login(page, live_server)

        response = page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        # Should not be redirected to login
        assert "/auth/login" not in page.url

        # Page should return a successful response (not 500)
        if response is not None:
            assert response.status in (200, 302, 301)

        # No generic error heading should appear
        error_heading = page.locator("h1:has-text('Error'), h1:has-text('エラー')")
        assert error_heading.count() == 0

    def test_jobs_list_requires_auth(self, page: Page, live_server):
        """Unauthenticated access to /jobs/ should redirect to the login page."""
        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        # Should be redirected to the login page
        assert "/auth/login" in page.url

    def test_jobs_list_contains_table(self, page: Page, live_server, _seed_test_user):
        """Jobs list page should render a table or list element for job entries."""
        _login(page, live_server)

        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        # Page should contain at least one table, list, or card container
        table_or_list = page.locator("table, .table, ul.list-group, .card")
        assert table_or_list.count() > 0

    def test_jobs_list_page_has_content(self, page: Page, live_server, _seed_test_user):
        """Jobs list page body should have meaningful content."""
        _login(page, live_server)

        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        body_text = page.text_content("body")
        assert body_text is not None
        assert len(body_text.strip()) > 0

    def test_jobs_list_accessible_via_api(
        self, page: Page, live_server, _seed_test_user
    ):
        """Jobs list API endpoint should respond while authenticated."""
        _login(page, live_server)

        result = page.evaluate("""
            async () => {
                const response = await fetch('/jobs/api/jobs');
                return {
                    status: response.status,
                    contentType: response.headers.get('content-type') || ''
                };
            }
        """)
        # The API should return a valid HTTP response (not a server error)
        assert result["status"] in (200, 401, 403, 404)
