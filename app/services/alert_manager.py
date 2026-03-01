"""
Alert Manager Service

Manages alert generation, notification delivery, and acknowledgment.
Supports multiple notification channels:
- Database alerts
- Email notifications
- Microsoft Teams webhooks
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

from app.config import Config
from app.models import Alert, BackupJob, User, db

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Alert type enumeration"""

    BACKUP_FAILED = "backup_failed"
    BACKUP_SUCCESS = "backup_success"
    RULE_VIOLATION = "rule_violation"
    COMPLIANCE_WARNING = "compliance_warning"
    OFFLINE_MEDIA_UPDATE_WARNING = "offline_media_update_warning"
    VERIFICATION_REMINDER = "verification_reminder"
    MEDIA_ROTATION_REMINDER = "media_rotation_reminder"
    MEDIA_OVERDUE_RETURN = "media_overdue_return"
    SYSTEM_ERROR = "system_error"


class AlertManager:
    """
    Manages alert generation and notification delivery.

    Responsibilities:
    - Create alerts for various events
    - Send notifications via multiple channels
    - Track alert acknowledgment
    - Query and filter alerts
    """

    def __init__(self):
        """Initialize alert manager"""
        self.notification_service = None  # Lazy load when needed

    def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        job_id: Optional[int] = None,
        notify: bool = True,
    ) -> Alert:
        """
        Create a new alert and optionally send notifications.

        Args:
            alert_type: Type of alert (AlertType enum)
            severity: Severity level (AlertSeverity enum)
            title: Short title
            message: Detailed message
            job_id: Related backup job ID (optional)
            notify: Whether to send notifications

        Returns:
            Created Alert object
        """
        try:
            # Create alert record
            alert = Alert(
                alert_type=alert_type.value if isinstance(alert_type, AlertType) else alert_type,
                severity=severity.value if isinstance(severity, AlertSeverity) else severity,
                title=title,
                message=message,
                job_id=job_id,
                is_acknowledged=False,
            )

            db.session.add(alert)
            db.session.commit()

            logger.info(f"Alert created: {alert_type} - {title}")

            # Send notifications if requested
            if notify:
                self.send_notifications(alert)

            return alert

        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}", exc_info=True)
            db.session.rollback()
            raise

    def send_notifications(self, alert: Alert) -> Dict[str, bool]:
        """
        Send alert notifications via configured channels.

        Args:
            alert: Alert object to notify about

        Returns:
            Dictionary indicating success of each channel
        """
        results = {"email": False, "teams": False, "dashboard": True}  # Always succeeds as it's just DB storage

        try:
            # Always logged to dashboard/database
            logger.info(f"Alert notification sent to dashboard: {alert.title}")

            # Send email notifications
            if self._should_send_email(alert):
                results["email"] = self._send_email_notification(alert)

            # Send Microsoft Teams notification
            if self._should_send_teams(alert):
                results["teams"] = self._send_teams_notification(alert)

            return results

        except Exception as e:
            logger.error(f"Error sending notifications for alert {alert.id}: {str(e)}")
            return results

    def _should_send_email(self, alert: Alert) -> bool:
        """
        Determine if email notification should be sent.

        Returns:
            True if email should be sent
        """
        if not Config.MAIL_SERVER or not Config.MAIL_USERNAME:
            return False

        # Send emails for warning and error severity
        return alert.severity in ["warning", "error", "critical"]

    def _send_email_notification(self, alert: Alert) -> bool:
        """
        Send email notification using new notification service.

        Args:
            alert: Alert to send

        Returns:
            True if successful
        """
        try:
            # Lazy load notification service
            if self.notification_service is None:
                from app.services.notification_service import get_notification_service

                self.notification_service = get_notification_service()

            # Get email recipients
            recipients = self._get_email_recipients(alert)

            if not recipients:
                logger.warning(f"No email recipients found for alert {alert.id}")
                return False

            # Route to appropriate notification method based on alert type
            success_count = 0

            if alert.alert_type == AlertType.BACKUP_SUCCESS.value:
                for recipient in recipients:
                    if self._send_backup_success_email(alert, recipient):
                        success_count += 1

            elif alert.alert_type == AlertType.BACKUP_FAILED.value:
                for recipient in recipients:
                    if self._send_backup_failure_email(alert, recipient):
                        success_count += 1

            elif alert.alert_type in [AlertType.RULE_VIOLATION.value, AlertType.COMPLIANCE_WARNING.value]:
                for recipient in recipients:
                    if self._send_rule_violation_email(alert, recipient):
                        success_count += 1

            elif alert.alert_type in [
                AlertType.OFFLINE_MEDIA_UPDATE_WARNING.value,
                AlertType.VERIFICATION_REMINDER.value,
                AlertType.MEDIA_ROTATION_REMINDER.value,
                AlertType.MEDIA_OVERDUE_RETURN.value,
            ]:
                for recipient in recipients:
                    if self._send_media_reminder_email(alert, recipient):
                        success_count += 1

            else:
                # Generic alert notification (fallback)
                subject = f"[{alert.severity.upper()}] {alert.title}"
                body = self._build_email_body(alert)
                for recipient in recipients:
                    if self.notification_service.send_email(to=recipient, subject=subject, html_body=body):
                        success_count += 1

            logger.info(f"Email notification sent for alert {alert.id} to {success_count}/{len(recipients)} recipients")
            return success_count > 0

        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}", exc_info=True)
            return False

    def _send_backup_success_email(self, alert: Alert, recipient: str) -> bool:
        """Send backup success notification email"""
        try:
            job = db.session.get(BackupJob, alert.job_id) if alert.job_id else None
            details = {}

            if job:
                # Get latest execution
                latest_exec = job.executions.filter_by(execution_result="success").order_by(BackupJob.id.desc()).first()
                if latest_exec:
                    details = {
                        "backup_size_bytes": latest_exec.backup_size_bytes,
                        "duration_seconds": latest_exec.duration_seconds,
                        "storage_path": job.target_path,
                    }

            return self.notification_service.send_backup_success_notification(
                job_name=alert.title, recipients=[recipient], **details
            ).get(recipient, False)

        except Exception as e:
            logger.error(f"Error sending backup success email: {str(e)}")
            return False

    def _send_backup_failure_email(self, alert: Alert, recipient: str) -> bool:
        """Send backup failure notification email"""
        try:
            return self.notification_service.send_backup_failure_notification(
                job_name=alert.title, recipients=[recipient], error_message=alert.message
            ).get(recipient, False)

        except Exception as e:
            logger.error(f"Error sending backup failure email: {str(e)}")
            return False

    def _send_rule_violation_email(self, alert: Alert, recipient: str) -> bool:
        """Send rule violation notification email"""
        try:
            # Parse violations from message
            violations = [line.strip() for line in alert.message.split("\n") if line.strip()]

            return self.notification_service.send_rule_violation_notification(
                job_name=alert.title, recipients=[recipient], violations=violations
            ).get(recipient, False)

        except Exception as e:
            logger.error(f"Error sending rule violation email: {str(e)}")
            return False

    def _send_media_reminder_email(self, alert: Alert, recipient: str) -> bool:
        """Send media reminder notification email"""
        try:
            # Determine reminder type from alert type
            reminder_type_map = {
                AlertType.OFFLINE_MEDIA_UPDATE_WARNING.value: "update",
                AlertType.VERIFICATION_REMINDER.value: "verification",
                AlertType.MEDIA_ROTATION_REMINDER.value: "rotation",
                AlertType.MEDIA_OVERDUE_RETURN.value: "return",
            }

            reminder_type = reminder_type_map.get(alert.alert_type, "reminder")

            return self.notification_service.send_media_reminder_notification(
                media_id=alert.title, recipients=[recipient], reminder_type=reminder_type
            ).get(recipient, False)

        except Exception as e:
            logger.error(f"Error sending media reminder email: {str(e)}")
            return False

    def _should_send_teams(self, alert: Alert) -> bool:
        """
        Determine if Microsoft Teams notification should be sent.

        Returns:
            True if Teams should be notified
        """
        if not Config.TEAMS_WEBHOOK_URL:
            return False

        # Send Teams notifications for error and critical severity
        return alert.severity in ["error", "critical"]

    def _send_teams_notification(self, alert: Alert) -> bool:
        """
        Send Microsoft Teams notification via webhook using TeamsNotificationService.

        Args:
            alert: Alert to send

        Returns:
            True if successful
        """
        try:
            # Lazy load Teams notification service
            from app.services.teams_notification_service import TeamsNotificationService

            teams_service = TeamsNotificationService()

            # Get job info if available
            job_name = None
            created_at = alert.created_at

            if alert.job_id:
                job = db.session.get(BackupJob, alert.job_id)
                if job:
                    job_name = job.job_name

            # Send alert card via new Teams service
            result = teams_service.send_alert_card(
                title=alert.title,
                message=alert.message,
                severity=alert.severity,
                alert_type=alert.alert_type,
                alert_id=alert.id,
                job_name=job_name,
                created_at=created_at,
            )

            if result:
                logger.info(f"Teams notification sent for alert {alert.id}")
            else:
                logger.error(f"Failed to send Teams notification for alert {alert.id}")

            return result

        except Exception as e:
            logger.error(f"Error sending Teams notification: {str(e)}")
            return False

    def _get_email_recipients(self, alert: Alert) -> List[str]:
        """
        Get email recipients for an alert.

        Args:
            alert: Alert to send

        Returns:
            List of email addresses
        """
        try:
            recipients = []

            # Add job owner if alert is job-related
            if alert.job_id:
                job = db.session.get(BackupJob, alert.job_id)
                if job and job.owner and job.owner.email:
                    recipients.append(job.owner.email)

            # Add admin users
            admin_users = User.query.filter(User.role == "admin", User.is_active == True, User.email != None).all()

            for user in admin_users:
                if user.email not in recipients:
                    recipients.append(user.email)

            return recipients

        except Exception as e:
            logger.error(f"Error getting email recipients: {str(e)}")
            return []

    def _build_email_body(self, alert: Alert) -> str:
        """
        Build HTML email body.

        Args:
            alert: Alert to format

        Returns:
            HTML email body
        """
        color_map = {"info": "#17a2b8", "warning": "#ffc107", "error": "#dc3545", "critical": "#721c24"}

        color = color_map.get(alert.severity, "#6c757d")

        job_info = ""
        if alert.job_id:
            job = db.session.get(BackupJob, alert.job_id)
            if job:
                job_info = f"<p><strong>Job:</strong> {job.job_name}</p>"

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; padding: 20px; border-radius: 5px;
                            border-left: 5px solid {color};">
                    <h2 style="color: {color}; margin-top: 0;">
                        [{alert.severity.upper()}] {alert.title}
                    </h2>
                    {job_info}
                    <p>{alert.message}</p>
                    <hr style="border-color: #e0e0e0;">
                    <p style="color: #666; font-size: 12px;">
                        Alert ID: {alert.id}<br>
                        Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </body>
        </html>
        """

        return html

    def acknowledge_alert(self, alert_id: int, user_id: int) -> Alert:
        """
        Mark alert as acknowledged.

        Args:
            alert_id: Alert ID
            user_id: User acknowledging the alert

        Returns:
            Updated Alert object
        """
        try:
            alert = db.session.get(Alert, alert_id)
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")

            alert.is_acknowledged = True
            alert.acknowledged_by = user_id
            alert.acknowledged_at = datetime.now(timezone.utc)

            db.session.commit()

            logger.info(f"Alert {alert_id} acknowledged by user {user_id}")

            return alert

        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
            db.session.rollback()
            raise

    def get_unacknowledged_alerts(self, limit: int = 50) -> List[Alert]:
        """
        Get unacknowledged alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of Alert objects
        """
        try:
            alerts = Alert.query.filter_by(is_acknowledged=False).order_by(Alert.created_at.desc()).limit(limit).all()

            return alerts

        except Exception as e:
            logger.error(f"Error fetching unacknowledged alerts: {str(e)}")
            return []

    def get_alerts_by_job(self, job_id: int, days: int = 30, limit: int = 100) -> List[Alert]:
        """
        Get alerts for a specific job.

        Args:
            job_id: Backup job ID
            days: Look back this many days
            limit: Maximum number of alerts to return

        Returns:
            List of Alert objects
        """
        try:
            since_date = datetime.now(timezone.utc) - timedelta(days=days)

            alerts = (
                Alert.query.filter(Alert.job_id == job_id, Alert.created_at >= since_date)
                .order_by(Alert.created_at.desc())
                .limit(limit)
                .all()
            )

            return alerts

        except Exception as e:
            logger.error(f"Error fetching alerts for job {job_id}: {str(e)}")
            return []

    def get_alerts_by_type(self, alert_type: str, days: int = 30, limit: int = 100) -> List[Alert]:
        """
        Get alerts of a specific type.

        Args:
            alert_type: Alert type to filter by
            days: Look back this many days
            limit: Maximum number of alerts to return

        Returns:
            List of Alert objects
        """
        try:
            since_date = datetime.now(timezone.utc) - timedelta(days=days)

            alerts = (
                Alert.query.filter(Alert.alert_type == alert_type, Alert.created_at >= since_date)
                .order_by(Alert.created_at.desc())
                .limit(limit)
                .all()
            )

            return alerts

        except Exception as e:
            logger.error(f"Error fetching alerts of type {alert_type}: {str(e)}")
            return []

    def get_alerts_by_severity(self, severity: str, days: int = 30, limit: int = 100) -> List[Alert]:
        """
        Get alerts by severity level.

        Args:
            severity: Severity level (critical, warning, info)
            days: Look back this many days
            limit: Maximum number of alerts to return

        Returns:
            List of Alert objects
        """
        try:
            since_date = datetime.now(timezone.utc) - timedelta(days=days)

            alerts = (
                Alert.query.filter(Alert.severity == severity, Alert.created_at >= since_date)
                .order_by(Alert.created_at.desc())
                .limit(limit)
                .all()
            )

            return alerts

        except Exception as e:
            logger.error(f"Error fetching alerts with severity {severity}: {str(e)}")
            return []

    def bulk_acknowledge_alerts(self, alert_ids: List[int], user_id: int) -> bool:
        """
        Acknowledge multiple alerts at once.

        Args:
            alert_ids: List of alert IDs to acknowledge
            user_id: User ID acknowledging the alerts

        Returns:
            True if successful, False otherwise
        """
        try:
            for alert_id in alert_ids:
                self.acknowledge_alert(alert_id, user_id)

            return True

        except Exception as e:
            logger.error(f"Error bulk acknowledging alerts: {str(e)}")
            return False

    def create_compliance_alert(self, job_id: int, issues: List[str], notify: bool = True) -> Alert:
        """
        Create a compliance-specific alert.

        Args:
            job_id: Backup job ID
            issues: List of compliance issues
            notify: Whether to send notifications

        Returns:
            Created Alert object
        """
        try:
            message = "Compliance violations detected: " + ", ".join(issues)

            alert = self.create_alert(
                alert_type="compliance",
                severity="warning" if len(issues) <= 2 else "critical",
                title="3-2-1-1-0 Compliance Violation",
                message=message,
                job_id=job_id,
                notify=notify,
            )

            return alert

        except Exception as e:
            logger.error(f"Error creating compliance alert: {str(e)}")
            raise

    def create_failure_alert(self, job_id: int, error_message: str, notify: bool = True) -> Alert:
        """
        Create a backup failure alert.

        Args:
            job_id: Backup job ID
            error_message: Error message
            notify: Whether to send notifications

        Returns:
            Created Alert object
        """
        try:
            alert = self.create_alert(
                alert_type="failure",
                severity="critical",
                title="Backup Failed",
                message=f"Backup failed with error: {error_message}",
                job_id=job_id,
                notify=notify,
            )

            return alert

        except Exception as e:
            logger.error(f"Error creating failure alert: {str(e)}")
            raise

    def send_notification(self, alert_id: int) -> Dict[str, bool]:
        """
        Send notification for a specific alert.

        Args:
            alert_id: Alert ID

        Returns:
            Dictionary of notification results
        """
        try:
            alert = db.session.get(Alert, alert_id)
            if not alert:
                return {}

            return self.send_notifications(alert)

        except Exception as e:
            logger.error(f"Error sending notification for alert {alert_id}: {str(e)}")
            return {}

    def clear_old_alerts(self, days: int = 90) -> int:
        """
        Delete acknowledged alerts older than specified days.

        Args:
            days: Delete alerts older than this many days

        Returns:
            Number of deleted alerts
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            count = Alert.query.filter(Alert.is_acknowledged == True, Alert.acknowledged_at < cutoff_date).delete()

            db.session.commit()

            logger.info(f"Cleared {count} old acknowledged alerts")

            return count

        except Exception as e:
            logger.error(f"Error clearing old alerts: {str(e)}")
            db.session.rollback()
            return 0
