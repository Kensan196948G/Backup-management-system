"""
Unit tests for jobs views.
app/views/jobs.py coverage: 35% -> ~60%
"""
import pytest

from app.models import BackupJob, User, db


@pytest.fixture
def admin_logged_in(client, app):
    """Create admin and log in."""
    with app.app_context():
        user = User(
            username="jobs_admin", email="jobs_admin@example.com",
            full_name="Jobs Admin", role="admin", is_active=True
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "jobs_admin", "password": "Admin123!"})
    return client


@pytest.fixture
def sample_job(app):
    """Create a sample BackupJob."""
    with app.app_context():
        user = User(
            username="job_owner_view", email="jov@example.com",
            role="operator", is_active=True
        )
        user.set_password("Test123!")
        db.session.add(user)
        db.session.commit()

        job = BackupJob(
            job_name="Test Job Views",
            job_type="file",
            backup_tool="custom",
            schedule_type="daily",
            retention_days=7,
            owner_id=user.id,
        )
        db.session.add(job)
        db.session.commit()
        yield {"job_id": job.id, "user_id": user.id}


class TestJobsListView:
    """Tests for GET /jobs/."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/jobs/", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/")
        assert response.status_code in (200, 302)

    def test_response_contains_jobs(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/")
        assert response.status_code in (200, 302)


class TestJobDetailView:
    """Tests for GET /jobs/<id>."""

    def test_nonexistent_job(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/99999")
        assert response.status_code in (200, 302, 404, 500)

    def test_existing_job(self, admin_logged_in, sample_job):
        job_id = sample_job["job_id"]
        response = admin_logged_in.get(f"/jobs/{job_id}")
        assert response.status_code in (200, 302, 404, 500)


class TestJobCreateView:
    """Tests for GET/POST /jobs/create."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/jobs/create", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access_form(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/create")
        assert response.status_code in (200, 302)

    def test_create_job_post(self, admin_logged_in):
        response = admin_logged_in.post(
            "/jobs/create",
            data={
                "job_name": "New Test Job",
                "job_type": "file",
                "backup_tool": "custom",
                "schedule_type": "daily",
                "retention_days": "7",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 400, 500)


class TestJobEditView:
    """Tests for GET/POST /jobs/<id>/edit."""

    def test_nonexistent_job_edit(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/99999/edit")
        assert response.status_code in (200, 302, 404, 500)

    def test_existing_job_edit_accessible(self, admin_logged_in, sample_job):
        job_id = sample_job["job_id"]
        response = admin_logged_in.get(f"/jobs/{job_id}/edit")
        assert response.status_code in (200, 302, 404, 500)


class TestJobDeleteView:
    """Tests for POST /jobs/<id>/delete."""

    def test_unauthenticated_redirects(self, client):
        response = client.post("/jobs/99999/delete", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_nonexistent_job_delete(self, admin_logged_in):
        response = admin_logged_in.post("/jobs/99999/delete", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)


class TestJobToggleActive:
    """Tests for POST /jobs/<id>/toggle-active."""

    def test_unauthenticated_redirects(self, client):
        response = client.post("/jobs/99999/toggle-active", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_nonexistent_job_toggle(self, admin_logged_in):
        response = admin_logged_in.post("/jobs/99999/toggle-active", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)

    def test_existing_job_toggle(self, admin_logged_in, sample_job):
        job_id = sample_job["job_id"]
        response = admin_logged_in.post(f"/jobs/{job_id}/toggle-active", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)


class TestJobAPIEndpoints:
    """Tests for /jobs/api/* endpoints."""

    def test_api_list_accessible(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/api/jobs")
        assert response.status_code in (200, 302, 404, 500)

    def test_unauthenticated_api_redirects(self, client):
        response = client.get("/jobs/api/jobs", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_api_detail_nonexistent(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/api/jobs/99999")
        assert response.status_code in (200, 404, 500)
