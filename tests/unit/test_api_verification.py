"""
Unit tests for verification API endpoints.
app/api/verification.py coverage target: 60%+
"""

import pytest
from datetime import date, timedelta

from app.models import BackupJob, User, VerificationSchedule, VerificationTest, db


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client(client, app):
    """Create admin user and return authenticated client."""
    with app.app_context():
        user = User(
            username="verif_api_admin",
            email="verif_api_admin@example.com",
            full_name="Verification API Admin",
            role="admin",
            is_active=True,
        )
        user.set_password("Admin123!@#")
        db.session.add(user)
        db.session.commit()

    client.post(
        "/auth/login",
        data={"username": "verif_api_admin", "password": "Admin123!@#"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def job_and_user(app):
    """Create a backup job owned by an operator user."""
    with app.app_context():
        user = User(
            username="verif_owner",
            email="verif_owner@example.com",
            full_name="Verif Owner",
            role="operator",
            is_active=True,
        )
        user.set_password("Test123!@#")
        db.session.add(user)
        db.session.commit()

        job = BackupJob(
            job_name="API Verif Job",
            job_type="file",
            backup_tool="custom",
            retention_days=30,
            owner_id=user.id,
            is_active=True,
            schedule_type="daily",
        )
        db.session.add(job)
        db.session.commit()

        yield {"job_id": job.id, "user_id": user.id}


@pytest.fixture
def existing_test(app, job_and_user):
    """Create a single VerificationTest record."""
    with app.app_context():
        from datetime import datetime, timezone

        test = VerificationTest(
            job_id=job_and_user["job_id"],
            tester_id=job_and_user["user_id"],
            test_type="integrity",
            test_date=datetime.now(timezone.utc),
            test_result="success",
            duration_seconds=300,
        )
        db.session.add(test)
        db.session.commit()
        db.session.refresh(test)
        yield test


@pytest.fixture
def existing_schedule(app, job_and_user):
    """Create a single VerificationSchedule record."""
    with app.app_context():
        schedule = VerificationSchedule(
            job_id=job_and_user["job_id"],
            test_frequency="monthly",
            next_test_date=date.today() + timedelta(days=30),
            is_active=True,
        )
        db.session.add(schedule)
        db.session.commit()
        db.session.refresh(schedule)
        yield schedule


# ---------------------------------------------------------------------------
# Tests: GET /api/verification/tests
# ---------------------------------------------------------------------------

class TestListVerificationTests:
    def test_list_verification_tests_authenticated(self, auth_client, existing_test):
        """Authenticated request returns 200 with pagination structure."""
        response = auth_client.get("/api/verification/tests")
        assert response.status_code == 200
        data = response.get_json()
        assert "tests" in data
        assert "pagination" in data
        assert isinstance(data["tests"], list)

    def test_list_verification_tests_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/verification/tests")
        assert response.status_code == 401

    def test_list_tests_filter_by_job(self, auth_client, job_and_user, existing_test):
        """Filter by job_id returns only matching tests."""
        job_id = job_and_user["job_id"]
        response = auth_client.get(f"/api/verification/tests?job_id={job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "tests" in data
        for t in data["tests"]:
            assert t["job_id"] == job_id

    def test_list_tests_filter_by_test_type(self, auth_client, existing_test):
        """Filter by test_type returns only matching tests."""
        response = auth_client.get("/api/verification/tests?test_type=integrity")
        assert response.status_code == 200
        data = response.get_json()
        for t in data["tests"]:
            assert t["test_type"] == "integrity"

    def test_list_tests_pagination(self, auth_client, existing_test):
        """Pagination parameters are respected."""
        response = auth_client.get("/api/verification/tests?page=1&per_page=5")
        assert response.status_code == 200
        data = response.get_json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 5

    def test_list_tests_empty_result(self, auth_client):
        """Returns empty list when no tests exist."""
        response = auth_client.get("/api/verification/tests")
        assert response.status_code == 200
        data = response.get_json()
        assert data["tests"] == []


# ---------------------------------------------------------------------------
# Tests: GET /api/verification/tests/<id>
# ---------------------------------------------------------------------------

class TestGetVerificationTest:
    def test_get_verification_test_found(self, auth_client, existing_test):
        """Returns 200 with test details for a valid ID."""
        response = auth_client.get(f"/api/verification/tests/{existing_test.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == existing_test.id
        assert data["test_type"] == "integrity"
        assert data["test_result"] == "success"

    def test_get_verification_test_not_found(self, auth_client):
        """Returns 404 for non-existent test ID."""
        response = auth_client.get("/api/verification/tests/999999")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "TEST_NOT_FOUND"

    def test_get_verification_test_unauthenticated(self, client, existing_test):
        """Unauthenticated request returns 401."""
        response = client.get(f"/api/verification/tests/{existing_test.id}")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: POST /api/verification/tests
# ---------------------------------------------------------------------------

class TestCreateVerificationTest:
    def test_create_verification_test_success(self, auth_client, job_and_user):
        """Valid POST creates a test and returns 201."""
        test_data = {
            "job_id": job_and_user["job_id"],
            "test_type": "integrity",
            "test_result": "success",
            "duration_seconds": 300,
        }
        response = auth_client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 201
        data = response.get_json()
        assert "test_id" in data
        assert data["test_result"] == "success"

    def test_create_verification_test_full_restore(self, auth_client, job_and_user):
        """Creates a full_restore type test."""
        test_data = {
            "job_id": job_and_user["job_id"],
            "test_type": "full_restore",
            "test_result": "failed",
            "restore_target": "TEST-SERVER",
            "notes": "Restore failed due to disk space",
        }
        response = auth_client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 201

    def test_create_verification_test_missing_fields(self, auth_client):
        """Missing required fields returns 400."""
        response = auth_client.post("/api/verification/tests", json={})
        assert response.status_code == 400
        data = response.get_json()
        assert "errors" in data or "error" in data

    def test_create_verification_test_missing_job_id(self, auth_client):
        """Missing job_id field returns 400."""
        test_data = {"test_type": "integrity", "test_result": "success"}
        response = auth_client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 400

    def test_create_verification_test_invalid_type(self, auth_client, job_and_user):
        """Invalid test_type returns 400."""
        test_data = {
            "job_id": job_and_user["job_id"],
            "test_type": "invalid_type",
            "test_result": "success",
        }
        response = auth_client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 400

    def test_create_verification_test_invalid_result(self, auth_client, job_and_user):
        """Invalid test_result returns 400."""
        test_data = {
            "job_id": job_and_user["job_id"],
            "test_type": "integrity",
            "test_result": "unknown",
        }
        response = auth_client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 400

    def test_create_verification_test_job_not_found(self, auth_client):
        """Non-existent job_id returns 404."""
        test_data = {
            "job_id": 999999,
            "test_type": "integrity",
            "test_result": "success",
        }
        response = auth_client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 404

    def test_create_verification_test_negative_duration(self, auth_client, job_and_user):
        """Negative duration_seconds returns 400."""
        test_data = {
            "job_id": job_and_user["job_id"],
            "test_type": "integrity",
            "test_result": "success",
            "duration_seconds": -10,
        }
        response = auth_client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 400

    def test_create_test_unauthenticated(self, client, job_and_user):
        """Unauthenticated POST returns 401."""
        test_data = {
            "job_id": job_and_user["job_id"],
            "test_type": "integrity",
            "test_result": "success",
        }
        response = client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 401

    def test_create_test_updates_schedule(self, auth_client, app, job_and_user):
        """Creating a test when schedule exists updates schedule dates."""
        with app.app_context():
            schedule = VerificationSchedule(
                job_id=job_and_user["job_id"],
                test_frequency="monthly",
                next_test_date=date.today() + timedelta(days=5),
                is_active=True,
            )
            db.session.add(schedule)
            db.session.commit()
            schedule_id = schedule.id

        test_data = {
            "job_id": job_and_user["job_id"],
            "test_type": "integrity",
            "test_result": "success",
        }
        response = auth_client.post("/api/verification/tests", json=test_data)
        assert response.status_code == 201

        with app.app_context():
            updated = db.session.get(VerificationSchedule, schedule_id)
            assert updated.last_test_date is not None


# ---------------------------------------------------------------------------
# Tests: GET /api/verification/schedules
# ---------------------------------------------------------------------------

class TestListSchedules:
    def test_list_schedules_authenticated(self, auth_client, existing_schedule):
        """Authenticated request returns 200 with schedules list."""
        response = auth_client.get("/api/verification/schedules")
        assert response.status_code == 200
        data = response.get_json()
        assert "schedules" in data
        assert "pagination" in data

    def test_list_schedules_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/verification/schedules")
        assert response.status_code == 401

    def test_list_schedules_empty(self, auth_client):
        """Returns empty list when no active schedules exist."""
        response = auth_client.get("/api/verification/schedules")
        assert response.status_code == 200
        data = response.get_json()
        assert data["schedules"] == []

    def test_list_schedules_overdue_filter(self, auth_client, app, job_and_user):
        """Overdue filter returns only past-due schedules."""
        with app.app_context():
            schedule = VerificationSchedule(
                job_id=job_and_user["job_id"],
                test_frequency="monthly",
                next_test_date=date.today() - timedelta(days=10),
                is_active=True,
            )
            db.session.add(schedule)
            db.session.commit()

        response = auth_client.get("/api/verification/schedules?overdue=true")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["schedules"]) >= 1
        for s in data["schedules"]:
            assert s["is_overdue"] is True

    def test_list_schedules_overdue_tests_endpoint(self, auth_client, app, job_and_user):
        """Overdue=true query param returns schedules with past next_test_date."""
        with app.app_context():
            overdue_sched = VerificationSchedule(
                job_id=job_and_user["job_id"],
                test_frequency="quarterly",
                next_test_date=date.today() - timedelta(days=30),
                is_active=True,
            )
            db.session.add(overdue_sched)
            db.session.commit()

        response = auth_client.get("/api/verification/schedules?overdue=true")
        assert response.status_code == 200
        data = response.get_json()
        assert "schedules" in data


# ---------------------------------------------------------------------------
# Tests: GET /api/verification/schedules/<id>
# ---------------------------------------------------------------------------

class TestGetSchedule:
    def test_get_schedule_not_found(self, auth_client):
        """PUT to non-existent schedule returns 404."""
        response = auth_client.put("/api/verification/schedules/999999", json={"test_frequency": "monthly"})
        assert response.status_code == 404

    def test_get_schedule_unauthenticated(self, client, existing_schedule):
        """Unauthenticated PUT returns 401."""
        response = client.put(
            f"/api/verification/schedules/{existing_schedule.id}",
            json={"test_frequency": "quarterly"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: POST /api/verification/schedules
# ---------------------------------------------------------------------------

class TestCreateSchedule:
    def test_create_schedule_success(self, auth_client, job_and_user):
        """Valid POST creates a schedule and returns 201."""
        schedule_data = {
            "job_id": job_and_user["job_id"],
            "test_frequency": "monthly",
            "next_test_date": "2026-12-01",
        }
        response = auth_client.post("/api/verification/schedules", json=schedule_data)
        assert response.status_code == 201
        data = response.get_json()
        assert "schedule_id" in data
        assert data["job_id"] == job_and_user["job_id"]

    def test_create_schedule_missing_fields(self, auth_client):
        """Missing required fields returns 400."""
        response = auth_client.post("/api/verification/schedules", json={})
        assert response.status_code == 400

    def test_create_schedule_invalid_frequency(self, auth_client, job_and_user):
        """Invalid test_frequency returns 400."""
        schedule_data = {
            "job_id": job_and_user["job_id"],
            "test_frequency": "biweekly",
            "next_test_date": "2026-12-01",
        }
        response = auth_client.post("/api/verification/schedules", json=schedule_data)
        assert response.status_code == 400

    def test_create_schedule_invalid_date_format(self, auth_client, job_and_user):
        """Invalid date format returns 400."""
        schedule_data = {
            "job_id": job_and_user["job_id"],
            "test_frequency": "monthly",
            "next_test_date": "01-12-2026",
        }
        response = auth_client.post("/api/verification/schedules", json=schedule_data)
        assert response.status_code == 400

    def test_create_schedule_job_not_found(self, auth_client):
        """Non-existent job_id returns 404."""
        schedule_data = {
            "job_id": 999999,
            "test_frequency": "monthly",
            "next_test_date": "2026-12-01",
        }
        response = auth_client.post("/api/verification/schedules", json=schedule_data)
        assert response.status_code == 404

    def test_create_schedule_conflict(self, auth_client, job_and_user, existing_schedule):
        """Creating duplicate active schedule returns 409."""
        schedule_data = {
            "job_id": job_and_user["job_id"],
            "test_frequency": "monthly",
            "next_test_date": "2026-12-01",
        }
        response = auth_client.post("/api/verification/schedules", json=schedule_data)
        assert response.status_code == 409

    def test_create_schedule_quarterly(self, auth_client, app, job_and_user):
        """Creates a quarterly schedule successfully."""
        # Use a different job to avoid conflict
        with app.app_context():
            user = db.session.get(User, job_and_user["user_id"])
            new_job = BackupJob(
                job_name="Quarterly Verif Job",
                job_type="file",
                backup_tool="custom",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
                schedule_type="weekly",
            )
            db.session.add(new_job)
            db.session.commit()
            new_job_id = new_job.id

        schedule_data = {
            "job_id": new_job_id,
            "test_frequency": "quarterly",
            "next_test_date": "2026-09-01",
        }
        response = auth_client.post("/api/verification/schedules", json=schedule_data)
        assert response.status_code == 201

    def test_create_schedule_unauthenticated(self, client, job_and_user):
        """Unauthenticated POST returns 401."""
        schedule_data = {
            "job_id": job_and_user["job_id"],
            "test_frequency": "monthly",
            "next_test_date": "2026-12-01",
        }
        response = client.post("/api/verification/schedules", json=schedule_data)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: PUT /api/verification/schedules/<id>
# ---------------------------------------------------------------------------

class TestUpdateSchedule:
    def test_update_schedule_success(self, auth_client, existing_schedule):
        """Valid PUT updates the schedule and returns 200."""
        update_data = {
            "test_frequency": "quarterly",
            "next_test_date": "2027-01-01",
        }
        response = auth_client.put(
            f"/api/verification/schedules/{existing_schedule.id}",
            json=update_data,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["schedule_id"] == existing_schedule.id

    def test_update_schedule_not_found(self, auth_client):
        """Returns 404 for non-existent schedule ID."""
        update_data = {"test_frequency": "quarterly"}
        response = auth_client.put("/api/verification/schedules/999999", json=update_data)
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "SCHEDULE_NOT_FOUND"

    def test_update_schedule_invalid_frequency(self, auth_client, existing_schedule):
        """Invalid test_frequency returns 400."""
        update_data = {"test_frequency": "daily"}
        response = auth_client.put(
            f"/api/verification/schedules/{existing_schedule.id}",
            json=update_data,
        )
        assert response.status_code == 400

    def test_update_schedule_deactivate(self, auth_client, existing_schedule):
        """Setting is_active=False deactivates the schedule."""
        update_data = {"is_active": False}
        response = auth_client.put(
            f"/api/verification/schedules/{existing_schedule.id}",
            json=update_data,
        )
        assert response.status_code == 200

    def test_update_schedule_unauthenticated(self, client, existing_schedule):
        """Unauthenticated PUT returns 401."""
        response = client.put(
            f"/api/verification/schedules/{existing_schedule.id}",
            json={"test_frequency": "quarterly"},
        )
        assert response.status_code == 401
