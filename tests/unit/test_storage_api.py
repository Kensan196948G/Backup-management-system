"""
Unit tests for app/api/v1/storage_api.py
Covers: list providers, get provider, test connection, get space, list backups
"""

import app.api.v1.storage_api  # register v1 storage routes onto api_bp  # noqa: F401

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models import User, db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_token(client, app, username="stor_admin", role="admin"):
    with app.app_context():
        user = User(
            username=username,
            email=f"{username}@example.com",
            full_name="Storage Admin",
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


def _make_backup_copy(id=1, job_id=1, storage_location="/backups", location_type="onsite"):
    bc = MagicMock()
    bc.id = id
    bc.job_id = job_id
    bc.storage_location = storage_location
    bc.location_type = location_type
    bc.copy_type = "primary"
    bc.backup_size_bytes = 1024 * 1024
    bc.created_at = datetime.now(timezone.utc)
    bc.verified_at = None
    return bc


# ---------------------------------------------------------------------------
# Tests: List Storage Providers
# ---------------------------------------------------------------------------

class TestListStorageProviders:

    def test_list_success(self, client, app):
        token = _get_token(client, app)

        provider_row = MagicMock()
        provider_row.storage_location = "/backups/primary"
        provider_row.location_type = "onsite"
        provider_row.backup_count = 5
        provider_row.total_size_bytes = 5 * 1024 * 1024
        provider_row.last_updated = datetime.now(timezone.utc)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [provider_row]

        with patch("app.api.v1.storage_api.db") as mock_db, \
             patch("app.api.v1.storage_api.BackupCopy") as MockBC:
            MockBC.storage_location = MagicMock()
            MockBC.location_type = MagicMock()
            mock_db.session.query.return_value.group_by.return_value = mock_query
            mock_db.func.count.return_value = MagicMock()
            mock_db.func.sum.return_value = MagicMock()
            mock_db.func.max.return_value = MagicMock()

            resp = client.get(
                "/api/v1/storage/providers",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_list_unauthenticated(self, client, app):
        resp = client.get("/api/v1/storage/providers")
        assert resp.status_code == 401

    def test_list_with_location_type_filter(self, client, app):
        token = _get_token(client, app, username="stor_admin2")

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        with patch("app.api.v1.storage_api.db") as mock_db, \
             patch("app.api.v1.storage_api.BackupCopy") as MockBC:
            MockBC.storage_location = MagicMock()
            MockBC.location_type = MagicMock()
            mock_db.session.query.return_value.group_by.return_value = mock_query
            mock_db.func.count.return_value = MagicMock()
            mock_db.func.sum.return_value = MagicMock()
            mock_db.func.max.return_value = MagicMock()

            resp = client.get(
                "/api/v1/storage/providers?location_type=offsite",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: Get Storage Provider
# ---------------------------------------------------------------------------

class TestGetStorageProvider:

    def test_get_returns_501(self, client, app):
        token = _get_token(client, app, username="stor_admin3")
        resp = client.get(
            "/api/v1/storage/providers/1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 501

    def test_get_unauthenticated(self, client, app):
        resp = client.get("/api/v1/storage/providers/1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Test Storage Connection
# ---------------------------------------------------------------------------

class TestTestStorageConnection:

    def test_test_connection_no_body(self, client, app):
        token = _get_token(client, app, username="stor_admin4")
        resp = client.post(
            "/api/v1/storage/test",
            data="",
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert resp.status_code in (400, 422, 500)

    def test_test_connection_nonexistent_path(self, client, app):
        token = _get_token(client, app, username="stor_admin5")
        resp = client.post(
            "/api/v1/storage/test",
            json={
                "provider_type": "local",
                "connection_string": "/nonexistent/path/xyz123",
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["success"] is False

    def test_test_connection_existing_path(self, client, app):
        token = _get_token(client, app, username="stor_admin6")
        resp = client.post(
            "/api/v1/storage/test",
            json={
                "provider_type": "local",
                "connection_string": "/tmp",
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_test_connection_unauthenticated(self, client, app):
        resp = client.post(
            "/api/v1/storage/test",
            json={"provider_type": "local", "connection_string": "/tmp"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_test_connection_validation_error(self, client, app):
        token = _get_token(client, app, username="stor_admin7")
        # Missing required fields
        resp = client.post(
            "/api/v1/storage/test",
            json={"provider_type": "local"},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Tests: Get Storage Space
# ---------------------------------------------------------------------------

class TestGetStorageSpace:

    def test_get_space_success(self, client, app):
        token = _get_token(client, app, username="stor_admin8")
        bc = _make_backup_copy(storage_location="/tmp")

        with patch("app.api.v1.storage_api.db") as mock_db, \
             patch("app.api.v1.storage_api.BackupCopy") as MockBC:
            mock_db.session.get.return_value = bc
            mock_q = MagicMock()
            MockBC.query = mock_q
            mock_q.filter_by.return_value = mock_q
            mock_q.count.return_value = 2
            mock_db.session.query.return_value.filter_by.return_value.scalar.return_value = 2048

            resp = client.get(
                "/api/v1/storage/1/space",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_get_space_not_found(self, client, app):
        token = _get_token(client, app, username="stor_admin9")

        with patch("app.api.v1.storage_api.db") as mock_db:
            mock_db.session.get.return_value = None
            resp = client.get(
                "/api/v1/storage/999/space",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 404

    def test_get_space_unauthenticated(self, client, app):
        resp = client.get("/api/v1/storage/1/space")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: List Storage Backups
# ---------------------------------------------------------------------------

class TestListStorageBackups:

    def test_list_backups_success(self, client, app):
        token = _get_token(client, app, username="stor_admin10")
        bc = _make_backup_copy(storage_location="/tmp")
        bc2 = _make_backup_copy(id=2, storage_location="/tmp")

        pagination = MagicMock()
        pagination.items = [bc2]
        pagination.total = 1
        pagination.pages = 1

        with patch("app.api.v1.storage_api.db") as mock_db, \
             patch("app.api.v1.storage_api.BackupCopy") as MockBC:
            mock_db.session.get.return_value = bc
            mock_q = MagicMock()
            MockBC.query = mock_q
            mock_q.filter_by.return_value = mock_q
            mock_db.desc.return_value = MagicMock()
            mock_q.order_by.return_value = mock_q
            mock_q.paginate.return_value = pagination

            resp = client.get(
                "/api/v1/storage/1/backups",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_list_backups_not_found(self, client, app):
        token = _get_token(client, app, username="stor_admin11")

        with patch("app.api.v1.storage_api.db") as mock_db:
            mock_db.session.get.return_value = None
            resp = client.get(
                "/api/v1/storage/999/backups",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 404

    def test_list_backups_unauthenticated(self, client, app):
        resp = client.get("/api/v1/storage/1/backups")
        assert resp.status_code == 401
