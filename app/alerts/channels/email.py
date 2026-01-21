"""
Email Notification Channel
Sends notifications via SMTP email with HTML templates
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from app.config import Config
from app.models import Alert, NotificationLog, db

logger = logging.getLogger(__name__)


class EmailChannel:
    """
    Email notification channel using SMTP
    Supports HTML templates and batch sending
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize email channel with configuration"""
        self.config = config or Config()
        self.mail_server = self.config.MAIL_SERVER
        self.mail_port = self.config.MAIL_PORT
        self.mail_use_tls = self.config.MAIL_USE_TLS
        self.mail_username = self.config.MAIL_USERNAME
        self.mail_password = self.config.MAIL_PASSWORD
        self.mail_sender = self.config.MAIL_DEFAULT_SENDER

    def send_alert(self, alert: Alert, recipients: List[str], include_html: bool = True) -> bool:
        """
        Send alert notification via email

        Args:
            alert: Alert object to send
            recipients: List of email addresses
            include_html: Whether to include HTML formatted email

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Generate email content
            subject = self._generate_subject(alert)
            text_body = self._generate_text_body(alert)
            html_body = self._generate_html_body(alert) if include_html else None

            # Send to all recipients
            success = self._send_email(
                recipients=recipients,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )

            # Log notification
            self._log_notification(
                alert=alert,
                recipients=recipients,
                subject=subject,
                success=success,
            )

            return success

        except Exception as e:
            logger.error(f"Error sending alert email: {e}", exc_info=True)
            self._log_notification(
                alert=alert,
                recipients=recipients,
                subject=f"Alert {alert.id}",
                success=False,
                error_message=str(e),
            )
            return False

    def send_batch_alerts(self, alerts: List[Alert], recipients: List[str], include_html: bool = True) -> bool:
        """
        Send multiple alerts in a single digest email

        Args:
            alerts: List of Alert objects
            recipients: List of email addresses
            include_html: Whether to include HTML formatted email

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not alerts:
                logger.warning("No alerts to send in batch")
                return False

            # Generate digest email content
            subject = self._generate_digest_subject(alerts)
            text_body = self._generate_digest_text_body(alerts)
            html_body = self._generate_digest_html_body(alerts) if include_html else None

            # Send email
            success = self._send_email(
                recipients=recipients,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )

            # Log notifications for all alerts
            for alert in alerts:
                self._log_notification(
                    alert=alert,
                    recipients=recipients,
                    subject=subject,
                    success=success,
                )

            return success

        except Exception as e:
            logger.error(f"Error sending batch alert email: {e}", exc_info=True)
            return False

    def send_report(
        self,
        report_title: str,
        report_content: str,
        recipients: List[str],
        attachment_path: Optional[str] = None,
    ) -> bool:
        """
        Send report notification via email

        Args:
            report_title: Title of the report
            report_content: Report summary/content
            recipients: List of email addresses
            attachment_path: Optional path to report file

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            subject = f"Backup Report: {report_title}"
            text_body = f"Report Generated: {report_title}\n\n{report_content}"
            html_body = self._generate_report_html(report_title, report_content)

            success = self._send_email(
                recipients=recipients,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )

            return success

        except Exception as e:
            logger.error(f"Error sending report email: {e}", exc_info=True)
            return False

    def _send_email(
        self,
        recipients: List[str],
        subject: str,
        text_body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """
        Send email using SMTP

        Args:
            recipients: List of email addresses
            subject: Email subject
            text_body: Plain text body
            html_body: Optional HTML body

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.mail_sender
            msg["To"] = ", ".join(recipients)
            msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

            # Attach text body
            msg.attach(MIMEText(text_body, "plain", "utf-8"))

            # Attach HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))

            # Connect to SMTP server and send
            with smtplib.SMTP(self.mail_server, self.mail_port) as server:
                if self.mail_use_tls:
                    server.starttls()

                if self.mail_username and self.mail_password:
                    server.login(self.mail_username, self.mail_password)

                server.send_message(msg)

            logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}", exc_info=True)
            return False

    def _generate_subject(self, alert: Alert) -> str:
        """Generate email subject from alert"""
        severity_prefix = {
            "info": "[INFO]",
            "warning": "[WARNING]",
            "error": "[ERROR]",
            "critical": "[CRITICAL]",
        }
        prefix = severity_prefix.get(alert.severity, "")
        return f"{prefix} {alert.title}"

    def _generate_text_body(self, alert: Alert) -> str:
        """Generate plain text email body from alert"""
        body = f"""
Backup Management System Alert

Severity: {alert.severity.upper()}
Alert Type: {alert.alert_type}
Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

{alert.title}

{alert.message}

{'Job ID: ' + str(alert.job_id) if alert.job_id else ''}

---
This is an automated notification from Backup Management System.
"""
        return body.strip()

    def _generate_html_body(self, alert: Alert) -> str:
        """Generate HTML email body from alert"""
        severity_colors = {
            "info": "#17a2b8",
            "warning": "#ffc107",
            "error": "#dc3545",
            "critical": "#721c24",
        }
        color = severity_colors.get(alert.severity, "#6c757d")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .footer {{ background-color: #e9ecef; padding: 10px; text-align: center; font-size: 12px; color: #6c757d; border-radius: 0 0 5px 5px; }}
        .badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
        .info {{ background-color: #d1ecf1; color: #0c5460; }}
        .warning {{ background-color: #fff3cd; color: #856404; }}
        .error {{ background-color: #f8d7da; color: #721c24; }}
        .critical {{ background-color: #721c24; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Backup Management System Alert</h2>
        </div>
        <div class="content">
            <p><strong>Severity:</strong> <span class="badge {alert.severity}">{alert.severity.upper()}</span></p>
            <p><strong>Alert Type:</strong> {alert.alert_type}</p>
            <p><strong>Time:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <h3>{alert.title}</h3>
            <p>{alert.message}</p>
            {f'<p><strong>Job ID:</strong> {alert.job_id}</p>' if alert.job_id else ''}
        </div>
        <div class="footer">
            <p>This is an automated notification from Backup Management System.</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_digest_subject(self, alerts: List[Alert]) -> str:
        """Generate subject for digest email"""
        critical_count = sum(1 for a in alerts if a.severity == "critical")
        error_count = sum(1 for a in alerts if a.severity == "error")
        warning_count = sum(1 for a in alerts if a.severity == "warning")

        if critical_count > 0:
            return f"[CRITICAL] Backup Alert Digest: {len(alerts)} alerts ({critical_count} critical)"
        elif error_count > 0:
            return f"[ERROR] Backup Alert Digest: {len(alerts)} alerts ({error_count} errors)"
        else:
            return f"[WARNING] Backup Alert Digest: {len(alerts)} alerts"

    def _generate_digest_text_body(self, alerts: List[Alert]) -> str:
        """Generate plain text body for digest email"""
        body = f"""
Backup Management System Alert Digest

Total Alerts: {len(alerts)}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        for i, alert in enumerate(alerts, 1):
            body += f"""
Alert #{i}
Severity: {alert.severity.upper()}
Type: {alert.alert_type}
Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Title: {alert.title}
Message: {alert.message}

"""

        body += """
---
This is an automated notification from Backup Management System.
"""
        return body.strip()

    def _generate_digest_html_body(self, alerts: List[Alert]) -> str:
        """Generate HTML body for digest email"""
        alert_items = ""
        for alert in alerts:
            severity_class = alert.severity
            alert_items += f"""
            <div style="margin-bottom: 15px; padding: 10px; border-left: 4px solid #dee2e6; background-color: white;">
                <p><span class="badge {severity_class}">{alert.severity.upper()}</span> <strong>{alert.title}</strong></p>
                <p style="font-size: 14px; color: #6c757d;">{alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>{alert.message}</p>
            </div>
"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #343a40; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .footer {{ background-color: #e9ecef; padding: 10px; text-align: center; font-size: 12px; color: #6c757d; border-radius: 0 0 5px 5px; }}
        .badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
        .info {{ background-color: #d1ecf1; color: #0c5460; }}
        .warning {{ background-color: #fff3cd; color: #856404; }}
        .error {{ background-color: #f8d7da; color: #721c24; }}
        .critical {{ background-color: #721c24; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Backup Alert Digest</h2>
            <p>Total Alerts: {len(alerts)}</p>
        </div>
        <div class="content">
            <p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            {alert_items}
        </div>
        <div class="footer">
            <p>This is an automated notification from Backup Management System.</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_report_html(self, title: str, content: str) -> str:
        """Generate HTML body for report email"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #007bff; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .footer {{ background-color: #e9ecef; padding: 10px; text-align: center; font-size: 12px; color: #6c757d; border-radius: 0 0 5px 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Backup Report</h2>
        </div>
        <div class="content">
            <h3>{title}</h3>
            <p>{content}</p>
        </div>
        <div class="footer">
            <p>Generated by Backup Management System</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _log_notification(
        self,
        alert: Alert,
        recipients: List[str],
        subject: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Log notification attempt to database"""
        try:
            for recipient in recipients:
                log = NotificationLog(
                    notification_type="email",
                    channel="smtp",
                    recipient=recipient,
                    subject=subject,
                    message=alert.message,
                    severity=alert.severity,
                    status="sent" if success else "failed",
                    error_message=error_message,
                    alert_id=alert.id,
                    job_id=alert.job_id,
                )
                db.session.add(log)

            db.session.commit()

        except Exception as e:
            logger.error(f"Error logging notification: {e}", exc_info=True)
            db.session.rollback()

    def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            with smtplib.SMTP(self.mail_server, self.mail_port, timeout=10) as server:
                if self.mail_use_tls:
                    server.starttls()

                if self.mail_username and self.mail_password:
                    server.login(self.mail_username, self.mail_password)

            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}", exc_info=True)
            return False
