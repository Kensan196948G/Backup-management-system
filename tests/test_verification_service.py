"""
Verification Service Integration Tests

Tests for backup verification and restore testing functionality.
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.models import (
    BackupCopy,
    BackupJob,
    User,
    VerificationSchedule,
    VerificationTest,
    db,
)
from app.services.verification_service import (
    TestResult,
    VerificationService,
    VerificationType,
)
from app.verification import ChecksumAlgorithm


class TestVerificationService:
    """Test verification service functionality"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Setup test environment"""
        with app.app_context():
            # Create test user
            user = User(
                username="test_verifier",
                email="verifier@test.com",
                role="operator",
                full_name="Test Verifier",
                is_active=True,
            )
            user.set_password("testpass123")
            db.session.add(user)

            # Create test backup job
            job = BackupJob(
                job_name="Test Backup Job",
                job_type="file",
                backup_tool="custom",
                schedule_type="daily",
                retention_days=30,
                owner_id=1,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()

            # Create temporary test directories
            self.test_source_dir = Path(tempfile.mkdtemp(prefix="test_source_"))
            self.test_backup_dir = Path(tempfile.mkdtemp(prefix="test_backup_"))

            # Create test files in source directory
            for i in range(5):
                test_file = self.test_source_dir / f"test_file_{i}.txt"
                test_file.write_text(f"Test content {i}\n" * 100)

            # Create backup copy
            backup_copy = BackupCopy(
                job_id=job.id,
                copy_type="primary",
                media_type="disk",
                storage_path=str(self.test_backup_dir),
                is_encrypted=False,
                is_compressed=False,
                status="success",
            )
            db.session.add(backup_copy)
            db.session.commit()

            # Copy files to backup directory
            for file in self.test_source_dir.glob("*.txt"):
                shutil.copy2(file, self.test_backup_dir / file.name)

            self.user_id = user.id
            self.job_id = job.id

            yield

            # Cleanup
            db.session.query(VerificationTest).delete()
            db.session.query(VerificationSchedule).delete()
            db.session.query(BackupCopy).delete()
            db.session.query(BackupJob).delete()
            db.session.query(User).filter(User.username == "test_verifier").delete()
            db.session.commit()

            # Remove temporary directories
            shutil.rmtree(self.test_source_dir, ignore_errors=True)
            shutil.rmtree(self.test_backup_dir, ignore_errors=True)

    def test_verification_service_initialization(self, app):
        """Test verification service initialization"""
        with app.app_context():
            service = VerificationService()

            assert service is not None
            assert service.checksum_service is not None
            assert service.file_validator is not None
            assert service.test_root_dir.exists()

    def test_integrity_check_success(self, app):
        """Test successful integrity check"""
        with app.app_context():
            service = VerificationService()

            result, details = service.execute_verification_test(
                job_id=self.job_id, test_type=VerificationType.INTEGRITY, tester_id=self.user_id
            )

            assert result == TestResult.SUCCESS
            assert details["test_type"] == "integrity"
            assert details["total_files_checked"] > 0
            assert details["total_files_valid"] > 0
            assert details["validity_rate"] == 100.0

            # Verify database record
            test_record = VerificationTest.query.filter_by(job_id=self.job_id).first()
            assert test_record is not None
            assert test_record.test_type == "integrity"
            assert test_record.test_result == "success"

    def test_partial_restore_test(self, app):
        """Test partial restore test"""
        with app.app_context():
            service = VerificationService()

            result, details = service.execute_verification_test(
                job_id=self.job_id, test_type=VerificationType.PARTIAL, tester_id=self.user_id, sample_files=None
            )

            assert result in [TestResult.SUCCESS, TestResult.WARNING]
            assert details["test_type"] == "partial"
            assert details["files_tested"] > 0
            assert details["verified_files"] >= 0

    def test_full_restore_test(self, app):
        """Test full restore test"""
        with app.app_context():
            service = VerificationService()

            result, details = service.execute_verification_test(
                job_id=self.job_id, test_type=VerificationType.FULL_RESTORE, tester_id=self.user_id
            )

            assert result in [TestResult.SUCCESS, TestResult.WARNING]
            assert details["test_type"] == "full_restore"
            assert details["total_files_restored"] > 0

    def test_verification_scheduling(self, app):
        """Test verification test scheduling"""
        with app.app_context():
            service = VerificationService()

            schedule = service.schedule_verification_test(
                job_id=self.job_id, test_frequency="monthly", assigned_to=self.user_id
            )

            assert schedule is not None
            assert schedule.job_id == self.job_id
            assert schedule.test_frequency == "monthly"
            assert schedule.assigned_to == self.user_id
            assert schedule.is_active is True

    def test_overdue_verification_tests(self, app):
        """Test getting overdue verification tests"""
        with app.app_context():
            # Create overdue schedule
            schedule = VerificationSchedule(
                job_id=self.job_id,
                test_frequency="monthly",
                next_test_date=(datetime.utcnow() - timedelta(days=1)).date(),
                is_active=True,
            )
            db.session.add(schedule)
            db.session.commit()

            service = VerificationService()
            overdue = service.get_overdue_verification_tests()

            assert len(overdue) > 0
            assert any(s.job_id == self.job_id for s in overdue)

    def test_verification_with_corrupted_file(self, app):
        """Test verification with corrupted file"""
        with app.app_context():
            # Corrupt one file
            corrupted_file = list(self.test_backup_dir.glob("*.txt"))[0]
            corrupted_file.write_text("CORRUPTED CONTENT")

            service = VerificationService()

            result, details = service.execute_verification_test(
                job_id=self.job_id, test_type=VerificationType.INTEGRITY, tester_id=self.user_id
            )

            # Should still complete but with warnings or errors
            assert result in [TestResult.SUCCESS, TestResult.WARNING, TestResult.FAILED]
            assert "errors" in details or details["validity_rate"] < 100.0

    def test_verification_statistics(self, app):
        """Test verification statistics"""
        with app.app_context():
            service = VerificationService()

            # Execute a test
            service.execute_verification_test(job_id=self.job_id, test_type=VerificationType.INTEGRITY, tester_id=self.user_id)

            stats = service.get_statistics()

            assert stats["total_tests"] > 0
            assert "db_total_tests" in stats
            assert "db_success_rate" in stats

    def test_calculate_next_test_date(self, app):
        """Test next test date calculation"""
        with app.app_context():
            service = VerificationService()

            # Test different frequencies
            monthly_date = service._calculate_next_test_date("monthly")
            quarterly_date = service._calculate_next_test_date("quarterly")
            annual_date = service._calculate_next_test_date("annual")

            now = datetime.utcnow()

            assert (monthly_date - now).days >= 29
            assert (quarterly_date - now).days >= 89
            assert (annual_date - now).days >= 364

    def test_verification_with_missing_backup(self, app):
        """Test verification with missing backup copy"""
        with app.app_context():
            # Delete backup copy
            BackupCopy.query.filter_by(job_id=self.job_id).delete()
            db.session.commit()

            service = VerificationService()

            result, details = service.execute_verification_test(
                job_id=self.job_id, test_type=VerificationType.INTEGRITY, tester_id=self.user_id
            )

            assert result == TestResult.ERROR
            assert "error" in details


@pytest.fixture
def app():
    """Create test Flask application"""
    from app import create_app

    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
