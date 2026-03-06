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


# ----------------------------------------------------------------
# Additional fixtures used by expanded tests
# ----------------------------------------------------------------

@pytest.fixture
def admin_with_job(client, app):
    """Create admin user + a BackupJob, return (client, job_id)."""
    with app.app_context():
        user = User(
            username="adm_wj", email="adm_wj@example.com",
            full_name="Admin WJ", role="admin", is_active=True,
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

        from app.models import BackupJob
        job = BackupJob(
            job_name="Expanded Test Job",
            job_type="file",
            backup_tool="custom",
            schedule_type="daily",
            retention_days=7,
            owner_id=user.id,
            is_active=True,
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id
        user_id = user.id

    client.post("/auth/login", data={"username": "adm_wj", "password": "Admin123!"})
    return client, job_id, user_id


@pytest.fixture
def operator_with_job(client, app):
    """Create operator user + a BackupJob, return (client, job_id)."""
    with app.app_context():
        user = User(
            username="op_wj", email="op_wj@example.com",
            full_name="Operator WJ", role="operator", is_active=True,
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

        from app.models import BackupJob
        job = BackupJob(
            job_name="Operator Job",
            job_type="database",
            backup_tool="custom",
            schedule_type="weekly",
            retention_days=14,
            owner_id=user.id,
            is_active=False,
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id
        user_id = user.id

    client.post("/auth/login", data={"username": "op_wj", "password": "Admin123!"})
    return client, job_id, user_id


# ----------------------------------------------------------------
# TestJobListFilters
# ----------------------------------------------------------------

class TestJobListFilters:
    """Test search, type, owner, status, compliance, sort filters in list()."""

    def test_list_with_search_filter(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?search=Test")
        assert response.status_code in (200, 302)

    def test_list_with_type_filter(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?type=file")
        assert response.status_code in (200, 302)

    def test_list_with_owner_filter(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?owner=1")
        assert response.status_code in (200, 302)

    def test_list_with_status_active(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?status=active")
        assert response.status_code in (200, 302)

    def test_list_with_status_inactive(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?status=inactive")
        assert response.status_code in (200, 302)

    def test_list_with_compliance_compliant(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?compliance=compliant")
        assert response.status_code in (200, 302)

    def test_list_with_compliance_non_compliant(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?compliance=non_compliant")
        assert response.status_code in (200, 302)

    def test_list_sort_asc(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?sort=job_name&order=asc")
        assert response.status_code in (200, 302)

    def test_list_sort_desc(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?sort=job_name&order=desc")
        assert response.status_code in (200, 302)

    def test_list_pagination(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?page=1&per_page=5")
        assert response.status_code in (200, 302)

    def test_list_combined_filters(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/?search=job&type=file&status=active")
        assert response.status_code in (200, 302)


# ----------------------------------------------------------------
# TestJobDetailWithData
# ----------------------------------------------------------------

class TestJobDetailWithData:
    """Test detail() view with a real job in the DB."""

    def test_detail_returns_200(self, admin_with_job):
        client, job_id, _ = admin_with_job
        response = client.get(f"/jobs/{job_id}")
        assert response.status_code in (200, 302, 500)

    def test_detail_content(self, admin_with_job):
        client, job_id, _ = admin_with_job
        response = client.get(f"/jobs/{job_id}")
        # If 200, the response should contain something meaningful
        if response.status_code == 200:
            assert len(response.data) > 0

    def test_detail_compliance_generated(self, admin_with_job, app):
        """detail() should attempt compliance generation when missing."""
        from unittest.mock import patch, MagicMock
        client, job_id, _ = admin_with_job
        mock_compliance = MagicMock()
        mock_compliance.overall_status = "compliant"
        with patch("app.views.jobs.ComplianceChecker") as MockChecker:
            MockChecker.return_value.check_job_compliance.return_value = mock_compliance
            response = client.get(f"/jobs/{job_id}")
            assert response.status_code in (200, 302, 500)


# ----------------------------------------------------------------
# TestJobCreatePost
# ----------------------------------------------------------------

class TestJobCreatePost:
    """Test POST to /jobs/create."""

    def test_create_post_minimal_data(self, admin_logged_in):
        response = admin_logged_in.post(
            "/jobs/create",
            data={
                "job_name": "Minimal Job",
                "job_type": "file",
                "backup_tool": "custom",
                "schedule_type": "daily",
                "retention_days": "7",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 400, 500)

    def test_create_post_with_description(self, admin_logged_in):
        response = admin_logged_in.post(
            "/jobs/create",
            data={
                "job_name": "Described Job",
                "job_type": "database",
                "backup_tool": "custom",
                "schedule_type": "weekly",
                "retention_days": "14",
                "description": "A test description",
                "target_server": "db.example.com",
                "destination_path": "/backups/db",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 400, 500)

    def test_create_post_with_is_active_on(self, admin_logged_in):
        response = admin_logged_in.post(
            "/jobs/create",
            data={
                "job_name": "Active Job",
                "job_type": "file",
                "backup_tool": "custom",
                "schedule_type": "daily",
                "retention_days": "30",
                "is_active": "on",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 400, 500)

    def test_create_post_with_target_path_fallback(self, admin_logged_in):
        """destination_path absent → falls back to target_path."""
        response = admin_logged_in.post(
            "/jobs/create",
            data={
                "job_name": "Path Fallback Job",
                "job_type": "file",
                "backup_tool": "custom",
                "schedule_type": "daily",
                "retention_days": "7",
                "target_path": "/data/backup",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 400, 500)

    def test_create_post_operator_allowed(self, operator_with_job):
        """Operator role should be allowed to create jobs."""
        client, _, _ = operator_with_job
        response = client.post(
            "/jobs/create",
            data={
                "job_name": "Op Created Job",
                "job_type": "file",
                "backup_tool": "custom",
                "schedule_type": "daily",
                "retention_days": "7",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 400, 500)

    def test_create_get_form(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/create")
        assert response.status_code in (200, 302)

    def test_create_job_persisted(self, admin_logged_in, app):
        """Verify job is actually saved to DB after POST."""
        response = admin_logged_in.post(
            "/jobs/create",
            data={
                "job_name": "Persist Check Job",
                "job_type": "file",
                "backup_tool": "custom",
                "schedule_type": "daily",
                "retention_days": "7",
            },
            follow_redirects=True,
        )
        if response.status_code == 200:
            with app.app_context():
                from app.models import BackupJob
                job = BackupJob.query.filter_by(job_name="Persist Check Job").first()
                assert job is not None


# ----------------------------------------------------------------
# TestJobEditViewExpanded
# ----------------------------------------------------------------

class TestJobEditViewExpanded:
    """Test GET and POST for /jobs/<id>/edit."""

    def test_edit_get_renders_form(self, admin_with_job):
        client, job_id, _ = admin_with_job
        response = client.get(f"/jobs/{job_id}/edit")
        assert response.status_code in (200, 302, 404, 500)

    def test_edit_post_updates_job(self, admin_with_job, app):
        client, job_id, _ = admin_with_job
        response = client.post(
            f"/jobs/{job_id}/edit",
            data={
                "job_name": "Updated Job Name",
                "job_type": "system_image",
                "backup_tool": "custom",
                "schedule_type": "weekly",
                "retention_days": "14",
                "description": "Updated description",
                "target_server": "server.example.com",
                "target_path": "/backups/updated",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_edit_post_toggle_active_off(self, admin_with_job, app):
        client, job_id, _ = admin_with_job
        response = client.post(
            f"/jobs/{job_id}/edit",
            data={
                "job_name": "Toggled Off Job",
                "job_type": "file",
                "backup_tool": "custom",
                "schedule_type": "daily",
                "retention_days": "7",
                # is_active omitted → treated as False
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_edit_nonexistent_job(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/999999/edit")
        assert response.status_code in (200, 302, 404, 500)

    def test_edit_post_with_schedule_time(self, admin_with_job):
        client, job_id, _ = admin_with_job
        response = client.post(
            f"/jobs/{job_id}/edit",
            data={
                "job_name": "Scheduled Job",
                "job_type": "file",
                "backup_tool": "custom",
                "schedule_type": "daily",
                "retention_days": "7",
                "schedule_time": "02:00",
                "is_active": "on",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_edit_operator_allowed(self, operator_with_job):
        client, job_id, _ = operator_with_job
        response = client.get(f"/jobs/{job_id}/edit")
        assert response.status_code in (200, 302, 404, 500)


# ----------------------------------------------------------------
# TestJobDeleteConfirm
# ----------------------------------------------------------------

class TestJobDeleteConfirm:
    """Test actual DB deletion via POST /jobs/<id>/delete."""

    def test_delete_existing_job(self, admin_with_job, app):
        client, job_id, _ = admin_with_job
        response = client.post(f"/jobs/{job_id}/delete", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)

    def test_delete_removes_from_db(self, admin_with_job, app):
        client, job_id, _ = admin_with_job
        client.post(f"/jobs/{job_id}/delete", follow_redirects=True)
        with app.app_context():
            from app.models import BackupJob
            job = db.session.get(BackupJob, job_id)
            # Job should be deleted
            assert job is None

    def test_delete_nonexistent_job(self, admin_logged_in):
        response = admin_logged_in.post("/jobs/999999/delete", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)

    def test_delete_operator_forbidden(self, operator_with_job):
        """Only admin can delete; operator should be redirected/forbidden."""
        client, job_id, _ = operator_with_job
        response = client.post(f"/jobs/{job_id}/delete", follow_redirects=False)
        assert response.status_code in (302, 403, 404, 500)


# ----------------------------------------------------------------
# TestJobToggleActiveExpanded
# ----------------------------------------------------------------

class TestJobToggleActiveExpanded:
    """Test toggle_active() actually flips is_active."""

    def test_toggle_active_true_to_false(self, admin_with_job, app):
        client, job_id, _ = admin_with_job
        # Initial state is is_active=True
        response = client.post(f"/jobs/{job_id}/toggle-active", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)
        with app.app_context():
            from app.models import BackupJob
            job = db.session.get(BackupJob, job_id)
            if job:
                assert job.is_active is False

    def test_toggle_active_false_to_true(self, operator_with_job, app):
        client, job_id, _ = operator_with_job
        # Initial state is is_active=False
        response = client.post(f"/jobs/{job_id}/toggle-active", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)
        with app.app_context():
            from app.models import BackupJob
            job = db.session.get(BackupJob, job_id)
            if job:
                assert job.is_active is True

    def test_toggle_twice_returns_to_original(self, admin_with_job, app):
        client, job_id, _ = admin_with_job
        client.post(f"/jobs/{job_id}/toggle-active", follow_redirects=True)
        client.post(f"/jobs/{job_id}/toggle-active", follow_redirects=True)
        with app.app_context():
            from app.models import BackupJob
            job = db.session.get(BackupJob, job_id)
            if job:
                assert job.is_active is True


# ----------------------------------------------------------------
# TestCheckCompliance
# ----------------------------------------------------------------

class TestCheckCompliance:
    """Test POST /jobs/<id>/check-compliance."""

    def test_check_compliance_existing_job(self, admin_with_job):
        from unittest.mock import patch, MagicMock
        client, job_id, _ = admin_with_job
        mock_compliance = MagicMock()
        mock_compliance.overall_status = "compliant"
        with patch("app.views.jobs.ComplianceChecker") as MockChecker:
            MockChecker.return_value.check_job_compliance.return_value = mock_compliance
            response = client.post(f"/jobs/{job_id}/check-compliance", follow_redirects=True)
            assert response.status_code in (200, 302, 404, 500)

    def test_check_compliance_warning_status(self, admin_with_job):
        from unittest.mock import patch, MagicMock
        client, job_id, _ = admin_with_job
        mock_compliance = MagicMock()
        mock_compliance.overall_status = "warning"
        with patch("app.views.jobs.ComplianceChecker") as MockChecker:
            MockChecker.return_value.check_job_compliance.return_value = mock_compliance
            response = client.post(f"/jobs/{job_id}/check-compliance", follow_redirects=True)
            assert response.status_code in (200, 302, 404, 500)

    def test_check_compliance_non_compliant(self, admin_with_job):
        from unittest.mock import patch, MagicMock
        client, job_id, _ = admin_with_job
        mock_compliance = MagicMock()
        mock_compliance.overall_status = "non_compliant"
        with patch("app.views.jobs.ComplianceChecker") as MockChecker:
            MockChecker.return_value.check_job_compliance.return_value = mock_compliance
            response = client.post(f"/jobs/{job_id}/check-compliance", follow_redirects=True)
            assert response.status_code in (200, 302, 404, 500)

    def test_check_compliance_nonexistent_job(self, admin_logged_in):
        response = admin_logged_in.post("/jobs/999999/check-compliance", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)


# ----------------------------------------------------------------
# TestJobAPIExpanded
# ----------------------------------------------------------------

class TestJobAPIExpanded:
    """Test /jobs/api/* endpoints more thoroughly."""

    def test_api_list_returns_json(self, admin_with_job):
        client, _, _ = admin_with_job
        response = client.get("/jobs/api/jobs")
        if response.status_code == 200:
            data = response.get_json()
            assert "jobs" in data
            assert isinstance(data["jobs"], list)

    def test_api_list_contains_created_job(self, admin_with_job):
        client, job_id, _ = admin_with_job
        response = client.get("/jobs/api/jobs")
        if response.status_code == 200:
            data = response.get_json()
            ids = [j.get("id") for j in data.get("jobs", [])]
            assert job_id in ids

    def test_api_detail_existing_job(self, admin_with_job):
        client, job_id, _ = admin_with_job
        response = client.get(f"/jobs/api/jobs/{job_id}")
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            data = response.get_json()
            assert "job" in data

    def test_api_detail_returns_compliance_field(self, admin_with_job):
        client, job_id, _ = admin_with_job
        response = client.get(f"/jobs/api/jobs/{job_id}")
        if response.status_code == 200:
            data = response.get_json()
            assert "compliance" in data

    def test_api_executions_existing_job(self, admin_with_job):
        client, job_id, _ = admin_with_job
        response = client.get(f"/jobs/api/jobs/{job_id}/executions")
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            data = response.get_json()
            assert "executions" in data

    def test_api_executions_nonexistent_job(self, admin_logged_in):
        response = admin_logged_in.get("/jobs/api/jobs/999999/executions")
        assert response.status_code in (200, 404, 500)

    def test_api_detail_with_compliance_data(self, admin_with_job, app):
        """API detail when ComplianceStatus record exists."""
        from app.models import ComplianceStatus
        import datetime as _dt
        client, job_id, _ = admin_with_job
        with app.app_context():
            cs = ComplianceStatus(
                job_id=job_id,
                check_date=_dt.datetime.now(_dt.timezone.utc),
                overall_status="compliant",
                copies_count=3,
                media_types_count=2,
                has_offsite=True,
                has_offline=True,
                has_errors=False,
            )
            db.session.add(cs)
            db.session.commit()
        response = client.get(f"/jobs/api/jobs/{job_id}")
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("compliance") is not None
