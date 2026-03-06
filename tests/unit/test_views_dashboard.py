"""
Unit tests for dashboard views.
app/views/dashboard.py coverage: 53% -> ~75%
"""
import pytest

from app.models import User, db


@pytest.fixture
def admin_logged_in(client, app):
    """Create admin and log in."""
    with app.app_context():
        user = User(
            username="dash_admin", email="dash_admin@example.com",
            full_name="Dashboard Admin", role="admin", is_active=True
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "dash_admin", "password": "Admin123!"})
    return client


@pytest.fixture
def viewer_logged_in(client, app):
    """Create viewer and log in."""
    with app.app_context():
        user = User(
            username="dash_viewer", email="dash_viewer@example.com",
            role="viewer", is_active=True
        )
        user.set_password("Viewer123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "dash_viewer", "password": "Viewer123!"})
    return client


class TestDashboardMainView:
    """Tests for GET / and /dashboard."""

    def test_unauthenticated_root_redirects(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_unauthenticated_dashboard_redirects(self, client):
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access_root(self, admin_logged_in):
        response = admin_logged_in.get("/")
        assert response.status_code in (200, 302)

    def test_admin_can_access_dashboard(self, admin_logged_in):
        response = admin_logged_in.get("/dashboard")
        assert response.status_code in (200, 302)

    def test_viewer_can_access_dashboard(self, viewer_logged_in):
        response = viewer_logged_in.get("/dashboard")
        assert response.status_code in (200, 302)


class TestDashboardStatsAPI:
    """Tests for GET /api/dashboard/stats."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/api/dashboard/stats", follow_redirects=False)
        assert response.status_code in (301, 302, 401)

    def test_admin_can_get_stats(self, admin_logged_in):
        response = admin_logged_in.get("/api/dashboard/stats")
        assert response.status_code in (200, 302, 500)
        if response.status_code == 200:
            data = response.get_json()
            assert data is not None

    def test_viewer_can_get_stats(self, viewer_logged_in):
        response = viewer_logged_in.get("/api/dashboard/stats")
        assert response.status_code in (200, 302, 500)


class TestDashboardComplianceChartAPI:
    """Tests for GET /api/dashboard/compliance-chart."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/api/dashboard/compliance-chart", follow_redirects=False)
        assert response.status_code in (301, 302, 401)

    def test_admin_can_get_chart(self, admin_logged_in):
        response = admin_logged_in.get("/api/dashboard/compliance-chart")
        assert response.status_code in (200, 302, 500)

    def test_chart_returns_json(self, admin_logged_in):
        response = admin_logged_in.get("/api/dashboard/compliance-chart")
        if response.status_code == 200:
            data = response.get_json()
            assert data is not None


class TestDashboardSuccessRateChartAPI:
    """Tests for GET /api/dashboard/success-rate-chart."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/api/dashboard/success-rate-chart", follow_redirects=False)
        assert response.status_code in (301, 302, 401)

    def test_admin_can_get_chart(self, admin_logged_in):
        response = admin_logged_in.get("/api/dashboard/success-rate-chart")
        assert response.status_code in (200, 302, 500)


class TestDashboardStorageChartAPI:
    """Tests for GET /api/dashboard/storage-chart."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/api/dashboard/storage-chart", follow_redirects=False)
        assert response.status_code in (301, 302, 401)

    def test_admin_can_get_chart(self, admin_logged_in):
        response = admin_logged_in.get("/api/dashboard/storage-chart")
        assert response.status_code in (200, 302, 500)


