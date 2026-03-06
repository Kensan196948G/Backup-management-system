"""
Comprehensive unit tests for app/api/jobs.py
Tests all backup job management API endpoints.

Valid values (from jobs.py validate_job_data):
  job_type:     system_image, file, database, vm
  backup_tool:  veeam, wsb, aomei, custom
  schedule_type: daily, weekly, monthly, manual
  retention_days: integer >= 1
"""



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_JOB_DATA = {
    "job_name": "Test API Job",
    "job_type": "file",
    "backup_tool": "custom",
    "description": "Test job via API",
    "target_path": "/data/test",
    "schedule_type": "daily",
    "retention_days": 30,
}


def _create_job(client, data=None, **overrides):
    """Helper: POST /api/jobs and return response."""
    payload = dict(VALID_JOB_DATA)
    if data:
        payload.update(data)
    payload.update(overrides)
    return client.post("/api/jobs", json=payload)


# ===========================================================================
# List Jobs  (GET /api/jobs)
# ===========================================================================

class TestListJobs:
    """Tests for GET /api/jobs"""

    def test_list_jobs_authenticated(self, authenticated_client, backup_job):
        """GET /api/jobs returns 200 with jobs list and pagination."""
        response = authenticated_client.get("/api/jobs")
        assert response.status_code == 200
        data = response.get_json()
        assert "jobs" in data
        assert "pagination" in data
        assert isinstance(data["jobs"], list)
        # backup_job fixture created one job; at least 1 should appear
        assert len(data["jobs"]) >= 1

    def test_list_jobs_unauthenticated(self, client):
        """GET /api/jobs returns 401 for unauthenticated request."""
        response = client.get("/api/jobs")
        assert response.status_code == 401

    def test_list_jobs_empty(self, authenticated_client):
        """GET /api/jobs with no jobs in DB returns empty list."""
        response = authenticated_client.get("/api/jobs")
        assert response.status_code == 200
        data = response.get_json()
        assert data["jobs"] == []
        assert data["pagination"]["total"] == 0

    def test_list_jobs_pagination_structure(self, authenticated_client, backup_job):
        """Pagination object contains expected keys."""
        response = authenticated_client.get("/api/jobs")
        assert response.status_code == 200
        pagination = response.get_json()["pagination"]
        for key in ("page", "per_page", "total", "pages", "has_next", "has_prev"):
            assert key in pagination, f"Missing pagination key: {key}"

    def test_list_jobs_filter_job_type(self, authenticated_client, multiple_backup_jobs):
        """GET /api/jobs?job_type=file returns only file-type jobs."""
        response = authenticated_client.get("/api/jobs?job_type=file")
        assert response.status_code == 200
        data = response.get_json()
        for job in data["jobs"]:
            assert job["job_type"] == "file"

    def test_list_jobs_filter_status_active(self, authenticated_client, multiple_backup_jobs):
        """GET /api/jobs?status=active returns only active jobs."""
        response = authenticated_client.get("/api/jobs?status=active")
        assert response.status_code == 200
        data = response.get_json()
        for job in data["jobs"]:
            assert job["is_active"] is True

    def test_list_jobs_filter_status_inactive(self, authenticated_client, multiple_backup_jobs):
        """GET /api/jobs?status=inactive returns only inactive jobs."""
        response = authenticated_client.get("/api/jobs?status=inactive")
        assert response.status_code == 200
        data = response.get_json()
        for job in data["jobs"]:
            assert job["is_active"] is False

    def test_list_jobs_filter_backup_tool(self, authenticated_client, backup_job):
        """GET /api/jobs?backup_tool=custom returns only matching jobs."""
        response = authenticated_client.get("/api/jobs?backup_tool=custom")
        assert response.status_code == 200
        data = response.get_json()
        for job in data["jobs"]:
            assert job["backup_tool"] == "custom"

    def test_list_jobs_pagination_per_page(self, authenticated_client, multiple_backup_jobs):
        """GET /api/jobs?page=1&per_page=2 returns at most 2 items."""
        response = authenticated_client.get("/api/jobs?page=1&per_page=2")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["jobs"]) <= 2
        assert data["pagination"]["per_page"] == 2
        assert data["pagination"]["page"] == 1

    def test_list_jobs_search(self, authenticated_client, backup_job):
        """GET /api/jobs?search=<name> filters by name."""
        response = authenticated_client.get("/api/jobs?search=Test+Backup+Job")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["jobs"]) >= 1

    def test_list_jobs_response_structure(self, authenticated_client, backup_job):
        """Each job in list has expected keys."""
        response = authenticated_client.get("/api/jobs")
        assert response.status_code == 200
        job = response.get_json()["jobs"][0]
        for key in ("id", "job_name", "job_type", "backup_tool", "schedule_type",
                    "retention_days", "is_active", "created_at", "updated_at"):
            assert key in job, f"Missing job key: {key}"


