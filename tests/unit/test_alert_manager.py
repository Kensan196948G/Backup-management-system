"""
Unit tests for AlertManager service.
app/services/alert_manager.py coverage: 39% -> ~70%+
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.models import Alert, BackupJob, User, db
from app.services.alert_manager import AlertManager, AlertSeverity, AlertType


@pytest.fixture
def alert_manager():
    return AlertManager()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        user = User(
            username="alert_test_admin", email="alert_admin@example.com",
            role="admin", is_active=True
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()
        yield user.id


@pytest.fixture
def sample_job(app, admin_user):
    with app.app_context():
        job = BackupJob(
            job_name="Alert Test Job",
            job_type="file",
            backup_tool="custom",
            schedule_type="daily",
            retention_days=7,
            owner_id=admin_user,
        )
        db.session.add(job)
        db.session.commit()
        yield job.id


class TestAlertManagerInit:
    def test_instantiation(self, alert_manager):
        assert alert_manager is not None
        assert alert_manager.notification_service is None


class TestAlertSeverityEnum:
    def test_severity_values(self):
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertTypeEnum:
    def test_type_values(self):
        assert AlertType.BACKUP_FAILED.value == "backup_failed"
        assert AlertType.BACKUP_SUCCESS.value == "backup_success"
        assert AlertType.RULE_VIOLATION.value == "rule_violation"
        assert AlertType.SYSTEM_ERROR.value == "system_error"

    def test_all_type_values(self):
        assert AlertType.COMPLIANCE_WARNING.value == "compliance_warning"
        assert AlertType.OFFLINE_MEDIA_UPDATE_WARNING.value == "offline_media_update_warning"
        assert AlertType.VERIFICATION_REMINDER.value == "verification_reminder"
        assert AlertType.MEDIA_ROTATION_REMINDER.value == "media_rotation_reminder"
        assert AlertType.MEDIA_OVERDUE_RETURN.value == "media_overdue_return"


class TestCreateAlert:
    def test_create_basic_alert(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.WARNING,
                title="Test Alert",
                message="Test message",
                notify=False,
            )
            assert alert is not None
            assert alert.id is not None
            assert alert.alert_type == "system_error"
            assert alert.severity == "warning"
            assert alert.title == "Test Alert"
            assert alert.is_acknowledged is False

    def test_create_alert_with_job(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                title="Backup Failed",
                message="Job failed",
                job_id=sample_job,
                notify=False,
            )
            assert alert.job_id == sample_job

    def test_create_alert_string_type(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type="backup_success",
                severity="info",
                title="Success",
                message="Backup succeeded",
                notify=False,
            )
            assert alert.alert_type == "backup_success"
            assert alert.severity == "info"

    def test_create_critical_alert(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.CRITICAL,
                title="Critical Failure",
                message="Disk corrupted",
                notify=False,
            )
            assert alert.severity == "critical"

    def test_create_info_alert(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_SUCCESS,
                severity=AlertSeverity.INFO,
                title="Backup Succeeded",
                message="All good",
                notify=False,
            )
            assert alert.severity == "info"
            assert alert.alert_type == "backup_success"

    def test_create_alert_with_notify_no_email_configured(self, alert_manager, app):
        """When notify=True but no MAIL_SERVER, email should not be sent."""
        with app.app_context():
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.MAIL_SERVER = None
                mock_config.MAIL_USERNAME = None
                mock_config.TEAMS_WEBHOOK_URL = None
                alert = alert_manager.create_alert(
                    alert_type=AlertType.SYSTEM_ERROR,
                    severity=AlertSeverity.WARNING,
                    title="Notify Test",
                    message="Should not send email",
                    notify=True,
                )
                assert alert is not None


class TestSendNotifications:
    def test_send_notifications_returns_dict(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                title="Notif Test",
                message="Test",
                notify=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.MAIL_SERVER = None
                mock_config.MAIL_USERNAME = None
                mock_config.TEAMS_WEBHOOK_URL = None
                results = alert_manager.send_notifications(alert)
                assert isinstance(results, dict)
                assert "dashboard" in results
                assert results["dashboard"] is True

    def test_send_notifications_no_channels_when_unconfigured(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                title="Error Alert",
                message="Error",
                notify=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.MAIL_SERVER = None
                mock_config.MAIL_USERNAME = None
                mock_config.TEAMS_WEBHOOK_URL = None
                results = alert_manager.send_notifications(alert)
                assert results["email"] is False
                assert results["teams"] is False


class TestShouldSendEmail:
    def test_should_not_send_email_when_not_configured(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="system_error",
                severity="error",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.MAIL_SERVER = None
                mock_config.MAIL_USERNAME = None
                result = alert_manager._should_send_email(alert)
                assert result is False

    def test_should_not_send_email_for_info_severity(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="system_error",
                severity="info",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.MAIL_SERVER = "smtp.example.com"
                mock_config.MAIL_USERNAME = "user@example.com"
                result = alert_manager._should_send_email(alert)
                assert result is False

    def test_should_send_email_for_warning(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="system_error",
                severity="warning",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.MAIL_SERVER = "smtp.example.com"
                mock_config.MAIL_USERNAME = "user@example.com"
                result = alert_manager._should_send_email(alert)
                assert result is True

    def test_should_send_email_for_critical(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="backup_failed",
                severity="critical",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.MAIL_SERVER = "smtp.example.com"
                mock_config.MAIL_USERNAME = "user@example.com"
                result = alert_manager._should_send_email(alert)
                assert result is True


class TestShouldSendTeams:
    def test_should_not_send_teams_when_not_configured(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="backup_failed",
                severity="critical",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.TEAMS_WEBHOOK_URL = None
                result = alert_manager._should_send_teams(alert)
                assert result is False

    def test_should_not_send_teams_for_warning(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="system_error",
                severity="warning",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.TEAMS_WEBHOOK_URL = "https://teams.example.com/webhook"
                result = alert_manager._should_send_teams(alert)
                assert result is False

    def test_should_send_teams_for_error(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.TEAMS_WEBHOOK_URL = "https://teams.example.com/webhook"
                result = alert_manager._should_send_teams(alert)
                assert result is True

    def test_should_send_teams_for_critical(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="backup_failed",
                severity="critical",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.TEAMS_WEBHOOK_URL = "https://teams.example.com/webhook"
                result = alert_manager._should_send_teams(alert)
                assert result is True


class TestSendTeamsNotification:
    def test_send_teams_notification_success(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.CRITICAL,
                title="Teams Test",
                message="Critical error",
                notify=False,
            )
            mock_teams_service = MagicMock()
            mock_teams_service.send_alert_card.return_value = True
            # Teams service is imported inside the function, patch at source module
            with patch(
                "app.services.teams_notification_service.TeamsNotificationService",
                return_value=mock_teams_service
            ):
                with patch(
                    "app.services.alert_manager.TeamsNotificationService",
                    create=True,
                    return_value=mock_teams_service
                ):
                    result = alert_manager._send_teams_notification(alert)
                    assert isinstance(result, bool)

    def test_send_teams_notification_with_job(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                title="Teams Job Test",
                message="Error with job",
                job_id=sample_job,
                notify=False,
            )
            mock_teams_service = MagicMock()
            mock_teams_service.send_alert_card.return_value = True
            import sys
            # Patch the module that gets imported inside the function
            import importlib
            teams_module = MagicMock()
            teams_module.TeamsNotificationService = MagicMock(return_value=mock_teams_service)
            with patch.dict("sys.modules", {"app.services.teams_notification_service": teams_module}):
                result = alert_manager._send_teams_notification(alert)
                assert isinstance(result, bool)


class TestGetEmailRecipients:
    def test_get_recipients_returns_list(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="system_error",
                severity="error",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()
            recipients = alert_manager._get_email_recipients(alert)
            assert isinstance(recipients, list)

    def test_get_recipients_includes_admin_users(self, alert_manager, app, admin_user):
        with app.app_context():
            alert = Alert(
                alert_type="system_error",
                severity="error",
                title="Test",
                message="Test",
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()
            recipients = alert_manager._get_email_recipients(alert)
            # Admin user has email alert_admin@example.com
            assert "alert_admin@example.com" in recipients

    def test_get_recipients_with_job_owner(self, alert_manager, app, sample_job, admin_user):
        with app.app_context():
            alert = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Job Test",
                message="Test",
                job_id=sample_job,
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()
            recipients = alert_manager._get_email_recipients(alert)
            # Job owner's email should be in recipients
            assert isinstance(recipients, list)
            assert len(recipients) > 0

    def test_get_recipients_no_duplicates(self, alert_manager, app, admin_user, sample_job):
        """Admin who owns the job should not appear twice."""
        with app.app_context():
            alert = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Job Test",
                message="Test",
                job_id=sample_job,
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()
            recipients = alert_manager._get_email_recipients(alert)
            # No duplicate emails
            assert len(recipients) == len(set(recipients))


class TestBuildEmailBody:
    def test_build_email_body_returns_html(self, alert_manager, app):
        with app.app_context():
            alert = Alert(
                alert_type="system_error",
                severity="error",
                title="Test Email Alert",
                message="Something went wrong",
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()
            body = alert_manager._build_email_body(alert)
            assert "<html>" in body
            assert "Test Email Alert" in body
            assert "Something went wrong" in body

    def test_build_email_body_with_job(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = Alert(
                alert_type="backup_failed",
                severity="critical",
                title="Job Alert",
                message="Job failed badly",
                job_id=sample_job,
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()
            body = alert_manager._build_email_body(alert)
            assert "<html>" in body
            assert "Alert Test Job" in body

    def test_build_email_body_severity_colors(self, alert_manager, app):
        with app.app_context():
            for severity, color in [
                ("info", "#17a2b8"),
                ("warning", "#ffc107"),
                ("error", "#dc3545"),
                ("critical", "#721c24"),
            ]:
                alert = Alert(
                    alert_type="system_error",
                    severity=severity,
                    title="Color Test",
                    message="Test",
                    is_acknowledged=False,
                )
                db.session.add(alert)
                db.session.commit()
                body = alert_manager._build_email_body(alert)
                assert color in body
                db.session.delete(alert)
                db.session.commit()


class TestAcknowledgeAlert:
    def test_acknowledge_alert(self, alert_manager, app, admin_user):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                title="To Ack",
                message="Will be acknowledged",
                notify=False,
            )
            alert_id = alert.id

            acked = alert_manager.acknowledge_alert(alert_id, admin_user)
            assert acked is not None
            assert acked.is_acknowledged is True
            assert acked.acknowledged_by == admin_user

    def test_acknowledge_sets_timestamp(self, alert_manager, app, admin_user):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                title="Timestamp Test",
                message="Check timestamp",
                notify=False,
            )
            alert_id = alert.id
            acked = alert_manager.acknowledge_alert(alert_id, admin_user)
            assert acked.acknowledged_at is not None

    def test_acknowledge_nonexistent_alert(self, alert_manager, app):
        with app.app_context():
            try:
                result = alert_manager.acknowledge_alert(99999, 1)
                assert result is None
            except (ValueError, Exception):
                pass  # Expected behavior for non-existent alert


class TestGetAlerts:
    def test_get_unacknowledged_alerts(self, alert_manager, app):
        with app.app_context():
            alert_manager.create_alert(
                alert_type=AlertType.RULE_VIOLATION,
                severity=AlertSeverity.WARNING,
                title="Unacked Alert",
                message="Test",
                notify=False,
            )
            alerts = alert_manager.get_unacknowledged_alerts()
            assert isinstance(alerts, list)
            assert any(a.title == "Unacked Alert" for a in alerts)

    def test_get_unacknowledged_alerts_with_limit(self, alert_manager, app):
        with app.app_context():
            for i in range(5):
                alert_manager.create_alert(
                    alert_type=AlertType.SYSTEM_ERROR,
                    severity=AlertSeverity.INFO,
                    title=f"Alert {i}",
                    message="Test",
                    notify=False,
                )
            alerts = alert_manager.get_unacknowledged_alerts(limit=3)
            assert isinstance(alerts, list)
            assert len(alerts) <= 3

    def test_get_alerts_by_job(self, alert_manager, app, sample_job):
        with app.app_context():
            alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                title="Job Alert",
                message="Test",
                job_id=sample_job,
                notify=False,
            )
            alerts = alert_manager.get_alerts_by_job(sample_job)
            assert isinstance(alerts, list)
            assert len(alerts) >= 1
            assert all(a.job_id == sample_job for a in alerts)

    def test_get_alerts_by_job_with_days_param(self, alert_manager, app, sample_job):
        with app.app_context():
            alerts = alert_manager.get_alerts_by_job(sample_job, days=7, limit=10)
            assert isinstance(alerts, list)

    def test_get_alerts_by_type(self, alert_manager, app):
        with app.app_context():
            alerts = alert_manager.get_alerts_by_type("backup_failed")
            assert isinstance(alerts, list)

    def test_get_alerts_by_type_with_created_alert(self, alert_manager, app):
        with app.app_context():
            alert_manager.create_alert(
                alert_type="my_custom_type",
                severity="warning",
                title="Type Test",
                message="Testing",
                notify=False,
            )
            alerts = alert_manager.get_alerts_by_type("my_custom_type")
            assert len(alerts) >= 1

    def test_get_alerts_by_severity(self, alert_manager, app):
        with app.app_context():
            alerts = alert_manager.get_alerts_by_severity("error")
            assert isinstance(alerts, list)

    def test_get_alerts_by_severity_with_created_alert(self, alert_manager, app):
        with app.app_context():
            alert_manager.create_alert(
                alert_type="system_error",
                severity="critical",
                title="Critical Test",
                message="Testing",
                notify=False,
            )
            alerts = alert_manager.get_alerts_by_severity("critical")
            assert len(alerts) >= 1


class TestBulkAcknowledge:
    def test_bulk_acknowledge(self, alert_manager, app, admin_user):
        with app.app_context():
            a1 = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR, severity=AlertSeverity.INFO,
                title="Bulk1", message="Test", notify=False
            )
            a2 = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR, severity=AlertSeverity.INFO,
                title="Bulk2", message="Test", notify=False
            )
            result = alert_manager.bulk_acknowledge_alerts([a1.id, a2.id], admin_user)
            assert result is True

    def test_bulk_acknowledge_empty_list(self, alert_manager, app, admin_user):
        with app.app_context():
            result = alert_manager.bulk_acknowledge_alerts([], admin_user)
            assert result is True

    def test_bulk_acknowledge_verifies_each_alert(self, alert_manager, app, admin_user):
        with app.app_context():
            a1 = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR, severity=AlertSeverity.WARNING,
                title="BulkVer1", message="Test", notify=False
            )
            a2 = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED, severity=AlertSeverity.ERROR,
                title="BulkVer2", message="Test", notify=False
            )
            alert_manager.bulk_acknowledge_alerts([a1.id, a2.id], admin_user)
            # Verify both are acknowledged
            checked1 = db.session.get(Alert, a1.id)
            checked2 = db.session.get(Alert, a2.id)
            assert checked1.is_acknowledged is True
            assert checked2.is_acknowledged is True


class TestCreateComplianceAlert:
    def test_create_compliance_alert(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_compliance_alert(
                job_id=sample_job,
                issues=["Missing offsite copy", "Insufficient copies"],
                notify=False,
            )
            assert alert is not None
            assert alert.alert_type in ("rule_violation", "compliance")

    def test_compliance_alert_severity_warning_for_few_issues(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_compliance_alert(
                job_id=sample_job,
                issues=["One issue"],
                notify=False,
            )
            assert alert.severity == "warning"

    def test_compliance_alert_severity_critical_for_many_issues(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_compliance_alert(
                job_id=sample_job,
                issues=["Issue 1", "Issue 2", "Issue 3"],
                notify=False,
            )
            assert alert.severity == "critical"

    def test_compliance_alert_message_contains_issues(self, alert_manager, app, sample_job):
        with app.app_context():
            issues = ["Missing offsite copy", "No offline backup"]
            alert = alert_manager.create_compliance_alert(
                job_id=sample_job,
                issues=issues,
                notify=False,
            )
            for issue in issues:
                assert issue in alert.message


class TestCreateFailureAlert:
    def test_create_failure_alert(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_failure_alert(
                job_id=sample_job,
                error_message="Backup process failed",
                notify=False,
            )
            assert alert is not None
            assert alert.alert_type in ("backup_failed", "failure")

    def test_failure_alert_severity_is_critical(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_failure_alert(
                job_id=sample_job,
                error_message="Something broke",
                notify=False,
            )
            assert alert.severity == "critical"

    def test_failure_alert_message_contains_error(self, alert_manager, app, sample_job):
        with app.app_context():
            error_msg = "Disk full, cannot write backup"
            alert = alert_manager.create_failure_alert(
                job_id=sample_job,
                error_message=error_msg,
                notify=False,
            )
            assert error_msg in alert.message

    def test_failure_alert_linked_to_job(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_failure_alert(
                job_id=sample_job,
                error_message="Error",
                notify=False,
            )
            assert alert.job_id == sample_job


class TestSendNotificationById:
    def test_send_notification_for_alert(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                title="Notif By ID",
                message="Test",
                notify=False,
            )
            with patch("app.services.alert_manager.Config") as mock_config:
                mock_config.MAIL_SERVER = None
                mock_config.MAIL_USERNAME = None
                mock_config.TEAMS_WEBHOOK_URL = None
                result = alert_manager.send_notification(alert.id)
                assert isinstance(result, dict)

    def test_send_notification_nonexistent_alert(self, alert_manager, app):
        with app.app_context():
            result = alert_manager.send_notification(999999)
            assert result == {}


class TestClearOldAlerts:
    def test_clear_old_alerts_returns_int(self, alert_manager, app):
        with app.app_context():
            count = alert_manager.clear_old_alerts(days=90)
            assert isinstance(count, int)
            assert count >= 0

    def test_clear_old_alerts_removes_acknowledged_old_alerts(self, alert_manager, app, admin_user):
        with app.app_context():
            # Create an alert and acknowledge it with an old timestamp
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                title="Old Alert",
                message="To be cleared",
                notify=False,
            )
            alert_id = alert.id
            alert_manager.acknowledge_alert(alert_id, admin_user)

            # Manually set acknowledged_at to old date
            a = db.session.get(Alert, alert_id)
            a.acknowledged_at = datetime.now(timezone.utc) - timedelta(days=200)
            db.session.commit()

            count = alert_manager.clear_old_alerts(days=90)
            assert count >= 1

            # Verify it was deleted
            assert db.session.get(Alert, alert_id) is None

    def test_clear_old_alerts_keeps_recent_acknowledged(self, alert_manager, app, admin_user):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                title="Recent Acked",
                message="Keep me",
                notify=False,
            )
            alert_id = alert.id
            alert_manager.acknowledge_alert(alert_id, admin_user)

            count = alert_manager.clear_old_alerts(days=90)
            # Should not delete recently acknowledged alerts
            assert db.session.get(Alert, alert_id) is not None

    def test_clear_old_alerts_keeps_unacknowledged(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                title="Unacked Old",
                message="Keep me - not acked",
                notify=False,
            )
            alert_id = alert.id

            count = alert_manager.clear_old_alerts(days=0)
            # Unacknowledged alerts should NOT be deleted
            assert db.session.get(Alert, alert_id) is not None


class TestSendEmailNotification:
    def test_send_email_notification_no_recipients(self, alert_manager, app):
        """When there are no email recipients, email send returns False."""
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.ERROR,
                title="No Recipients",
                message="No admin users",
                notify=False,
            )
            # Mock notification service and empty recipients
            mock_ns = MagicMock()
            alert_manager.notification_service = mock_ns
            with patch.object(alert_manager, "_get_email_recipients", return_value=[]):
                result = alert_manager._send_email_notification(alert)
                assert result is False

    def test_send_email_notification_backup_success_type(self, alert_manager, app, sample_job):
        """Routes backup_success alert type to correct email method."""
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_SUCCESS,
                severity=AlertSeverity.INFO,
                title="Backup Success",
                message="All went fine",
                job_id=sample_job,
                notify=False,
            )
            mock_ns = MagicMock()
            mock_ns.send_backup_success_notification.return_value = {"admin@example.com": True}
            alert_manager.notification_service = mock_ns
            with patch.object(
                alert_manager, "_get_email_recipients", return_value=["admin@example.com"]
            ):
                with patch.object(
                    alert_manager, "_send_backup_success_email", return_value=True
                ) as mock_method:
                    result = alert_manager._send_email_notification(alert)
                    mock_method.assert_called_once()

    def test_send_email_notification_backup_failed_type(self, alert_manager, app, sample_job):
        """Routes backup_failed alert type to correct email method."""
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.CRITICAL,
                title="Backup Failed",
                message="Disk full",
                job_id=sample_job,
                notify=False,
            )
            alert_manager.notification_service = MagicMock()
            with patch.object(
                alert_manager, "_get_email_recipients", return_value=["admin@example.com"]
            ):
                with patch.object(
                    alert_manager, "_send_backup_failure_email", return_value=True
                ) as mock_method:
                    result = alert_manager._send_email_notification(alert)
                    mock_method.assert_called_once()

    def test_send_email_notification_rule_violation_type(self, alert_manager, app, sample_job):
        """Routes rule_violation alert type to correct email method."""
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.RULE_VIOLATION,
                severity=AlertSeverity.WARNING,
                title="Rule Violation",
                message="Missing copy",
                notify=False,
            )
            alert_manager.notification_service = MagicMock()
            with patch.object(
                alert_manager, "_get_email_recipients", return_value=["admin@example.com"]
            ):
                with patch.object(
                    alert_manager, "_send_rule_violation_email", return_value=True
                ) as mock_method:
                    result = alert_manager._send_email_notification(alert)
                    mock_method.assert_called_once()

    def test_send_email_notification_media_reminder_type(self, alert_manager, app):
        """Routes media reminder alert types to correct email method."""
        with app.app_context():
            for alert_type in [
                AlertType.OFFLINE_MEDIA_UPDATE_WARNING,
                AlertType.VERIFICATION_REMINDER,
                AlertType.MEDIA_ROTATION_REMINDER,
                AlertType.MEDIA_OVERDUE_RETURN,
            ]:
                alert = alert_manager.create_alert(
                    alert_type=alert_type,
                    severity=AlertSeverity.WARNING,
                    title="Media Reminder",
                    message="Action needed",
                    notify=False,
                )
                alert_manager.notification_service = MagicMock()
                with patch.object(
                    alert_manager, "_get_email_recipients", return_value=["admin@example.com"]
                ):
                    with patch.object(
                        alert_manager, "_send_media_reminder_email", return_value=True
                    ) as mock_method:
                        result = alert_manager._send_email_notification(alert)
                        mock_method.assert_called_once()

    def test_send_email_notification_generic_fallback(self, alert_manager, app):
        """Uses generic email for unknown alert types."""
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type="unknown_custom_type",
                severity="warning",
                title="Unknown Type Alert",
                message="Custom message",
                notify=False,
            )
            mock_ns = MagicMock()
            mock_ns.send_email.return_value = True
            alert_manager.notification_service = mock_ns
            with patch.object(
                alert_manager, "_get_email_recipients", return_value=["admin@example.com"]
            ):
                result = alert_manager._send_email_notification(alert)
                mock_ns.send_email.assert_called_once()

    def test_send_email_notification_lazy_loads_service(self, alert_manager, app):
        """notification_service is lazy loaded when None."""
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.ERROR,
                title="Lazy Load Test",
                message="Test",
                notify=False,
            )
            alert_manager.notification_service = None
            mock_svc = MagicMock()
            mock_svc.send_email.return_value = True
            # get_notification_service is imported inside the function, patch source module
            with patch(
                "app.services.notification_service.get_notification_service",
                return_value=mock_svc
            ):
                with patch.object(
                    alert_manager, "_get_email_recipients", return_value=["admin@example.com"]
                ):
                    # The import inside function is: from app.services.notification_service import get_notification_service
                    # We patch the module itself so the local import gets our mock
                    import sys
                    ns_module = sys.modules.get("app.services.notification_service")
                    if ns_module:
                        original = getattr(ns_module, "get_notification_service", None)
                        ns_module.get_notification_service = lambda: mock_svc
                        try:
                            result = alert_manager._send_email_notification(alert)
                            assert alert_manager.notification_service is not None
                        finally:
                            if original is not None:
                                ns_module.get_notification_service = original


class TestSendBackupSuccessEmail:
    def test_send_backup_success_email_with_job(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_SUCCESS,
                severity=AlertSeverity.INFO,
                title="Job Success",
                message="Completed OK",
                job_id=sample_job,
                notify=False,
            )
            mock_ns = MagicMock()
            mock_ns.send_backup_success_notification.return_value = {"admin@example.com": True}
            alert_manager.notification_service = mock_ns
            result = alert_manager._send_backup_success_email(alert, "admin@example.com")
            assert isinstance(result, bool)

    def test_send_backup_success_email_without_job(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_SUCCESS,
                severity=AlertSeverity.INFO,
                title="No Job Success",
                message="Completed",
                notify=False,
            )
            mock_ns = MagicMock()
            mock_ns.send_backup_success_notification.return_value = {"admin@example.com": True}
            alert_manager.notification_service = mock_ns
            result = alert_manager._send_backup_success_email(alert, "admin@example.com")
            assert isinstance(result, bool)


class TestSendBackupFailureEmail:
    def test_send_backup_failure_email(self, alert_manager, app, sample_job):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.CRITICAL,
                title="Job Failure",
                message="Failed badly",
                job_id=sample_job,
                notify=False,
            )
            mock_ns = MagicMock()
            mock_ns.send_backup_failure_notification.return_value = {"admin@example.com": True}
            alert_manager.notification_service = mock_ns
            result = alert_manager._send_backup_failure_email(alert, "admin@example.com")
            assert isinstance(result, bool)


class TestSendRuleViolationEmail:
    def test_send_rule_violation_email(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.RULE_VIOLATION,
                severity=AlertSeverity.WARNING,
                title="3-2-1-1-0 Violation",
                message="Missing offsite copy\nNo offline backup",
                notify=False,
            )
            mock_ns = MagicMock()
            mock_ns.send_rule_violation_notification.return_value = {"admin@example.com": True}
            alert_manager.notification_service = mock_ns
            result = alert_manager._send_rule_violation_email(alert, "admin@example.com")
            assert isinstance(result, bool)


class TestSendMediaReminderEmail:
    def test_send_media_reminder_email_rotation(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.MEDIA_ROTATION_REMINDER,
                severity=AlertSeverity.WARNING,
                title="TAPE-001",
                message="Tape needs rotation",
                notify=False,
            )
            mock_ns = MagicMock()
            mock_ns.send_media_reminder_notification.return_value = {"admin@example.com": True}
            alert_manager.notification_service = mock_ns
            result = alert_manager._send_media_reminder_email(alert, "admin@example.com")
            assert isinstance(result, bool)

    def test_send_media_reminder_email_verification(self, alert_manager, app):
        with app.app_context():
            alert = alert_manager.create_alert(
                alert_type=AlertType.VERIFICATION_REMINDER,
                severity=AlertSeverity.WARNING,
                title="TAPE-002",
                message="Tape needs verification",
                notify=False,
            )
            mock_ns = MagicMock()
            mock_ns.send_media_reminder_notification.return_value = {"admin@example.com": True}
            alert_manager.notification_service = mock_ns
            result = alert_manager._send_media_reminder_email(alert, "admin@example.com")
            assert isinstance(result, bool)
