"""
Unit tests for email tasks.
Phase 11: Asynchronous Task Processing
"""
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestSendEmailTask:
    """Tests for send_email task."""

    @pytest.fixture
    def mock_email_service(self):
        """Create mock email service."""
        with patch("app.tasks.email_tasks.EmailNotificationService") as mock:
            service = Mock()
            service.is_configured.return_value = True
            service.validate_email.return_value = True
            service.check_rate_limit.return_value = True
            service.send_email.return_value = True
            mock.return_value = service
            yield service

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_send_email_success(self, app, mock_email_service, celery_app):
        """Test successful email sending."""
        from app.tasks.email_tasks import send_email

        with app.app_context():
            result = send_email(
                to="test@example.com",
                subject="Test Subject",
                html_body="<h1>Test</h1>",
            )

            assert result["status"] == "sent"
            assert result["to"] == "test@example.com"
            mock_email_service.send_email.assert_called_once()

    def test_send_email_not_configured(self, app, celery_app):
        """Test email sending when service not configured."""
        from app.tasks.email_tasks import send_email

        with patch("app.tasks.email_tasks.EmailNotificationService") as mock:
            service = Mock()
            service.is_configured.return_value = False
            mock.return_value = service

            with app.app_context():
                result = send_email(
                    to="test@example.com",
                    subject="Test",
                    html_body="<h1>Test</h1>",
                )

                assert result["status"] == "failed"
                assert "not configured" in result["error"]

    def test_send_email_invalid_address(self, app, celery_app):
        """Test email sending with invalid address."""
        from app.tasks.email_tasks import send_email

        with patch("app.tasks.email_tasks.EmailNotificationService") as mock:
            service = Mock()
            service.is_configured.return_value = True
            service.validate_email.return_value = False
            mock.return_value = service

            with app.app_context():
                result = send_email(
                    to="invalid-email",
                    subject="Test",
                    html_body="<h1>Test</h1>",
                )

                assert result["status"] == "failed"
                assert "Invalid email" in result["error"]

    def test_send_email_rate_limited(self, app, celery_app):
        """Test email sending when rate limited."""
        from app.tasks.email_tasks import send_email

        with patch("app.tasks.email_tasks.EmailNotificationService") as mock:
            service = Mock()
            service.is_configured.return_value = True
            service.validate_email.return_value = True
            service.check_rate_limit.return_value = False
            mock.return_value = service

            with app.app_context():
                # Rate limited should trigger retry, which in eager mode raises
                with pytest.raises(Exception):
                    send_email(
                        to="test@example.com",
                        subject="Test",
                        html_body="<h1>Test</h1>",
                    )


class TestSendBulkEmailsTask:
    """Tests for send_bulk_emails task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_send_bulk_emails_queues_tasks(self, app, celery_app):
        """Test bulk email queues individual tasks."""
        from app.tasks.email_tasks import send_bulk_emails

        with patch("app.tasks.email_tasks.send_email") as mock_send:
            mock_send.apply_async.return_value = Mock(id="task-123")

            with app.app_context():
                result = send_bulk_emails(
                    recipients=["a@test.com", "b@test.com", "c@test.com"],
                    subject="Bulk Test",
                    html_body="<h1>Bulk</h1>",
                )

                assert result["status"] == "queued"
                assert result["queued_count"] == 3
                assert len(result["queued_tasks"]) == 3


class TestSendBackupNotificationTask:
    """Tests for send_backup_notification task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_send_backup_notification_success(self, app, celery_app):
        """Test backup notification sends email."""
        from app.tasks.email_tasks import send_backup_notification

        with patch("app.tasks.email_tasks.send_email") as mock_send:
            mock_send.apply_async.return_value = Mock(id="task-456")

            with patch("app.tasks.email_tasks.EmailNotificationService") as mock_svc:
                service = Mock()
                service.render_template.return_value = "<h1>Backup Success</h1>"
                mock_svc.return_value = service

                with app.app_context():
                    result = send_backup_notification(
                        notification_type="success",
                        recipient="admin@test.com",
                        job_name="Daily Backup",
                        status="success",
                    )

                    assert result["status"] == "queued"
                    assert result["notification_type"] == "success"

    def test_send_backup_notification_failure(self, app, celery_app):
        """Test backup failure notification."""
        from app.tasks.email_tasks import send_backup_notification

        with patch("app.tasks.email_tasks.send_email") as mock_send:
            mock_send.apply_async.return_value = Mock(id="task-789")

            with patch("app.tasks.email_tasks.EmailNotificationService") as mock_svc:
                service = Mock()
                service.render_template.return_value = None  # Template not found
                mock_svc.return_value = service

                with app.app_context():
                    result = send_backup_notification(
                        notification_type="failure",
                        recipient="admin@test.com",
                        job_name="Critical Backup",
                        status="failed",
                        details={"error": "Disk full"},
                    )

                    assert result["status"] == "queued"
                    assert result["notification_type"] == "failure"
