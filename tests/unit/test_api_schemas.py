"""
Unit tests for app/api/schemas.py
Pydantic v2 schema validation tests.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestAPIResponse:
    """Tests for APIResponse schema"""

    def test_defaults(self):
        from app.api.schemas import APIResponse
        resp = APIResponse()
        assert resp.success is True
        assert resp.message is None
        assert resp.data is None

    def test_with_message(self):
        from app.api.schemas import APIResponse
        resp = APIResponse(message="ok", data={"key": "value"})
        assert resp.message == "ok"
        assert resp.data == {"key": "value"}

    def test_success_false(self):
        from app.api.schemas import APIResponse
        resp = APIResponse(success=False, message="failed")
        assert resp.success is False


class TestErrorResponse:
    """Tests for ErrorResponse schema"""

    def test_required_fields(self):
        from app.api.schemas import ErrorResponse
        resp = ErrorResponse(error="NOT_FOUND", message="Resource not found")
        assert resp.success is False
        assert resp.error == "NOT_FOUND"
        assert resp.message == "Resource not found"
        assert resp.details is None

    def test_with_details(self):
        from app.api.schemas import ErrorResponse
        resp = ErrorResponse(
            error="VALIDATION_ERROR",
            message="Invalid data",
            details={"field": "value"}
        )
        assert resp.details == {"field": "value"}

    def test_missing_required_fields_raises(self):
        from app.api.schemas import ErrorResponse
        with pytest.raises(ValidationError):
            ErrorResponse()  # missing 'error' and 'message'


class TestPaginatedResponse:
    """Tests for PaginatedResponse schema"""

    def test_basic_pagination(self):
        from app.api.schemas import PaginatedResponse
        resp = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}],
            total=100,
            page=2,
            page_size=20,
            total_pages=5,
        )
        assert resp.success is True
        assert resp.total == 100
        assert resp.page == 2
        assert resp.page_size == 20
        assert resp.total_pages == 5
        assert len(resp.data) == 2

    def test_empty_data(self):
        from app.api.schemas import PaginatedResponse
        resp = PaginatedResponse(total=0, page=1, page_size=20, total_pages=0)
        assert resp.data == []


class TestBackupJobCreate:
    """Tests for BackupJobCreate schema"""

    def _valid_data(self):
        return {
            "name": "Daily Backup",
            "source_path": "/data/backups",
            "backup_type": "full",
            "schedule_type": "daily",
        }

    def test_valid_creation(self):
        from app.api.schemas import BackupJobCreate
        job = BackupJobCreate(**self._valid_data())
        assert job.name == "Daily Backup"
        assert job.backup_type == "full"
        assert job.retention_days == 30  # default
        assert job.is_active is True  # default
        assert job.priority == 5  # default

    def test_invalid_backup_type_raises(self):
        from app.api.schemas import BackupJobCreate
        data = {**self._valid_data(), "backup_type": "mirror"}
        with pytest.raises(ValidationError) as exc_info:
            BackupJobCreate(**data)
        assert "backup_type" in str(exc_info.value)

    def test_invalid_schedule_type_raises(self):
        from app.api.schemas import BackupJobCreate
        data = {**self._valid_data(), "schedule_type": "hourly"}
        with pytest.raises(ValidationError) as exc_info:
            BackupJobCreate(**data)
        assert "schedule_type" in str(exc_info.value)

    def test_all_valid_backup_types(self):
        from app.api.schemas import BackupJobCreate
        for btype in ["full", "incremental", "differential"]:
            data = {**self._valid_data(), "backup_type": btype}
            job = BackupJobCreate(**data)
            assert job.backup_type == btype

    def test_all_valid_schedule_types(self):
        from app.api.schemas import BackupJobCreate
        for stype in ["daily", "weekly", "monthly", "custom"]:
            data = {**self._valid_data(), "schedule_type": stype}
            job = BackupJobCreate(**data)
            assert job.schedule_type == stype

    def test_retention_days_bounds(self):
        from app.api.schemas import BackupJobCreate
        with pytest.raises(ValidationError):
            BackupJobCreate(**{**self._valid_data(), "retention_days": 0})
        with pytest.raises(ValidationError):
            BackupJobCreate(**{**self._valid_data(), "retention_days": 9999})

    def test_priority_bounds(self):
        from app.api.schemas import BackupJobCreate
        with pytest.raises(ValidationError):
            BackupJobCreate(**{**self._valid_data(), "priority": 0})
        with pytest.raises(ValidationError):
            BackupJobCreate(**{**self._valid_data(), "priority": 11})

    def test_name_length_validation(self):
        from app.api.schemas import BackupJobCreate
        with pytest.raises(ValidationError):
            BackupJobCreate(**{**self._valid_data(), "name": ""})
        with pytest.raises(ValidationError):
            BackupJobCreate(**{**self._valid_data(), "name": "x" * 201})

    def test_missing_required_fields_raises(self):
        from app.api.schemas import BackupJobCreate
        with pytest.raises(ValidationError):
            BackupJobCreate(name="Test")  # missing source_path, backup_type, schedule_type


class TestBackupJobUpdate:
    """Tests for BackupJobUpdate schema"""

    def test_all_fields_optional(self):
        from app.api.schemas import BackupJobUpdate
        update = BackupJobUpdate()
        assert update.name is None
        assert update.backup_type is None

    def test_partial_update(self):
        from app.api.schemas import BackupJobUpdate
        update = BackupJobUpdate(name="New Name", is_active=False)
        assert update.name == "New Name"
        assert update.is_active is False
        assert update.priority is None


class TestStorageTestRequest:
    """Tests for StorageTestRequest schema"""

    def test_valid_provider_types(self):
        from app.api.schemas import StorageTestRequest
        for ptype in ["local", "network", "cloud", "tape", "s3", "azure", "gcs"]:
            req = StorageTestRequest(
                provider_type=ptype,
                connection_string="/path/to/storage"
            )
            assert req.provider_type == ptype

    def test_invalid_provider_type_raises(self):
        from app.api.schemas import StorageTestRequest
        with pytest.raises(ValidationError):
            StorageTestRequest(provider_type="ftp", connection_string="/path")

    def test_empty_connection_string_raises(self):
        from app.api.schemas import StorageTestRequest
        with pytest.raises(ValidationError):
            StorageTestRequest(provider_type="local", connection_string="")


class TestVerificationStartRequest:
    """Tests for VerificationStartRequest schema"""

    def test_valid_test_types(self):
        from app.api.schemas import VerificationStartRequest
        for ttype in ["checksum", "restore", "read", "integrity"]:
            req = VerificationStartRequest(test_type=ttype)
            assert req.test_type == ttype

    def test_invalid_test_type_raises(self):
        from app.api.schemas import VerificationStartRequest
        with pytest.raises(ValidationError):
            VerificationStartRequest(test_type="manual")

    def test_valid_scopes(self):
        from app.api.schemas import VerificationStartRequest
        for scope in ["full", "sample", "quick"]:
            req = VerificationStartRequest(test_type="checksum", scope=scope)
            assert req.scope == scope

    def test_invalid_scope_raises(self):
        from app.api.schemas import VerificationStartRequest
        with pytest.raises(ValidationError):
            VerificationStartRequest(test_type="checksum", scope="partial")

    def test_defaults(self):
        from app.api.schemas import VerificationStartRequest
        req = VerificationStartRequest(test_type="checksum")
        assert req.scope == "full"
        assert req.notify_on_completion is True
