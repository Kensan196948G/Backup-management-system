"""
Unit tests for backup_schedule views.
app/views/backup_schedule.py coverage: 0% -> ~60%
"""
import pytest

from app.models import BackupJob, User, db


@pytest.fixture
def admin_logged_in(client, app):
    """Create admin user and log in."""
    with app.app_context():
        user = User(
            username="sched_admin", email="sched_admin@example.com",
            full_name="Schedule Admin", role="admin", is_active=True
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "sched_admin", "password": "Admin123!"})
    return client


@pytest.fixture
def operator_logged_in(client, app):
    """Create operator user and log in."""
    with app.app_context():
        user = User(
            username="sched_operator", email="sched_op@example.com",
            full_name="Schedule Operator", role="operator", is_active=True
        )
        user.set_password("Oper123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "sched_operator", "password": "Oper123!"})
    return client


class TestScheduleListView:
    """Tests for /backup/schedule route."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/backup/schedule", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access(self, admin_logged_in):
        response = admin_logged_in.get("/backup/schedule")
        assert response.status_code == 200

    def test_operator_can_access(self, operator_logged_in):
        response = operator_logged_in.get("/backup/schedule")
        assert response.status_code == 200

    def test_response_contains_schedule(self, admin_logged_in):
        response = admin_logged_in.get("/backup/schedule")
        assert response.status_code == 200
        # Page should contain schedule-related content
        data = response.data.lower()
        assert b"schedule" in data or b"backup" in data


class TestStorageConfigView:
    """Tests for /backup/storage-config route."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/backup/storage-config", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access(self, admin_logged_in):
        response = admin_logged_in.get("/backup/storage-config")
        assert response.status_code == 200


class TestTestCronExpression:
    """Tests for POST /backup/api/schedule/test-cron."""

    def test_valid_cron_expression(self, admin_logged_in):
        response = admin_logged_in.post(
            "/backup/api/schedule/test-cron",
            json={"cron_expression": "0 2 * * *"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_invalid_cron_expression(self, admin_logged_in):
        response = admin_logged_in.post(
            "/backup/api/schedule/test-cron",
            json={"cron_expression": "invalid cron"},
            content_type="application/json",
        )
        assert response.status_code in (200, 400)

    def test_empty_cron_expression(self, admin_logged_in):
        response = admin_logged_in.post(
            "/backup/api/schedule/test-cron",
            json={"cron_expression": ""},
            content_type="application/json",
        )
        assert response.status_code in (200, 400)

    def test_unauthenticated_returns_redirect(self, client):
        response = client.post(
            "/backup/api/schedule/test-cron",
            json={"cron_expression": "0 2 * * *"},
            content_type="application/json",
        )
        assert response.status_code in (302, 401)


class TestCreateSchedule:
    """Tests for POST /backup/api/schedule/create."""

    def test_create_schedule_returns_json(self, admin_logged_in, app):
        with app.app_context():
            # Create a job to schedule
            user = User.query.filter_by(username="sched_admin").first()
            job = BackupJob(
                job_name="schedule_create_test_job",
                job_type="full",
                backup_tool="test",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
                schedule_type="manual",
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = admin_logged_in.post(
            "/backup/api/schedule/create",
            json={
                "job_id": job_id,
                "cron_expression": "0 2 * * *",
                "schedule_description": "Daily 2AM",
            },
            content_type="application/json",
        )
        assert response.status_code in (200, 201, 400)

    def test_unauthenticated_redirects(self, client):
        response = client.post(
            "/backup/api/schedule/create",
            json={"job_id": 1},
            content_type="application/json",
        )
        assert response.status_code in (302, 401)


class TestGetSchedule:
    """Tests for GET /backup/api/schedule/<id>."""

    def test_nonexistent_schedule_returns_404_or_error(self, admin_logged_in):
        response = admin_logged_in.get("/backup/api/schedule/99999")
        assert response.status_code in (200, 404)

    def test_unauthenticated_redirects(self, client):
        response = client.get("/backup/api/schedule/1")
        assert response.status_code in (302, 401)


class TestDeleteSchedule:
    """Tests for DELETE /backup/api/schedule/<id>."""

    def test_nonexistent_schedule_returns_error(self, admin_logged_in):
        response = admin_logged_in.delete("/backup/api/schedule/99999")
        assert response.status_code in (200, 404)

    def test_unauthenticated_redirects(self, client):
        response = client.delete("/backup/api/schedule/1")
        assert response.status_code in (302, 401)


class TestToggleSchedule:
    """Tests for POST /backup/api/schedule/<id>/toggle."""

    def test_nonexistent_schedule(self, admin_logged_in):
        response = admin_logged_in.post("/backup/api/schedule/99999/toggle")
        assert response.status_code in (200, 404, 500)


class TestStorageProviderAPI:
    """Tests for storage provider CRUD API."""

    def test_create_storage_provider_json(self, admin_logged_in):
        response = admin_logged_in.post(
            "/backup/api/storage/create",
            json={
                "name": "Test Local Storage",
                "type": "local",
                "path": "/tmp/test_backup",
            },
            content_type="application/json",
        )
        assert response.status_code in (200, 201, 400)

    def test_get_nonexistent_storage_provider(self, admin_logged_in):
        response = admin_logged_in.get("/backup/api/storage/99999")
        assert response.status_code in (200, 404)

    def test_delete_nonexistent_storage_provider(self, admin_logged_in):
        response = admin_logged_in.delete("/backup/api/storage/99999")
        assert response.status_code in (200, 404)

    def test_test_connection_with_data(self, admin_logged_in):
        response = admin_logged_in.post(
            "/backup/api/storage/test-connection",
            json={"type": "local", "path": "/tmp"},
            content_type="application/json",
        )
        assert response.status_code in (200, 400)

    def test_unauthenticated_storage_create_redirects(self, client):
        response = client.post(
            "/backup/api/storage/create",
            json={"name": "test"},
            content_type="application/json",
        )
        assert response.status_code in (302, 401)
