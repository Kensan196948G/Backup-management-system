"""
Celery Notification Tasks for Backup Management System
Phase 11: Asynchronous Notification Processing

This module provides asynchronous notification capabilities
for Microsoft Teams and multi-channel orchestration.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.send_teams_notification",
    max_retries=3,
    default_retry_delay=60,
    rate_limit="30/m",  # 30 Teams messages per minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_teams_notification(
    self,
    webhook_url: str,
    title: str,
    message: str,
    card_type: str = "message",
    severity: str = "info",
    facts: Optional[List[Dict[str, str]]] = None,
    actions: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Send Microsoft Teams notification asynchronously.

    This task sends Adaptive Card messages to Microsoft Teams
    via webhook with automatic retries on failure.

    Args:
        self: Celery task instance (bound)
        webhook_url: Teams incoming webhook URL
        title: Card title
        message: Main message content
        card_type: Type of card (message, alert, report, etc.)
        severity: Severity level (info, warning, error, critical)
        facts: List of key-value facts to display
        actions: List of action buttons

    Returns:
        Dict with delivery status
    """
    from app.services.teams_notification_service import TeamsNotificationService

    task_id = self.request.id
    attempt = self.request.retries + 1

    logger.info(f"[Task {task_id}] Sending Teams notification (attempt {attempt})")

    result = {
        "task_id": task_id,
        "title": title,
        "card_type": card_type,
        "severity": severity,
        "attempt": attempt,
        "status": "pending",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        teams_service = TeamsNotificationService(webhook_url=webhook_url)

        # Check if service is configured
        if not teams_service.is_configured():
            logger.error(f"[Task {task_id}] Teams service not configured")
            result["status"] = "failed"
            result["error"] = "Teams webhook URL not configured"
            return result

        # Build and send notification based on severity
        if severity == "critical":
            success = teams_service.send_critical_alert(
                title=title,
                message=message,
                facts=facts,
                actions=actions,
            )
        elif severity == "error":
            success = teams_service.send_error_notification(
                title=title,
                message=message,
                facts=facts,
            )
        elif severity == "warning":
            success = teams_service.send_warning_notification(
                title=title,
                message=message,
                facts=facts,
            )
        else:
            success = teams_service.send_info_notification(
                title=title,
                message=message,
                facts=facts,
            )

        if success:
            logger.info(f"[Task {task_id}] Teams notification sent successfully")
            result["status"] = "sent"
            result["sent_at"] = datetime.utcnow().isoformat()

            # Record in database
            _record_teams_notification(
                title=title,
                status="sent",
                task_id=task_id,
            )
        else:
            logger.error(f"[Task {task_id}] Teams notification failed")
            result["status"] = "failed"
            raise self.retry(countdown=60 * (2**self.request.retries))

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error sending Teams notification: {e}")
        result["status"] = "error"
        result["error"] = str(e)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2**self.request.retries))

        return result


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.send_multi_channel_notification",
    max_retries=2,
    default_retry_delay=120,
)
def send_multi_channel_notification(
    self,
    channels: List[str],
    title: str,
    message: str,
    severity: str = "info",
    recipient_email: Optional[str] = None,
    teams_webhook_url: Optional[str] = None,
    job_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send notification to multiple channels simultaneously.

    This task orchestrates notifications across multiple channels
    (email, Teams, etc.) based on the provided channel list.

    Args:
        self: Celery task instance (bound)
        channels: List of channels to notify (email, teams, dashboard)
        title: Notification title
        message: Notification message
        severity: Severity level
        recipient_email: Email recipient (required if email in channels)
        teams_webhook_url: Teams webhook (required if teams in channels)
        job_name: Related backup job name
        details: Additional details

    Returns:
        Dict with multi-channel delivery status
    """
    from app.tasks.email_tasks import send_backup_notification

    task_id = self.request.id

    logger.info(f"[Task {task_id}] Sending multi-channel notification to {channels}")

    result = {
        "task_id": task_id,
        "channels": channels,
        "title": title,
        "severity": severity,
        "status": "processing",
        "channel_results": {},
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Email channel
        if "email" in channels and recipient_email:
            notification_type = _severity_to_notification_type(severity)
            email_task = send_backup_notification.apply_async(
                kwargs={
                    "notification_type": notification_type,
                    "recipient": recipient_email,
                    "job_name": job_name or title,
                    "status": severity,
                    "details": details,
                }
            )
            result["channel_results"]["email"] = {
                "status": "queued",
                "task_id": email_task.id,
            }

        # Teams channel
        if "teams" in channels and teams_webhook_url:
            facts = []
            if details:
                facts = [{"title": k, "value": str(v)} for k, v in details.items()]

            teams_task = send_teams_notification.apply_async(
                kwargs={
                    "webhook_url": teams_webhook_url,
                    "title": title,
                    "message": message,
                    "severity": severity,
                    "facts": facts,
                }
            )
            result["channel_results"]["teams"] = {
                "status": "queued",
                "task_id": teams_task.id,
            }

        # Dashboard channel (database alert)
        if "dashboard" in channels:
            _create_dashboard_alert(
                title=title,
                message=message,
                severity=severity,
                job_name=job_name,
                details=details,
            )
            result["channel_results"]["dashboard"] = {"status": "created"}

        result["status"] = "queued"

        logger.info(f"[Task {task_id}] Multi-channel notification queued")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error in multi-channel notification: {e}")
        result["status"] = "error"
        result["error"] = str(e)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120)

        return result


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.send_backup_status_update",
    max_retries=3,
    default_retry_delay=60,
)
def send_backup_status_update(
    self,
    job_id: int,
    status: str,
    notify_channels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Send backup job status update notifications.

    This task fetches job details from the database and sends
    appropriate notifications based on the job status.

    Args:
        self: Celery task instance (bound)
        job_id: Backup job ID
        status: New status (success, failure, warning, etc.)
        notify_channels: Channels to notify (defaults to configured channels)

    Returns:
        Dict with notification status
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Sending status update for job {job_id}")

    result = {
        "task_id": task_id,
        "job_id": job_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        from app.models import BackupJob, db

        # Fetch job details
        job = BackupJob.query.get(job_id)
        if not job:
            logger.warning(f"[Task {task_id}] Job {job_id} not found")
            result["error"] = "Job not found"
            return result

        # Determine severity and message
        if status == "success":
            severity = "info"
            title = f"✅ バックアップ成功: {job.name}"
            message = f"バックアップジョブ '{job.name}' が正常に完了しました。"
        elif status == "failure":
            severity = "critical"
            title = f"❌ バックアップ失敗: {job.name}"
            message = f"バックアップジョブ '{job.name}' が失敗しました。"
        elif status == "warning":
            severity = "warning"
            title = f"⚠️ バックアップ警告: {job.name}"
            message = f"バックアップジョブ '{job.name}' で警告が発生しました。"
        else:
            severity = "info"
            title = f"📊 バックアップ更新: {job.name}"
            message = f"バックアップジョブ '{job.name}' のステータスが更新されました。"

        # Prepare details
        details = {
            "ジョブ名": job.name,
            "ステータス": status,
            "タイプ": job.job_type if hasattr(job, "job_type") else "N/A",
            "更新時刻": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Determine channels
        channels = notify_channels or _get_default_channels_for_severity(severity)

        # Queue multi-channel notification
        multi_task = send_multi_channel_notification.apply_async(
            kwargs={
                "channels": channels,
                "title": title,
                "message": message,
                "severity": severity,
                "job_name": job.name,
                "details": details,
            }
        )

        result["notification_task_id"] = multi_task.id
        result["channels"] = channels
        result["notification_status"] = "queued"

        logger.info(f"[Task {task_id}] Status update notification queued: {multi_task.id}")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error sending status update: {e}")
        result["error"] = str(e)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return result


def _severity_to_notification_type(severity: str) -> str:
    """Convert severity level to notification type."""
    mapping = {
        "critical": "failure",
        "error": "failure",
        "warning": "violation",
        "info": "success",
    }
    return mapping.get(severity, "success")


def _get_default_channels_for_severity(severity: str) -> List[str]:
    """Get default notification channels based on severity."""
    if severity in ("critical", "error"):
        return ["email", "teams", "dashboard"]
    elif severity == "warning":
        return ["email", "dashboard"]
    else:
        return ["dashboard"]


def _record_teams_notification(
    title: str,
    status: str,
    task_id: str,
    error: Optional[str] = None,
):
    """Record Teams notification in database."""
    try:
        from app.models import NotificationLog, db

        notification = NotificationLog(
            channel="teams",
            subject=title,
            status=status,
            task_id=task_id,
            error_message=error,
            sent_at=datetime.utcnow() if status == "sent" else None,
        )

        db.session.add(notification)
        db.session.commit()

    except Exception as e:
        logger.warning(f"Failed to record Teams notification: {e}")
        db.session.rollback()


def _create_dashboard_alert(
    title: str,
    message: str,
    severity: str,
    job_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """Create dashboard alert in database."""
    try:
        from app.models import Alert, db

        # Map severity to alert level
        level_map = {
            "critical": "critical",
            "error": "error",
            "warning": "warning",
            "info": "info",
        }

        alert = Alert(
            title=title,
            message=message,
            level=level_map.get(severity, "info"),
            source="notification_task",
            is_read=False,
            created_at=datetime.utcnow(),
        )

        db.session.add(alert)
        db.session.commit()

        logger.debug(f"Created dashboard alert: {alert.id}")

    except Exception as e:
        logger.warning(f"Failed to create dashboard alert: {e}")
        db.session.rollback()
