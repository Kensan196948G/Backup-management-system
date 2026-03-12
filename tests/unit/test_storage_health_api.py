"""
Unit tests for app/api/v1/storage_health.py and the backup-progress endpoint.

Covers:
  - GET /api/v1/storage/health       (unauthenticated, empty DB, with data)
  - GET /api/v1/storage/capacity     (unauthenticated, active-only filter, capacity math)
  - GET /api/v1/storage/alerts       (no alerts, threshold alert, sorting, role check)
  - GET /api/v1/dashboard/backup-progress (unauthenticated, empty, with recent execution)
"""

import app.api.v1.storage_health  # register routes onto api_bp  # noqa: F401

from datetime import datetime, timedelta, timezone

import pytest

from app.models import BackupExecution, BackupJob, StorageProvider, User, db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_jwt_token(client, app, username="sh_admin", role="admin"):
    """Create a user and return a JWT access token."""
    with app.app_context():
        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                email=f"{username}@example.com",
                full_name="Storage Health Admin",
                role=role,
                is_active=True,
            )
            user.set_password("Admin123!@#")
            db.session.add(user)
            db.session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Admin123!@#"},
        content_type="application/json",
    )
    assert resp.status_code == 200, f"Login failed: {resp.get_data(as_text=True)}"
    return resp.get_json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _make_provider(app, name="Primary NAS", provider_type="nfs", connection_status="online",
                   is_active=True, total_capacity=None, used_capacity=None, success_rate=100.0):
    """Insert a StorageProvider and return its id."""
    with app.app_context():
        # Need a user for created_by_id (nullable, so skip)
        provider = StorageProvider(
            name=name,
            provider_type=provider_type,
            endpoint="/mnt/nas",
            is_active=is_active,
            connection_status=connection_status,
            total_capacity=total_capacity,
            used_capacity=used_capacity,
            backup_count=2,
            file_count=10,
            success_rate=success_rate,
            last_check=datetime.now(timezone.utc),
        )
        db.session.add(provider)
        db.session.commit()
        return provider.id


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/storage/health
# ---------------------------------------------------------------------------


