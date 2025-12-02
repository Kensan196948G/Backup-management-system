"""
Unit tests for notification tasks.
Phase 11: Asynchronous Task Processing
"""
from unittest.mock import Mock, patch

import pytest


class TestSendTeamsNotificationTask:
    """Tests for send_teams_notification task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_send_teams_notification_success(self, app, celery_app):
        """Test successful Teams notification."""
        from app.tasks.notification_tasks import send_teams_notification

        with patch("app.services.teams_notification_service.TeamsNotificationService") as mock:
            service = Mock()
            service.is_configured.return_value = True
            service.send_info_notification.return_value = True
            mock.return_value = service

            with app.app_context():
                result = send_teams_notification(
                    webhook_url="https://teams.webhook.url",
                    title="Test Alert",
                    message="Test message",
                    severity="info",
                )

                assert result["status"] == "sent"
                assert result["title"] == "Test Alert"

    def test_send_teams_notification_not_configured(self, app, celery_app):
        """Test Teams notification when not configured."""
        from app.tasks.notification_tasks import send_teams_notification

        with patch("app.services.teams_notification_service.TeamsNotificationService") as mock:
            service = Mock()
            service.is_configured.return_value = False
            mock.return_value = service

            with app.app_context():
                result = send_teams_notification(
                    webhook_url="",
                    title="Test",
                    message="Test",
                )

                assert result["status"] == "failed"
                assert "not configured" in result.get("error", "")

    def test_send_teams_critical_alert(self, app, celery_app):
        """Test critical alert sends to Teams."""
        from app.tasks.notification_tasks import send_teams_notification

        with patch("app.services.teams_notification_service.TeamsNotificationService") as mock:
            service = Mock()
            service.is_configured.return_value = True
            service.send_critical_alert.return_value = True
            mock.return_value = service

            with app.app_context():
                result = send_teams_notification(
                    webhook_url="https://teams.webhook.url",
                    title="Critical Alert",
                    message="System failure",
                    severity="critical",
                )

                assert result["status"] == "sent"
                service.send_critical_alert.assert_called_once()


class TestSendMultiChannelNotificationTask:
    """Tests for send_multi_channel_notification task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_multi_channel_email_only(self, app, celery_app):
        """Test multi-channel with email only."""
        from app.tasks.notification_tasks import send_multi_channel_notification

        with patch("app.tasks.email_tasks.send_backup_notification") as mock_email:
            mock_email.apply_async.return_value = Mock(id="email-task-123")

            with app.app_context():
                result = send_multi_channel_notification(
                    channels=["email"],
                    title="Test Notification",
                    message="Test message",
                    severity="info",
                    recipient_email="test@example.com",
                    job_name="Test Job",
                )

                assert result["status"] == "queued"
                assert "email" in result["channel_results"]
                mock_email.apply_async.assert_called_once()

    def test_multi_channel_teams_only(self, app, celery_app):
        """Test multi-channel with Teams only."""
        from app.tasks.notification_tasks import send_multi_channel_notification

        with patch("app.tasks.notification_tasks.send_teams_notification") as mock_teams:
            mock_teams.apply_async.return_value = Mock(id="teams-task-123")

            with app.app_context():
                result = send_multi_channel_notification(
                    channels=["teams"],
                    title="Test Notification",
                    message="Test message",
                    severity="warning",
                    teams_webhook_url="https://teams.webhook.url",
                )

                assert result["status"] == "queued"
                assert "teams" in result["channel_results"]
                mock_teams.apply_async.assert_called_once()

    def test_multi_channel_dashboard(self, app, celery_app):
        """Test multi-channel with dashboard alert."""
        from app.tasks.notification_tasks import send_multi_channel_notification

        with patch("app.tasks.notification_tasks._create_dashboard_alert") as mock_alert:
            with app.app_context():
                result = send_multi_channel_notification(
                    channels=["dashboard"],
                    title="Dashboard Alert",
                    message="System notification",
                    severity="info",
                )

                assert result["status"] == "queued"
                assert "dashboard" in result["channel_results"]
                mock_alert.assert_called_once()

    def test_multi_channel_all_channels(self, app, celery_app):
        """Test multi-channel with all channels."""
        from app.tasks.notification_tasks import send_multi_channel_notification

        with patch("app.tasks.email_tasks.send_backup_notification") as mock_email:
            with patch("app.tasks.notification_tasks.send_teams_notification") as mock_teams:
                with patch("app.tasks.notification_tasks._create_dashboard_alert") as mock_alert:
                    mock_email.apply_async.return_value = Mock(id="email-123")
                    mock_teams.apply_async.return_value = Mock(id="teams-123")

                    with app.app_context():
                        result = send_multi_channel_notification(
                            channels=["email", "teams", "dashboard"],
                            title="Multi-Channel Alert",
                            message="Critical system alert",
                            severity="critical",
                            recipient_email="admin@example.com",
                            teams_webhook_url="https://teams.webhook.url",
                            job_name="Critical Job",
                        )

                        assert result["status"] == "queued"
                        assert len(result["channel_results"]) == 3


class TestSendBackupStatusUpdateTask:
    """Tests for send_backup_status_update task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_status_update_job_not_found(self, app, celery_app):
        """Test status update when job not found."""
        from app.tasks.notification_tasks import send_backup_status_update

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = None

            with app.app_context():
                result = send_backup_status_update(
                    job_id=99999,  # Non-existent job
                    status="success",
                )

                assert "error" in result
                assert "not found" in result["error"]

    def test_status_update_success(self, app, celery_app):
        """Test successful status update notification."""
        from app.tasks.notification_tasks import send_backup_status_update

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job = Mock()
            mock_job.name = "Test Backup Job"
            mock_job.job_type = "full"
            mock_job_class.query.get.return_value = mock_job

            with patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:
                mock_notify.apply_async.return_value = Mock(id="notify-123")

                with app.app_context():
                    result = send_backup_status_update(
                        job_id=1,
                        status="success",
                    )

                    assert "notification_task_id" in result
                    mock_notify.apply_async.assert_called_once()
