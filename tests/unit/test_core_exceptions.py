"""
Unit tests for core exception classes.
app/core/exceptions.py coverage: 31% -> ~95%
"""
import pytest

from app.core.exceptions import (
    BackupEngineError,
    BackupJobNotFoundError,
    CopyOperationError,
    InsufficientStorageError,
    RetryExhaustedError,
    Rule321110ViolationError,
    VerificationFailedError,
)


class TestBackupEngineError:
    """Tests for the base BackupEngineError class."""

    def test_basic_creation(self):
        err = BackupEngineError("test message")
        assert err.message == "test message"
        assert err.details == {}
        assert str(err) == "test message"

    def test_creation_with_details(self):
        details = {"key": "value", "num": 42}
        err = BackupEngineError("msg", details)
        assert err.details == {"key": "value", "num": 42}

    def test_to_dict(self):
        err = BackupEngineError("test", {"foo": "bar"})
        d = err.to_dict()
        assert d["error_type"] == "BackupEngineError"
        assert d["message"] == "test"
        assert d["details"] == {"foo": "bar"}

    def test_is_exception(self):
        with pytest.raises(BackupEngineError):
            raise BackupEngineError("error!")

    def test_details_default_empty_dict(self):
        err = BackupEngineError("msg", None)
        assert err.details == {}


class TestCopyOperationError:
    """Tests for CopyOperationError."""

    def test_creation(self):
        err = CopyOperationError("/src/file", "/dst/file", "permission denied")
        assert "/src/file" in err.message
        assert "/dst/file" in err.message
        assert "permission denied" in err.message

    def test_details_populated(self):
        err = CopyOperationError("/src", "/dst", "reason")
        assert err.details["source"] == "/src"
        assert err.details["destination"] == "/dst"
        assert err.details["reason"] == "reason"

    def test_is_backup_engine_error(self):
        err = CopyOperationError("/src", "/dst", "err")
        assert isinstance(err, BackupEngineError)

    def test_to_dict(self):
        err = CopyOperationError("/a", "/b", "test")
        d = err.to_dict()
        assert d["error_type"] == "CopyOperationError"

    def test_extra_details_merged(self):
        err = CopyOperationError("/src", "/dst", "r", {"extra": "info"})
        assert err.details["extra"] == "info"
        assert err.details["source"] == "/src"


class TestInsufficientStorageError:
    """Tests for InsufficientStorageError."""

    def test_creation(self):
        err = InsufficientStorageError(1000, 500, "/backup")
        assert "1000" in err.message
        assert "500" in err.message

    def test_details_populated(self):
        err = InsufficientStorageError(2000, 100, "/path")
        assert err.details["required_bytes"] == 2000
        assert err.details["available_bytes"] == 100
        assert err.details["storage_path"] == "/path"

    def test_is_backup_engine_error(self):
        assert isinstance(InsufficientStorageError(0, 0, "/"), BackupEngineError)

    def test_to_dict(self):
        err = InsufficientStorageError(100, 50, "/x")
        d = err.to_dict()
        assert d["error_type"] == "InsufficientStorageError"


class TestVerificationFailedError:
    """Tests for VerificationFailedError."""

    def test_creation(self):
        err = VerificationFailedError(42, "checksum", "hash mismatch")
        assert "42" in err.message
        assert "hash mismatch" in err.message

    def test_details_populated(self):
        err = VerificationFailedError(10, "integrity", "corrupted")
        assert err.details["backup_id"] == 10
        assert err.details["verification_type"] == "integrity"
        assert err.details["reason"] == "corrupted"

    def test_is_backup_engine_error(self):
        assert isinstance(VerificationFailedError(1, "t", "r"), BackupEngineError)

    def test_to_dict(self):
        err = VerificationFailedError(5, "checksum", "failed")
        d = err.to_dict()
        assert d["error_type"] == "VerificationFailedError"


class TestRule321110ViolationError:
    """Tests for Rule321110ViolationError."""

    def test_all_violations(self):
        violations = {
            "min_copies": False,
            "different_media": False,
            "offsite_copy": False,
            "offline_copy": False,
            "zero_errors": False,
        }
        err = Rule321110ViolationError(1, violations)
        assert "最低3コピー未満" in err.message
        assert "2種類以上の異なるメディア未使用" in err.message
        assert "オフサイトコピーなし" in err.message
        assert "オフラインコピーなし" in err.message
        assert "検証エラーあり" in err.message

    def test_partial_violations(self):
        violations = {
            "min_copies": True,
            "different_media": False,
            "offsite_copy": True,
            "offline_copy": False,
            "zero_errors": True,
        }
        err = Rule321110ViolationError(2, violations)
        assert "最低3コピー未満" not in err.message
        assert "2種類以上の異なるメディア未使用" in err.message
        assert "オフラインコピーなし" in err.message

    def test_details_populated(self):
        violations = {"min_copies": False, "different_media": False, "offsite_copy": False, "offline_copy": False, "zero_errors": False}
        err = Rule321110ViolationError(99, violations)
        assert err.details["job_id"] == 99
        assert err.details["violations"] == violations

    def test_is_backup_engine_error(self):
        err = Rule321110ViolationError(1, {"min_copies": False, "different_media": True, "offsite_copy": True, "offline_copy": True, "zero_errors": True})
        assert isinstance(err, BackupEngineError)

    def test_to_dict(self):
        err = Rule321110ViolationError(1, {"min_copies": False, "different_media": True, "offsite_copy": True, "offline_copy": True, "zero_errors": True})
        d = err.to_dict()
        assert d["error_type"] == "Rule321110ViolationError"


class TestBackupJobNotFoundError:
    """Tests for BackupJobNotFoundError."""

    def test_creation(self):
        err = BackupJobNotFoundError(123)
        assert "123" in err.message

    def test_details_populated(self):
        err = BackupJobNotFoundError(99)
        assert err.details["job_id"] == 99

    def test_is_backup_engine_error(self):
        assert isinstance(BackupJobNotFoundError(1), BackupEngineError)

    def test_to_dict(self):
        err = BackupJobNotFoundError(5)
        d = err.to_dict()
        assert d["error_type"] == "BackupJobNotFoundError"


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError."""

    def test_creation(self):
        err = RetryExhaustedError("copy_operation", 3, "connection timeout")
        assert "copy_operation" in err.message
        assert "3" in err.message
        assert "connection timeout" in err.message

    def test_details_populated(self):
        err = RetryExhaustedError("op", 5, "error msg")
        assert err.details["operation"] == "op"
        assert err.details["max_retries"] == 5
        assert err.details["last_error"] == "error msg"

    def test_is_backup_engine_error(self):
        assert isinstance(RetryExhaustedError("op", 1, "err"), BackupEngineError)

    def test_to_dict(self):
        err = RetryExhaustedError("backup", 3, "failed")
        d = err.to_dict()
        assert d["error_type"] == "RetryExhaustedError"
