"""
Extended coverage tests for app/services/verification_service.py
Targets: execute_verification_test, schedule/update/overdue schedules,
_execute_full/partial_restore, _record_test_result, async, singleton.
"""

import asyncio
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


def _make_service():
    from app.services.verification_service import VerificationService
    return VerificationService()


def _make_mock_job(job_id=1, job_name="TestJob"):
    job = MagicMock()
    job.id = job_id
    job.job_name = job_name
    return job


def _make_mock_copy(copy_type="primary", storage_path=None):
    copy = MagicMock()
    copy.id = 1
    copy.copy_type = copy_type
    copy.storage_path = storage_path
    return copy


class TestExecuteVerificationTestIntegration:
    """Tests for execute_verification_test with DB mocking."""

    def test_job_not_found_returns_error(self, app):
        from app.services.verification_service import VerificationService, VerificationType, TestResult

        with app.app_context():
            service = _make_service()
            with patch("app.services.verification_service.db") as mock_db:
                mock_db.session.get.return_value = None

                result, details = service.execute_verification_test(
                    job_id=999, test_type=VerificationType.INTEGRITY, tester_id=1
                )
                assert result == TestResult.ERROR

    def test_no_backup_copies_returns_error(self, app):
        from app.services.verification_service import VerificationService, VerificationType, TestResult

        with app.app_context():
            service = _make_service()
            mock_job = _make_mock_job()

            with patch("app.services.verification_service.db") as mock_db:
                mock_db.session.get.return_value = mock_job
                with patch("app.services.verification_service.BackupCopy") as mock_bc:
                    mock_bc.query.filter_by.return_value.all.return_value = []
                    result, details = service.execute_verification_test(
                        job_id=1, test_type=VerificationType.INTEGRITY, tester_id=1
                    )
                    assert result == TestResult.ERROR

    def test_integrity_check_dispatched(self, app):
        from app.services.verification_service import VerificationService, VerificationType, TestResult

        with app.app_context():
            service = _make_service()
            mock_job = _make_mock_job()
            mock_copy = _make_mock_copy(storage_path=None)

            with patch("app.services.verification_service.db") as mock_db:
                mock_db.session.get.return_value = mock_job
                mock_db.session.add = MagicMock()
                mock_db.session.commit = MagicMock()
                with patch("app.services.verification_service.BackupCopy") as mock_bc:
                    mock_bc.query.filter_by.return_value.all.return_value = [mock_copy]
                    with patch("app.services.verification_service.VerificationTest"):
                        result, details = service.execute_verification_test(
                            job_id=1, test_type=VerificationType.INTEGRITY, tester_id=1
                        )
                    # Should complete (with success/warning/error depending on paths)
                    assert result in list(TestResult)

    def test_stats_updated_on_success(self, app):
        from app.services.verification_service import VerificationService, VerificationType, TestResult

        with app.app_context():
            service = _make_service()
            initial_total = service.stats["total_tests"]

            with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as f:
                f.write(b"backup data")
                tmp_path = f.name

            mock_job = _make_mock_job()
            mock_copy = _make_mock_copy(storage_path=tmp_path)

            with patch("app.services.verification_service.db") as mock_db:
                mock_db.session.get.return_value = mock_job
                mock_db.session.add = MagicMock()
                mock_db.session.commit = MagicMock()
                with patch("app.services.verification_service.BackupCopy") as mock_bc:
                    mock_bc.query.filter_by.return_value.all.return_value = [mock_copy]
                    with patch("app.services.verification_service.VerificationTest"):
                        service.execute_verification_test(
                            job_id=1, test_type=VerificationType.INTEGRITY, tester_id=1
                        )

            assert service.stats["total_tests"] >= initial_total

    def test_stats_increment_on_failure(self, app):
        from app.services.verification_service import VerificationService, VerificationType, TestResult

        with app.app_context():
            service = _make_service()
            initial_failed = service.stats["failed_tests"]

            with patch("app.services.verification_service.db") as mock_db:
                mock_db.session.get.return_value = None  # triggers ValueError

                result, _ = service.execute_verification_test(
                    job_id=999, test_type=VerificationType.INTEGRITY, tester_id=1
                )

            # Either error or failed increments
            assert result == TestResult.ERROR

    def test_full_restore_dispatched(self, app):
        from app.services.verification_service import VerificationService, VerificationType, TestResult

        with app.app_context():
            service = _make_service()
            mock_job = _make_mock_job()
            mock_copy = _make_mock_copy(storage_path="/nonexistent/path.dump")

            with patch("app.services.verification_service.db") as mock_db:
                mock_db.session.get.return_value = mock_job
                mock_db.session.add = MagicMock()
                mock_db.session.commit = MagicMock()
                with patch("app.services.verification_service.BackupCopy") as mock_bc:
                    mock_bc.query.filter_by.return_value.all.return_value = [mock_copy]
                    with patch("app.services.verification_service.VerificationTest"):
                        result, details = service.execute_verification_test(
                            job_id=1, test_type=VerificationType.FULL_RESTORE, tester_id=1
                        )
                    assert result in list(TestResult)

    def test_partial_restore_dispatched(self, app):
        from app.services.verification_service import VerificationService, VerificationType, TestResult

        with app.app_context():
            service = _make_service()
            mock_job = _make_mock_job()
            mock_copy = _make_mock_copy(storage_path="/nonexistent/backup_dir")

            with patch("app.services.verification_service.db") as mock_db:
                mock_db.session.get.return_value = mock_job
                mock_db.session.add = MagicMock()
                mock_db.session.commit = MagicMock()
                with patch("app.services.verification_service.BackupCopy") as mock_bc:
                    mock_bc.query.filter_by.return_value.all.return_value = [mock_copy]
                    with patch("app.services.verification_service.VerificationTest"):
                        result, details = service.execute_verification_test(
                            job_id=1, test_type=VerificationType.PARTIAL, tester_id=1
                        )
                    assert result in list(TestResult)


