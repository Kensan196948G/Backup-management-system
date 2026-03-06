"""
Comprehensive unit tests for app/api/backup.py
Tests backup status update and last execution API endpoints.
"""

from unittest.mock import patch

import pytest

from app.models import BackupExecution, BackupJob, User, db


class TestUpdateBackupStatus:
    """Tests for POST /api/backup/status"""

    def _post_status(self, client, data):
        return client.post(
            "/api/backup/status",
            json=data,
            content_type="application/json",
        )

    def test_update_backup_status_success(self, authenticated_client, backup_job):
        """POST /api/backup/status with valid data returns 201."""
        with patch("app.api.backup.AlertManager") as mock_am, \
             patch("app.api.backup.ComplianceChecker") as mock_cc:
            mock_cc.return_value.check_3_2_1_1_0.return_value = {"status": "compliant"}
            response = self._post_status(authenticated_client, {
                "job_id": backup_job.id,
                "execution_result": "success",
                "backup_size_bytes": 1073741824,
                "duration_seconds": 300,
            })
        assert response.status_code == 201
        data = response.get_json()
        assert "execution_id" in data
        assert "compliance_status" in data
        assert data["compliance_status"] == "compliant"

    def test_update_backup_status_unauthenticated(self, client, backup_job):
        """POST /api/backup/status returns 401 for unauthenticated user."""
        response = self._post_status(client, {
            "job_id": backup_job.id,
            "execution_result": "success",
        })
        assert response.status_code == 401

    def test_update_backup_status_missing_job_id(self, authenticated_client):
        """POST /api/backup/status missing job_id returns 400."""
        response = self._post_status(authenticated_client, {
            "execution_result": "success",
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "job_id" in data["error"]["details"]["fields"]

    def test_update_backup_status_missing_execution_result(self, authenticated_client, backup_job):
        """POST /api/backup/status missing execution_result returns 400."""
        response = self._post_status(authenticated_client, {
            "job_id": backup_job.id,
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "execution_result" in data["error"]["details"]["fields"]

    def test_update_backup_status_job_not_found(self, authenticated_client):
        """POST /api/backup/status with invalid job_id returns 404."""
        with patch("app.api.backup.AlertManager"), \
             patch("app.api.backup.ComplianceChecker"):
            response = self._post_status(authenticated_client, {
                "job_id": 99999,
                "execution_result": "success",
            })
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "JOB_NOT_FOUND"

    def test_update_backup_status_invalid_result(self, authenticated_client, backup_job):
        """POST /api/backup/status with bad execution_result returns 400."""
        response = self._post_status(authenticated_client, {
            "job_id": backup_job.id,
            "execution_result": "invalid_result",
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "execution_result" in data["error"]["details"]["fields"]

    def test_update_backup_status_with_date(self, authenticated_client, backup_job):
        """POST /api/backup/status with execution_date returns 201."""
        with patch("app.api.backup.AlertManager") as mock_am, \
             patch("app.api.backup.ComplianceChecker") as mock_cc:
            mock_cc.return_value.check_3_2_1_1_0.return_value = {"status": "compliant"}
            response = self._post_status(authenticated_client, {
                "job_id": backup_job.id,
                "execution_result": "success",
                "execution_date": "2025-10-30T03:00:00Z",
            })
        assert response.status_code == 201

    def test_update_backup_status_with_invalid_date(self, authenticated_client, backup_job):
        """POST /api/backup/status with bad execution_date returns 400."""
        response = self._post_status(authenticated_client, {
            "job_id": backup_job.id,
            "execution_result": "success",
            "execution_date": "not-a-date",
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_update_backup_status_failed_result(self, authenticated_client, backup_job):
        """POST /api/backup/status with failed execution_result triggers alert creation."""
        with patch("app.api.backup.AlertManager") as mock_am, \
             patch("app.api.backup.ComplianceChecker") as mock_cc:
            mock_cc.return_value.check_3_2_1_1_0.return_value = {"status": "non_compliant"}
            response = self._post_status(authenticated_client, {
                "job_id": backup_job.id,
                "execution_result": "failed",
                "error_message": "Disk full",
            })
        assert response.status_code == 201
        # AlertManager.create_failure_alert should have been called
        mock_am.return_value.create_failure_alert.assert_called_once()

    def test_update_backup_status_warning_result(self, authenticated_client, backup_job):
        """POST /api/backup/status with warning execution_result triggers alert creation."""
        with patch("app.api.backup.AlertManager") as mock_am, \
             patch("app.api.backup.ComplianceChecker") as mock_cc:
            mock_cc.return_value.check_3_2_1_1_0.return_value = {"status": "compliant"}
            response = self._post_status(authenticated_client, {
                "job_id": backup_job.id,
                "execution_result": "warning",
            })
        assert response.status_code == 201
        mock_am.return_value.create_failure_alert.assert_called_once()

    def test_update_backup_status_success_no_alert(self, authenticated_client, backup_job):
        """POST /api/backup/status with success does NOT trigger alert creation."""
        with patch("app.api.backup.AlertManager") as mock_am, \
             patch("app.api.backup.ComplianceChecker") as mock_cc:
            mock_cc.return_value.check_3_2_1_1_0.return_value = {"status": "compliant"}
            response = self._post_status(authenticated_client, {
                "job_id": backup_job.id,
                "execution_result": "success",
            })
        assert response.status_code == 201
        mock_am.return_value.create_failure_alert.assert_not_called()

    def test_update_backup_status_creates_execution_record(self, authenticated_client, backup_job, app):
        """POST /api/backup/status creates a BackupExecution record in the DB."""
        with patch("app.api.backup.AlertManager"), \
             patch("app.api.backup.ComplianceChecker") as mock_cc:
            mock_cc.return_value.check_3_2_1_1_0.return_value = {"status": "compliant"}
            response = self._post_status(authenticated_client, {
                "job_id": backup_job.id,
                "execution_result": "success",
                "backup_size_bytes": 512000,
                "duration_seconds": 120,
                "source_system": "pytest",
            })
        assert response.status_code == 201
        exec_id = response.get_json()["execution_id"]
        with app.app_context():
            execution = db.session.get(BackupExecution, exec_id)
            assert execution is not None
            assert execution.job_id == backup_job.id
            assert execution.execution_result == "success"
            assert execution.backup_size_bytes == 512000
            assert execution.source_system == "pytest"


class TestUpdateCopyStatus:
    """Tests for POST /api/backup/copy-status"""

    def _post_copy_status(self, client, data):
        return client.post(
            "/api/backup/copy-status",
            json=data,
            content_type="application/json",
        )

    def test_update_copy_status_success(self, authenticated_client, backup_copies):
        """POST /api/backup/copy-status with valid data returns 200."""
        copy = backup_copies[0]
        response = self._post_copy_status(authenticated_client, {
            "copy_id": copy.id,
            "status": "success",
            "last_backup_size": 2048,
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["copy_id"] == copy.id
        assert data["status"] == "success"

    def test_update_copy_status_unauthenticated(self, client, backup_copies):
        """POST /api/backup/copy-status returns 401 for unauthenticated user."""
        response = self._post_copy_status(client, {
            "copy_id": backup_copies[0].id,
            "status": "success",
        })
        assert response.status_code == 401

    def test_update_copy_status_missing_copy_id(self, authenticated_client):
        """POST /api/backup/copy-status missing copy_id returns 400."""
        response = self._post_copy_status(authenticated_client, {
            "status": "success",
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "copy_id" in data["error"]["details"]["fields"]

    def test_update_copy_status_not_found(self, authenticated_client):
        """POST /api/backup/copy-status with invalid copy_id returns 404."""
        response = self._post_copy_status(authenticated_client, {
            "copy_id": 99999,
            "status": "success",
        })
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "COPY_NOT_FOUND"

    def test_update_copy_status_invalid_status(self, authenticated_client, backup_copies):
        """POST /api/backup/copy-status with invalid status returns 400."""
        response = self._post_copy_status(authenticated_client, {
            "copy_id": backup_copies[0].id,
            "status": "invalid_status",
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "status" in data["error"]["details"]["fields"]

    def test_update_copy_status_with_date(self, authenticated_client, backup_copies):
        """POST /api/backup/copy-status with last_backup_date updates correctly."""
        copy = backup_copies[0]
        response = self._post_copy_status(authenticated_client, {
            "copy_id": copy.id,
            "status": "success",
            "last_backup_date": "2025-10-30T03:00:00Z",
        })
        assert response.status_code == 200

    def test_update_copy_status_invalid_date(self, authenticated_client, backup_copies):
        """POST /api/backup/copy-status with bad last_backup_date returns 400."""
        response = self._post_copy_status(authenticated_client, {
            "copy_id": backup_copies[0].id,
            "last_backup_date": "not-a-date",
        })
        assert response.status_code == 400

    def test_update_copy_status_negative_size(self, authenticated_client, backup_copies):
        """POST /api/backup/copy-status with negative last_backup_size returns 400."""
        response = self._post_copy_status(authenticated_client, {
            "copy_id": backup_copies[0].id,
            "last_backup_size": -1,
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_update_copy_status_valid_statuses(self, authenticated_client, backup_copies):
        """POST /api/backup/copy-status accepts all valid status values."""
        copy = backup_copies[0]
        for status in ["success", "failed", "warning", "unknown"]:
            response = self._post_copy_status(authenticated_client, {
                "copy_id": copy.id,
                "status": status,
            })
            assert response.status_code == 200, f"Expected 200 for status={status}"


class TestGetLastExecution:
    """Tests for GET /api/backup/jobs/<job_id>/last-execution"""

    def _create_execution(self, app, backup_job, result="success"):
        """Helper to create a BackupExecution for a job."""
        from datetime import datetime, timezone
        with app.app_context():
            execution = BackupExecution(
                job_id=backup_job.id,
                execution_date=datetime.now(timezone.utc),
                execution_result=result,
                backup_size_bytes=1024,
                duration_seconds=60,
                source_system="pytest",
            )
            db.session.add(execution)
            db.session.commit()
            db.session.refresh(execution)
            return execution

    def test_get_last_execution_success(self, authenticated_client, backup_job, app):
        """GET /api/backup/jobs/<id>/last-execution returns 200 with execution data."""
        self._create_execution(app, backup_job)
        response = authenticated_client.get(f"/api/backup/jobs/{backup_job.id}/last-execution")
        assert response.status_code == 200
        data = response.get_json()
        assert "execution_id" in data
        assert data["job_id"] == backup_job.id
        assert "execution_date" in data
        assert "execution_result" in data
        assert "backup_size_bytes" in data
        assert "duration_seconds" in data
        assert "source_system" in data

    def test_get_last_execution_unauthenticated(self, client, backup_job, app):
        """GET /api/backup/jobs/<id>/last-execution returns 401 for unauthenticated user."""
        self._create_execution(app, backup_job)
        response = client.get(f"/api/backup/jobs/{backup_job.id}/last-execution")
        assert response.status_code == 401

    def test_get_last_execution_job_not_found(self, authenticated_client):
        """GET /api/backup/jobs/99999/last-execution returns 404."""
        response = authenticated_client.get("/api/backup/jobs/99999/last-execution")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "JOB_NOT_FOUND"

    def test_get_last_execution_no_executions(self, authenticated_client, backup_job):
        """GET /api/backup/jobs/<id>/last-execution returns 404 when no executions exist."""
        response = authenticated_client.get(f"/api/backup/jobs/{backup_job.id}/last-execution")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "NO_EXECUTIONS"

    def test_get_last_execution_returns_most_recent(self, authenticated_client, backup_job, app):
        """GET /api/backup/jobs/<id>/last-execution returns the most recent execution."""
        from datetime import datetime, timezone, timedelta
        with app.app_context():
            older = BackupExecution(
                job_id=backup_job.id,
                execution_date=datetime.now(timezone.utc) - timedelta(days=2),
                execution_result="failed",
                source_system="pytest",
            )
            newer = BackupExecution(
                job_id=backup_job.id,
                execution_date=datetime.now(timezone.utc) - timedelta(days=1),
                execution_result="success",
                source_system="pytest",
            )
            db.session.add_all([older, newer])
            db.session.commit()

        response = authenticated_client.get(f"/api/backup/jobs/{backup_job.id}/last-execution")
        assert response.status_code == 200
        data = response.get_json()
        assert data["execution_result"] == "success"
