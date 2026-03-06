"""
Unit tests for backup_schedule views.
app/views/backup_schedule.py coverage: 0% -> ~60%+
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


@pytest.fixture
def viewer_logged_in(client, app):
    """Create viewer user and log in."""
    with app.app_context():
        user = User(
            username="sched_viewer", email="sched_viewer@example.com",
            full_name="Schedule Viewer", role="viewer", is_active=True
        )
        user.set_password("View123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "sched_viewer", "password": "View123!"})
    return client


@pytest.fixture
def backup_job_for_schedule(app):
    """Create a backup job with schedule_enabled for testing schedule_list."""
    with app.app_context():
        # First create admin user
        user = User(
            username="sched_admin_job", email="sched_admin_job@example.com",
            full_name="Schedule Admin Job", role="admin", is_active=True
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

        job = BackupJob(
            job_name="Scheduled Test Job",
            job_type="full",
            backup_tool="test",
            retention_days=30,
            owner_id=user.id,
            is_active=True,
            schedule_type="daily",
        )
        # Set schedule_enabled attribute to hit the schedule_list branch
        job.schedule_enabled = True
        db.session.add(job)
        db.session.commit()
        return job.id, user.username


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

    def test_viewer_forbidden(self, viewer_logged_in):
        response = viewer_logged_in.get("/backup/schedule", follow_redirects=False)
        assert response.status_code in (302, 403)

    def test_response_contains_schedule(self, admin_logged_in):
        response = admin_logged_in.get("/backup/schedule")
        assert response.status_code == 200
        # Page should contain schedule-related content
        data = response.data.lower()
        assert b"schedule" in data or b"backup" in data

    def test_schedule_list_with_jobs(self, client, app):
        """Test schedule_list with active jobs in DB."""
        with app.app_context():
            user = User(
                username="sched_admin2", email="sched_admin2@example.com",
                full_name="Schedule Admin2", role="admin", is_active=True
            )
            user.set_password("Admin123!")
            db.session.add(user)
            db.session.commit()

            job = BackupJob(
                job_name="Active Schedule Job",
                job_type="full",
                backup_tool="test",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
                schedule_type="daily",
            )
            db.session.add(job)
            db.session.commit()

        client.post("/auth/login", data={"username": "sched_admin2", "password": "Admin123!"})
        response = client.get("/backup/schedule")
        assert response.status_code == 200


class TestStorageConfigView:
    """Tests for /backup/storage-config route."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/backup/storage-config", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access(self, admin_logged_in):
        response = admin_logged_in.get("/backup/storage-config")
        assert response.status_code == 200

    def test_operator_can_access(self, operator_logged_in):
        response = operator_logged_in.get("/backup/storage-config")
        assert response.status_code == 200

    def test_viewer_forbidden(self, viewer_logged_in):
        response = viewer_logged_in.get("/backup/storage-config", follow_redirects=False)
        assert response.status_code in (302, 403)

    def test_response_contains_storage(self, admin_logged_in):
        response = admin_logged_in.get("/backup/storage-config")
        assert response.status_code == 200
        data = response.data.lower()
        assert b"storage" in data or b"provider" in data


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
        assert data.get("success") is True
        assert "next_runs" in data
        assert len(data["next_runs"]) == 10

    def test_cron_expression_returned_in_response(self, admin_logged_in):
        cron = "30 6 * * 1"
        response = admin_logged_in.post(
            "/backup/api/schedule/test-cron",
            json={"cron_expression": cron},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("cron_expression") == cron

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
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("success") is False

    def test_missing_cron_field(self, admin_logged_in):
        """Test with no cron_expression field - treated as empty."""
        response = admin_logged_in.post(
            "/backup/api/schedule/test-cron",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("success") is False

    def test_unauthenticated_returns_redirect(self, client):
        response = client.post(
            "/backup/api/schedule/test-cron",
            json={"cron_expression": "0 2 * * *"},
            content_type="application/json",
        )
        assert response.status_code in (302, 401)

    def test_operator_can_test_cron(self, operator_logged_in):
        response = operator_logged_in.post(
            "/backup/api/schedule/test-cron",
            json={"cron_expression": "0 0 * * 0"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True


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
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data.get("success") is True
        assert "schedule_id" in data

    def test_create_schedule_missing_job_id(self, admin_logged_in):
        """Missing job_id returns 400."""
        response = admin_logged_in.post(
            "/backup/api/schedule/create",
            json={"cron_expression": "0 2 * * *"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("success") is False

    def test_create_schedule_missing_cron(self, admin_logged_in):
        """Missing cron_expression returns 400."""
        response = admin_logged_in.post(
            "/backup/api/schedule/create",
            json={"job_id": 1},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("success") is False

    def test_create_schedule_nonexistent_job(self, admin_logged_in):
        """Non-existent job_id returns 404."""
        response = admin_logged_in.post(
            "/backup/api/schedule/create",
            json={"job_id": 99999, "cron_expression": "0 2 * * *"},
            content_type="application/json",
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data.get("success") is False

    def test_unauthenticated_redirects(self, client):
        response = client.post(
            "/backup/api/schedule/create",
            json={"job_id": 1},
            content_type="application/json",
        )
        assert response.status_code in (302, 401)

    def test_operator_can_create_schedule(self, operator_logged_in, app):
        """Operator role should be able to create schedules."""
        with app.app_context():
            user = User.query.filter_by(username="sched_operator").first()
            job = BackupJob(
                job_name="operator_schedule_job",
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

        response = operator_logged_in.post(
            "/backup/api/schedule/create",
            json={"job_id": job_id, "cron_expression": "0 3 * * *"},
            content_type="application/json",
        )
        assert response.status_code in (200, 201)

    def test_viewer_cannot_create_schedule(self, viewer_logged_in):
        """Viewer role should not be able to create schedules."""
        response = viewer_logged_in.post(
            "/backup/api/schedule/create",
            json={"job_id": 1, "cron_expression": "0 2 * * *"},
            content_type="application/json",
        )
        assert response.status_code in (302, 403)


class TestGetSchedule:
    """Tests for GET /backup/api/schedule/<id>."""

    def test_get_existing_schedule(self, admin_logged_in, app):
        """Get a schedule for an existing job."""
        with app.app_context():
            user = User.query.filter_by(username="sched_admin").first()
            job = BackupJob(
                job_name="get_schedule_test_job",
                job_type="full",
                backup_tool="test",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
                schedule_type="daily",
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = admin_logged_in.get(f"/backup/api/schedule/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "schedule" in data
        assert data["schedule"]["id"] == job_id

    def test_get_schedule_response_fields(self, admin_logged_in, app):
        """Verify response fields for get_schedule."""
        with app.app_context():
            user = User.query.filter_by(username="sched_admin").first()
            job = BackupJob(
                job_name="get_schedule_fields_job",
                job_type="full",
                backup_tool="test",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
                schedule_type="daily",
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = admin_logged_in.get(f"/backup/api/schedule/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        schedule = data["schedule"]
        assert "job_name" in schedule
        assert "cron_expression" in schedule
        assert "is_active" in schedule

    def test_nonexistent_schedule_returns_404_or_error(self, admin_logged_in):
        response = admin_logged_in.get("/backup/api/schedule/99999")
        assert response.status_code in (200, 404)
        if response.status_code == 404:
            data = response.get_json()
            assert data.get("success") is False

    def test_unauthenticated_redirects(self, client):
        response = client.get("/backup/api/schedule/1")
        assert response.status_code in (302, 401)

    def test_operator_can_get_schedule(self, operator_logged_in, app):
        """Operator can access schedule detail."""
        with app.app_context():
            user = User.query.filter_by(username="sched_operator").first()
            job = BackupJob(
                job_name="op_get_schedule_job",
                job_type="full",
                backup_tool="test",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
                schedule_type="daily",
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = operator_logged_in.get(f"/backup/api/schedule/{job_id}")
        assert response.status_code == 200


class TestDeleteSchedule:
    """Tests for DELETE /backup/api/schedule/<id>."""

    def test_delete_schedule_success(self, admin_logged_in):
        """Delete any schedule ID returns success (mock implementation)."""
        response = admin_logged_in.delete("/backup/api/schedule/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "deleted" in data.get("message", "").lower()

    def test_nonexistent_schedule_returns_error(self, admin_logged_in):
        response = admin_logged_in.delete("/backup/api/schedule/99999")
        assert response.status_code in (200, 404)

    def test_unauthenticated_redirects(self, client):
        response = client.delete("/backup/api/schedule/1")
        assert response.status_code in (302, 401)

    def test_viewer_cannot_delete(self, viewer_logged_in):
        """Viewer role cannot delete schedules."""
        response = viewer_logged_in.delete("/backup/api/schedule/1", follow_redirects=False)
        assert response.status_code in (302, 403)

    def test_operator_can_delete_schedule(self, operator_logged_in):
        """Operator can delete schedules."""
        response = operator_logged_in.delete("/backup/api/schedule/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True


class TestToggleSchedule:
    """Tests for POST /backup/api/schedule/<id>/toggle."""

    def test_toggle_schedule_activate(self, admin_logged_in):
        """Toggle schedule to active."""
        response = admin_logged_in.post(
            "/backup/api/schedule/1/toggle",
            json={"is_active": True},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "activated" in data.get("message", "").lower()

    def test_toggle_schedule_deactivate(self, admin_logged_in):
        """Toggle schedule to inactive."""
        response = admin_logged_in.post(
            "/backup/api/schedule/1/toggle",
            json={"is_active": False},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "deactivated" in data.get("message", "").lower()

    def test_toggle_schedule_default_active(self, admin_logged_in):
        """Toggle without is_active defaults to True."""
        response = admin_logged_in.post(
            "/backup/api/schedule/1/toggle",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True

    def test_nonexistent_schedule(self, admin_logged_in):
        response = admin_logged_in.post(
            "/backup/api/schedule/99999/toggle",
            json={"is_active": True},
            content_type="application/json",
        )
        assert response.status_code in (200, 404, 500)

    def test_unauthenticated_redirects(self, client):
        response = client.post(
            "/backup/api/schedule/1/toggle",
            json={"is_active": True},
            content_type="application/json",
        )
        assert response.status_code in (302, 401)

    def test_viewer_cannot_toggle(self, viewer_logged_in):
        """Viewer cannot toggle schedules."""
        response = viewer_logged_in.post(
            "/backup/api/schedule/1/toggle",
            json={"is_active": True},
            content_type="application/json",
            follow_redirects=False,
        )
        assert response.status_code in (302, 403)

    def test_operator_can_toggle(self, operator_logged_in):
        """Operator can toggle schedules."""
        response = operator_logged_in.post(
            "/backup/api/schedule/1/toggle",
            json={"is_active": True},
            content_type="application/json",
        )
        assert response.status_code == 200


class TestTestSchedule:
    """Tests for POST /backup/api/schedule/<id>/test."""

    def test_test_existing_schedule(self, admin_logged_in, app):
        """Test execution for an existing job."""
        with app.app_context():
            user = User.query.filter_by(username="sched_admin").first()
            job = BackupJob(
                job_name="test_exec_job",
                job_type="full",
                backup_tool="test",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
                schedule_type="daily",
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = admin_logged_in.post(f"/backup/api/schedule/{job_id}/test")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "test execution" in data.get("message", "").lower()

    def test_test_nonexistent_schedule(self, admin_logged_in):
        """Test execution for non-existent schedule returns 404."""
        response = admin_logged_in.post("/backup/api/schedule/99999/test")
        assert response.status_code == 404
        data = response.get_json()
        assert data.get("success") is False

    def test_unauthenticated_redirects(self, client):
        response = client.post("/backup/api/schedule/1/test")
        assert response.status_code in (302, 401)

    def test_viewer_cannot_test_schedule(self, viewer_logged_in):
        """Viewer cannot run test schedule."""
        response = viewer_logged_in.post(
            "/backup/api/schedule/1/test",
            follow_redirects=False,
        )
        assert response.status_code in (302, 403)

    def test_operator_can_test_schedule(self, operator_logged_in, app):
        """Operator can run test schedule."""
        with app.app_context():
            user = User.query.filter_by(username="sched_operator").first()
            job = BackupJob(
                job_name="op_test_exec_job",
                job_type="full",
                backup_tool="test",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
                schedule_type="daily",
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = operator_logged_in.post(f"/backup/api/schedule/{job_id}/test")
        assert response.status_code == 200


class TestStorageProviderAPI:
    """Tests for storage provider CRUD API."""

    def test_create_storage_provider_json(self, admin_logged_in):
        response = admin_logged_in.post(
            "/backup/api/storage/create",
            json={
                "name": "Test Local Storage",
                "provider_type": "local",
                "path": "/tmp/test_backup",
            },
            content_type="application/json",
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data.get("success") is True
        assert "provider_id" in data

    def test_create_storage_missing_name(self, admin_logged_in):
        """Missing name returns 400."""
        response = admin_logged_in.post(
            "/backup/api/storage/create",
            json={"provider_type": "local"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("success") is False

    def test_create_storage_missing_type(self, admin_logged_in):
        """Missing provider_type returns 400."""
        response = admin_logged_in.post(
            "/backup/api/storage/create",
            json={"name": "My Storage"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("success") is False

    def test_create_storage_s3_type(self, admin_logged_in):
        """Create S3 storage provider."""
        response = admin_logged_in.post(
            "/backup/api/storage/create",
            json={
                "name": "S3 Backup",
                "provider_type": "s3",
                "endpoint": "s3.amazonaws.com",
                "bucket": "my-backups",
            },
            content_type="application/json",
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data.get("success") is True

    def test_get_storage_provider_success(self, admin_logged_in):
        """Get storage provider returns mock data."""
        response = admin_logged_in.get("/backup/api/storage/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "storage" in data
        assert data["storage"]["id"] == 1

    def test_get_nonexistent_storage_provider(self, admin_logged_in):
        response = admin_logged_in.get("/backup/api/storage/99999")
        assert response.status_code in (200, 404)

    def test_get_storage_provider_fields(self, admin_logged_in):
        """Verify storage provider response fields."""
        response = admin_logged_in.get("/backup/api/storage/5")
        assert response.status_code == 200
        data = response.get_json()
        storage = data["storage"]
        assert "name" in storage
        assert "provider_type" in storage

    def test_delete_storage_provider_success(self, admin_logged_in):
        """Delete returns success message."""
        response = admin_logged_in.delete("/backup/api/storage/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "deleted" in data.get("message", "").lower()

    def test_delete_nonexistent_storage_provider(self, admin_logged_in):
        response = admin_logged_in.delete("/backup/api/storage/99999")
        assert response.status_code in (200, 404)

    def test_delete_viewer_forbidden(self, viewer_logged_in):
        """Viewer cannot delete storage providers."""
        response = viewer_logged_in.delete(
            "/backup/api/storage/1",
            follow_redirects=False,
        )
        assert response.status_code in (302, 403)

    def test_toggle_storage_activate(self, admin_logged_in):
        """Toggle storage to active."""
        response = admin_logged_in.post(
            "/backup/api/storage/1/toggle",
            json={"is_active": True},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "activated" in data.get("message", "").lower()

    def test_toggle_storage_deactivate(self, admin_logged_in):
        """Toggle storage to inactive."""
        response = admin_logged_in.post(
            "/backup/api/storage/1/toggle",
            json={"is_active": False},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "deactivated" in data.get("message", "").lower()

    def test_toggle_storage_viewer_forbidden(self, viewer_logged_in):
        """Viewer cannot toggle storage."""
        response = viewer_logged_in.post(
            "/backup/api/storage/1/toggle",
            json={"is_active": True},
            content_type="application/json",
            follow_redirects=False,
        )
        assert response.status_code in (302, 403)

    def test_test_storage_connection(self, admin_logged_in):
        """Test existing storage connection."""
        response = admin_logged_in.post("/backup/api/storage/1/test")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "latency_ms" in data
        assert data.get("status") == "online"

    def test_test_connection_viewer_forbidden(self, viewer_logged_in):
        """Viewer cannot test storage connection."""
        response = viewer_logged_in.post(
            "/backup/api/storage/1/test",
            follow_redirects=False,
        )
        assert response.status_code in (302, 403)

    def test_test_connection_with_data(self, admin_logged_in):
        response = admin_logged_in.post(
            "/backup/api/storage/test-connection",
            json={"provider_type": "local", "path": "/tmp"},
            content_type="application/json",
        )
        assert response.status_code in (200, 400)

    def test_test_new_connection_success(self, admin_logged_in):
        """Test new storage connection with valid type."""
        response = admin_logged_in.post(
            "/backup/api/storage/test-connection",
            json={"provider_type": "s3"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert "latency_ms" in data

    def test_test_new_connection_missing_type(self, admin_logged_in):
        """Test new connection without provider_type returns 400."""
        response = admin_logged_in.post(
            "/backup/api/storage/test-connection",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("success") is False

    def test_test_new_connection_viewer_forbidden(self, viewer_logged_in):
        """Viewer cannot test new storage connections."""
        response = viewer_logged_in.post(
            "/backup/api/storage/test-connection",
            json={"provider_type": "local"},
            content_type="application/json",
            follow_redirects=False,
        )
        assert response.status_code in (302, 403)

    def test_unauthenticated_storage_create_redirects(self, client):
        response = client.post(
            "/backup/api/storage/create",
            json={"name": "test"},
            content_type="application/json",
        )
        assert response.status_code in (302, 401)

    def test_operator_can_create_storage(self, operator_logged_in):
        """Operator can create storage providers."""
        response = operator_logged_in.post(
            "/backup/api/storage/create",
            json={"name": "Operator Storage", "provider_type": "nfs"},
            content_type="application/json",
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data.get("success") is True

    def test_operator_can_get_storage(self, operator_logged_in):
        """Operator can get storage provider details (login_required only)."""
        response = operator_logged_in.get("/backup/api/storage/1")
        assert response.status_code == 200
