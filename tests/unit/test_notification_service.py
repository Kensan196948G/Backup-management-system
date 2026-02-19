"""
Unit tests for Email Notification Service

Tests cover:
- Email validation
- Rate limiting
- Template rendering
- SMTP sending (mocked)
- Various notification types
"""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from app.services.notification_service import (
    EmailNotificationService,
    get_notification_service,
)


class TestEmailNotificationService(unittest.TestCase):
    """Test cases for EmailNotificationService"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = EmailNotificationService()

    def test_email_validation(self):
        """Test email address validation"""
        # Valid emails
        self.assertTrue(self.service.validate_email("test@example.com"))
        self.assertTrue(self.service.validate_email("user.name+tag@example.co.uk"))
        self.assertTrue(self.service.validate_email("admin123@test-domain.com"))

        # Invalid emails
        self.assertFalse(self.service.validate_email("invalid"))
        self.assertFalse(self.service.validate_email("@example.com"))
        self.assertFalse(self.service.validate_email("user@"))
        self.assertFalse(self.service.validate_email(""))

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        recipient = "test@example.com"

        # First check should pass
        self.assertTrue(self.service.check_rate_limit(recipient))

        # Simulate sending emails up to the limit
        for _ in range(self.service.rate_limit_max):
            self.service.record_delivery(recipient)

        # Should now be rate limited
        self.assertFalse(self.service.check_rate_limit(recipient))

        # Clear old entries (simulate time passing)
        cutoff = datetime.utcnow() - timedelta(seconds=self.service.rate_limit_window + 1)
        self.service.delivery_history[recipient] = [cutoff for _ in range(5)]

        # Should now pass again
        self.assertTrue(self.service.check_rate_limit(recipient))

    def test_is_configured(self):
        """Test configuration check"""
        # With default (unconfigured) values
        service = EmailNotificationService()
        # Should be False if MAIL_SERVER is localhost and no credentials
        self.assertFalse(service.is_configured())

        # With configured values
        service.smtp_server = "smtp.gmail.com"
        service.username = "test@example.com"
        service.password = "password123"
        self.assertTrue(service.is_configured())

    @patch("smtplib.SMTP")
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        # Mock SMTP connection
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Send email
        result = self.service.send_email(to="recipient@example.com", subject="Test Subject", html_body="<h1>Test</h1>")

        # Verify success
        self.assertTrue(result)
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_email_with_retry(self, mock_smtp):
        """Test email retry on failure"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        # Mock SMTP to fail twice then succeed
        mock_server = MagicMock()
        mock_server.send_message.side_effect = [Exception("Network error"), Exception("Network error"), None]
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Send email with 3 retries
        result = self.service.send_email(to="recipient@example.com", subject="Test", html_body="<h1>Test</h1>", retry_count=3)

        # Should succeed on third attempt
        self.assertTrue(result)
        self.assertEqual(mock_server.send_message.call_count, 3)

    def test_send_email_invalid_recipient(self):
        """Test email sending with invalid recipient"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        # Try to send to invalid email
        result = self.service.send_email(to="invalid-email", subject="Test", html_body="<h1>Test</h1>")

        # Should fail
        self.assertFalse(result)

    def test_send_email_rate_limited(self):
        """Test email sending when rate limited"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        recipient = "test@example.com"

        # Exceed rate limit
        for _ in range(self.service.rate_limit_max):
            self.service.record_delivery(recipient)

        # Try to send email
        result = self.service.send_email(to=recipient, subject="Test", html_body="<h1>Test</h1>")

        # Should fail due to rate limiting
        self.assertFalse(result)

    @patch("smtplib.SMTP")
    def test_send_backup_success_notification(self, mock_smtp):
        """Test backup success notification"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Mock template environment
        self.service.jinja_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Backup Success</h1>"
        self.service.jinja_env.get_template.return_value = mock_template

        # Send notification
        results = self.service.send_backup_success_notification(
            job_name="Test Job", recipients=["admin@example.com"], backup_size_bytes=1000000, duration_seconds=120
        )

        # Verify
        self.assertIn("admin@example.com", results)
        self.assertTrue(results["admin@example.com"])

    @patch("smtplib.SMTP")
    def test_send_backup_failure_notification(self, mock_smtp):
        """Test backup failure notification"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Mock template environment
        self.service.jinja_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Backup Failed</h1>"
        self.service.jinja_env.get_template.return_value = mock_template

        # Send notification
        results = self.service.send_backup_failure_notification(
            job_name="Test Job", recipients=["admin@example.com"], error_message="Disk full"
        )

        # Verify
        self.assertIn("admin@example.com", results)
        self.assertTrue(results["admin@example.com"])

    @patch("smtplib.SMTP")
    def test_send_rule_violation_notification(self, mock_smtp):
        """Test 3-2-1-1-0 rule violation notification"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Mock template environment
        self.service.jinja_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Rule Violation</h1>"
        self.service.jinja_env.get_template.return_value = mock_template

        # Send notification
        violations = ["Missing offsite copy", "No offline backup"]
        results = self.service.send_rule_violation_notification(
            job_name="Test Job", recipients=["admin@example.com"], violations=violations
        )

        # Verify
        self.assertIn("admin@example.com", results)
        self.assertTrue(results["admin@example.com"])

    @patch("smtplib.SMTP")
    def test_send_media_reminder_notification(self, mock_smtp):
        """Test media reminder notification"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Mock template environment
        self.service.jinja_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Media Reminder</h1>"
        self.service.jinja_env.get_template.return_value = mock_template

        # Send notification
        results = self.service.send_media_reminder_notification(
            media_id="TAPE-001",
            recipients=["admin@example.com"],
            reminder_type="rotation",
            next_rotation_date="2025-11-01",
        )

        # Verify
        self.assertIn("admin@example.com", results)
        self.assertTrue(results["admin@example.com"])

    @patch("smtplib.SMTP")
    def test_send_daily_report(self, mock_smtp):
        """Test daily report notification"""
        # Configure service
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Mock template environment
        self.service.jinja_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Daily Report</h1>"
        self.service.jinja_env.get_template.return_value = mock_template

        # Send report
        report_data = {
            "total_jobs": 10,
            "successful_backups": 8,
            "failed_backups": 2,
            "system_health": "warning",
        }

        results = self.service.send_daily_report(recipients=["admin@example.com"], report_data=report_data)

        # Verify
        self.assertIn("admin@example.com", results)
        self.assertTrue(results["admin@example.com"])

    def test_get_notification_service_singleton(self):
        """Test that get_notification_service returns singleton instance"""
        service1 = get_notification_service()
        service2 = get_notification_service()

        # Should be the same instance
        self.assertIs(service1, service2)


class TestEmailTemplates(unittest.TestCase):
    """Test email template rendering"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = EmailNotificationService()

    def test_template_directory_exists(self):
        """Test that template directory exists"""
        template_dir = Path(__file__).parent.parent.parent / "app" / "templates" / "email"
        self.assertTrue(template_dir.exists(), f"Template directory not found: {template_dir}")

    def test_base_template_exists(self):
        """Test that base template exists"""
        template_dir = Path(__file__).parent.parent.parent / "app" / "templates" / "email"
        base_template = template_dir / "base.html"
        self.assertTrue(base_template.exists(), "base.html template not found")

    def test_all_templates_exist(self):
        """Test that all required templates exist"""
        template_dir = Path(__file__).parent.parent.parent / "app" / "templates" / "email"

        required_templates = [
            "base.html",
            "backup_success.html",
            "backup_failure.html",
            "rule_violation.html",
            "media_reminder.html",
            "daily_report.html",
        ]

        for template_name in required_templates:
            template_path = template_dir / template_name
            self.assertTrue(template_path.exists(), f"Template {template_name} not found")


if __name__ == "__main__":
    unittest.main()
