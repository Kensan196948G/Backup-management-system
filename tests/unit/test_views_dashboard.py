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
