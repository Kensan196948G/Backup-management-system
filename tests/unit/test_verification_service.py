"""
Unit tests for app/services/verification_service.py
VerificationService: enums, init, _calculate_next_test_date, _execute_integrity_check,
get_statistics, and error handling.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestVerificationType:
    """Tests for VerificationType enum"""

    def test_all_values_exist(self):
        from app.services.verification_service import VerificationType
        assert VerificationType.FULL_RESTORE.value == "full_restore"
        assert VerificationType.PARTIAL.value == "partial"
        assert VerificationType.INTEGRITY.value == "integrity"

    def test_three_types_defined(self):
        from app.services.verification_service import VerificationType
        assert len(VerificationType) == 3


class TestTestResult:
    """Tests for TestResult enum"""

    def test_all_values_exist(self):
        from app.services.verification_service import TestResult
        assert TestResult.SUCCESS.value == "success"
        assert TestResult.FAILED.value == "failed"
        assert TestResult.WARNING.value == "warning"
        assert TestResult.ERROR.value == "error"

    def test_four_results_defined(self):
        from app.services.verification_service import TestResult
        assert len(TestResult) == 4


class TestVerificationServiceInit:
    """Tests for VerificationService initialization"""

    def test_default_init(self):
        from app.services.verification_service import VerificationService
        service = VerificationService()
        assert service.checksum_service is not None
        assert service.file_validator is not None

    def test_custom_checksum_service(self):
        from app.services.verification_service import VerificationService
        mock_cs = MagicMock()
        mock_fv = MagicMock()
        service = VerificationService(checksum_service=mock_cs, file_validator=mock_fv)
        assert service.checksum_service is mock_cs
        assert service.file_validator is mock_fv

    def test_initial_stats_are_zero(self):
        from app.services.verification_service import VerificationService
        service = VerificationService()
        assert service.stats["total_tests"] == 0
        assert service.stats["successful_tests"] == 0
        assert service.stats["failed_tests"] == 0

    def test_repr_contains_stats(self):
        from app.services.verification_service import VerificationService
        service = VerificationService()
        r = repr(service)
        assert "VerificationService" in r
        assert "total_tests" in r


class TestCalculateNextTestDate:
    """Tests for _calculate_next_test_date"""

    def _make_service(self):
        from app.services.verification_service import VerificationService
        return VerificationService()

    def test_monthly_frequency(self):
        service = self._make_service()
        now = datetime.now(timezone.utc)
        result = service._calculate_next_test_date("monthly")
        delta = result - now
        assert 28 <= delta.days <= 32  # ~30 days

    def test_quarterly_frequency(self):
        service = self._make_service()
        now = datetime.now(timezone.utc)
        result = service._calculate_next_test_date("quarterly")
        delta = result - now
        assert 88 <= delta.days <= 92  # ~90 days

    def test_semi_annual_frequency(self):
        service = self._make_service()
        now = datetime.now(timezone.utc)
        result = service._calculate_next_test_date("semi-annual")
        delta = result - now
        assert 178 <= delta.days <= 182  # ~180 days

    def test_annual_frequency(self):
        service = self._make_service()
        now = datetime.now(timezone.utc)
        result = service._calculate_next_test_date("annual")
        delta = result - now
        assert 363 <= delta.days <= 367  # ~365 days

    def test_unknown_frequency_defaults_to_monthly(self):
        service = self._make_service()
        now = datetime.now(timezone.utc)
        result = service._calculate_next_test_date("unknown_frequency")
        delta = result - now
        assert 28 <= delta.days <= 32  # default 30 days

    def test_returns_future_datetime(self):
        service = self._make_service()
        result = service._calculate_next_test_date("monthly")
        assert result > datetime.now(timezone.utc)


class TestExecuteIntegrityCheck:
    """Tests for _execute_integrity_check"""

    def _make_service(self):
        from app.services.verification_service import VerificationService
        service = VerificationService()
        return service

    def _make_job(self, name="TestJob"):
        job = MagicMock()
        job.job_name = name
        return job

    def _make_copy(self, storage_path=None, copy_type="primary"):
        copy = MagicMock()
        copy.id = 1
        copy.storage_path = storage_path
        copy.copy_type = copy_type
        return copy

    def test_no_storage_path_skips_copy(self):
        from app.services.verification_service import TestResult
        service = self._make_service()
        job = self._make_job()
        copy = self._make_copy(storage_path=None)

        result, details = service._execute_integrity_check(job, [copy])
        assert result == TestResult.SUCCESS
        assert details["total_files_checked"] == 0

    def test_nonexistent_path_adds_error(self):
        from app.services.verification_service import TestResult
        service = self._make_service()
        job = self._make_job()
        copy = self._make_copy(storage_path="/nonexistent/path/backup.dump")

        result, details = service._execute_integrity_check(job, [copy])
        assert len(details["errors"]) >= 1
        assert details["total_files_checked"] == 0

    def test_single_file_integrity_check(self):
        import tempfile
        import os
        from app.services.verification_service import TestResult

        service = self._make_service()
        job = self._make_job()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "backup.dump")
            with open(test_file, "wb") as f:
                f.write(b"backup data content")

            mock_cs = MagicMock()
            mock_cs.calculate_checksum.return_value = "abc123checksum"
            service.checksum_service = mock_cs

            copy = self._make_copy(storage_path=test_file)
            result, details = service._execute_integrity_check(job, [copy])

        assert result == TestResult.SUCCESS
        assert details["total_files_checked"] == 1
        assert details["total_files_valid"] == 1
        assert details["validity_rate"] == 100.0

    def test_directory_integrity_check(self):
        import tempfile
        import os
        from app.services.verification_service import TestResult

        service = self._make_service()
        job = self._make_job()

        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                with open(os.path.join(tmpdir, f"file{i}.bak"), "wb") as f:
                    f.write(b"data")

            mock_cs = MagicMock()
            mock_cs.calculate_checksums_parallel.return_value = {"f1": "h1", "f2": "h2", "f3": "h3"}
            service.checksum_service = mock_cs

            copy = self._make_copy(storage_path=tmpdir)
            result, details = service._execute_integrity_check(job, [copy])

        assert result == TestResult.SUCCESS

    def test_empty_backup_list_returns_success(self):
        from app.services.verification_service import TestResult
        service = self._make_service()
        job = self._make_job()

        result, details = service._execute_integrity_check(job, [])
        assert result == TestResult.SUCCESS
        assert details["total_files_checked"] == 0
        assert details["validity_rate"] == 0.0

    def test_checksum_exception_marks_error(self):
        import tempfile
        import os
        from app.services.verification_service import TestResult

        service = self._make_service()
        job = self._make_job()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "backup.dump")
            with open(test_file, "wb") as f:
                f.write(b"data")

            mock_cs = MagicMock()
            mock_cs.calculate_checksum.side_effect = Exception("Checksum error")
            service.checksum_service = mock_cs

            copy = self._make_copy(storage_path=test_file)
            result, details = service._execute_integrity_check(job, [copy])

        assert result == TestResult.ERROR
        assert len(details["errors"]) >= 1

    def test_details_contains_required_keys(self):
        from app.services.verification_service import TestResult
        service = self._make_service()
        job = self._make_job()

        _, details = service._execute_integrity_check(job, [])
        assert "test_type" in details
        assert "job_name" in details
        assert "timestamp" in details
        assert "copies_checked" in details
        assert "total_files_checked" in details
        assert "total_files_valid" in details
        assert "errors" in details
        assert "validity_rate" in details


class TestVerifyRestoredFile:
    """Tests for _verify_restored_file"""

    def _make_service(self):
        from app.services.verification_service import VerificationService
        return VerificationService()

    def test_success_case(self):
        from app.verification.interfaces import VerificationStatus, ChecksumAlgorithm
        service = self._make_service()
        mock_fv = MagicMock()
        mock_fv.verify_file.return_value = (VerificationStatus.SUCCESS, {"detail": "ok"})
        service.file_validator = mock_fv

        result = service._verify_restored_file(Path("/src"), Path("/dst"), ChecksumAlgorithm.SHA256)
        assert result["status"] == VerificationStatus.SUCCESS

    def test_exception_returns_failed_status(self):
        from app.verification.interfaces import VerificationStatus, ChecksumAlgorithm
        service = self._make_service()
        mock_fv = MagicMock()
        mock_fv.verify_file.side_effect = Exception("IO error")
        service.file_validator = mock_fv

        result = service._verify_restored_file(Path("/src"), Path("/dst"), ChecksumAlgorithm.SHA256)
        assert result["status"] == VerificationStatus.FAILED
        assert "error" in result


class TestGetStatistics:
    """Tests for get_statistics"""

    def test_statistics_has_required_keys(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            service = VerificationService()
            stats = service.get_statistics()

        assert "total_tests" in stats
        assert "successful_tests" in stats
        assert "failed_tests" in stats
        assert "db_total_tests" in stats
        assert "db_successful_tests" in stats
        assert "db_failed_tests" in stats
        assert "db_success_rate" in stats

    def test_db_success_rate_zero_when_no_tests(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            service = VerificationService()
            stats = service.get_statistics()

        assert stats["db_success_rate"] == 0.0
        assert stats["db_total_tests"] >= 0

    def test_success_rate_calculation(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            service = VerificationService()
            with patch("app.services.verification_service.VerificationTest") as MockVT:
                MockVT.query.count.return_value = 10
                MockVT.query.filter_by.return_value.count.side_effect = [8, 2]  # success, failed

                stats = service.get_statistics()

        assert stats["db_total_tests"] == 10
        assert stats["db_success_rate"] == 80.0
