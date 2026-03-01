"""
Celery Verification Tasks for Backup Management System
Phase 11: Asynchronous Verification Processing

This module provides asynchronous backup verification tasks
for integrity checking and restore testing.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.verification_tasks.verify_backup",
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,  # 1 hour max
    soft_time_limit=3300,  # 55 minutes soft limit
)
def verify_backup(
    self,
    job_id: int,
    verification_type: str = "checksum",
    notify_on_complete: bool = True,
) -> Dict[str, Any]:
    """
    Verify backup integrity asynchronously.

    This task performs backup verification in the background,
    including checksum validation and optional restore testing.

    Args:
        self: Celery task instance (bound)
        job_id: Backup job ID to verify
        verification_type: Type of verification (checksum, restore_test, full)
        notify_on_complete: Send notification when complete

    Returns:
        Dict with verification results
    """
    from app.services.verification_service import VerificationService

    task_id = self.request.id

    logger.info(f"[Task {task_id}] Starting {verification_type} verification for job {job_id}")

    result = {
        "task_id": task_id,
        "job_id": job_id,
        "verification_type": verification_type,
        "status": "processing",
        "started_at": datetime.now(UTC).isoformat(),
    }

    try:
        from app.models import BackupJob, VerificationResult, db

        # Fetch job
        job = db.session.get(BackupJob, job_id)
        if not job:
            logger.warning(f"[Task {task_id}] Job {job_id} not found")
            result["status"] = "failed"
            result["error"] = "Job not found"
            return result

        verification_service = VerificationService()

        # Perform verification based on type
        if verification_type == "checksum":
            verification_result = verification_service.verify_checksum(job_id)
        elif verification_type == "restore_test":
            verification_result = verification_service.verify_restore_test(job_id)
        elif verification_type == "full":
            # Full verification includes both checksum and restore test
            checksum_result = verification_service.verify_checksum(job_id)
            restore_result = verification_service.verify_restore_test(job_id)
            verification_result = {
                "checksum": checksum_result,
                "restore_test": restore_result,
                "overall_success": checksum_result.get("success", False) and restore_result.get("success", False),
            }
        else:
            logger.error(f"[Task {task_id}] Unknown verification type: {verification_type}")
            result["status"] = "failed"
            result["error"] = f"Unknown verification type: {verification_type}"
            return result

        # Process results
        success = verification_result.get("success", False) or verification_result.get("overall_success", False)

        result["status"] = "completed"
        result["success"] = success
        result["verification_result"] = verification_result
        result["completed_at"] = datetime.now(UTC).isoformat()

        # Record verification result
        _record_verification(
            job_id=job_id,
            verification_type=verification_type,
            success=success,
            details=verification_result,
            task_id=task_id,
        )

        # Update job verification status
        job.last_verified_at = datetime.now(UTC)
        job.verification_status = "verified" if success else "failed"
        db.session.commit()

        logger.info(f"[Task {task_id}] Verification {'succeeded' if success else 'failed'} for job {job_id}")

        # Send notification if requested
        if notify_on_complete:
            _send_verification_notification(
                job_name=job.name,
                success=success,
                verification_type=verification_type,
            )

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error verifying backup: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        result["completed_at"] = datetime.now(UTC).isoformat()

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)

        return result


@celery_app.task(
    bind=True,
    name="app.tasks.verification_tasks.verify_all_pending",
    max_retries=1,
    time_limit=7200,  # 2 hours max
)
def verify_all_pending(
    self,
    max_jobs: int = 10,
    verification_type: str = "checksum",
) -> Dict[str, Any]:
    """
    Verify all pending backup jobs.

    This task finds jobs that need verification and queues
    individual verification tasks for each.

    Args:
        self: Celery task instance (bound)
        max_jobs: Maximum number of jobs to verify in this batch
        verification_type: Type of verification to perform

    Returns:
        Dict with batch verification status
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Starting batch verification (max {max_jobs} jobs)")

    result = {
        "task_id": task_id,
        "verification_type": verification_type,
        "status": "processing",
        "queued_jobs": [],
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        from datetime import timedelta

        from app.models import BackupJob, db

        # Find jobs needing verification
        # Criteria: completed successfully, not verified in last 7 days
        cutoff = datetime.now(UTC) - timedelta(days=7)

        pending_jobs = (
            BackupJob.query.filter(
                BackupJob.status == "success",
                (BackupJob.last_verified_at.is_(None)) | (BackupJob.last_verified_at < cutoff),
            )
            .order_by(BackupJob.last_verified_at.asc().nullsfirst())
            .limit(max_jobs)
            .all()
        )

        # Queue verification tasks
        for job in pending_jobs:
            verification_task = verify_backup.apply_async(
                kwargs={
                    "job_id": job.id,
                    "verification_type": verification_type,
                    "notify_on_complete": False,
                },
                countdown=len(result["queued_jobs"]) * 60,  # Stagger by 1 minute
            )

            result["queued_jobs"].append(
                {
                    "job_id": job.id,
                    "job_name": job.name,
                    "task_id": verification_task.id,
                }
            )

        result["status"] = "queued"
        result["queued_count"] = len(result["queued_jobs"])

        logger.info(f"[Task {task_id}] Queued {result['queued_count']} verification tasks")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error in batch verification: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.verification_tasks.check_verification_reminders",
    max_retries=1,
)
def check_verification_reminders(self) -> Dict[str, Any]:
    """
    Check for jobs that need verification reminders.

    This task identifies jobs that haven't been verified
    recently and sends reminder notifications.

    Returns:
        Dict with reminder status
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Checking verification reminders")

    result = {
        "task_id": task_id,
        "status": "processing",
        "reminders_sent": 0,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        from datetime import timedelta

        from app.models import BackupJob, db

        # Find jobs not verified in 30 days
        cutoff = datetime.now(UTC) - timedelta(days=30)

        overdue_jobs = (
            BackupJob.query.filter(
                BackupJob.status == "success",
                (BackupJob.last_verified_at.is_(None)) | (BackupJob.last_verified_at < cutoff),
            )
            .order_by(BackupJob.last_verified_at.asc().nullsfirst())
            .all()
        )

        if overdue_jobs:
            # Create reminder alert
            from app.models import Alert

            job_names = [job.name for job in overdue_jobs[:10]]  # Limit to first 10
            message = (
                f"{len(overdue_jobs)}件のバックアップジョブが30日以上検証されていません。\n"
                f"対象ジョブ: {', '.join(job_names)}"
            )

            alert = Alert(
                title="検証リマインダー",
                message=message,
                level="warning",
                source="verification_reminder",
                is_read=False,
                created_at=datetime.now(UTC),
            )

            db.session.add(alert)
            db.session.commit()

            result["reminders_sent"] = len(overdue_jobs)
            result["overdue_jobs"] = [j.name for j in overdue_jobs]

        result["status"] = "completed"

        logger.info(f"[Task {task_id}] Found {len(overdue_jobs)} jobs needing verification")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error checking verification reminders: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


def _record_verification(
    job_id: int,
    verification_type: str,
    success: bool,
    details: Dict[str, Any],
    task_id: str,
):
    """Record verification result in database."""
    try:
        from app.models import VerificationResult, db

        verification = VerificationResult(
            job_id=job_id,
            verification_type=verification_type,
            success=success,
            details=str(details),
            task_id=task_id,
            verified_at=datetime.now(UTC),
        )

        db.session.add(verification)
        db.session.commit()

        logger.debug(f"Recorded verification result: {verification.id}")

    except Exception as e:
        logger.warning(f"Failed to record verification: {e}")
        db.session.rollback()


def _send_verification_notification(
    job_name: str,
    success: bool,
    verification_type: str,
):
    """Send verification completion notification."""
    from app.tasks.notification_tasks import send_multi_channel_notification

    if success:
        title = f"✅ 検証成功: {job_name}"
        severity = "info"
    else:
        title = f"❌ 検証失敗: {job_name}"
        severity = "error"

    send_multi_channel_notification.apply_async(
        kwargs={
            "channels": ["dashboard"] if success else ["dashboard", "email"],
            "title": title,
            "message": f"バックアップジョブ '{job_name}' の{verification_type}検証が"
            f"{'成功' if success else '失敗'}しました。",
            "severity": severity,
            "job_name": job_name,
            "details": {"verification_type": verification_type, "success": success},
        }
    )