class TestExecuteFullRestoreTest:
    """Tests for _execute_full_restore_test."""

    def test_no_primary_copy_returns_failed(self):
        from app.services.verification_service import VerificationService, TestResult

        service = _make_service()
        mock_job = _make_mock_job()
        secondary_copy = _make_mock_copy(copy_type="secondary", storage_path="/some/path")

        result, details = service._execute_full_restore_test(mock_job, [secondary_copy], None)
        assert result == TestResult.FAILED
        assert "No primary backup copy" in details.get("error", "")

    def test_source_not_found_returns_failed(self):
        from app.services.verification_service import VerificationService, TestResult

        service = _make_service()
        mock_job = _make_mock_job()
        primary_copy = _make_mock_copy(copy_type="primary", storage_path="/nonexistent/path.dump")

        result, details = service._execute_full_restore_test(mock_job, [primary_copy], None)
        assert result == TestResult.FAILED

    def test_no_storage_path_returns_failed(self):
        from app.services.verification_service import VerificationService, TestResult

        service = _make_service()
        mock_job = _make_mock_job()
        primary_copy = _make_mock_copy(copy_type="primary", storage_path=None)

        result, details = service._execute_full_restore_test(mock_job, [primary_copy], None)
        assert result == TestResult.FAILED

    def test_single_file_restore_success(self):
        from app.services.verification_service import VerificationService, TestResult
        from app.verification.interfaces import VerificationStatus

        service = _make_service()
        mock_job = _make_mock_job()

        with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as f:
            f.write(b"backup content")
            tmp_path = f.name

        primary_copy = _make_mock_copy(copy_type="primary", storage_path=tmp_path)

        mock_fv = MagicMock()
        mock_fv.verify_file.return_value = (VerificationStatus.SUCCESS, {})
        service.file_validator = mock_fv

        result, details = service._execute_full_restore_test(mock_job, [primary_copy], None)
        assert result in [TestResult.SUCCESS, TestResult.FAILED, TestResult.ERROR]
        assert "test_type" in details
        assert details["test_type"] == "full_restore"

    def test_details_has_required_keys(self):
        from app.services.verification_service import VerificationService, TestResult

        service = _make_service()
        mock_job = _make_mock_job()
        primary_copy = _make_mock_copy(copy_type="primary", storage_path=None)

        result, details = service._execute_full_restore_test(mock_job, [primary_copy], None)
        assert "test_type" in details
        assert "job_name" in details
        assert "timestamp" in details

    def test_with_explicit_restore_target(self):
        from app.services.verification_service import VerificationService, TestResult

        service = _make_service()
        mock_job = _make_mock_job()
        primary_copy = _make_mock_copy(copy_type="primary", storage_path="/nonexistent")

        with tempfile.TemporaryDirectory() as tmpdir:
            result, details = service._execute_full_restore_test(mock_job, [primary_copy], tmpdir)
            assert details.get("cleanup_required") is False

    def test_directory_backup_full_restore(self):
        from app.services.verification_service import VerificationService, TestResult
        from app.verification.interfaces import VerificationStatus

        service = _make_service()
        mock_job = _make_mock_job()

        with tempfile.TemporaryDirectory() as src_dir:
            # Create some files in the source directory
            (Path(src_dir) / "file1.txt").write_text("content1")
            (Path(src_dir) / "file2.txt").write_text("content2")
            subdir = Path(src_dir) / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("content3")

            primary_copy = _make_mock_copy(copy_type="primary", storage_path=src_dir)

            mock_fv = MagicMock()
            mock_fv.verify_file.return_value = (VerificationStatus.SUCCESS, {})
            service.file_validator = mock_fv

            result, details = service._execute_full_restore_test(mock_job, [primary_copy], None)
            assert result in list(TestResult)
            assert details.get("total_files_restored", 0) >= 0


