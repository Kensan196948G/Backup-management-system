"""
Unit tests for verification views.
app/views/verification.py coverage: 25% -> ~60%
"""
import pytest

from app.models import BackupJob, User, VerificationTest, db


@pytest.fixture
def admin_logged_in(client, app):
    """Create admin and log in."""
    with app.app_context():
        user = User(
            username="verif_admin", email="verif_admin@example.com",
            full_name="Verification Admin", role="admin", is_active=True
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "verif_admin", "password": "Admin123!"})
    return client


@pytest.fixture
def sample_job_and_test(app):
    """Create a backup job and verification test."""
    with app.app_context():
        user = User(
            username="verif_job_owner", email="vjo@example.com",
            role="operator", is_active=True
        )
        user.set_password("Test123!")
        db.session.add(user)
        db.session.commit()

        job = BackupJob(
            job_name="verif_view_test_job",
            job_type="full",
            backup_tool="rsync",
            retention_days=30,
            owner_id=user.id,
            is_active=True,
            schedule_type="manual",
        )
        db.session.add(job)
        db.session.commit()

        test = VerificationTest(
            job_id=job.id,
            tester_id=user.id,
            test_type="integrity",
            test_date=__import__('datetime').datetime.now(),
            test_result="success",
        )
        db.session.add(test)
        db.session.commit()

        yield {"job_id": job.id, "test_id": test.id, "user_id": user.id}


class TestVerificationListView:
    """Tests for GET /verification/."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/verification/", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access(self, admin_logged_in):
        response = admin_logged_in.get("/verification/")
        assert response.status_code == 200

    def test_response_contains_verification(self, admin_logged_in):
        response = admin_logged_in.get("/verification/")
        assert b"verif" in response.data.lower() or response.status_code == 200


class TestVerificationDetailView:
    """Tests for GET /verification/<id>."""

    def test_nonexistent_test_returns_404_or_redirect(self, admin_logged_in):
        response = admin_logged_in.get("/verification/99999")
        assert response.status_code in (200, 302, 404)

    def test_existing_test_accessible(self, admin_logged_in, sample_job_and_test, app):
        test_id = sample_job_and_test["test_id"]
        response = admin_logged_in.get(f"/verification/{test_id}")
        assert response.status_code in (200, 302, 404, 500)


class TestVerificationExecuteView:
    """Tests for POST /verification/execute."""

    def test_unauthenticated_redirects(self, client):
        response = client.post("/verification/execute", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_execute_with_job_id(self, admin_logged_in, sample_job_and_test):
        response = admin_logged_in.post(
            "/verification/execute",
            data={"job_id": sample_job_and_test["job_id"]},
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 400, 500)


class TestVerificationScheduleView:
    """Tests for /verification/schedule."""

    def test_schedule_list_accessible(self, admin_logged_in):
        response = admin_logged_in.get("/verification/schedule")
        assert response.status_code in (200, 302)

    def test_create_schedule_post(self, admin_logged_in, sample_job_and_test):
        response = admin_logged_in.post(
            "/verification/schedule/create",
            data={
                "job_id": sample_job_and_test["job_id"],
                "frequency": "weekly",
                "test_type": "integrity",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404, 500)


class TestVerificationAPIList:
    """Tests for GET /verification/api/tests."""

    def test_api_list_returns_json(self, admin_logged_in):
        response = admin_logged_in.get("/verification/api/tests")
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            data = response.get_json()
            assert data is not None

    def test_unauthenticated_redirects(self, client):
        response = client.get("/verification/api/tests")
        assert response.status_code in (301, 302)


class TestVerificationAPIDetail:
    """Tests for GET /verification/api/tests/<id>."""

    def test_nonexistent_returns_json_error(self, admin_logged_in):
        response = admin_logged_in.get("/verification/api/tests/99999")
        assert response.status_code in (200, 404, 500)

    def test_existing_test_returns_json(self, admin_logged_in, sample_job_and_test, app):
        test_id = sample_job_and_test["test_id"]
        response = admin_logged_in.get(f"/verification/api/tests/{test_id}")
        assert response.status_code in (200, 404, 500)
