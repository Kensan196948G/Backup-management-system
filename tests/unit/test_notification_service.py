"""
Unit tests for Email Notification Service and MultiChannelNotificationOrchestrator

Tests cover:
- Email validation
- Rate limiting
- Template rendering
- SMTP sending (mocked)
- Various notification types
- MultiChannelNotificationOrchestrator
- Channel health and statistics
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

from app.services.notification_service import (
    EmailNotificationService,
    MultiChannelNotificationOrchestrator,
    NotificationChannel,
    get_email_service,
    get_notification_orchestrator,
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
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.service.rate_limit_window + 1)
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

    def test_is_configured_requires_server(self):
        """Test that server is required for configuration"""
        service = EmailNotificationService()
        service.smtp_server = None
        service.username = "test@example.com"
        service.password = "password123"
        self.assertFalse(service.is_configured())

    def test_is_configured_requires_username(self):
        """Test that username is required for configuration"""
        service = EmailNotificationService()
        service.smtp_server = "smtp.example.com"
        service.username = None
        service.password = "password123"
        self.assertFalse(service.is_configured())

    def test_is_configured_requires_password(self):
        """Test that password is required for configuration"""
        service = EmailNotificationService()
        service.smtp_server = "smtp.example.com"
        service.username = "user@example.com"
        service.password = None
        self.assertFalse(service.is_configured())

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
    def test_send_email_with_plain_body(self, mock_smtp):
        """Test email sending with plain text alternative"""
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = self.service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<h1>Test</h1>",
            plain_body="Test plain text"
        )
        self.assertTrue(result)

    @patch("smtplib.SMTP")
    def test_send_email_with_tls(self, mock_smtp):
        """Test email sending with TLS enabled"""
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"
        self.service.use_tls = True

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = self.service.send_email(to="recipient@example.com", subject="Test", html_body="<h1>Test</h1>")
        self.assertTrue(result)
        mock_server.starttls.assert_called_once()

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

    @patch("smtplib.SMTP")
    def test_send_email_all_retries_fail(self, mock_smtp):
        """Test email all retries fail returns False"""
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        mock_server = MagicMock()
        mock_server.send_message.side_effect = Exception("Always fails")
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch("time.sleep"):  # Skip sleep in tests
            result = self.service.send_email(
                to="recipient@example.com",
                subject="Test",
                html_body="<h1>Test</h1>",
                retry_count=2
            )
        self.assertFalse(result)

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

    def test_send_email_not_configured(self):
        """Test email sending when service is not configured"""
        result = self.service.send_email(
            to="recipient@example.com",
            subject="Test",
            html_body="<h1>Test</h1>"
        )
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

    def test_record_delivery_creates_entry(self):
        """Test that record_delivery creates history entry"""
        recipient = "newuser@example.com"
        self.assertNotIn(recipient, self.service.delivery_history)
        self.service.record_delivery(recipient)
        self.assertIn(recipient, self.service.delivery_history)
        self.assertEqual(len(self.service.delivery_history[recipient]), 1)

    def test_record_delivery_appends(self):
        """Test that record_delivery appends to existing history"""
        recipient = "appendtest@example.com"
        self.service.record_delivery(recipient)
        self.service.record_delivery(recipient)
        self.assertEqual(len(self.service.delivery_history[recipient]), 2)

    def test_send_template_email_no_jinja_env(self):
        """Test send_template_email when jinja_env is None"""
        self.service.jinja_env = None
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "user@example.com"
        self.service.password = "pass"
        result = self.service.send_template_email(
            to="test@example.com",
            subject="Test",
            template_name="backup_success.html",
            context={}
        )
        self.assertFalse(result)

    @patch("smtplib.SMTP")
    def test_send_template_email_success(self, mock_smtp):
        """Test send_template_email with valid template"""
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        self.service.jinja_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Template Content</h1>"
        self.service.jinja_env.get_template.return_value = mock_template

        result = self.service.send_template_email(
            to="recipient@example.com",
            subject="Template Test",
            template_name="test_template.html",
            context={"key": "value"}
        )
        self.assertTrue(result)
        mock_template.render.assert_called_once_with(key="value")

    def test_send_template_email_render_error(self):
        """Test send_template_email handles template rendering errors"""
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        self.service.jinja_env = MagicMock()
        self.service.jinja_env.get_template.side_effect = Exception("Template not found")

        result = self.service.send_template_email(
            to="recipient@example.com",
            subject="Test",
            template_name="nonexistent.html",
            context={}
        )
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
    def test_send_backup_success_notification_multiple_recipients(self, mock_smtp):
        """Test backup success notification to multiple recipients"""
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        self.service.jinja_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Success</h1>"
        self.service.jinja_env.get_template.return_value = mock_template

        results = self.service.send_backup_success_notification(
            job_name="Test Job",
            recipients=["admin@example.com", "ops@example.com"]
        )

        self.assertIn("admin@example.com", results)
        self.assertIn("ops@example.com", results)

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

    @patch("smtplib.SMTP")
    def test_send_bulk_notification(self, mock_smtp):
        """Test bulk notification to multiple recipients"""
        self.service.smtp_server = "smtp.gmail.com"
        self.service.username = "test@example.com"
        self.service.password = "password123"

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        self.service.jinja_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Bulk</h1>"
        self.service.jinja_env.get_template.return_value = mock_template

        results = self.service.send_bulk_notification(
            recipients=["user1@example.com", "user2@example.com"],
            subject="Bulk Test",
            template_name="test.html",
            context={"data": "value"}
        )

        self.assertIn("user1@example.com", results)
        self.assertIn("user2@example.com", results)

    def test_get_notification_service_singleton(self):
        """Test that get_notification_service returns singleton instance"""
        service1 = get_notification_service()
        service2 = get_notification_service()

        # Should be the same instance
        self.assertIs(service1, service2)

    def test_get_email_service_singleton(self):
        """Test that get_email_service returns singleton instance"""
        svc1 = get_email_service()
        svc2 = get_email_service()
        self.assertIs(svc1, svc2)

    def test_get_notification_service_equals_email_service(self):
        """Test that get_notification_service and get_email_service return same instance"""
        ns = get_notification_service()
        es = get_email_service()
        self.assertIs(ns, es)


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


class TestNotificationChannel(unittest.TestCase):
    """Test NotificationChannel enum"""

    def test_channel_values(self):
        self.assertEqual(NotificationChannel.DASHBOARD.value, "dashboard")
        self.assertEqual(NotificationChannel.EMAIL.value, "email")
        self.assertEqual(NotificationChannel.TEAMS.value, "teams")
        self.assertEqual(NotificationChannel.SMS.value, "sms")
        self.assertEqual(NotificationChannel.SLACK.value, "slack")


class TestMultiChannelNotificationOrchestrator(unittest.TestCase):
    """Test cases for MultiChannelNotificationOrchestrator"""

    def setUp(self):
        """Set up test fixtures"""
        self.orchestrator = MultiChannelNotificationOrchestrator()

    def test_instantiation(self):
        """Test orchestrator initialization"""
        self.assertIsNotNone(self.orchestrator)
        self.assertIsNone(self.orchestrator.teams_service)
        self.assertIsNone(self.orchestrator.email_service)
        self.assertEqual(self.orchestrator._delivery_stats, {})

    def test_get_channels_for_severity_critical(self):
        """Test channel selection for critical severity"""
        channels = self.orchestrator._get_channels_for_severity("critical")
        self.assertIn(NotificationChannel.TEAMS, channels)
        self.assertIn(NotificationChannel.EMAIL, channels)
        self.assertIn(NotificationChannel.DASHBOARD, channels)

    def test_get_channels_for_severity_error(self):
        """Test channel selection for error severity"""
        channels = self.orchestrator._get_channels_for_severity("error")
        self.assertIn(NotificationChannel.TEAMS, channels)
        self.assertIn(NotificationChannel.EMAIL, channels)

    def test_get_channels_for_severity_warning(self):
        """Test channel selection for warning severity"""
        channels = self.orchestrator._get_channels_for_severity("warning")
        self.assertIn(NotificationChannel.EMAIL, channels)
        self.assertIn(NotificationChannel.DASHBOARD, channels)
        self.assertNotIn(NotificationChannel.TEAMS, channels)

    def test_get_channels_for_severity_info(self):
        """Test channel selection for info severity"""
        channels = self.orchestrator._get_channels_for_severity("info")
        self.assertIn(NotificationChannel.DASHBOARD, channels)
        self.assertNotIn(NotificationChannel.EMAIL, channels)
        self.assertNotIn(NotificationChannel.TEAMS, channels)

    def test_get_channels_for_unknown_severity_defaults_to_dashboard(self):
        """Test that unknown severity defaults to dashboard"""
        channels = self.orchestrator._get_channels_for_severity("unknown_level")
        self.assertEqual(channels, [NotificationChannel.DASHBOARD])

    def test_send_notification_info_level(self):
        """Test sending info-level notification (dashboard only)"""
        results = self.orchestrator.send_notification(
            title="Test Info",
            message="Info message",
            severity="info"
        )
        self.assertIn("dashboard", results)
        self.assertTrue(results["dashboard"])

    def test_send_notification_with_custom_channels(self):
        """Test sending notification with explicitly specified channels"""
        results = self.orchestrator.send_notification(
            title="Custom Channel Test",
            message="Test message",
            severity="info",
            channels=[NotificationChannel.DASHBOARD]
        )
        self.assertIn("dashboard", results)
        self.assertTrue(results["dashboard"])

    def test_send_to_dashboard_always_succeeds(self):
        """Test that dashboard channel always succeeds"""
        result = self.orchestrator._send_to_dashboard(
            title="Dashboard Test",
            message="Test",
            severity="info",
            metadata={}
        )
        self.assertTrue(result)

    def test_send_to_email_no_config(self):
        """Test sending to email when not configured"""
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.MAIL_SERVER = None
            mock_config.MAIL_USERNAME = None
            result = self.orchestrator._send_to_email(
                title="Test",
                message="Message",
                severity="error",
                metadata={"recipients": ["test@example.com"]}
            )
            self.assertFalse(result)

    def test_send_to_email_no_recipients(self):
        """Test sending to email with no recipients"""
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.MAIL_SERVER = "smtp.example.com"
            mock_config.MAIL_USERNAME = "user@example.com"
            result = self.orchestrator._send_to_email(
                title="Test",
                message="Message",
                severity="error",
                metadata={}  # No recipients key
            )
            self.assertFalse(result)

    def test_send_to_teams_no_config(self):
        """Test sending to Teams when not configured"""
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.TEAMS_WEBHOOK_URL = None
            result = self.orchestrator._send_to_teams(
                title="Test",
                message="Message",
                severity="critical",
                metadata={}
            )
            self.assertFalse(result)

    def test_send_to_unsupported_channel(self):
        """Test sending to unsupported channel returns False"""
        # Create a mock channel that doesn't match any handler
        mock_channel = MagicMock()
        mock_channel.value = "unsupported"

        # Patch the channel comparison
        result = self.orchestrator._send_to_channel(
            channel=NotificationChannel.SMS,  # SMS is not implemented
            title="Test",
            message="Message",
            severity="info",
            metadata={}
        )
        self.assertFalse(result)

    def test_track_delivery_creates_stats(self):
        """Test that _track_delivery creates stats for new channel"""
        self.orchestrator._track_delivery("email", True, "error")
        self.assertIn("email", self.orchestrator._delivery_stats)
        stats = self.orchestrator._delivery_stats["email"]
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["successful"], 1)
        self.assertEqual(stats["failed"], 0)

    def test_track_delivery_updates_stats(self):
        """Test that _track_delivery updates existing stats"""
        self.orchestrator._track_delivery("email", True, "error")
        self.orchestrator._track_delivery("email", False, "error")
        stats = self.orchestrator._delivery_stats["email"]
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["successful"], 1)
        self.assertEqual(stats["failed"], 1)

    def test_track_delivery_by_severity(self):
        """Test that _track_delivery tracks stats by severity"""
        self.orchestrator._track_delivery("email", True, "critical")
        self.orchestrator._track_delivery("email", False, "warning")
        stats = self.orchestrator._delivery_stats["email"]
        self.assertIn("critical", stats["by_severity"])
        self.assertIn("warning", stats["by_severity"])
        self.assertEqual(stats["by_severity"]["critical"]["total"], 1)
        self.assertEqual(stats["by_severity"]["warning"]["total"], 1)

    def test_get_channel_statistics_returns_data(self):
        """Test that get_channel_statistics returns stats data"""
        self.orchestrator._track_delivery("dashboard", True, "info")
        stats = self.orchestrator.get_channel_statistics()
        self.assertIn("dashboard", stats)
        # The returned value should contain the tracked data
        self.assertEqual(stats["dashboard"]["total"], 1)
        self.assertEqual(stats["dashboard"]["successful"], 1)

    def test_get_channel_health_no_stats(self):
        """Test channel health when no stats available"""
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.TEAMS_WEBHOOK_URL = None
            mock_config.MAIL_SERVER = None
            health = self.orchestrator.get_channel_health()
            # Dashboard always healthy
            self.assertEqual(health.get("dashboard"), "healthy")

    def test_get_channel_health_healthy(self):
        """Test channel health calculation for healthy channel"""
        for _ in range(20):
            self.orchestrator._track_delivery("email", True, "error")
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.TEAMS_WEBHOOK_URL = None
            mock_config.MAIL_SERVER = None
            health = self.orchestrator.get_channel_health()
            self.assertEqual(health.get("email"), "healthy")

    def test_get_channel_health_degraded(self):
        """Test channel health calculation for degraded channel"""
        for _ in range(10):
            self.orchestrator._track_delivery("email", True, "error")
        for _ in range(2):
            self.orchestrator._track_delivery("email", False, "error")
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.TEAMS_WEBHOOK_URL = None
            mock_config.MAIL_SERVER = None
            health = self.orchestrator.get_channel_health()
            # 10/12 = 83% success rate -> degraded
            self.assertEqual(health.get("email"), "degraded")

    def test_get_channel_health_unhealthy(self):
        """Test channel health calculation for unhealthy channel"""
        for _ in range(5):
            self.orchestrator._track_delivery("email", True, "error")
        for _ in range(10):
            self.orchestrator._track_delivery("email", False, "error")
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.TEAMS_WEBHOOK_URL = None
            mock_config.MAIL_SERVER = None
            health = self.orchestrator.get_channel_health()
            # 5/15 = 33% success rate -> unhealthy
            self.assertEqual(health.get("email"), "unhealthy")

    def test_get_channel_health_teams_configured(self):
        """Test health includes Teams channel when configured"""
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.TEAMS_WEBHOOK_URL = "https://teams.example.com/webhook"
            mock_config.MAIL_SERVER = None
            health = self.orchestrator.get_channel_health()
            self.assertIn("teams", health)

    def test_get_channel_health_email_configured(self):
        """Test health includes email channel when configured"""
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.TEAMS_WEBHOOK_URL = None
            mock_config.MAIL_SERVER = "smtp.example.com"
            health = self.orchestrator.get_channel_health()
            self.assertIn("email", health)

    def test_build_email_html_contains_title(self):
        """Test that _build_email_html contains the title"""
        html = self.orchestrator._build_email_html(
            title="Test Title",
            message="Test Message",
            severity="error",
            metadata={}
        )
        self.assertIn("Test Title", html)
        self.assertIn("Test Message", html)

    def test_build_email_html_severity_colors(self):
        """Test that _build_email_html uses correct severity colors"""
        color_map = {
            "info": "#17a2b8",
            "warning": "#ffc107",
            "error": "#dc3545",
            "critical": "#721c24"
        }
        for severity, expected_color in color_map.items():
            html = self.orchestrator._build_email_html(
                title="Test",
                message="Message",
                severity=severity,
                metadata={}
            )
            self.assertIn(expected_color, html)

    def test_build_email_html_with_metadata(self):
        """Test that _build_email_html includes metadata"""
        html = self.orchestrator._build_email_html(
            title="Test",
            message="Message",
            severity="info",
            metadata={"job_name": "My Backup Job", "duration": "120s"}
        )
        self.assertIn("My Backup Job", html)
        self.assertIn("120s", html)

    def test_build_email_html_excludes_recipients_from_metadata(self):
        """Test that recipients are not shown in email body metadata"""
        html = self.orchestrator._build_email_html(
            title="Test",
            message="Message",
            severity="info",
            metadata={"recipients": ["secret@example.com"], "visible_key": "visible_value"}
        )
        self.assertNotIn("secret@example.com", html)
        self.assertIn("visible_value", html)

    def test_send_notification_tracks_stats(self):
        """Test that send_notification tracks delivery stats"""
        self.orchestrator.send_notification(
            title="Stats Test",
            message="Test",
            severity="info"
        )
        # Dashboard channel should have stats
        self.assertIn("dashboard", self.orchestrator._delivery_stats)

    def test_test_all_channels_dashboard_always_true(self):
        """Test that test_all_channels always shows dashboard as True"""
        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.MAIL_SERVER = None
            mock_config.MAIL_USERNAME = None
            mock_config.TEAMS_WEBHOOK_URL = None
            results = self.orchestrator.test_all_channels()
            self.assertTrue(results.get("dashboard"))

    def test_send_to_email_with_configured_service(self):
        """Test send_to_email when configured, with mocked email service"""
        mock_email_svc = MagicMock()
        mock_email_svc.send_email.return_value = True
        self.orchestrator.email_service = mock_email_svc

        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.MAIL_SERVER = "smtp.example.com"
            mock_config.MAIL_USERNAME = "user@example.com"
            result = self.orchestrator._send_to_email(
                title="Test Email",
                message="Test message",
                severity="error",
                metadata={"recipients": ["test@example.com"]}
            )
            self.assertTrue(result)
            mock_email_svc.send_email.assert_called_once()

    def test_send_to_email_partial_failure(self):
        """Test send_to_email returns False if any recipient fails"""
        mock_email_svc = MagicMock()
        mock_email_svc.send_email.side_effect = [True, False]
        self.orchestrator.email_service = mock_email_svc

        with patch("app.services.notification_service.Config") as mock_config:
            mock_config.MAIL_SERVER = "smtp.example.com"
            mock_config.MAIL_USERNAME = "user@example.com"
            result = self.orchestrator._send_to_email(
                title="Test",
                message="Test",
                severity="error",
                metadata={"recipients": ["user1@example.com", "user2@example.com"]}
            )
            self.assertFalse(result)


class TestGetNotificationOrchestrator(unittest.TestCase):
    """Test the global orchestrator factory function"""

    def test_get_notification_orchestrator_returns_instance(self):
        """Test that get_notification_orchestrator returns an instance"""
        orchestrator = get_notification_orchestrator()
        self.assertIsInstance(orchestrator, MultiChannelNotificationOrchestrator)

    def test_get_notification_orchestrator_singleton(self):
        """Test that get_notification_orchestrator returns singleton"""
        o1 = get_notification_orchestrator()
        o2 = get_notification_orchestrator()
        self.assertIs(o1, o2)


if __name__ == "__main__":
    unittest.main()
