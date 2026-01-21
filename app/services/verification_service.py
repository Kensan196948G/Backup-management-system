"""
Backup Verification and Restore Test Service

This service provides comprehensive backup verification and restore testing
capabilities including:
- Full restore tests (complete backup restoration)
- Partial restore tests (selective file restoration)
- Integrity checks (checksum validation)
- Automated verification scheduling
- Test result recording and analysis
"""

import asyncio
import logging
import shutil
import tempfile
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models import (
    BackupCopy,
    BackupJob,
    User,
    VerificationSchedule,
    VerificationTest,
    db,
)
from app.verification import ChecksumService, FileValidator
from app.verification.interfaces import ChecksumAlgorithm, VerificationStatus

logger = logging.getLogger(__name__)


class VerificationType(Enum):
    """Verification test types"""

    FULL_RESTORE = "full_restore"  # Complete backup restoration test
    PARTIAL = "partial"  # Selective file restoration test
    INTEGRITY = "integrity"  # Checksum-only validation


class TestResult(Enum):
    """Test result status"""

    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


class VerificationService:
    """
    Main service for backup verification and restore testing.

    Features:
    - Full restore test execution
    - Partial restore test execution
    - Integrity-only verification
    - Automated scheduling integration
    - Detailed test result recording
    - Async test execution support
    """

    def __init__(
        self,
        checksum_service: Optional[ChecksumService] = None,
        file_validator: Optional[FileValidator] = None,
        test_root_dir: Optional[Path] = None,
    ):
        """
        Initialize verification service.

        Args:
            checksum_service: Checksum calculation service
            file_validator: File validation service
            test_root_dir: Root directory for test restorations
        """
        self.checksum_service = checksum_service or ChecksumService(default_algorithm=ChecksumAlgorithm.SHA256)
        self.file_validator = file_validator or FileValidator(checksum_service=self.checksum_service)
        self.test_root_dir = test_root_dir or Path(tempfile.gettempdir()) / "backup_verification_tests"

        # Ensure test directory exists
        self.test_root_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "last_test": None,
        }

    def execute_verification_test(
        self,
        job_id: int,
        test_type: VerificationType,
        tester_id: int,
        restore_target: Optional[str] = None,
        sample_files: Optional[List[str]] = None,
    ) -> Tuple[TestResult, Dict]:
        """
        Execute a verification test for a backup job.

        Args:
            job_id: Backup job ID
            test_type: Type of verification test
            tester_id: User ID performing the test
            restore_target: Target location for restoration (optional)
            sample_files: List of files to test (for partial tests)

        Returns:
            Tuple of (result, details_dict)
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting {test_type.value} verification for job {job_id}")

        try:
            # Get backup job
            job = BackupJob.query.get(job_id)
            if not job:
                raise ValueError(f"Backup job {job_id} not found")

            # Get backup copies
            backup_copies = BackupCopy.query.filter_by(job_id=job_id).all()
            if not backup_copies:
                raise ValueError(f"No backup copies found for job {job_id}")

            # Execute appropriate test type
            if test_type == VerificationType.FULL_RESTORE:
                result, details = self._execute_full_restore_test(job, backup_copies, restore_target)
            elif test_type == VerificationType.PARTIAL:
                result, details = self._execute_partial_restore_test(job, backup_copies, restore_target, sample_files)
            elif test_type == VerificationType.INTEGRITY:
                result, details = self._execute_integrity_check(job, backup_copies)
            else:
                raise ValueError(f"Unknown test type: {test_type}")

            # Calculate duration
            duration_seconds = int((datetime.utcnow() - start_time).total_seconds())

            # Record test result in database
            self._record_test_result(
                job_id=job_id,
                test_type=test_type.value,
                tester_id=tester_id,
                test_result=result.value,
                duration_seconds=duration_seconds,
                restore_target=restore_target,
                details=details,
            )

            # Update statistics
            self.stats["total_tests"] += 1
            if result == TestResult.SUCCESS:
                self.stats["successful_tests"] += 1
            else:
                self.stats["failed_tests"] += 1
            self.stats["last_test"] = datetime.utcnow().isoformat()

            logger.info(f"Verification test completed: {result.value} in {duration_seconds}s")

            return result, details

        except Exception as e:
            logger.error(f"Error executing verification test: {e}", exc_info=True)
            duration_seconds = int((datetime.utcnow() - start_time).total_seconds())

            # Record error
            self._record_test_result(
                job_id=job_id,
                test_type=test_type.value,
                tester_id=tester_id,
                test_result=TestResult.ERROR.value,
                duration_seconds=duration_seconds,
                restore_target=restore_target,
                details={"error": str(e), "exception_type": type(e).__name__},
            )

            return TestResult.ERROR, {"error": str(e), "exception_type": type(e).__name__}

    def _execute_full_restore_test(
        self, job: BackupJob, backup_copies: List[BackupCopy], restore_target: Optional[str]
    ) -> Tuple[TestResult, Dict]:
        """
        Execute full restore test.

        Args:
            job: Backup job
            backup_copies: List of backup copies
            restore_target: Target directory for restoration

        Returns:
            Tuple of (result, details)
        """
        details = {
            "test_type": "full_restore",
            "job_name": job.job_name,
            "timestamp": datetime.utcnow().isoformat(),
            "copies_tested": [],
        }

        # Use test directory if no target specified
        if not restore_target:
            test_dir = self.test_root_dir / f"full_restore_{job.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            restore_target = str(test_dir)
            details["cleanup_required"] = True
        else:
            details["cleanup_required"] = False

        restore_path = Path(restore_target)
        restore_path.mkdir(parents=True, exist_ok=True)

        overall_result = TestResult.SUCCESS
        total_files_restored = 0
        total_files_verified = 0
        errors = []

        # Test primary backup copy
        primary_copy = next((c for c in backup_copies if c.copy_type == "primary"), None)
        if not primary_copy:
            logger.warning(f"No primary backup copy found for job {job.id}")
            return TestResult.FAILED, {**details, "error": "No primary backup copy found"}

        try:
            # Simulate full restoration
            source_path = Path(primary_copy.storage_path) if primary_copy.storage_path else None

            if not source_path or not source_path.exists():
                logger.error(f"Backup source path not found: {source_path}")
                return TestResult.FAILED, {**details, "error": f"Backup source not found: {source_path}"}

            # Copy backup files to restore target
            if source_path.is_file():
                # Single file backup
                shutil.copy2(source_path, restore_path / source_path.name)
                total_files_restored = 1

                # Verify restored file
                verification_result = self._verify_restored_file(
                    source_path, restore_path / source_path.name, ChecksumAlgorithm.SHA256
                )
                if verification_result["status"] == VerificationStatus.SUCCESS:
                    total_files_verified = 1
                else:
                    errors.append(f"Verification failed for {source_path.name}")
                    overall_result = TestResult.FAILED

            elif source_path.is_dir():
                # Directory backup - copy all files
                restored_files = []
                for file_path in source_path.rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(source_path)
                        target_file = restore_path / relative_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)

                        try:
                            shutil.copy2(file_path, target_file)
                            restored_files.append((file_path, target_file))
                            total_files_restored += 1
                        except Exception as e:
                            logger.error(f"Failed to restore {file_path}: {e}")
                            errors.append(f"Restore failed for {relative_path}: {str(e)}")

                # Verify restored files (sample or all if small)
                files_to_verify = restored_files if len(restored_files) <= 100 else restored_files[:100]

                for source_file, target_file in files_to_verify:
                    verification_result = self._verify_restored_file(source_file, target_file, ChecksumAlgorithm.SHA256)
                    if verification_result["status"] == VerificationStatus.SUCCESS:
                        total_files_verified += 1
                    else:
                        errors.append(f"Verification failed for {source_file.name}")

                if total_files_verified < len(files_to_verify):
                    overall_result = TestResult.WARNING if total_files_verified > 0 else TestResult.FAILED

            details["copies_tested"].append(
                {
                    "copy_type": primary_copy.copy_type,
                    "storage_path": primary_copy.storage_path,
                    "files_restored": total_files_restored,
                    "files_verified": total_files_verified,
                }
            )

        except Exception as e:
            logger.error(f"Error during full restore test: {e}", exc_info=True)
            errors.append(f"Restore error: {str(e)}")
            overall_result = TestResult.ERROR

        finally:
            # Cleanup test directory if created
            if details["cleanup_required"]:
                try:
                    shutil.rmtree(restore_path, ignore_errors=True)
                    logger.debug(f"Cleaned up test directory: {restore_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup test directory: {e}")

        details["total_files_restored"] = total_files_restored
        details["total_files_verified"] = total_files_verified
        details["errors"] = errors
        details["verification_rate"] = (total_files_verified / total_files_restored * 100) if total_files_restored > 0 else 0.0

        return overall_result, details

    def _execute_partial_restore_test(
        self,
        job: BackupJob,
        backup_copies: List[BackupCopy],
        restore_target: Optional[str],
        sample_files: Optional[List[str]],
    ) -> Tuple[TestResult, Dict]:
        """
        Execute partial restore test (selective file restoration).

        Args:
            job: Backup job
            backup_copies: List of backup copies
            restore_target: Target directory for restoration
            sample_files: Specific files to test

        Returns:
            Tuple of (result, details)
        """
        details = {
            "test_type": "partial",
            "job_name": job.job_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Use test directory if no target specified
        if not restore_target:
            test_dir = self.test_root_dir / f"partial_restore_{job.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            restore_target = str(test_dir)
            details["cleanup_required"] = True
        else:
            details["cleanup_required"] = False

        restore_path = Path(restore_target)
        restore_path.mkdir(parents=True, exist_ok=True)

        # Get primary backup copy
        primary_copy = next((c for c in backup_copies if c.copy_type == "primary"), None)
        if not primary_copy or not primary_copy.storage_path:
            return TestResult.FAILED, {**details, "error": "No valid primary backup copy found"}

        source_path = Path(primary_copy.storage_path)
        if not source_path.exists():
            return TestResult.FAILED, {**details, "error": f"Backup source not found: {source_path}"}

        overall_result = TestResult.SUCCESS
        verified_files = 0
        failed_files = 0
        errors = []

        try:
            # Determine files to test
            if sample_files:
                # Use specified files
                files_to_test = [source_path / f for f in sample_files if (source_path / f).exists()]
            else:
                # Use random sample (up to 10 files)
                if source_path.is_dir():
                    all_files = [f for f in source_path.rglob("*") if f.is_file()]
                    import random

                    files_to_test = random.sample(all_files, min(10, len(all_files)))
                else:
                    files_to_test = [source_path]

            # Restore and verify each file
            for file_path in files_to_test:
                try:
                    if source_path.is_dir():
                        relative_path = file_path.relative_to(source_path)
                    else:
                        relative_path = file_path.name

                    target_file = restore_path / relative_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Restore file
                    shutil.copy2(file_path, target_file)

                    # Verify
                    verification_result = self._verify_restored_file(file_path, target_file, ChecksumAlgorithm.SHA256)

                    if verification_result["status"] == VerificationStatus.SUCCESS:
                        verified_files += 1
                    else:
                        failed_files += 1
                        errors.append(f"Verification failed: {relative_path}")

                except Exception as e:
                    logger.error(f"Error restoring {file_path}: {e}")
                    failed_files += 1
                    errors.append(f"Restore error for {file_path.name}: {str(e)}")

            # Determine overall result
            if failed_files == 0:
                overall_result = TestResult.SUCCESS
            elif verified_files > failed_files:
                overall_result = TestResult.WARNING
            else:
                overall_result = TestResult.FAILED

        except Exception as e:
            logger.error(f"Error during partial restore test: {e}", exc_info=True)
            errors.append(f"Test error: {str(e)}")
            overall_result = TestResult.ERROR

        finally:
            # Cleanup
            if details["cleanup_required"]:
                try:
                    shutil.rmtree(restore_path, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Failed to cleanup: {e}")

        details["files_tested"] = len(files_to_test) if "files_to_test" in locals() else 0
        details["verified_files"] = verified_files
        details["failed_files"] = failed_files
        details["errors"] = errors
        details["success_rate"] = (verified_files / len(files_to_test) * 100) if files_to_test else 0.0

        return overall_result, details

    def _execute_integrity_check(self, job: BackupJob, backup_copies: List[BackupCopy]) -> Tuple[TestResult, Dict]:
        """
        Execute integrity check (checksum validation without restoration).

        Args:
            job: Backup job
            backup_copies: List of backup copies

        Returns:
            Tuple of (result, details)
        """
        details = {
            "test_type": "integrity",
            "job_name": job.job_name,
            "timestamp": datetime.utcnow().isoformat(),
            "copies_checked": [],
        }

        overall_result = TestResult.SUCCESS
        total_files_checked = 0
        total_files_valid = 0
        errors = []

        for copy in backup_copies:
            if not copy.storage_path:
                logger.warning(f"Backup copy {copy.id} has no storage path")
                continue

            source_path = Path(copy.storage_path)
            if not source_path.exists():
                logger.error(f"Backup copy path not found: {source_path}")
                errors.append(f"Path not found for {copy.copy_type} copy: {source_path}")
                continue

            copy_details = {
                "copy_type": copy.copy_type,
                "storage_path": copy.storage_path,
                "files_checked": 0,
                "files_valid": 0,
            }

            try:
                # Calculate checksums for all files
                if source_path.is_file():
                    # Single file
                    checksum = self.checksum_service.calculate_checksum(source_path, ChecksumAlgorithm.SHA256)
                    copy_details["files_checked"] = 1
                    copy_details["files_valid"] = 1
                    copy_details["checksum"] = checksum
                    total_files_checked += 1
                    total_files_valid += 1

                elif source_path.is_dir():
                    # Directory - check all files
                    files = [f for f in source_path.rglob("*") if f.is_file()]
                    checksums = self.checksum_service.calculate_checksums_parallel(files, ChecksumAlgorithm.SHA256)

                    copy_details["files_checked"] = len(files)
                    copy_details["files_valid"] = len(checksums)
                    total_files_checked += len(files)
                    total_files_valid += len(checksums)

                    if len(checksums) < len(files):
                        missing = len(files) - len(checksums)
                        errors.append(f"{missing} files failed checksum calculation in {copy.copy_type} copy")
                        overall_result = TestResult.WARNING

            except Exception as e:
                logger.error(f"Error checking integrity for copy {copy.id}: {e}", exc_info=True)
                errors.append(f"Integrity check error for {copy.copy_type}: {str(e)}")
                overall_result = TestResult.ERROR

            details["copies_checked"].append(copy_details)

        details["total_files_checked"] = total_files_checked
        details["total_files_valid"] = total_files_valid
        details["errors"] = errors
        details["validity_rate"] = (total_files_valid / total_files_checked * 100) if total_files_checked > 0 else 0.0

        # Determine final result
        if errors and overall_result == TestResult.SUCCESS:
            overall_result = TestResult.WARNING
        if total_files_valid == 0 and total_files_checked > 0:
            overall_result = TestResult.FAILED

        return overall_result, details

    def _verify_restored_file(self, source_path: Path, restored_path: Path, algorithm: ChecksumAlgorithm) -> Dict:
        """
        Verify a restored file against the original.

        Args:
            source_path: Original file path
            restored_path: Restored file path
            algorithm: Checksum algorithm

        Returns:
            Verification result dictionary
        """
        try:
            status, details = self.file_validator.verify_file(source_path, restored_path, algorithm)
            return {"status": status, "details": details}
        except Exception as e:
            logger.error(f"Error verifying restored file: {e}")
            return {"status": VerificationStatus.FAILED, "error": str(e)}

    def _record_test_result(
        self,
        job_id: int,
        test_type: str,
        tester_id: int,
        test_result: str,
        duration_seconds: int,
        restore_target: Optional[str],
        details: Dict,
    ) -> None:
        """
        Record verification test result in database.

        Args:
            job_id: Backup job ID
            test_type: Type of test
            tester_id: User ID
            test_result: Test result
            duration_seconds: Test duration
            restore_target: Restoration target
            details: Test details
        """
        try:
            # Format issues found
            issues_found = None
            if details.get("errors"):
                issues_found = "\n".join(details["errors"])

            # Create verification test record
            test = VerificationTest(
                job_id=job_id,
                test_type=test_type,
                test_date=datetime.utcnow(),
                tester_id=tester_id,
                restore_target=restore_target,
                test_result=test_result,
                duration_seconds=duration_seconds,
                issues_found=issues_found,
                notes=f"Test completed. Details: {details.get('test_type', 'unknown')} test",
            )

            db.session.add(test)
            db.session.commit()

            logger.info(f"Recorded verification test result for job {job_id}: {test_result}")

        except Exception as e:
            logger.error(f"Error recording test result: {e}", exc_info=True)
            db.session.rollback()

    def schedule_verification_test(
        self, job_id: int, test_frequency: str, assigned_to: Optional[int] = None, next_test_date: Optional[datetime] = None
    ) -> VerificationSchedule:
        """
        Schedule a recurring verification test.

        Args:
            job_id: Backup job ID
            test_frequency: Frequency (monthly/quarterly/semi-annual/annual)
            assigned_to: User ID to assign to
            next_test_date: Next test date (auto-calculated if not provided)

        Returns:
            Created VerificationSchedule object
        """
        # Calculate next test date if not provided
        if not next_test_date:
            next_test_date = self._calculate_next_test_date(test_frequency)

        schedule = VerificationSchedule(
            job_id=job_id,
            test_frequency=test_frequency,
            next_test_date=next_test_date.date(),
            assigned_to=assigned_to,
            is_active=True,
        )

        db.session.add(schedule)
        db.session.commit()

        logger.info(f"Scheduled verification test for job {job_id}: {test_frequency} starting {next_test_date.date()}")

        return schedule

    def _calculate_next_test_date(self, frequency: str) -> datetime:
        """
        Calculate next test date based on frequency.

        Args:
            frequency: Test frequency

        Returns:
            Next test date
        """
        now = datetime.utcnow()

        frequency_mapping = {"monthly": 30, "quarterly": 90, "semi-annual": 180, "annual": 365}

        days = frequency_mapping.get(frequency, 30)
        return now + timedelta(days=days)

    def update_verification_schedule(self, schedule_id: int, next_test_date: datetime) -> None:
        """
        Update verification schedule after test execution.

        Args:
            schedule_id: Schedule ID
            next_test_date: New next test date
        """
        schedule = VerificationSchedule.query.get(schedule_id)
        if schedule:
            schedule.last_test_date = datetime.utcnow().date()
            schedule.next_test_date = next_test_date.date()
            db.session.commit()
            logger.info(f"Updated verification schedule {schedule_id}: next test on {next_test_date.date()}")

    def get_overdue_verification_tests(self) -> List[VerificationSchedule]:
        """
        Get overdue verification tests.

        Returns:
            List of overdue schedules
        """
        today = datetime.utcnow().date()
        overdue = VerificationSchedule.query.filter(
            VerificationSchedule.is_active == True, VerificationSchedule.next_test_date <= today
        ).all()

        logger.info(f"Found {len(overdue)} overdue verification tests")
        return overdue

    def get_statistics(self) -> Dict:
        """
        Get verification service statistics.

        Returns:
            Statistics dictionary
        """
        stats = self.stats.copy()

        # Add database statistics
        total_tests_db = VerificationTest.query.count()
        successful_tests_db = VerificationTest.query.filter_by(test_result="success").count()
        failed_tests_db = VerificationTest.query.filter_by(test_result="failed").count()

        stats["db_total_tests"] = total_tests_db
        stats["db_successful_tests"] = successful_tests_db
        stats["db_failed_tests"] = failed_tests_db
        stats["db_success_rate"] = (successful_tests_db / total_tests_db * 100) if total_tests_db > 0 else 0.0

        return stats

    async def execute_verification_test_async(
        self,
        job_id: int,
        test_type: VerificationType,
        tester_id: int,
        restore_target: Optional[str] = None,
        sample_files: Optional[List[str]] = None,
    ) -> Tuple[TestResult, Dict]:
        """
        Execute verification test asynchronously.

        Args:
            job_id: Backup job ID
            test_type: Type of test
            tester_id: User ID
            restore_target: Restoration target
            sample_files: Sample files for partial test

        Returns:
            Tuple of (result, details)
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self.execute_verification_test, job_id, test_type, tester_id, restore_target, sample_files
        )
        return result

    def __repr__(self) -> str:
        return (
            f"VerificationService("
            f"total_tests={self.stats['total_tests']}, "
            f"successful={self.stats['successful_tests']}, "
            f"failed={self.stats['failed_tests']})"
        )


# Singleton instance
_verification_service_instance = None


def get_verification_service() -> VerificationService:
    """
    Get verification service singleton instance.

    Returns:
        VerificationService instance
    """
    global _verification_service_instance
    if _verification_service_instance is None:
        _verification_service_instance = VerificationService()
    return _verification_service_instance