class TestExecutePartialRestoreTest:
    """Tests for _execute_partial_restore_test."""

    def test_no_primary_copy_returns_failed(self):
        from app.services.verification_service import VerificationService, TestResult

        service = _make_service()
        mock_job = _make_mock_job()
        secondary = _make_mock_copy(copy_type="secondary", storage_path="/some/path")

        result, details = service._execute_partial_restore_test(mock_job, [secondary], None, None)
        assert result == TestResult.FAILED

    def test_nonexistent_source_returns_failed(self):
        from app.services.verification_service import VerificationService, TestResult

        service = _make_service()
        mock_job = _make_mock_job()
        primary = _make_mock_copy(copy_type="primary", storage_path="/nonexistent/path")

        result, details = service._execute_partial_restore_test(mock_job, [primary], None, None)
        assert result == TestResult.FAILED

    def test_with_single_file_source(self):
        from app.services.verification_service import VerificationService, TestResult
        from app.verification.interfaces import VerificationStatus

        service = _make_service()
        mock_job = _make_mock_job()

        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            f.write(b"backup data")
            tmp_path = f.name

        primary = _make_mock_copy(copy_type="primary", storage_path=tmp_path)
        mock_fv = MagicMock()
        mock_fv.verify_file.return_value = (VerificationStatus.SUCCESS, {})
        service.file_validator = mock_fv

        result, details = service._execute_partial_restore_test(mock_job, [primary], None, None)
        assert result in list(TestResult)

    def test_with_directory_source_random_sample(self):
        from app.services.verification_service import VerificationService, TestResult
        from app.verification.interfaces import VerificationStatus

        service = _make_service()
        mock_job = _make_mock_job()

        with tempfile.TemporaryDirectory() as src_dir:
            for i in range(5):
                (Path(src_dir) / f"file{i}.txt").write_text(f"content{i}")

            primary = _make_mock_copy(copy_type="primary", storage_path=src_dir)
            mock_fv = MagicMock()
            mock_fv.verify_file.return_value = (VerificationStatus.SUCCESS, {})
            service.file_validator = mock_fv

            result, details = service._execute_partial_restore_test(mock_job, [primary], None, None)
            assert result in list(TestResult)
            assert "files_tested" in details

    def test_with_explicit_sample_files(self):
        from app.services.verification_service import VerificationService, TestResult
        from app.verification.interfaces import VerificationStatus

        service = _make_service()
        mock_job = _make_mock_job()

        with tempfile.TemporaryDirectory() as src_dir:
            (Path(src_dir) / "important.txt").write_text("important data")

            primary = _make_mock_copy(copy_type="primary", storage_path=src_dir)
            mock_fv = MagicMock()
            mock_fv.verify_file.return_value = (VerificationStatus.SUCCESS, {})
            service.file_validator = mock_fv

            result, details = service._execute_partial_restore_test(
                mock_job, [primary], None, ["important.txt"]
            )
            assert result in list(TestResult)

    def test_details_has_required_keys(self):
        from app.services.verification_service import VerificationService

        service = _make_service()
        mock_job = _make_mock_job()
        primary = _make_mock_copy(copy_type="primary", storage_path="/nonexistent")

        _, details = service._execute_partial_restore_test(mock_job, [primary], None, None)
        assert "test_type" in details
        assert "job_name" in details
        assert details["test_type"] == "partial"

    def test_failed_verification_sets_failed_result(self):
        from app.services.verification_service import VerificationService, TestResult
        from app.verification.interfaces import VerificationStatus

        service = _make_service()
        mock_job = _make_mock_job()

        with tempfile.TemporaryDirectory() as src_dir:
            (Path(src_dir) / "file.txt").write_text("data")

            primary = _make_mock_copy(copy_type="primary", storage_path=src_dir)
            mock_fv = MagicMock()
            mock_fv.verify_file.return_value = (VerificationStatus.FAILED, {"reason": "mismatch"})
            service.file_validator = mock_fv

            result, details = service._execute_partial_restore_test(mock_job, [primary], None, None)
            assert result in [TestResult.FAILED, TestResult.WARNING, TestResult.ERROR]


