"""
E2E Tests: Backup Jobs

Tests the backup job list page and job creation wizard flow
using Playwright against a live Flask server.
"""

import re

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


class TestJobList:
    """Backup job list page tests."""

    def test_job_list_page_loads(self, page, live_server, _seed_test_user):
        """Job list page should load and display the heading."""
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        assert "/auth/login" not in page.url
        expect(page).to_have_title(re.compile("ジョブ"))

    def test_job_list_has_heading(self, page, live_server, _seed_test_user):
        """Job list page should display the main heading."""
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        heading = page.locator("h1")
        expect(heading).to_contain_text("バックアップジョブ一覧")

    def test_job_list_has_create_button(self, page, live_server, _seed_test_user):
        """Job list page should have a create-new-job button."""
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        create_link = page.locator("a:has-text('新規ジョブ作成')")
        expect(create_link).to_be_visible()

    def test_job_list_has_filter_form(self, page, live_server, _seed_test_user):
        """Job list page should display search and type filter inputs."""
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#search")).to_be_visible()
        expect(page.locator("#type")).to_be_visible()

    def test_job_list_create_button_navigates(
        self, page, live_server, _seed_test_user
    ):
        """Clicking the create button should navigate to the creation wizard."""
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/")
        page.wait_for_load_state("networkidle")

        page.locator("a:has-text('新規ジョブ作成')").click()
        page.wait_for_load_state("networkidle")

        assert "/jobs/create" in page.url


class TestJobCreate:
    """Job creation wizard tests."""

    def test_create_page_loads(self, page, live_server, _seed_test_user):
        """Job creation page should load with the wizard UI."""
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/create")
        page.wait_for_load_state("networkidle")

        assert "/auth/login" not in page.url
        expect(page).to_have_title(re.compile("ジョブ作成"))

    def test_create_page_has_wizard_steps(
        self, page, live_server, _seed_test_user
    ):
        """Creation page should show at least 3 wizard steps."""
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/create")
        page.wait_for_load_state("networkidle")

        assert page.locator(".wizard-step").count() >= 3
        expect(page.locator(".wizard-step.active")).to_be_visible()

    def test_create_page_step1_fields(
        self, page, live_server, _seed_test_user
    ):
        """Step 1 should have job name, type, and target server fields."""
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/create")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#job_name")).to_be_visible()
        expect(page.locator("#job_type")).to_be_visible()
        expect(page.locator("#target_server")).to_be_visible()

    def test_create_job_full_wizard_flow(
        self, page, live_server, _seed_test_user, e2e_app
    ):
        """Complete the full job creation wizard and verify the job is created.

        The form's submit handler shows a confirm() dialog that must be
        accepted via Playwright's dialog API for the form to actually submit.
        """
        _login(page, live_server)
        page.goto(f"{live_server}/jobs/create")
        page.wait_for_load_state("networkidle")

        # Step 1: Basic Info
        page.fill("#job_name", "E2E Test Backup Job")
        page.select_option("#job_type", "file")
        page.fill("#target_server", "e2e-test-server")
        page.fill("#description", "Created by E2E test")
        page.click("#nextBtn")
        page.wait_for_timeout(500)

        # Step 2: Backup Settings
        page.fill("#source_path", "/data/source")
        page.fill("#destination_path", "/mnt/backup/dest")
        page.select_option("#backup_tool", "veeam")
        page.click("#nextBtn")
        page.wait_for_timeout(500)

        # Step 3: Advanced Options - submit button should be visible
        submit_btn = page.locator("#submitBtn")
        expect(submit_btn).to_be_visible()

        # Register a dialog handler to accept the confirm() prompt
        page.on("dialog", lambda dialog: dialog.accept())

        submit_btn.click()
        page.wait_for_load_state("networkidle")

        # After successful creation, the page should redirect away from /jobs/create
        assert "/jobs/create" not in page.url

        body_text = page.text_content("body")
        assert body_text is not None
        assert (
            "E2E Test Backup Job" in body_text or "作成しました" in body_text
        )
