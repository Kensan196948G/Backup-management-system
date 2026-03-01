"""
E2E Tests: Alert Display on Dashboard

Tests that alert-related elements on the dashboard render correctly.
"""

import pytest
from playwright.sync_api import Page, expect

from app.models import Alert, db


pytestmark = pytest.mark.e2e


def _login(page: Page, live_server: str) -> None:
    """Helper: log in as the seeded E2E admin user."""
    page.goto(f"{live_server}/auth/login")
    page.fill("#username", "e2e_admin")
    page.fill("#password", "E2eTest123!")
    page.click("#loginBtn")
    page.wait_for_url(f"{live_server}/**", timeout=5000)


class TestAlertDisplay:
    """Tests for alert display on the dashboard."""

    def test_dashboard_shows_alert_stats_card(
        self, page, live_server, _seed_test_user
    ):
        """Dashboard should show the unacknowledged alerts stats card."""
        _login(page, live_server)
        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        expect(page.locator("text=未確認アラート").first).to_be_visible()

    def test_dashboard_alert_section_present(
        self, page, live_server, _seed_test_user
    ):
        """Dashboard should render the alert bell icon section."""
        _login(page, live_server)
        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        expect(page.locator(".bi-bell").first).to_be_visible()

    def test_dashboard_no_alerts_message(
        self, page, live_server, _seed_test_user
    ):
        """With no alerts, the dashboard should show the empty-state message."""
        _login(page, live_server)
        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        body_text = page.text_content("body")
        assert "未確認のアラートはありません" in body_text

    def test_dashboard_alert_stats_card_shows_count(
        self, page, live_server, _seed_test_user
    ):
        """The alert stats card should display a count (0 when no alerts)."""
        _login(page, live_server)
        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        alert_card = page.locator(
            ".dashboard-card:has-text('未確認アラート')"
        )
        card_text = alert_card.text_content()
        assert "0" in card_text

    def test_dashboard_with_seeded_alert(
        self, page, live_server, _seed_test_user, e2e_app
    ):
        """Seeding an alert should make it visible on the dashboard."""
        with e2e_app.app_context():
            from datetime import datetime, timezone

            alert = Alert(
                alert_type="backup_failure",
                severity="warning",
                title="E2E Test Alert",
                message="E2E test alert message",
                is_acknowledged=False,
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(alert)
            db.session.commit()

        try:
            _login(page, live_server)
            page.goto(f"{live_server}/dashboard")
            page.wait_for_load_state("networkidle")

            body_text = page.text_content("body")
            assert "E2E test alert message" in body_text
        finally:
            with e2e_app.app_context():
                Alert.query.filter_by(
                    message="E2E test alert message"
                ).delete()
                db.session.commit()

    def test_dashboard_alert_severity_labels(
        self, page, live_server, _seed_test_user
    ):
        """Dashboard should display severity label text for alert categories."""
        _login(page, live_server)
        page.goto(f"{live_server}/dashboard")
        page.wait_for_load_state("networkidle")

        body_text = page.text_content("body")
        assert "重大" in body_text
        assert "警告" in body_text
