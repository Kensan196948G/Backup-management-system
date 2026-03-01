"""
Notification Service

Multi-channel notification orchestrator and email notification service.

Orchestrates notifications across multiple channels (Email, Teams, Dashboard).
Manages channel priorities, fallback strategies, and delivery tracking.

Features:
- Multi-channel notification support (Email, Teams, Dashboard)
- Channel prioritization by severity
- SMTP configuration management
- HTML email templates with Jinja2
- Async email sending support
- Rate limiting per recipient
- Email delivery tracking
- Retry on failure
- Support for multiple notification types
"""

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from flask import current_app, render_template
from jinja2 import Environment, FileSystemLoader, Template

from app.config import Config
from app.models import db

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification delivery channels"""

    DASHBOARD = "dashboard"  # Database/UI alerts
    EMAIL = "email"  # Email notifications
    TEAMS = "teams"  # Microsoft Teams
    SMS = "sms"  # SMS (future)
    SLACK = "slack"  # Slack (future)


class EmailNotificationService:
    """
    Email notification service with template support and delivery tracking.

    Responsibilities:
    - Send HTML/plain text emails
    - Track email delivery status
    - Apply rate limiting
    - Retry failed deliveries
    - Validate recipients
    """

    def __init__(self):
        """Initialize email notification service"""
        self.smtp_server = Config.MAIL_SERVER
        self.smtp_port = Config.MAIL_PORT
        self.use_tls = Config.MAIL_USE_TLS
        self.username = Config.MAIL_USERNAME
        self.password = Config.MAIL_PASSWORD
        self.default_sender = Config.MAIL_DEFAULT_SENDER

        # Rate limiting: max emails per recipient per hour
        self.rate_limit_max = 10
        self.rate_limit_window = 3600  # seconds

        # Email delivery tracking
        self.delivery_history: Dict[str, List[datetime]] = {}

        # Template directory
        self.template_dir = Path(__file__).parent.parent / "templates" / "email"

        # Initialize Jinja2 environment
        self.jinja_env = None
        if self.template_dir.exists():
            self.jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)), autoescape=True)

    def is_configured(self) -> bool:
        """
        Check if email service is properly configured.

        Returns:
            True if SMTP settings are configured
        """
        return bool(self.smtp_server and self.username and self.password)

    def validate_email(self, email: str) -> bool:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            True if valid
        """
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def check_rate_limit(self, recipient: str) -> bool:
        """
        Check if recipient has exceeded rate limit.

        Args:
            recipient: Email address to check

        Returns:
            True if rate limit not exceeded
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.rate_limit_window)

        # Clean old entries
        if recipient in self.delivery_history:
            self.delivery_history[recipient] = [ts for ts in self.delivery_history[recipient] if ts > cutoff]

            # Check limit
            if len(self.delivery_history[recipient]) >= self.rate_limit_max:
                logger.warning(f"Rate limit exceeded for {recipient}")
                return False

        return True

    def record_delivery(self, recipient: str):
        """
        Record email delivery for rate limiting.

        Args:
            recipient: Email address
        """
        now = datetime.now(timezone.utc)
        if recipient not in self.delivery_history:
            self.delivery_history[recipient] = []

        self.delivery_history[recipient].append(now)

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None,
        retry_count: int = 3,
        **kwargs,
    ) -> bool:
        """
        Send HTML email with optional plain text fallback.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            plain_body: Plain text fallback (optional)
            retry_count: Number of retry attempts on failure
            **kwargs: Additional parameters

        Returns:
            True if sent successfully
        """
        # Validation
        if not self.is_configured():
            logger.error("Email service not configured")
            return False

        if not self.validate_email(to):
            logger.error(f"Invalid email address: {to}")
            return False

        # Rate limiting
        if not self.check_rate_limit(to):
            logger.warning(f"Rate limit exceeded for {to}, email not sent")
            return False

        # Build message
        msg = MIMEMultipart("alternative")
        msg["From"] = self.default_sender
        msg["To"] = to
        msg["Subject"] = subject

        # Attach plain text if provided
        if plain_body:
            msg.attach(MIMEText(plain_body, "plain"))

        # Attach HTML
        msg.attach(MIMEText(html_body, "html"))

        # Send with retry
        for attempt in range(retry_count):
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()

                    if self.username and self.password:
                        server.login(self.username, self.password)

                    server.send_message(msg)

                logger.info(f"Email sent successfully to {to}: {subject}")
                self.record_delivery(to)
                return True

            except Exception as e:
                logger.error(f"Failed to send email (attempt {attempt + 1}/{retry_count}): {str(e)}", exc_info=True)

                if attempt < retry_count - 1:
                    import time

                    time.sleep(2**attempt)  # Exponential backoff

        return False

    def send_template_email(self, to: str, subject: str, template_name: str, context: Dict, retry_count: int = 3) -> bool:
        """
        Send email using Jinja2 template.

        Args:
            to: Recipient email address
            subject: Email subject
            template_name: Template filename (e.g., 'backup_success.html')
            context: Template context variables
            retry_count: Number of retry attempts

        Returns:
            True if sent successfully
        """
        if not self.jinja_env:
            logger.error("Template environment not initialized")
            return False

        try:
            # Render template
            template = self.jinja_env.get_template(template_name)
            html_body = template.render(**context)

            # Send email
            return self.send_email(to=to, subject=subject, html_body=html_body, retry_count=retry_count)

        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {str(e)}", exc_info=True)
            return False

    def send_backup_success_notification(self, job_name: str, recipients: List[str], **details) -> Dict[str, bool]:
        """
        Send backup success notification.

        Args:
            job_name: Backup job name
            recipients: List of email addresses
            **details: Additional job details (size, duration, etc.)

        Returns:
            Dictionary mapping recipients to success status
        """
        subject = f"Backup Success: {job_name}"
        context = {"job_name": job_name, "timestamp": datetime.now(timezone.utc), "details": details}

        results = {}
        for recipient in recipients:
            results[recipient] = self.send_template_email(
                to=recipient, subject=subject, template_name="backup_success.html", context=context
            )

        return results

    def send_backup_failure_notification(
        self, job_name: str, recipients: List[str], error_message: str, **details
    ) -> Dict[str, bool]:
        """
        Send backup failure notification.

        Args:
            job_name: Backup job name
            recipients: List of email addresses
            error_message: Error message
            **details: Additional failure details

        Returns:
            Dictionary mapping recipients to success status
        """
        subject = f"[CRITICAL] Backup Failed: {job_name}"
        context = {
            "job_name": job_name,
            "timestamp": datetime.now(timezone.utc),
            "error_message": error_message,
            "details": details,
        }

        results = {}
        for recipient in recipients:
            results[recipient] = self.send_template_email(
                to=recipient, subject=subject, template_name="backup_failure.html", context=context
            )

        return results

    def send_rule_violation_notification(
        self, job_name: str, recipients: List[str], violations: List[str], **details
    ) -> Dict[str, bool]:
        """
        Send 3-2-1-1-0 rule violation notification.

        Args:
            job_name: Backup job name
            recipients: List of email addresses
            violations: List of rule violations
            **details: Additional compliance details

        Returns:
            Dictionary mapping recipients to success status
        """
        subject = f"[WARNING] 3-2-1-1-0 Rule Violation: {job_name}"
        context = {
            "job_name": job_name,
            "timestamp": datetime.now(timezone.utc),
            "violations": violations,
            "details": details,
        }

        results = {}
        for recipient in recipients:
            results[recipient] = self.send_template_email(
                to=recipient, subject=subject, template_name="rule_violation.html", context=context
            )

        return results

    def send_media_reminder_notification(
        self, media_id: str, recipients: List[str], reminder_type: str, **details
    ) -> Dict[str, bool]:
        """
        Send offline media reminder (rotation, return, verification).

        Args:
            media_id: Media identifier
            recipients: List of email addresses
            reminder_type: Type of reminder (rotation, return, verification)
            **details: Additional media details

        Returns:
            Dictionary mapping recipients to success status
        """
        subject = f"Media Reminder: {reminder_type.title()} - {media_id}"
        context = {
            "media_id": media_id,
            "reminder_type": reminder_type,
            "timestamp": datetime.now(timezone.utc),
            "details": details,
        }

        results = {}
        for recipient in recipients:
            results[recipient] = self.send_template_email(
                to=recipient, subject=subject, template_name="media_reminder.html", context=context
            )

        return results

    def send_daily_report(self, recipients: List[str], report_data: Dict) -> Dict[str, bool]:
        """
        Send daily compliance report.

        Args:
            recipients: List of email addresses
            report_data: Report data dictionary

        Returns:
            Dictionary mapping recipients to success status
        """
        subject = f"Daily Backup Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        context = {"report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "data": report_data}

        results = {}
        for recipient in recipients:
            results[recipient] = self.send_template_email(
                to=recipient, subject=subject, template_name="daily_report.html", context=context
            )

        return results

    def send_bulk_notification(
        self, recipients: List[str], subject: str, template_name: str, context: Dict
    ) -> Dict[str, bool]:
        """
        Send bulk notification to multiple recipients.

        Args:
            recipients: List of email addresses
            subject: Email subject
            template_name: Template filename
            context: Template context

        Returns:
            Dictionary mapping recipients to success status
        """
        results = {}
        for recipient in recipients:
            results[recipient] = self.send_template_email(
                to=recipient, subject=subject, template_name=template_name, context=context
            )

        return results


class MultiChannelNotificationOrchestrator:
    """
    Multi-channel notification orchestrator.

    Features:
    - Channel prioritization
    - Automatic fallback
    - Delivery tracking
    - Channel health monitoring
    - Rate limiting per channel
    """

    # Channel priority by severity
    CHANNEL_PRIORITY = {
        "critical": [NotificationChannel.TEAMS, NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
        "error": [NotificationChannel.TEAMS, NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
        "warning": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
        "info": [NotificationChannel.DASHBOARD],
    }

    def __init__(self):
        """Initialize notification orchestrator"""
        self.teams_service = None  # Lazy load
        self.email_service = None  # Lazy load
        self._delivery_stats: Dict[str, Dict] = {}

    def send_notification(
        self,
        title: str,
        message: str,
        severity: str = "info",
        channels: Optional[List[NotificationChannel]] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, bool]:
        """
        Send notification via specified channels.

        Args:
            title: Notification title
            message: Notification message
            severity: Severity level (info/warning/error/critical)
            channels: Override channel list (defaults to severity-based)
            metadata: Additional metadata for specific channels

        Returns:
            Dictionary of channel: success status
        """
        # Determine channels
        target_channels = channels or self._get_channels_for_severity(severity)

        results = {}
        metadata = metadata or {}

        # Send to each channel
        for channel in target_channels:
            try:
                success = self._send_to_channel(
                    channel=channel, title=title, message=message, severity=severity, metadata=metadata
                )
                results[channel.value] = success

                # Track statistics
                self._track_delivery(channel=channel.value, success=success, severity=severity)

            except Exception as e:
                logger.error(f"Failed to send notification via {channel.value}: {str(e)}")
                results[channel.value] = False
                self._track_delivery(channel=channel.value, success=False, severity=severity)

        return results

    def _get_channels_for_severity(self, severity: str) -> List[NotificationChannel]:
        """
        Get notification channels for severity level.

        Args:
            severity: Severity level

        Returns:
            List of notification channels
        """
        return self.CHANNEL_PRIORITY.get(severity, [NotificationChannel.DASHBOARD])

    def _send_to_channel(self, channel: NotificationChannel, title: str, message: str, severity: str, metadata: Dict) -> bool:
        """
        Send notification to specific channel.

        Args:
            channel: Target channel
            title: Notification title
            message: Notification message
            severity: Severity level
            metadata: Additional metadata

        Returns:
            True if successful
        """
        if channel == NotificationChannel.DASHBOARD:
            return self._send_to_dashboard(title, message, severity, metadata)

        elif channel == NotificationChannel.EMAIL:
            return self._send_to_email(title, message, severity, metadata)

        elif channel == NotificationChannel.TEAMS:
            return self._send_to_teams(title, message, severity, metadata)

        else:
            logger.warning(f"Unsupported notification channel: {channel.value}")
            return False

    def _send_to_dashboard(self, title: str, message: str, severity: str, metadata: Dict) -> bool:
        """
        Send notification to dashboard (database).

        Args:
            title: Notification title
            message: Notification message
            severity: Severity level
            metadata: Additional metadata

        Returns:
            True if successful
        """
        # Dashboard notifications are always successful as they're just DB records
        # This is handled by AlertManager.create_alert()
        logger.debug(f"Dashboard notification: {title}")
        return True

    def _send_to_email(self, title: str, message: str, severity: str, metadata: Dict) -> bool:
        """
        Send email notification.

        Args:
            title: Email subject
            message: Email body
            severity: Severity level
            metadata: Additional metadata (recipients, etc.)

        Returns:
            True if successful
        """
        # Check if email is configured
        if not Config.MAIL_SERVER or not Config.MAIL_USERNAME:
            logger.debug("Email not configured, skipping")
            return False

        try:
            # Lazy load email service
            if self.email_service is None:
                self.email_service = EmailNotificationService()

            # Get recipients
            recipients = metadata.get("recipients", [])
            if not recipients:
                logger.warning("No email recipients specified")
                return False

            # Build email
            subject = f"[{severity.upper()}] {title}"
            html_body = self._build_email_html(title, message, severity, metadata)

            # Send to each recipient
            success = True
            for recipient in recipients:
                try:
                    result = self.email_service.send_email(to=recipient, subject=subject, html_body=html_body)
                    if not result:
                        success = False
                except Exception as e:
                    logger.error(f"Failed to send email to {recipient}: {str(e)}")
                    success = False

            return success

        except Exception as e:
            logger.error(f"Email notification failed: {str(e)}")
            return False

    def _send_to_teams(self, title: str, message: str, severity: str, metadata: Dict) -> bool:
        """
        Send Microsoft Teams notification.

        Args:
            title: Notification title
            message: Notification message
            severity: Severity level
            metadata: Additional metadata

        Returns:
            True if successful
        """
        # Check if Teams is configured
        if not Config.TEAMS_WEBHOOK_URL:
            logger.debug("Teams webhook not configured, skipping")
            return False

        try:
            # Lazy load Teams service
            if self.teams_service is None:
                from app.services.teams_notification_service import (
                    TeamsNotificationService,
                )

                self.teams_service = TeamsNotificationService()

            # Extract metadata
            alert_type = metadata.get("alert_type", "general")
            alert_id = metadata.get("alert_id")
            job_name = metadata.get("job_name")
            created_at = metadata.get("created_at")

            # Send alert card
            return self.teams_service.send_alert_card(
                title=title,
                message=message,
                severity=severity,
                alert_type=alert_type,
                alert_id=alert_id,
                job_name=job_name,
                created_at=created_at,
            )

        except Exception as e:
            logger.error(f"Teams notification failed: {str(e)}")
            return False

    def _build_email_html(self, title: str, message: str, severity: str, metadata: Dict) -> str:
        """
        Build HTML email body.

        Args:
            title: Email title
            message: Email message
            severity: Severity level
            metadata: Additional metadata

        Returns:
            HTML email body
        """
        color_map = {"info": "#17a2b8", "warning": "#ffc107", "error": "#dc3545", "critical": "#721c24"}

        color = color_map.get(severity, "#6c757d")

        # Build metadata section
        meta_html = ""
        if metadata:
            meta_items = []
            for key, value in metadata.items():
                if key not in ["recipients"]:  # Skip internal keys
                    meta_items.append(f"<strong>{key.replace('_', ' ').title()}:</strong> {value}")

            if meta_items:
                meta_html = "<p>" + "<br>".join(meta_items) + "</p>"

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; padding: 20px; border-radius: 5px;
                            border-left: 5px solid {color}; max-width: 600px;">
                    <h2 style="color: {color}; margin-top: 0;">
                        {title}
                    </h2>
                    <p style="font-size: 14px; line-height: 1.6; color: #333;">
                        {message}
                    </p>
                    {meta_html}
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                    <p style="color: #666; font-size: 12px; margin-bottom: 0;">
                        Backup Management System<br>
                        {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                    </p>
                </div>
            </body>
        </html>
        """

        return html

    def _track_delivery(self, channel: str, success: bool, severity: str):
        """
        Track notification delivery statistics.

        Args:
            channel: Delivery channel
            success: Whether delivery was successful
            severity: Severity level
        """
        if channel not in self._delivery_stats:
            self._delivery_stats[channel] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "by_severity": {},
            }

        stats = self._delivery_stats[channel]
        stats["total"] += 1

        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1

        # Track by severity
        if severity not in stats["by_severity"]:
            stats["by_severity"][severity] = {"total": 0, "successful": 0, "failed": 0}

        stats["by_severity"][severity]["total"] += 1
        if success:
            stats["by_severity"][severity]["successful"] += 1
        else:
            stats["by_severity"][severity]["failed"] += 1

    def get_channel_statistics(self) -> Dict[str, Dict]:
        """
        Get notification statistics by channel.

        Returns:
            Dictionary of channel statistics
        """
        return self._delivery_stats.copy()

    def get_channel_health(self) -> Dict[str, str]:
        """
        Get health status of each channel.

        Returns:
            Dictionary of channel: health status
        """
        health = {}

        for channel, stats in self._delivery_stats.items():
            if stats["total"] == 0:
                health[channel] = "unknown"
            else:
                success_rate = stats["successful"] / stats["total"]
                if success_rate >= 0.95:
                    health[channel] = "healthy"
                elif success_rate >= 0.80:
                    health[channel] = "degraded"
                else:
                    health[channel] = "unhealthy"

        # Check configured channels
        if Config.TEAMS_WEBHOOK_URL and NotificationChannel.TEAMS.value not in health:
            health[NotificationChannel.TEAMS.value] = "unknown"

        if Config.MAIL_SERVER and NotificationChannel.EMAIL.value not in health:
            health[NotificationChannel.EMAIL.value] = "unknown"

        health[NotificationChannel.DASHBOARD.value] = "healthy"  # Always healthy

        return health

    def test_all_channels(self) -> Dict[str, bool]:
        """
        Test connectivity to all configured channels.

        Returns:
            Dictionary of channel: test result
        """
        results = {}

        # Test Dashboard (always works)
        results[NotificationChannel.DASHBOARD.value] = True

        # Test Email
        if Config.MAIL_SERVER and Config.MAIL_USERNAME:
            try:
                if self.email_service is None:
                    self.email_service = EmailNotificationService()

                # Send to configured sender (self-test)
                test_result = self.email_service.send_email(
                    to=Config.MAIL_USERNAME,
                    subject="[TEST] Backup Management System - Email Test",
                    html_body="<p>This is a test email from Backup Management System.</p>",
                )
                results[NotificationChannel.EMAIL.value] = test_result
            except Exception as e:
                logger.error(f"Email test failed: {str(e)}")
                results[NotificationChannel.EMAIL.value] = False
        else:
            logger.info("Email not configured, skipping test")

        # Test Teams
        if Config.TEAMS_WEBHOOK_URL:
            try:
                if self.teams_service is None:
                    from app.services.teams_notification_service import (
                        TeamsNotificationService,
                    )

                    self.teams_service = TeamsNotificationService()

                results[NotificationChannel.TEAMS.value] = self.teams_service.test_connection()
            except Exception as e:
                logger.error(f"Teams test failed: {str(e)}")
                results[NotificationChannel.TEAMS.value] = False
        else:
            logger.info("Teams webhook not configured, skipping test")

        return results


# Global service instances (lazy initialization)
_email_service: Optional[EmailNotificationService] = None
_notification_orchestrator: Optional[MultiChannelNotificationOrchestrator] = None


def get_email_service() -> EmailNotificationService:
    """
    Get global email service instance.

    Returns:
        EmailNotificationService instance
    """
    global _email_service
    if _email_service is None:
        _email_service = EmailNotificationService()
    return _email_service


def get_notification_service() -> EmailNotificationService:
    """
    Get global email service instance (backward compatibility).

    Returns:
        EmailNotificationService instance
    """
    return get_email_service()


def get_notification_orchestrator() -> MultiChannelNotificationOrchestrator:
    """
    Get global multi-channel notification orchestrator.

    Returns:
        MultiChannelNotificationOrchestrator instance
    """
    global _notification_orchestrator
    if _notification_orchestrator is None:
        _notification_orchestrator = MultiChannelNotificationOrchestrator()
    return _notification_orchestrator