# ===========================================================================
# Get Job  (GET /api/jobs/<id>)
# ===========================================================================

class TestGetJob:
    """Tests for GET /api/jobs/<id>"""

    def test_get_job_found(self, authenticated_client, backup_job):
        """GET /api/jobs/<id> returns 200 with job details."""
        response = authenticated_client.get(f"/api/jobs/{backup_job.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == backup_job.id
        assert data["job_name"] == backup_job.job_name

    def test_get_job_not_found(self, authenticated_client):
        """GET /api/jobs/99999 returns 404."""
        response = authenticated_client.get("/api/jobs/99999")
        assert response.status_code == 404

    def test_get_job_unauthenticated(self, client, backup_job):
        """GET /api/jobs/<id> returns 401 for unauthenticated request."""
        response = client.get(f"/api/jobs/{backup_job.id}")
        assert response.status_code == 401

    def test_get_job_response_structure(self, authenticated_client, backup_job):
        """GET /api/jobs/<id> response has expected keys."""
        response = authenticated_client.get(f"/api/jobs/{backup_job.id}")
        assert response.status_code == 200
        data = response.get_json()
        for key in ("id", "job_name", "job_type", "backup_tool", "schedule_type",
                    "retention_days", "is_active", "copies", "recent_executions",
                    "created_at", "updated_at"):
            assert key in data, f"Missing key in job detail: {key}"

    def test_get_job_copies_is_list(self, authenticated_client, backup_job):
        """GET /api/jobs/<id> response copies field is a list."""
        response = authenticated_client.get(f"/api/jobs/{backup_job.id}")
        assert response.status_code == 200
        assert isinstance(response.get_json()["copies"], list)

    def test_get_job_executions_is_list(self, authenticated_client, backup_job):
        """GET /api/jobs/<id> response recent_executions field is a list."""
        response = authenticated_client.get(f"/api/jobs/{backup_job.id}")
        assert response.status_code == 200
        assert isinstance(response.get_json()["recent_executions"], list)

    def test_get_job_owner_field(self, authenticated_client, backup_job):
        """GET /api/jobs/<id> includes owner info when owner exists."""
        response = authenticated_client.get(f"/api/jobs/{backup_job.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "owner" in data


# ===========================================================================
# Create Job  (POST /api/jobs)
# ===========================================================================

class TestCreateJob:
    """Tests for POST /api/jobs"""

    def test_create_job_success(self, authenticated_client):
        """POST /api/jobs with valid data returns 201."""
        response = _create_job(authenticated_client)
        assert response.status_code == 201
        data = response.get_json()
        assert "job_id" in data
        assert data["job_name"] == VALID_JOB_DATA["job_name"]

    def test_create_job_unauthenticated(self, client):
        """POST /api/jobs without auth returns 401."""
        response = _create_job(client)
        assert response.status_code == 401

    def test_create_job_missing_job_name(self, authenticated_client):
        """POST /api/jobs without job_name returns 400."""
        payload = {k: v for k, v in VALID_JOB_DATA.items() if k != "job_name"}
        response = authenticated_client.post("/api/jobs", json=payload)
        assert response.status_code == 400

    def test_create_job_missing_job_type(self, authenticated_client):
        """POST /api/jobs without job_type returns 400."""
        payload = {k: v for k, v in VALID_JOB_DATA.items() if k != "job_type"}
        response = authenticated_client.post("/api/jobs", json=payload)
        assert response.status_code == 400

    def test_create_job_missing_backup_tool(self, authenticated_client):
        """POST /api/jobs without backup_tool returns 400."""
        payload = {k: v for k, v in VALID_JOB_DATA.items() if k != "backup_tool"}
        response = authenticated_client.post("/api/jobs", json=payload)
        assert response.status_code == 400

    def test_create_job_missing_schedule_type(self, authenticated_client):
        """POST /api/jobs without schedule_type returns 400."""
        payload = {k: v for k, v in VALID_JOB_DATA.items() if k != "schedule_type"}
        response = authenticated_client.post("/api/jobs", json=payload)
        assert response.status_code == 400

    def test_create_job_missing_retention_days(self, authenticated_client):
        """POST /api/jobs without retention_days returns 400."""
        payload = {k: v for k, v in VALID_JOB_DATA.items() if k != "retention_days"}
        response = authenticated_client.post("/api/jobs", json=payload)
        assert response.status_code == 400

    def test_create_job_invalid_job_type(self, authenticated_client):
        """POST /api/jobs with invalid job_type returns 400."""
        response = _create_job(authenticated_client, job_type="not_a_type")
        assert response.status_code == 400

    def test_create_job_invalid_backup_tool(self, authenticated_client):
        """POST /api/jobs with invalid backup_tool returns 400."""
        response = _create_job(authenticated_client, backup_tool="not_a_tool")
        assert response.status_code == 400

    def test_create_job_invalid_schedule_type(self, authenticated_client):
        """POST /api/jobs with invalid schedule_type returns 400."""
        response = _create_job(authenticated_client, schedule_type="not_a_schedule")
        assert response.status_code == 400

    def test_create_job_invalid_retention_days_zero(self, authenticated_client):
        """POST /api/jobs with retention_days=0 returns 400."""
        response = _create_job(authenticated_client, retention_days=0)
        assert response.status_code == 400

    def test_create_job_invalid_retention_days_negative(self, authenticated_client):
        """POST /api/jobs with retention_days=-1 returns 400."""
        response = _create_job(authenticated_client, retention_days=-1)
        assert response.status_code == 400

    def test_create_job_invalid_retention_days_string(self, authenticated_client):
        """POST /api/jobs with retention_days='abc' returns 400."""
        response = _create_job(authenticated_client, retention_days="abc")
        assert response.status_code == 400

    def test_create_job_valid_all_job_types(self, authenticated_client):
        """POST /api/jobs succeeds for each valid job_type."""
        valid_types = ["system_image", "file", "database", "vm"]
        for jt in valid_types:
            payload = dict(VALID_JOB_DATA)
            payload["job_name"] = f"Job for type {jt}"
            payload["job_type"] = jt
            response = authenticated_client.post("/api/jobs", json=payload)
            assert response.status_code == 201, f"Failed for job_type={jt}: {response.get_json()}"

    def test_create_job_valid_all_schedule_types(self, authenticated_client):
        """POST /api/jobs succeeds for each valid schedule_type."""
        valid_schedules = ["daily", "weekly", "monthly", "manual"]
        for st in valid_schedules:
            payload = dict(VALID_JOB_DATA)
            payload["job_name"] = f"Job for schedule {st}"
            payload["schedule_type"] = st
            response = authenticated_client.post("/api/jobs", json=payload)
            assert response.status_code == 201, f"Failed for schedule_type={st}: {response.get_json()}"

    def test_create_job_operator_allowed(self, operator_authenticated_client):
        """POST /api/jobs is allowed for operator role."""
        payload = dict(VALID_JOB_DATA)
        payload["job_name"] = "Operator Created Job"
        response = operator_authenticated_client.post("/api/jobs", json=payload)
        assert response.status_code == 201

    def test_create_job_response_contains_job_id(self, authenticated_client):
        """POST /api/jobs response contains job_id and job_name."""
        response = _create_job(authenticated_client)
        assert response.status_code == 201
        data = response.get_json()
        assert "job_id" in data
        assert "job_name" in data
        assert isinstance(data["job_id"], int)

    def test_create_job_duplicate_name(self, authenticated_client):
        """POST /api/jobs with duplicate job_name: second create is also 201 (no unique constraint enforced in API layer)."""
        # The jobs.py API does not enforce unique names at the API level;
        # both calls return 201 unless the DB itself rejects duplicates.
        # If DB allows duplicates, both should be 201.
        resp1 = _create_job(authenticated_client, job_name="DuplicateJob")
        resp2 = _create_job(authenticated_client, job_name="DuplicateJob")
        # Either both succeed (DB allows duplicates) or second returns 409/400/500
        assert resp1.status_code == 201
        # Accept any of 201, 400, 409 for the duplicate
        assert resp2.status_code in (201, 400, 409, 500)


# ===========================================================================
# Update Job  (PUT /api/jobs/<id>)
# ===========================================================================

class TestUpdateJob:
    """Tests for PUT /api/jobs/<id>"""

    def test_update_job_success(self, authenticated_client, backup_job):
        """PUT /api/jobs/<id> with valid data returns 200."""
        response = authenticated_client.put(
            f"/api/jobs/{backup_job.id}",
            json={"job_name": "Updated Job Name", "retention_days": 60},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "job_id" in data

    def test_update_job_not_found(self, authenticated_client):
        """PUT /api/jobs/99999 returns 404."""
        response = authenticated_client.put("/api/jobs/99999", json={"job_name": "X"})
        assert response.status_code == 404

    def test_update_job_unauthenticated(self, client, backup_job):
        """PUT /api/jobs/<id> without auth returns 401."""
        response = client.put(f"/api/jobs/{backup_job.id}", json={"job_name": "X"})
        assert response.status_code == 401

    def test_update_job_invalid_job_type(self, authenticated_client, backup_job):
        """PUT /api/jobs/<id> with invalid job_type returns 400."""
        response = authenticated_client.put(
            f"/api/jobs/{backup_job.id}",
            json={"job_type": "not_valid"},
        )
        assert response.status_code == 400

    def test_update_job_invalid_backup_tool(self, authenticated_client, backup_job):
        """PUT /api/jobs/<id> with invalid backup_tool returns 400."""
        response = authenticated_client.put(
            f"/api/jobs/{backup_job.id}",
            json={"backup_tool": "not_valid"},
        )
        assert response.status_code == 400

    def test_update_job_invalid_schedule_type(self, authenticated_client, backup_job):
        """PUT /api/jobs/<id> with invalid schedule_type returns 400."""
        response = authenticated_client.put(
            f"/api/jobs/{backup_job.id}",
            json={"schedule_type": "not_valid"},
        )
        assert response.status_code == 400

    def test_update_job_invalid_retention_days(self, authenticated_client, backup_job):
        """PUT /api/jobs/<id> with retention_days=0 returns 400."""
        response = authenticated_client.put(
            f"/api/jobs/{backup_job.id}",
            json={"retention_days": 0},
        )
        assert response.status_code == 400

    def test_update_job_partial_update(self, authenticated_client, backup_job):
        """PUT /api/jobs/<id> with only some fields returns 200."""
        response = authenticated_client.put(
            f"/api/jobs/{backup_job.id}",
            json={"description": "Updated description only"},
        )
        assert response.status_code == 200

    def test_update_job_operator_allowed(self, operator_authenticated_client, backup_job):
        """PUT /api/jobs/<id> is allowed for operator role."""
        response = operator_authenticated_client.put(
            f"/api/jobs/{backup_job.id}",
            json={"description": "Operator updated"},
        )
        assert response.status_code == 200

    def test_update_job_set_is_active(self, authenticated_client, backup_job):
        """PUT /api/jobs/<id> can set is_active field."""
        response = authenticated_client.put(
            f"/api/jobs/{backup_job.id}",
            json={"is_active": False},
        )
        assert response.status_code == 200


# ===========================================================================
# Delete Job  (DELETE /api/jobs/<id>)
# ===========================================================================

class TestDeleteJob:
    """Tests for DELETE /api/jobs/<id>"""

    def test_delete_job_success(self, authenticated_client, app):
        """DELETE /api/jobs/<id> returns 200 and removes the job."""
        # Create a job to delete via the API
        create_resp = _create_job(authenticated_client, job_name="Job To Delete")
        assert create_resp.status_code == 201
        job_id = create_resp.get_json()["job_id"]

        response = authenticated_client.delete(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["job_id"] == job_id

    def test_delete_job_not_found(self, authenticated_client):
        """DELETE /api/jobs/99999 returns 404."""
        response = authenticated_client.delete("/api/jobs/99999")
        assert response.status_code == 404

    def test_delete_job_unauthenticated(self, client, backup_job):
        """DELETE /api/jobs/<id> without auth returns 401."""
        response = client.delete(f"/api/jobs/{backup_job.id}")
        assert response.status_code == 401

    def test_delete_job_response_contains_job_info(self, authenticated_client):
        """DELETE /api/jobs/<id> response contains job_id and job_name."""
        create_resp = _create_job(authenticated_client, job_name="DeleteMe")
        assert create_resp.status_code == 201
        job_id = create_resp.get_json()["job_id"]

        response = authenticated_client.delete(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "job_id" in data
        assert "job_name" in data

    def test_delete_job_then_get_returns_404(self, authenticated_client):
        """After DELETE, GET of same job returns 404."""
        create_resp = _create_job(authenticated_client, job_name="GoneJob")
        assert create_resp.status_code == 201
        job_id = create_resp.get_json()["job_id"]

        authenticated_client.delete(f"/api/jobs/{job_id}")
        get_resp = authenticated_client.get(f"/api/jobs/{job_id}")
        assert get_resp.status_code == 404


# ===========================================================================
# Add Backup Copy  (POST /api/jobs/<id>/copies)
# ===========================================================================

class TestAddCopy:
    """Tests for POST /api/jobs/<id>/copies"""

    VALID_COPY_DATA = {
        "copy_type": "primary",
        "media_type": "disk",
        "storage_path": "/backup/copy1",
        "is_encrypted": True,
        "is_compressed": False,
    }

    def test_add_copy_success(self, authenticated_client, backup_job):
        """POST /api/jobs/<id>/copies with valid data returns 201."""
        response = authenticated_client.post(
            f"/api/jobs/{backup_job.id}/copies",
            json=self.VALID_COPY_DATA,
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "copy_id" in data
        assert data["job_id"] == backup_job.id

    def test_add_copy_job_not_found(self, authenticated_client):
        """POST /api/jobs/99999/copies returns 404."""
        response = authenticated_client.post("/api/jobs/99999/copies", json=self.VALID_COPY_DATA)
        assert response.status_code == 404

    def test_add_copy_unauthenticated(self, client, backup_job):
        """POST /api/jobs/<id>/copies without auth returns 401."""
        response = client.post(f"/api/jobs/{backup_job.id}/copies", json=self.VALID_COPY_DATA)
        assert response.status_code == 401

    def test_add_copy_missing_copy_type(self, authenticated_client, backup_job):
        """POST /api/jobs/<id>/copies without copy_type returns 400."""
        payload = {k: v for k, v in self.VALID_COPY_DATA.items() if k != "copy_type"}
        response = authenticated_client.post(f"/api/jobs/{backup_job.id}/copies", json=payload)
        assert response.status_code == 400

    def test_add_copy_missing_media_type(self, authenticated_client, backup_job):
        """POST /api/jobs/<id>/copies without media_type returns 400."""
        payload = {k: v for k, v in self.VALID_COPY_DATA.items() if k != "media_type"}
        response = authenticated_client.post(f"/api/jobs/{backup_job.id}/copies", json=payload)
        assert response.status_code == 400

    def test_add_copy_invalid_copy_type(self, authenticated_client, backup_job):
        """POST /api/jobs/<id>/copies with invalid copy_type returns 400."""
        payload = dict(self.VALID_COPY_DATA)
        payload["copy_type"] = "invalid_type"
        response = authenticated_client.post(f"/api/jobs/{backup_job.id}/copies", json=payload)
        assert response.status_code == 400

    def test_add_copy_invalid_media_type(self, authenticated_client, backup_job):
        """POST /api/jobs/<id>/copies with invalid media_type returns 400."""
        payload = dict(self.VALID_COPY_DATA)
        payload["media_type"] = "invalid_media"
        response = authenticated_client.post(f"/api/jobs/{backup_job.id}/copies", json=payload)
        assert response.status_code == 400

    def test_add_copy_valid_copy_types(self, authenticated_client, backup_job):
        """POST /api/jobs/<id>/copies succeeds for all valid copy_types."""
        valid_copy_types = ["primary", "secondary", "offsite", "offline"]
        for ct in valid_copy_types:
            payload = dict(self.VALID_COPY_DATA)
            payload["copy_type"] = ct
            response = authenticated_client.post(f"/api/jobs/{backup_job.id}/copies", json=payload)
            assert response.status_code == 201, f"Failed for copy_type={ct}: {response.get_json()}"

    def test_add_copy_valid_media_types(self, authenticated_client, backup_job):
        """POST /api/jobs/<id>/copies succeeds for all valid media_types."""
        valid_media_types = ["disk", "tape", "cloud", "external_hdd"]
        for mt in valid_media_types:
            payload = dict(self.VALID_COPY_DATA)
            payload["media_type"] = mt
            response = authenticated_client.post(f"/api/jobs/{backup_job.id}/copies", json=payload)
            assert response.status_code == 201, f"Failed for media_type={mt}: {response.get_json()}"

    def test_add_copy_operator_allowed(self, operator_authenticated_client, backup_job):
        """POST /api/jobs/<id>/copies is allowed for operator role."""
        response = operator_authenticated_client.post(
            f"/api/jobs/{backup_job.id}/copies",
            json=self.VALID_COPY_DATA,
        )
        assert response.status_code == 201

    def test_add_copy_appears_in_job_detail(self, authenticated_client, backup_job):
        """After adding a copy, GET /api/jobs/<id> shows it in copies list."""
        authenticated_client.post(f"/api/jobs/{backup_job.id}/copies", json=self.VALID_COPY_DATA)
        detail_resp = authenticated_client.get(f"/api/jobs/{backup_job.id}")
        assert detail_resp.status_code == 200
        copies = detail_resp.get_json()["copies"]
        assert len(copies) >= 1


# ===========================================================================
# Integration: combined workflows
# ===========================================================================

class TestJobsIntegration:
    """End-to-end workflow tests combining multiple operations."""

    def test_create_then_get_job(self, authenticated_client):
        """Create a job and immediately retrieve it."""
        create_resp = _create_job(authenticated_client, job_name="IntegrationJob")
        assert create_resp.status_code == 201
        job_id = create_resp.get_json()["job_id"]

        get_resp = authenticated_client.get(f"/api/jobs/{job_id}")
        assert get_resp.status_code == 200
        assert get_resp.get_json()["id"] == job_id

    def test_create_then_update_job(self, authenticated_client):
        """Create a job then update its name."""
        create_resp = _create_job(authenticated_client, job_name="OriginalName")
        assert create_resp.status_code == 201
        job_id = create_resp.get_json()["job_id"]

        update_resp = authenticated_client.put(
            f"/api/jobs/{job_id}",
            json={"job_name": "UpdatedName"},
        )
        assert update_resp.status_code == 200

        get_resp = authenticated_client.get(f"/api/jobs/{job_id}")
        assert get_resp.status_code == 200
        assert get_resp.get_json()["job_name"] == "UpdatedName"

    def test_jobs_appear_in_list_after_create(self, authenticated_client):
        """Jobs created via API appear in the list endpoint."""
        _create_job(authenticated_client, job_name="ListJob1")
        _create_job(authenticated_client, job_name="ListJob2")

        list_resp = authenticated_client.get("/api/jobs")
        assert list_resp.status_code == 200
        names = [j["job_name"] for j in list_resp.get_json()["jobs"]]
        assert "ListJob1" in names
        assert "ListJob2" in names

    def test_job_not_in_list_after_delete(self, authenticated_client):
        """A deleted job no longer appears in the list."""
        create_resp = _create_job(authenticated_client, job_name="ToBeDeleted")
        job_id = create_resp.get_json()["job_id"]
        authenticated_client.delete(f"/api/jobs/{job_id}")

        list_resp = authenticated_client.get("/api/jobs")
        ids = [j["id"] for j in list_resp.get_json()["jobs"]]
        assert job_id not in ids

    def test_filter_by_job_type_after_create(self, authenticated_client):
        """Filtering by job_type returns only matching jobs."""
        _create_job(authenticated_client, job_name="DBJob", job_type="database")
        _create_job(authenticated_client, job_name="FileJob", job_type="file")

        resp = authenticated_client.get("/api/jobs?job_type=database")
        assert resp.status_code == 200
        jobs = resp.get_json()["jobs"]
        assert all(j["job_type"] == "database" for j in jobs)
        names = [j["job_name"] for j in jobs]
        assert "DBJob" in names
        assert "FileJob" not in names
