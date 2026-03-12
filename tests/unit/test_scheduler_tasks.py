"""
Unit tests for app/scheduler/tasks.py
Covers all scheduled task functions with mocked services.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app import create_app


# ---------------------------------------------------------------------------
# Fixture: app with testing config
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app(app):
    return app


# ---------------------------------------------------------------------------
# Tests: check_compliance_status
# ---------------------------------------------------------------------------

class TestCheckComplianceStatus:

    def test_runs_for_active_jobs(self, test_app):
        from app.scheduler.tasks import check_compliance_status

        mock_job1 = MagicMock()
        mock_job1.id = 1
        mock_job2 = MagicMock()
        mock_job2.id = 2

        with patch("app.models.BackupJob") as MockJob, \
             patch("app.models.db") as mock_db, \
             patch("app.services.compliance_checker.ComplianceChecker") as MockChecker, \
             patch("app.services.alert_manager.AlertManager") as MockAlert:

            from app.models import BackupJob, db
            BackupJob.query.filter_by.return_value.all.return_value = [mock_job1, mock_job2]

            mock_checker = MagicMock()
            mock_checker.check_3_2_1_1_0.return_value = {"status": "compliant"}
            MockChecker.return_value = mock_checker

            mock_alert = MagicMock()
            MockAlert.return_value = mock_alert

            check_compliance_status(test_app)

    def test_creates_alert_for_non_compliant(self, test_app):
        from app.scheduler.tasks import check_compliance_status
        from app.models import BackupJob, db

        mock_job = MagicMock()
        mock_job.id = 1

        original_query = BackupJob.query

        try:
            mock_q = MagicMock()
            mock_q.filter_by.return_value.all.return_value = [mock_job]
            BackupJob.query = mock_q

            with patch("app.services.compliance_checker.ComplianceChecker") as MockChecker, \
                 patch("app.services.alert_manager.AlertManager") as MockAlert:

                mock_checker = MagicMock()
                mock_checker.check_3_2_1_1_0.return_value = {"status": "non_compliant"}
                MockChecker.return_value = mock_checker

                mock_alert_svc = MagicMock()
                MockAlert.return_value = mock_alert_svc

                check_compliance_status(test_app)
        finally:
            BackupJob.query = original_query

    def test_handles_exception(self, test_app):
        from app.scheduler.tasks import check_compliance_status
        from app.models import BackupJob, db

        original_query = BackupJob.query
        try:
            mock_q = MagicMock()
            mock_q.filter_by.return_value.all.side_effect = Exception("DB error")
            BackupJob.query = mock_q

            # Should not raise
            check_compliance_status(test_app)
        finally:
            BackupJob.query = original_query


# ---------------------------------------------------------------------------
# Tests: check_offline_media_updates
# ---------------------------------------------------------------------------

class TestCheckOfflineMediaUpdates:

    def test_creates_alert_for_outdated_media(self, test_app):
        from app.scheduler.tasks import check_offline_media_updates
        from app.models import OfflineMedia

        mock_media = MagicMock()
        mock_media.id = 1

        original_query = OfflineMedia.query
        try:
            mock_q = MagicMock()
            mock_q.filter.return_value.all.return_value = [mock_media]
            OfflineMedia.query = mock_q

            with patch("app.services.alert_manager.AlertManager") as MockAlert:
                mock_alert = MagicMock()
                MockAlert.return_value = mock_alert

                check_offline_media_updates(test_app)
        finally:
            OfflineMedia.query = original_query

    def test_no_outdated_media(self, test_app):
        from app.scheduler.tasks import check_offline_media_updates
        from app.models import OfflineMedia

        original_query = OfflineMedia.query
        try:
            mock_q = MagicMock()
            mock_q.filter.return_value.all.return_value = []
            OfflineMedia.query = mock_q

            with patch("app.services.alert_manager.AlertManager") as MockAlert:
                mock_alert = MagicMock()
                MockAlert.return_value = mock_alert

                check_offline_media_updates(test_app)
                mock_alert.create_media_update_alert.assert_not_called()
        finally:
            OfflineMedia.query = original_query

    def test_handles_exception(self, test_app):
        from app.scheduler.tasks import check_offline_media_updates
        from app.models import OfflineMedia

        original_query = OfflineMedia.query
        try:
            mock_q = MagicMock()
            mock_q.filter.side_effect = Exception("DB error")
            OfflineMedia.query = mock_q

            # Should not raise
            check_offline_media_updates(test_app)
        finally:
            OfflineMedia.query = original_query


# ---------------------------------------------------------------------------
# Tests: check_verification_reminders
# ---------------------------------------------------------------------------

class TestCheckVerificationReminders:

    def test_sends_reminders(self, test_app):
        from app.scheduler.tasks import check_verification_reminders
        from app.models import VerificationSchedule

        mock_schedule = MagicMock()
        mock_schedule.id = 1

        original_query = VerificationSchedule.query
        try:
            mock_q = MagicMock()
            mock_q.filter.return_value.all.return_value = [mock_schedule]
            VerificationSchedule.query = mock_q

            with patch("app.services.alert_manager.AlertManager") as MockAlert:
                mock_alert = MagicMock()
                MockAlert.return_value = mock_alert

                check_verification_reminders(test_app)
                mock_alert.create_verification_reminder.assert_called_once()
        finally:
            VerificationSchedule.query = original_query

    def test_no_upcoming_tests(self, test_app):
        from app.scheduler.tasks import check_verification_reminders
        from app.models import VerificationSchedule

        original_query = VerificationSchedule.query
        try:
            mock_q = MagicMock()
            mock_q.filter.return_value.all.return_value = []
            VerificationSchedule.query = mock_q

            with patch("app.services.alert_manager.AlertManager") as MockAlert:
                mock_alert = MagicMock()
                MockAlert.return_value = mock_alert

                check_verification_reminders(test_app)
                mock_alert.create_verification_reminder.assert_not_called()
        finally:
            VerificationSchedule.query = original_query

    def test_handles_exception(self, test_app):
        from app.scheduler.tasks import check_verification_reminders
        from app.models import VerificationSchedule

        original_query = VerificationSchedule.query
        try:
            mock_q = MagicMock()
            mock_q.filter.side_effect = Exception("error")
            VerificationSchedule.query = mock_q

            # Should not raise
            check_verification_reminders(test_app)
        finally:
            VerificationSchedule.query = original_query


# ---------------------------------------------------------------------------
# Tests: cleanup_old_logs
# ---------------------------------------------------------------------------

class TestCleanupOldLogs:

    def test_cleans_audit_and_execution_logs(self, test_app):
        from app.scheduler.tasks import cleanup_old_logs
        from app.models import AuditLog, BackupExecution, db

        orig_audit_query = AuditLog.query
        orig_exec_query = BackupExecution.query
        try:
            mock_aq = MagicMock()
            mock_aq.filter.return_value.delete.return_value = 5
            AuditLog.query = mock_aq

            mock_eq = MagicMock()
            mock_eq.filter.return_value.delete.return_value = 3
            BackupExecution.query = mock_eq

            cleanup_old_logs(test_app)

        finally:
            AuditLog.query = orig_audit_query
            BackupExecution.query = orig_exec_query

    def test_handles_exception(self, test_app):
        from app.scheduler.tasks import cleanup_old_logs
        from app.models import AuditLog

        original_query = AuditLog.query
        try:
            mock_q = MagicMock()
            mock_q.filter.side_effect = Exception("DB error")
            AuditLog.query = mock_q

            # Should not raise
            cleanup_old_logs(test_app)
        finally:
            AuditLog.query = original_query


# ---------------------------------------------------------------------------
# Tests: generate_daily_report
# ---------------------------------------------------------------------------

class TestGenerateDailyReport:

    def test_sends_report_to_admins(self, test_app):
        from app.scheduler.tasks import generate_daily_report
        from app.models import BackupJob, BackupExecution, ComplianceStatus, User, Alert

        mock_exec = MagicMock()
        mock_exec.execution_result = "success"
        mock_exec.backup_size_bytes = 1024 * 1024 * 1024
        mock_exec.job = MagicMock()
        mock_exec.job.job_name = "Test Job"
        mock_exec.error_message = None

        mock_cs = MagicMock()
        mock_cs.overall_status = "compliant"

        mock_user = MagicMock()
        mock_user.email = "admin@example.com"

        mock_alert_obj = MagicMock()
        mock_alert_obj.severity = "warning"
        mock_alert_obj.title = "Test alert"
        mock_alert_obj.created_at = datetime.now(timezone.utc)

        orig_job_query = BackupJob.query
        orig_exec_query = BackupExecution.query
        orig_cs_query = ComplianceStatus.query
        orig_user_query = User.query
        orig_alert_query = Alert.query

        try:
            mock_jq = MagicMock()
            mock_jq.filter_by.return_value.count.return_value = 5
            BackupJob.query = mock_jq

            mock_eq = MagicMock()
            mock_eq.filter.return_value.all.return_value = [mock_exec]
            BackupExecution.query = mock_eq

            mock_csq = MagicMock()
            mock_csq.all.return_value = [mock_cs]
            ComplianceStatus.query = mock_csq

            mock_uq = MagicMock()
            mock_uq.filter.return_value.all.return_value = [mock_user]
            User.query = mock_uq

            mock_aq = MagicMock()
            mock_aq.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_alert_obj]
            Alert.query = mock_aq

            with patch("app.services.notification_service.get_notification_service") as MockNotif:
                mock_notif_svc = MagicMock()
                mock_notif_svc.send_daily_report.return_value = {"admin@example.com": True}
                MockNotif.return_value = mock_notif_svc

                generate_daily_report(test_app)

        finally:
            BackupJob.query = orig_job_query
            BackupExecution.query = orig_exec_query
            ComplianceStatus.query = orig_cs_query
            User.query = orig_user_query
            Alert.query = orig_alert_query

    def test_no_admin_recipients(self, test_app):
        from app.scheduler.tasks import generate_daily_report
        from app.models import BackupJob, BackupExecution, ComplianceStatus, User, Alert

        orig_job_query = BackupJob.query
        orig_exec_query = BackupExecution.query
        orig_cs_query = ComplianceStatus.query
        orig_user_query = User.query
        orig_alert_query = Alert.query

        try:
            mock_jq = MagicMock()
            mock_jq.filter_by.return_value.count.return_value = 0
            BackupJob.query = mock_jq

            mock_eq = MagicMock()
            mock_eq.filter.return_value.all.return_value = []
            BackupExecution.query = mock_eq

            mock_csq = MagicMock()
            mock_csq.all.return_value = []
            ComplianceStatus.query = mock_csq

            mock_uq = MagicMock()
            mock_uq.filter.return_value.all.return_value = []
            User.query = mock_uq

            mock_aq = MagicMock()
            mock_aq.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = []
            Alert.query = mock_aq

            generate_daily_report(test_app)

        finally:
            BackupJob.query = orig_job_query
            BackupExecution.query = orig_exec_query
            ComplianceStatus.query = orig_cs_query
            User.query = orig_user_query
            Alert.query = orig_alert_query

    def test_handles_exception(self, test_app):
        from app.scheduler.tasks import generate_daily_report
        from app.models import BackupJob

        original_query = BackupJob.query
        try:
            mock_q = MagicMock()
            mock_q.filter_by.return_value.count.side_effect = Exception("DB error")
            BackupJob.query = mock_q

            # Should not raise
            generate_daily_report(test_app)
        finally:
            BackupJob.query = original_query


# ---------------------------------------------------------------------------
# Tests: cleanup_verification_test_data
# ---------------------------------------------------------------------------

class TestCleanupVerificationTestData:

    def test_deletes_old_records(self, test_app):
        from app.scheduler.tasks import cleanup_verification_test_data
        from app.models import VerificationTest, db

        original_query = VerificationTest.query
        try:
            mock_q = MagicMock()
            mock_q.filter.return_value.delete.return_value = 10
            VerificationTest.query = mock_q

            cleanup_verification_test_data(test_app)

        finally:
            VerificationTest.query = original_query

    def test_handles_exception(self, test_app):
        from app.scheduler.tasks import cleanup_verification_test_data
        from app.models import VerificationTest

        original_query = VerificationTest.query
        try:
            mock_q = MagicMock()
            mock_q.filter.side_effect = Exception("DB error")
            VerificationTest.query = mock_q

            # Should not raise
            cleanup_verification_test_data(test_app)
        finally:
            VerificationTest.query = original_query
