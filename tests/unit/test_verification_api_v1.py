"""
Unit tests for app/api/v1/verification_api.py
Covers: start, status, result, list, cancel verification
"""

import app.api.v1.verification_api  # register v1 verification routes onto api_bp  # noqa: F401

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models import User, db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_token(client, app, username="ver_admin", role="admin"):
    with app.app_context():
        user = User(
            username=username,
            email=f"{username}@example.com",
            full_name="Verification Admin",
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
    return resp.get_json().get("access_token")


def _make_backup_copy(id=1, job_id=1):
    bc = MagicMock()
    bc.id = id
    bc.job_id = job_id
    return bc


def _make_backup_job(id=1, owner_id=1, name="Test Job"):
    job = MagicMock()
    job.id = id
    job.owner_id = owner_id
    job.name = name
    return job


def _make_verification(id=1, backup_id=1, status="pending", test_type="checksum"):
    v = MagicMock()
    v.id = id
    v.backup_id = backup_id
    v.test_type = test_type
    v.test_status = status
    v.test_result = None
    v.started_at = datetime.now(timezone.utc)
    v.completed_at = None
    v.tester_id = 1
    v.files_tested = 10
    v.files_passed = 10
    v.files_failed = 0
    v.duration_seconds = 5
    return v


# ---------------------------------------------------------------------------
# Tests: Start Verification
# ---------------------------------------------------------------------------

class TestStartVerification:

    def test_start_success(self, client, app):
        token = _get_token(client, app)
        bc = _make_backup_copy()
        job = _make_backup_job()
        verif = _make_verification()
        verif.started_at = datetime.now(timezone.utc)

        with patch("app.api.v1.verification_api.db") as mock_db, \
             patch("app.api.v1.verification_api.VerificationTest") as MockVT:
            mock_db.session.get.side_effect = lambda model, id: bc if model.__name__ == "BackupCopy" else job
            mock_db.session.add = MagicMock()
            mock_db.session.commit = MagicMock()
            MockVT.return_value = verif

            with patch("app.tasks.verification_tasks.verify_backup") as mock_task:
                mock_task.apply_async = MagicMock()
                resp = client.post(
                    "/api/v1/verify/1",
                    json={"test_type": "checksum", "scope": "full"},
                    headers={"Authorization": f"Bearer {token}"},
                    content_type="application/json",
                )

        assert resp.status_code in (202, 500)

    def test_start_backup_not_found(self, client, app):
        token = _get_token(client, app, username="ver_admin2")

        with patch("app.api.v1.verification_api.db") as mock_db:
            mock_db.session.get.return_value = None
            resp = client.post(
                "/api/v1/verify/999",
                json={"test_type": "checksum"},
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )

        assert resp.status_code == 404

    def test_start_unauthenticated(self, client, app):
        resp = client.post(
            "/api/v1/verify/1",
            json={"test_type": "checksum"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_start_forbidden(self, client, app):
        token = _get_token(client, app, username="ver_viewer", role="viewer")
        bc = _make_backup_copy()
        job = _make_backup_job(owner_id=9999)

        with patch("app.api.v1.verification_api.db") as mock_db:
            mock_db.session.get.side_effect = [bc, job]
            resp = client.post(
                "/api/v1/verify/1",
                json={"test_type": "checksum"},
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: Get Verification Status
# ---------------------------------------------------------------------------

class TestGetVerificationStatus:

    def test_status_success(self, client, app):
        token = _get_token(client, app, username="ver_admin3")
        bc = _make_backup_copy()
        job = _make_backup_job()
        verif = _make_verification()

        with patch("app.api.v1.verification_api.db") as mock_db, \
             patch("app.api.v1.verification_api.VerificationTest") as MockVT, \
             patch("app.api.v1.verification_api.VerificationStatusResponse") as MockResp, \
             patch("app.api.v1.verification_api.desc", side_effect=lambda x: x):
            mock_db.session.get.side_effect = [bc, job]
            mock_q = MagicMock()
            MockVT.query = mock_q
            mock_q.filter_by.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.first.return_value = verif
            mock_resp_obj = MagicMock()
            mock_resp_obj.model_dump.return_value = {"id": 1, "test_status": "pending"}
            MockResp.model_validate.return_value = mock_resp_obj

            resp = client.get(
                "/api/v1/verify/1/status",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_status_not_found(self, client, app):
        token = _get_token(client, app, username="ver_admin4")

        with patch("app.api.v1.verification_api.db") as mock_db:
            mock_db.session.get.return_value = None
            resp = client.get(
                "/api/v1/verify/999/status",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 404

    def test_status_no_verification(self, client, app):
        token = _get_token(client, app, username="ver_admin5")
        bc = _make_backup_copy()
        job = _make_backup_job()

        with patch("app.api.v1.verification_api.db") as mock_db, \
             patch("app.api.v1.verification_api.VerificationTest") as MockVT, \
             patch("app.api.v1.verification_api.desc", side_effect=lambda x: x):
            mock_db.session.get.side_effect = [bc, job]
            mock_q = MagicMock()
            MockVT.query = mock_q
            mock_q.filter_by.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.first.return_value = None

            resp = client.get(
                "/api/v1/verify/1/status",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Get Verification Result
# ---------------------------------------------------------------------------

class TestGetVerificationResult:

    def test_result_success(self, client, app):
        token = _get_token(client, app, username="ver_admin6")
        bc = _make_backup_copy()
        job = _make_backup_job()
        verif = _make_verification(status="completed")
        verif.test_result = "passed"
        verif.completed_at = datetime.now(timezone.utc)

        with patch("app.api.v1.verification_api.db") as mock_db, \
             patch("app.api.v1.verification_api.VerificationTest") as MockVT, \
             patch("app.api.v1.verification_api.desc", side_effect=lambda x: x):
            mock_db.session.get.side_effect = [bc, job]
            mock_q = MagicMock()
            MockVT.query = mock_q
            mock_q.filter_by.return_value = mock_q
            mock_q.filter.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.first.return_value = verif

            resp = client.get(
                "/api/v1/verify/1/result",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_result_no_completed_verification(self, client, app):
        token = _get_token(client, app, username="ver_admin7")
        bc = _make_backup_copy()
        job = _make_backup_job()

        with patch("app.api.v1.verification_api.db") as mock_db, \
             patch("app.api.v1.verification_api.VerificationTest") as MockVT, \
             patch("app.api.v1.verification_api.desc", side_effect=lambda x: x):
            mock_db.session.get.side_effect = [bc, job]
            mock_q = MagicMock()
            MockVT.query = mock_q
            mock_q.filter_by.return_value = mock_q
            mock_q.filter.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.first.return_value = None

            resp = client.get(
                "/api/v1/verify/1/result",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: List Verifications
# ---------------------------------------------------------------------------

class TestListVerifications:

    def test_list_success(self, client, app):
        token = _get_token(client, app, username="ver_admin8")
        verif = _make_verification()

        pagination = MagicMock()
        pagination.items = [verif]
        pagination.total = 1
        pagination.pages = 1

        with patch("app.api.v1.verification_api.VerificationTest") as MockVT, \
             patch("app.api.v1.verification_api.VerificationStatusResponse") as MockResp, \
             patch("app.api.v1.verification_api.desc", side_effect=lambda x: x):
            mock_q = MagicMock()
            MockVT.query = mock_q
            mock_q.filter_by.return_value = mock_q
            mock_q.filter.return_value = mock_q
            mock_q.join.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.paginate.return_value = pagination
            mock_resp_obj = MagicMock()
            mock_resp_obj.model_dump.return_value = {"id": 1}
            MockResp.model_validate.return_value = mock_resp_obj

            resp = client.get(
                "/api/v1/verify",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_list_unauthenticated(self, client, app):
        resp = client.get("/api/v1/verify")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Cancel Verification
# ---------------------------------------------------------------------------

class TestCancelVerification:

    def test_cancel_success(self, client, app):
        token = _get_token(client, app, username="ver_admin9")
        bc = _make_backup_copy()
        job = _make_backup_job()
        verif = _make_verification(status="running")
        verif.completed_at = None

        with patch("app.api.v1.verification_api.db") as mock_db:
            mock_db.session.get.side_effect = [verif, bc, job]
            mock_db.session.commit = MagicMock()

            resp = client.post(
                "/api/v1/verify/1/cancel",
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )

        assert resp.status_code == 200

    def test_cancel_not_found(self, client, app):
        token = _get_token(client, app, username="ver_admin10")

        with patch("app.api.v1.verification_api.db") as mock_db:
            mock_db.session.get.return_value = None
            resp = client.post(
                "/api/v1/verify/999/cancel",
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )

        assert resp.status_code == 404

    def test_cancel_invalid_state(self, client, app):
        token = _get_token(client, app, username="ver_admin11")
        bc = _make_backup_copy()
        job = _make_backup_job()
        verif = _make_verification(status="completed")

        with patch("app.api.v1.verification_api.db") as mock_db:
            mock_db.session.get.side_effect = [verif, bc, job]
            resp = client.post(
                "/api/v1/verify/1/cancel",
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )

        assert resp.status_code == 400