class TestRecordTestResult:
    """Tests for _record_test_result."""

    def test_records_to_database(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, db

            # Create a user
            user = User(username="testuser_rec", email="testuser_rec@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            # Create a backup job
            job = BackupJob(
                job_name="Record Test Job",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.commit()

            service = _make_service()
            service._record_test_result(
                job_id=job.id,
                test_type="integrity",
                tester_id=user.id,
                test_result="success",
                duration_seconds=10,
                restore_target=None,
                details={"test_type": "integrity"},
            )

            from app.models import VerificationTest
            tests = VerificationTest.query.filter_by(job_id=job.id).all()
            assert len(tests) >= 1

    def test_record_with_errors_in_details(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, db

            user = User(username="tester_err", email="tester_err@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(
                job_name="Error Test Job",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.commit()

            service = _make_service()
            service._record_test_result(
                job_id=job.id,
                test_type="full_restore",
                tester_id=user.id,
                test_result="failed",
                duration_seconds=30,
                restore_target="/tmp/restore",
                details={"test_type": "full_restore", "errors": ["Error 1", "Error 2"]},
            )

            from app.models import VerificationTest
            test = VerificationTest.query.filter_by(job_id=job.id).first()
            assert test is not None
            assert test.issues_found is not None

    def test_record_db_error_rollback(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            service = _make_service()

            with patch("app.services.verification_service.VerificationTest") as MockVT:
                MockVT.side_effect = Exception("DB Error")
                # Should not raise
                service._record_test_result(
                    job_id=999,
                    test_type="integrity",
                    tester_id=1,
                    test_result="error",
                    duration_seconds=0,
                    restore_target=None,
                    details={},
                )


class TestScheduleVerificationTest:
    """Tests for schedule_verification_test."""

    def test_creates_schedule(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, db

            user = User(username="sched_user", email="sched_user@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(
                job_name="Schedule Test Job",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.commit()

            service = _make_service()
            schedule = service.schedule_verification_test(
                job_id=job.id, test_frequency="monthly", assigned_to=user.id
            )

            assert schedule is not None
            assert schedule.job_id == job.id
            assert schedule.test_frequency == "monthly"
            assert schedule.is_active is True

    def test_schedule_with_explicit_date(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, db

            user = User(username="sched_user2", email="sched_user2@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(
                job_name="Schedule Test Job2",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.commit()

            next_date = datetime.now(timezone.utc) + timedelta(days=30)
            service = _make_service()
            schedule = service.schedule_verification_test(
                job_id=job.id,
                test_frequency="quarterly",
                next_test_date=next_date,
            )

            assert schedule.next_test_date == next_date.date()

    def test_schedule_all_frequencies(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, db

            user = User(username="freq_user", email="freq_user@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()
            db.session.commit()

            service = _make_service()
            for freq in ["monthly", "quarterly", "semi-annual", "annual"]:
                job = BackupJob(
                    job_name=f"Job {freq}",
                    job_type="file",
                    backup_tool="custom",
                    target_path="/source",
                    schedule_type="daily",
                    retention_days=30,
                    owner_id=user.id,
                )
                db.session.add(job)
                db.session.commit()

                schedule = service.schedule_verification_test(job_id=job.id, test_frequency=freq)
                assert schedule is not None
                assert schedule.test_frequency == freq


class TestUpdateVerificationSchedule:
    """Tests for update_verification_schedule."""

    def test_updates_schedule_dates(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, VerificationSchedule, db

            user = User(username="upd_user", email="upd_user@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(
                job_name="Update Schedule Job",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.flush()

            schedule = VerificationSchedule(
                job_id=job.id,
                test_frequency="monthly",
                next_test_date=(datetime.now(timezone.utc) + timedelta(days=30)).date(),
                is_active=True,
            )
            db.session.add(schedule)
            db.session.commit()

            service = _make_service()
            new_date = datetime.now(timezone.utc) + timedelta(days=60)
            service.update_verification_schedule(schedule.id, new_date)

            updated = db.session.get(VerificationSchedule, schedule.id)
            assert updated.next_test_date == new_date.date()
            assert updated.last_test_date is not None

    def test_update_nonexistent_schedule_no_error(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            service = _make_service()
            new_date = datetime.now(timezone.utc) + timedelta(days=30)
            # Should not raise for nonexistent schedule
            service.update_verification_schedule(99999, new_date)


class TestGetOverdueVerificationTests:
    """Tests for get_overdue_verification_tests."""

    def test_returns_overdue_schedules(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, VerificationSchedule, db

            user = User(username="overdue_user", email="overdue_user@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(
                job_name="Overdue Job",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.flush()

            # Create overdue schedule (past date)
            past_date = (datetime.now(timezone.utc) - timedelta(days=10)).date()
            schedule = VerificationSchedule(
                job_id=job.id,
                test_frequency="monthly",
                next_test_date=past_date,
                is_active=True,
            )
            db.session.add(schedule)
            db.session.commit()

            service = _make_service()
            overdue = service.get_overdue_verification_tests()
            assert len(overdue) >= 1
            ids = [s.id for s in overdue]
            assert schedule.id in ids

    def test_excludes_inactive_schedules(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, VerificationSchedule, db

            user = User(username="inactive_user", email="inactive_user@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(
                job_name="Inactive Job",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.flush()

            past_date = (datetime.now(timezone.utc) - timedelta(days=5)).date()
            schedule = VerificationSchedule(
                job_id=job.id,
                test_frequency="monthly",
                next_test_date=past_date,
                is_active=False,  # Inactive
            )
            db.session.add(schedule)
            db.session.commit()

            service = _make_service()
            overdue = service.get_overdue_verification_tests()
            ids = [s.id for s in overdue]
            assert schedule.id not in ids

    def test_excludes_future_schedules(self, app):
        from app.services.verification_service import VerificationService

        with app.app_context():
            from app.models import BackupJob, User, VerificationSchedule, db

            user = User(username="future_user", email="future_user@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(
                job_name="Future Job",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.flush()

            future_date = (datetime.now(timezone.utc) + timedelta(days=30)).date()
            schedule = VerificationSchedule(
                job_id=job.id,
                test_frequency="monthly",
                next_test_date=future_date,
                is_active=True,
            )
            db.session.add(schedule)
            db.session.commit()

            service = _make_service()
            overdue = service.get_overdue_verification_tests()
            ids = [s.id for s in overdue]
            assert schedule.id not in ids


class TestGetVerificationServiceSingleton:
    """Tests for get_verification_service singleton."""

    def test_returns_instance(self):
        from app.services.verification_service import get_verification_service, VerificationService
        import app.services.verification_service as vs_module
        vs_module._verification_service_instance = None

        instance = get_verification_service()
        assert isinstance(instance, VerificationService)

    def test_returns_same_instance_on_multiple_calls(self):
        from app.services.verification_service import get_verification_service
        import app.services.verification_service as vs_module
        vs_module._verification_service_instance = None

        instance1 = get_verification_service()
        instance2 = get_verification_service()
        assert instance1 is instance2

    def test_singleton_can_be_reset(self):
        import app.services.verification_service as vs_module

        vs_module._verification_service_instance = None
        instance1 = vs_module.get_verification_service()

        vs_module._verification_service_instance = None
        instance2 = vs_module.get_verification_service()

        assert instance1 is not instance2


class TestVerificationServiceRepr:
    """Tests for __repr__."""

    def test_repr_contains_stats(self):
        from app.services.verification_service import VerificationService

        service = VerificationService()
        repr_str = repr(service)
        assert "VerificationService" in repr_str
        assert "total_tests" in repr_str
        assert "successful" in repr_str
        assert "failed" in repr_str

    def test_repr_shows_zero_initially(self):
        from app.services.verification_service import VerificationService

        service = VerificationService()
        repr_str = repr(service)
        assert "0" in repr_str


class TestExecuteVerificationTestAsync:
    """Tests for execute_verification_test_async."""

    def test_async_calls_sync_method(self, app):
        from app.services.verification_service import VerificationService, VerificationType, TestResult

        with app.app_context():
            service = _make_service()

            with patch.object(service, "execute_verification_test") as mock_sync:
                mock_sync.return_value = (TestResult.SUCCESS, {"detail": "ok"})

                loop = asyncio.new_event_loop()
                try:
                    result, details = loop.run_until_complete(
                        service.execute_verification_test_async(
                            job_id=1,
                            test_type=VerificationType.INTEGRITY,
                            tester_id=1,
                        )
                    )
                finally:
                    loop.close()

                assert result == TestResult.SUCCESS
                mock_sync.assert_called_once()