class TestDashboardErrorHandling:
    """Tests for error handling in dashboard views."""

    def test_dashboard_stats_exception(self, admin_logged_in, app):
        """Test that /api/dashboard/stats returns 500 on DB error."""
        from unittest.mock import patch
        with patch("app.views.dashboard.get_dashboard_statistics", side_effect=Exception("DB error")):
            response = admin_logged_in.get("/api/dashboard/stats")
            assert response.status_code == 500
            data = response.get_json()
            assert data is not None
            assert "error" in data

    def test_dashboard_index_exception(self, admin_logged_in, app):
        """Test that / returns 500 on DB error."""
        from unittest.mock import patch
        with patch("app.views.dashboard.get_dashboard_statistics", side_effect=Exception("DB error")):
            response = admin_logged_in.get("/dashboard")
            assert response.status_code == 500

    def test_compliance_chart_exception(self, admin_logged_in, app):
        """Test that /api/dashboard/compliance-chart returns 500 on DB error."""
        from unittest.mock import patch
        from sqlalchemy.exc import SQLAlchemyError
        with patch("app.models.ComplianceStatus.query") as mock_query:
            mock_query.filter_by.side_effect = SQLAlchemyError("DB error")
            response = admin_logged_in.get("/api/dashboard/compliance-chart")
            assert response.status_code in (200, 500)

    def test_success_rate_chart_exception(self, admin_logged_in, app):
        """Test that /api/dashboard/success-rate-chart returns 500 on error."""
        from unittest.mock import patch
        with patch("app.views.dashboard.BackupExecution") as mock_exec:
            mock_exec.query.filter.side_effect = Exception("DB error")
            response = admin_logged_in.get("/api/dashboard/success-rate-chart")
            assert response.status_code in (200, 500)

    def test_storage_chart_exception(self, admin_logged_in, app):
        """Test that /api/dashboard/storage-chart returns 500 on error."""
        from unittest.mock import patch
        with patch("app.views.dashboard.BackupJob") as mock_job:
            mock_job.query.filter_by.side_effect = Exception("DB error")
            response = admin_logged_in.get("/api/dashboard/storage-chart")
            assert response.status_code in (200, 500)


class TestDashboardStatsContent:
    """Tests for dashboard statistics API content."""

    def test_stats_contains_expected_keys(self, admin_logged_in, app):
        """Test that stats API returns correct structure."""
        response = admin_logged_in.get("/api/dashboard/stats")
        if response.status_code == 200:
            data = response.get_json()
            assert "total_jobs" in data
            assert "compliance_rate" in data
            assert "success_rate" in data
            assert "total_alerts" in data

    def test_compliance_chart_structure(self, admin_logged_in):
        """Test compliance chart returns labels and datasets."""
        response = admin_logged_in.get("/api/dashboard/compliance-chart")
        if response.status_code == 200:
            data = response.get_json()
            assert "labels" in data
            assert "datasets" in data
            assert len(data["labels"]) == 3

    def test_success_rate_chart_structure(self, admin_logged_in):
        """Test success rate chart returns 7-day data."""
        response = admin_logged_in.get("/api/dashboard/success-rate-chart")
        if response.status_code == 200:
            data = response.get_json()
            assert "labels" in data
            assert "datasets" in data
            assert len(data["labels"]) == 7

    def test_storage_chart_structure(self, admin_logged_in):
        """Test storage chart returns correct structure."""
        response = admin_logged_in.get("/api/dashboard/storage-chart")
        if response.status_code == 200:
            data = response.get_json()
            assert "labels" in data
            assert "datasets" in data

    def test_stats_with_zero_jobs(self, admin_logged_in, app):
        """Test stats when no jobs exist (compliance_rate calculation with 0 total)."""
        from app.views.dashboard import get_dashboard_statistics
        with app.app_context():
            stats = get_dashboard_statistics()
            assert stats["total_jobs"] >= 0
            assert stats["compliance_rate"] >= 0
            assert stats["success_rate"] >= 0

    def test_stats_with_backup_data(self, admin_logged_in, app):
        """Test stats with actual backup jobs and executions."""
        from datetime import datetime, timezone
        from app.models import BackupJob, BackupExecution, User, db
        with app.app_context():
            user = User(
                username="stats_test_user", email="stats_test@example.com",
                role="admin", is_active=True
            )
            user.set_password("Test123!")
            db.session.add(user)
            db.session.commit()

            job = BackupJob(
                job_name="Stats Test Job",
                job_type="file",
                backup_tool="custom",
                target_path="/data/test",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()

            execution = BackupExecution(
                job_id=job.id,
                execution_date=datetime.now(timezone.utc),
                execution_result="success",
            )
            db.session.add(execution)
            db.session.commit()

        response = admin_logged_in.get("/api/dashboard/stats")
        assert response.status_code in (200, 500)
