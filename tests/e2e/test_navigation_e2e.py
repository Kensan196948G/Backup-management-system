"""
E2E Tests: Navigation and Access Control

Tests that application navigation flows work correctly:
- Authenticated users can access protected pages
- Unauthenticated users are redirected to login
- Navigation bar is visible after login
- Role-based access control (viewer vs admin)
"""

import pytest
from playwright.sync_api import Page, expect

from app.models import User, db


pytestmark = pytest.mark.e2e


def _login(page: Page, live_server: str, username: str = "e2e_admin", password: str = "E2eTest123!") -> None:
    """Helper: log in with given credentials."""
    page.goto(f"{live_server}/auth/login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#loginBtn")
    page.wait_for_url(f"{live_server}/**", timeout=5000)


@pytest.fixture(scope="session")
def _seed_viewer_user(e2e_app):
    """Seed a viewer-role user for access control tests."""
    with e2e_app.app_context():
        db.create_all()

        existing = User.query.filter_by(username="e2e_viewer").first()
        if not existing:
            user = User(
                username="e2e_viewer",
                email="e2e_viewer@example.com",
                full_name="E2E Viewer",
                role="viewer",
                is_active=True,
            )
            user.set_password("E2eViewer123!")
            db.session.add(user)
            db.session.commit()


class TestNavigation:
    """General navigation flow tests."""

    def test_dashboard_accessible_after_login(
        self, page: Page, live_server, _seed_test_user
    ):
        """After a successful login, the dashboard page should be accessible."""
        _login(page, live_server)

        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        # Should not be redirected back to login
        assert "/auth/login" not in page.url

        # Page body should have content
        body_text = page.text_content("body")
        assert body_text is not None
        assert len(body_text.strip()) > 0

    def test_protected_page_redirects_to_login(self, page: Page, live_server):
        """Accessing a protected page without authentication should redirect to login."""
        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        # Should end up on the login page
        assert "/auth/login" in page.url

    def test_navbar_visible_after_login(
        self, page: Page, live_server, _seed_test_user
    ):
        """After login, a navigation bar should be visible on the page."""
        _login(page, live_server)

        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        # Navigation element should be present (navbar, sidebar, or nav tag)
        nav = page.locator("nav, #sidebar, .navbar, .nav, [role='navigation']")
        assert nav.count() > 0

    def test_jobs_page_accessible_after_login(
        self, page: Page, live_server, _seed_test_user
    ):
        """After login, the jobs list page should be accessible."""
        _login(page, live_server)

        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        assert "/auth/login" not in page.url

    def test_media_page_accessible_after_login(
        self, page: Page, live_server, _seed_test_user
    ):
        """After login, the media management page should be accessible."""
        _login(page, live_server)

        page.goto(f"{live_server}/media/")
        page.wait_for_load_state("networkidle")

        assert "/auth/login" not in page.url

    def test_reports_page_accessible_after_login(
        self, page: Page, live_server, _seed_test_user
    ):
        """After login, the reports page should be accessible."""
        _login(page, live_server)

        page.goto(f"{live_server}/reports/")
        page.wait_for_load_state("networkidle")

        assert "/auth/login" not in page.url


class TestAccessControl:
    """Role-based access control tests."""

    def test_viewer_can_access_dashboard(
        self, page: Page, live_server, _seed_test_user, _seed_viewer_user
    ):
        """A user with viewer role should be able to access the dashboard."""
        _login(page, live_server, username="e2e_viewer", password="E2eViewer123!")

        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        # Viewer should be able to see the dashboard (not redirected to login)
        assert "/auth/login" not in page.url

        body_text = page.text_content("body")
        assert body_text is not None
        assert len(body_text.strip()) > 0

    def test_admin_pages_accessible(
        self, page: Page, live_server, _seed_test_user
    ):
        """Admin user should be able to access the dashboard and job pages."""
        _login(page, live_server)

        for path in ["/dashboard", "/jobs/", "/media/", "/reports/"]:
            page.goto(f"{live_server}{path}")
            page.wait_for_load_state("networkidle")

            assert "/auth/login" not in page.url, (
                f"Admin was unexpectedly redirected to login when accessing {path}"
            )

    def test_logout_clears_session(
        self, page: Page, live_server, _seed_test_user
    ):
        """After logout, protected pages should redirect to login again."""
        # Log in
        _login(page, live_server)
        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")
        assert "/auth/login" not in page.url

        # Log out
        page.goto(f"{live_server}/auth/logout")
        page.wait_for_load_state("networkidle")

        # Try to access a protected page again
        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        # Should be redirected to login
        assert "/auth/login" in page.url