class TestGetStorageHealth:

    def test_unauthenticated_returns_401(self, client):
        """Health endpoint requires authentication."""
        resp = client.get("/api/v1/storage/health")
        assert resp.status_code == 401

    def test_returns_200_with_empty_db(self, client, app):
        """Health endpoint returns empty list when no providers exist."""
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/health", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["total"] == 0

    def test_returns_provider_with_healthy_status(self, client, app):
        """Online provider with low usage reports 'healthy'."""
        _make_provider(app, total_capacity=100 * 1024 ** 3, used_capacity=20 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/health", headers=_auth_headers(token))
        assert resp.status_code == 200
        providers = resp.get_json()["data"]
        assert len(providers) >= 1
        provider = providers[0]
        assert provider["health_status"] == "healthy"
        assert provider["connection_status"] == "online"
        assert "usage_percent" in provider

    def test_offline_provider_returns_critical(self, client, app):
        """Offline provider reports 'critical' health status."""
        _make_provider(app, name="Offline NAS", connection_status="offline",
                       total_capacity=100 * 1024 ** 3, used_capacity=10 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/health", headers=_auth_headers(token))
        data = resp.get_json()
        offline = [p for p in data["data"] if p["name"] == "Offline NAS"]
        assert len(offline) == 1
        assert offline[0]["health_status"] == "critical"

    def test_high_usage_provider_returns_warning(self, client, app):
        """Provider at 85% usage reports 'warning' health status."""
        _make_provider(app, name="Full NAS", total_capacity=100 * 1024 ** 3,
                       used_capacity=85 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/health", headers=_auth_headers(token))
        data = resp.get_json()
        full = [p for p in data["data"] if p["name"] == "Full NAS"]
        assert len(full) == 1
        assert full[0]["health_status"] == "warning"
        assert full[0]["usage_percent"] == pytest.approx(85.0, abs=0.1)

    def test_response_includes_timestamp(self, client, app):
        """Health response includes an ISO timestamp."""
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/health", headers=_auth_headers(token))
        data = resp.get_json()
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/storage/capacity
# ---------------------------------------------------------------------------


class TestGetStorageCapacity:

    def test_unauthenticated_returns_401(self, client):
        """Capacity endpoint requires authentication."""
        resp = client.get("/api/v1/storage/capacity")
        assert resp.status_code == 401

    def test_returns_only_active_providers(self, client, app):
        """Capacity endpoint only returns active providers."""
        _make_provider(app, name="Active Store", is_active=True,
                       total_capacity=200 * 1024 ** 3, used_capacity=50 * 1024 ** 3)
        _make_provider(app, name="Inactive Store", is_active=False,
                       total_capacity=100 * 1024 ** 3, used_capacity=10 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/capacity", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.get_json()
        names = [p["name"] for p in data["data"]]
        assert "Active Store" in names
        assert "Inactive Store" not in names

    def test_capacity_fields_present(self, client, app):
        """Capacity response includes all required fields."""
        _make_provider(app, total_capacity=500 * 1024 ** 3, used_capacity=100 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/capacity", headers=_auth_headers(token))
        data = resp.get_json()
        assert data["success"] is True
        item = data["data"][0]
        for field in ("id", "name", "provider_type", "total_bytes", "used_bytes",
                      "free_bytes", "usage_percent", "backup_count"):
            assert field in item, f"Missing field: {field}"

    def test_free_bytes_calculated_correctly(self, client, app):
        """free_bytes = total_bytes - used_bytes."""
        total = 1_000_000_000
        used = 400_000_000
        _make_provider(app, total_capacity=total, used_capacity=used)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/capacity", headers=_auth_headers(token))
        item = resp.get_json()["data"][0]
        assert item["free_bytes"] == total - used
        assert item["usage_percent"] == pytest.approx(40.0, abs=0.01)


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/storage/alerts
# ---------------------------------------------------------------------------


class TestGetStorageAlerts:

    def test_unauthenticated_returns_401(self, client):
        """Alerts endpoint requires authentication."""
        resp = client.get("/api/v1/storage/alerts")
        assert resp.status_code == 401

    def test_viewer_role_returns_403(self, client, app):
        """Alerts endpoint denies viewers (requires admin or operator)."""
        _get_jwt_token(client, app, username="sh_viewer", role="viewer")
        token = _get_jwt_token(client, app, username="sh_viewer", role="viewer")
        resp = client.get("/api/v1/storage/alerts", headers=_auth_headers(token))
        assert resp.status_code == 403

    def test_no_alerts_when_usage_below_threshold(self, client, app):
        """No alerts when all providers are below 80% usage."""
        _make_provider(app, total_capacity=100 * 1024 ** 3, used_capacity=50 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/alerts", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 0
        assert data["data"] == []

    def test_alert_raised_above_threshold(self, client, app):
        """Alert is raised when provider exceeds 80% usage."""
        _make_provider(app, name="Alert NAS", total_capacity=100 * 1024 ** 3,
                       used_capacity=82 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/alerts", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        alert = data["data"][0]
        assert alert["usage_percent"] >= 80
        assert alert["severity"] == "warning"
        assert "alert_message" in alert

    def test_critical_severity_above_95_percent(self, client, app):
        """Provider at 96% usage triggers a 'critical' severity alert."""
        _make_provider(app, name="Critical NAS", total_capacity=100 * 1024 ** 3,
                       used_capacity=96 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/alerts", headers=_auth_headers(token))
        data = resp.get_json()
        critical = [a for a in data["data"] if a["name"] == "Critical NAS"]
        assert len(critical) == 1
        assert critical[0]["severity"] == "critical"

    def test_alerts_sorted_by_usage_descending(self, client, app):
        """Multiple alerts are sorted with highest usage first."""
        _make_provider(app, name="NAS-A", total_capacity=100 * 1024 ** 3,
                       used_capacity=81 * 1024 ** 3)
        _make_provider(app, name="NAS-B", total_capacity=100 * 1024 ** 3,
                       used_capacity=96 * 1024 ** 3)
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/alerts", headers=_auth_headers(token))
        data = resp.get_json()
        assert data["total"] >= 2
        percents = [a["usage_percent"] for a in data["data"]]
        assert percents == sorted(percents, reverse=True)

    def test_response_includes_threshold(self, client, app):
        """Alerts response includes the threshold_percent value."""
        token = _get_jwt_token(client, app)
        resp = client.get("/api/v1/storage/alerts", headers=_auth_headers(token))
        data = resp.get_json()
        assert "threshold_percent" in data
        assert data["threshold_percent"] == 80.0


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/dashboard/backup-progress
# ---------------------------------------------------------------------------


class TestGetBackupProgress:

    def test_unauthenticated_returns_401(self, client):
        """Backup progress endpoint requires authentication."""
        resp = client.get("/api/v1/dashboard/backup-progress")
        assert resp.status_code == 401

    def test_returns_empty_when_no_recent_executions(self, authenticated_client):
        """Returns empty list when there are no executions in the last 2 hours."""
        resp = authenticated_client.get("/api/v1/dashboard/backup-progress")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_returns_recent_execution_with_progress(self, authenticated_client, app):
        """Recent execution within 2 hours is returned with progress percentage."""
        with app.app_context():
            owner = User.query.filter_by(username="admin_test").first()
            job = BackupJob(
                job_name="Progress Test Job",
                job_type="file",
                target_server="server1",
                target_path="/data",
                backup_tool="custom",
                schedule_type="daily",
                retention_days=30,
                owner_id=owner.id,
                is_active=True,
            )
            db.session.add(job)
            db.session.flush()

            execution = BackupExecution(
                job_id=job.id,
                execution_date=datetime.now(timezone.utc) - timedelta(minutes=10),
                execution_result="success",
                backup_size_bytes=1024 * 1024,
                duration_seconds=600,
                source_system="manual",
            )
            db.session.add(execution)
            db.session.commit()

        resp = authenticated_client.get("/api/v1/dashboard/backup-progress")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        item = data["data"][0]
        assert "progress_percent" in item
        assert "elapsed_seconds" in item
        assert "job_name" in item
        assert 0 < item["progress_percent"] <= 99.0
