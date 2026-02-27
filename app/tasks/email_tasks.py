"""
Celery Email Tasks for Backup Management System
Phase 11: Asynchronous Email Processing

This module provides asynchronous email sending capabilities,
allowing emails to be sent in the background without blocking
the main application thread.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, Retry

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_email",
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    rate_limit="10/m",  # 10 emails per minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,
)
def send_email(
    self,
    to: str,
    subject: str,
    html_body: str,
    plain_body: Optional[str] = None,
    sender: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Send email asynchronously via Celery.

    This task wraps the EmailNotificationService to send emails
    in the background. It includes automatic retries with exponential
    backoff on failure.

    Args:
        self: Celery task instance (bound)
        to: Recipient email address
        subject: Email subject line
        html_body: HTML email content
        plain_body: Plain text fallback content (optional)
        sender: Sender email address (uses default if not specified)
        cc: Carbon copy recipients (optional)
        bcc: Blind carbon copy recipients (optional)
        reply_to: Reply-to address (optional)
        headers: Additional email headers (optional)

    Returns:
        Dict with delivery status and metadata

    Raises:
        Retry: If delivery fails and retries are available
    """
    from app.services.notification_service import EmailNotificationService

    task_id = self.request.id
    attempt = self.request.retries + 1
    max_attempts = self.max_retries + 1

    logger.info(f"[Task {task_id}] Sending email to {to} (attempt {attempt}/{max_attempts})")

    result = {
        "task_id": task_id,
        "to": to,
        "subject": subject,
        "attempt": attempt,
        "status": "pending",
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        # Initialize email service
        email_service = EmailNotificationService()

        # Check if service is configured
        if not email_service.is_configured():
            logger.error(f"[Task {task_id}] Email service not configured")
            result["status"] = "failed"
            result["error"] = "Email service not configured"
            return result

        # Validate recipient
        if not email_service.validate_email(to):
            logger.error(f"[Task {task_id}] Invalid email address: {to}")
            result["status"] = "failed"
            result["error"] = f"Invalid email address: {to}"
            return result

        # Check rate limit
        if not email_service.check_rate_limit(to):
            logger.warning(f"[Task {task_id}] Rate limit exceeded for {to}")
            result["status"] = "rate_limited"
            result["error"] = "Rate limit exceeded"
            # Retry after rate limit window
            raise self.retry(countdown=3600)  # Retry after 1 hour

        # Send email
        success = email_service.send_email(
            to=to,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            sender=sender,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            headers=headers,
        )

        if success:
            logger.info(f"[Task {task_id}] Email sent successfully to {to}")
            result["status"] = "sent"
            result["sent_at"] = datetime.now(UTC).isoformat()

            # Record notification in database
            _record_notification(
                notification_type="email",
                recipient=to,
                subject=subject,
                status="sent",
                task_id=task_id,
            )
        else:
            logger.error(f"[Task {task_id}] Email send failed to {to}")
            result["status"] = "failed"
            result["error"] = "Send operation returned false"
            raise self.retry(countdown=60 * (2**self.request.retries))

        return result

    except Retry:
        raise
    except MaxRetriesExceededError:
        logger.error(f"[Task {task_id}] Max retries exceeded for email to {to}")
        result["status"] = "failed"
        result["error"] = "Max retries exceeded"

        # Record failed notification
        _record_notification(
            notification_type="email",
            recipient=to,
            subject=subject,
            status="failed",
            task_id=task_id,
            error="Max retries exceeded",
        )
        return result
    except Exception as e:
        logger.exception(f"[Task {task_id}] Unexpected error sending email to {to}: {e}")
        result["status"] = "error"
        result["error"] = str(e)

        # Retry if possible
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2**self.request.retries))

        return result


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_bulk_emails",
    max_retries=1,
    default_retry_delay=120,
)
def send_bulk_emails(
    self,
    recipients: List[str],
    subject: str,
    html_body: str,
    plain_body: Optional[str] = None,
    sender: Optional[str] = None,
    batch_size: int = 10,
) -> Dict[str, Any]:
    """
    Send emails to multiple recipients in batches.

    This task splits the recipient list into batches and queues
    individual send_email tasks for each recipient.

    Args:
        self: Celery task instance (bound)
        recipients: List of recipient email addresses
        subject: Email subject line
        html_body: HTML email content
        plain_body: Plain text fallback content (optional)
        sender: Sender email address (optional)
        batch_size: Number of emails per batch (default 10)

    Returns:
        Dict with batch processing status
    """
    task_id = self.request.id
    total_recipients = len(recipients)

    logger.info(f"[Task {task_id}] Starting bulk email to {total_recipients} recipients")

    result = {
        "task_id": task_id,
        "total_recipients": total_recipients,
        "batch_size": batch_size,
        "queued_tasks": [],
        "status": "processing",
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        # Queue individual email tasks
        for i, recipient in enumerate(recipients):
            # Queue with staggered delays to avoid overwhelming SMTP server
            delay = (i // batch_size) * 60  # 1 minute delay per batch

            task = send_email.apply_async(
                kwargs={
                    "to": recipient,
                    "subject": subject,
                    "html_body": html_body,
                    "plain_body": plain_body,
                    "sender": sender,
                },
                countdown=delay,
            )

            result["queued_tasks"].append({"recipient": recipient, "task_id": task.id, "delay": delay})

        result["status"] = "queued"
        result["queued_count"] = len(result["queued_tasks"])

        logger.info(f"[Task {task_id}] Queued {result['queued_count']} email tasks")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error queueing bulk emails: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_backup_notification",
    max_retries=3,
    default_retry_delay=60,
)
def send_backup_notification(
    self,
    notification_type: str,
    recipient: str,
    job_name: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send backup-related notification email.

    This task sends templated emails for backup events such as
    success, failure, or rule violations.

    Args:
        self: Celery task instance (bound)
        notification_type: Type of notification (success, failure, violation, reminder)
        recipient: Recipient email address
        job_name: Backup job name
        status: Backup job status
        details: Additional details for the notification

    Returns:
        Dict with notification status
    """
    from app.services.notification_service import EmailNotificationService

    task_id = self.request.id
    logger.info(f"[Task {task_id}] Sending {notification_type} notification for job '{job_name}'")

    # Map notification types to templates
    template_map = {
        "success": "backup_success.html",
        "failure": "backup_failure.html",
        "violation": "rule_violation.html",
        "reminder": "media_reminder.html",
        "daily_report": "daily_report.html",
    }

    # Subject prefixes
    subject_map = {
        "success": "✅ バックアップ成功",
        "failure": "❌ バックアップ失敗",
        "violation": "⚠️ ルール違反検出",
        "reminder": "📅 メディアリマインダー",
        "daily_report": "📊 日次レポート",
    }

    template_name = template_map.get(notification_type, "backup_success.html")
    subject_prefix = subject_map.get(notification_type, "📧 通知")
    subject = f"{subject_prefix}: {job_name}"

    result = {
        "task_id": task_id,
        "notification_type": notification_type,
        "recipient": recipient,
        "job_name": job_name,
        "status": "pending",
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        email_service = EmailNotificationService()

        # Render template
        template_context = {
            "job_name": job_name,
            "status": status,
            "timestamp": datetime.now(UTC),
            **(details or {}),
        }

        html_body = email_service.render_template(template_name, **template_context)

        if html_body is None:
            # Fallback to simple HTML if template not found
            html_body = _generate_fallback_html(notification_type, job_name, status, details)

        # Generate plain text version
        plain_body = _generate_plain_text(notification_type, job_name, status, details)

        # Send via the main send_email task
        email_result = send_email.apply_async(
            kwargs={
                "to": recipient,
                "subject": subject,
                "html_body": html_body,
                "plain_body": plain_body,
            }
        )

        result["status"] = "queued"
        result["email_task_id"] = email_result.id

        logger.info(f"[Task {task_id}] Notification queued: {email_result.id}")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error sending backup notification: {e}")
        result["status"] = "error"
        result["error"] = str(e)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2**self.request.retries))

        return result


def _record_notification(
    notification_type: str,
    recipient: str,
    subject: str,
    status: str,
    task_id: str,
    error: Optional[str] = None,
):
    """
    Record notification in database for tracking.

    Args:
        notification_type: Type of notification
        recipient: Recipient address
        subject: Notification subject
        status: Delivery status
        task_id: Celery task ID
        error: Error message if failed
    """
    try:
        from app.models import NotificationLog, db

        notification = NotificationLog(
            channel=notification_type,
            recipient=recipient,
            subject=subject,
            status=status,
            task_id=task_id,
            error_message=error,
            sent_at=datetime.now(UTC) if status == "sent" else None,
        )

        db.session.add(notification)
        db.session.commit()

        logger.debug(f"Recorded notification: {notification.id}")

    except Exception as e:
        logger.warning(f"Failed to record notification: {e}")
        # Don't fail the task if recording fails
        db.session.rollback()


def _generate_fallback_html(
    notification_type: str,
    job_name: str,
    status: str,
    details: Optional[Dict[str, Any]],
) -> str:
    """Generate fallback HTML when template is not available."""
    status_color = "#28a745" if status == "success" else "#dc3545"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .header {{ background: {status_color}; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background: #f9f9f9; }}
            .footer {{ padding: 10px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>バックアップ通知</h1>
            </div>
            <div class="content">
                <h2>{job_name}</h2>
                <p><strong>ステータス:</strong> {status}</p>
                <p><strong>種類:</strong> {notification_type}</p>
                <p><strong>時刻:</strong> {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
    """

    if details:
        html += "<h3>詳細</h3><ul>"
        for key, value in details.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"

    html += """
            </div>
            <div class="footer">
                <p>3-2-1-1-0 Backup Management System</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def _generate_plain_text(
    notification_type: str,
    job_name: str,
    status: str,
    details: Optional[Dict[str, Any]],
) -> str:
    """Generate plain text email content."""
    lines = [
        f"バックアップ通知: {notification_type}",
        "=" * 40,
        f"ジョブ名: {job_name}",
        f"ステータス: {status}",
        f"時刻: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
    ]

    if details:
        lines.append("詳細:")
        lines.append("-" * 20)
        for key, value in details.items():
            lines.append(f"  {key}: {value}")

    lines.extend(
        [
            "",
            "-" * 40,
            "3-2-1-1-0 Backup Management System",
        ]
    )

    return "\n".join(lines)
