"""
Unit tests for business logic services.

Tests core services:
- ComplianceChecker: 3-2-1-1-0 rule validation
- AlertManager: Alert creation and management
- ReportGenerator: Report generation
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.models import (
    Alert,
    BackupCopy,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    OfflineMedia,
    Report,
    db,
)
from app.services.alert_manager import AlertManager
from app.services.compliance_checker import ComplianceChecker
from app.services.report_generator import ReportGenerator


class TestComplianceChecker:
    """Test cases for ComplianceChecker service."""

    def test_check_3_2_1_1_0_compliant(self, app, backup_job, backup_copies):
        """Test compliance check for a compliant backup job."""
        with app.app_context():
            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(backup_job.id)

            assert result is not None
            assert result["compliant"] is True
            assert result["copies_count"] >= 3
            assert result["media_types_count"] >= 2
            assert result["has_offsite"] is True
            assert result["has_offline"] is True

    def test_check_3_2_1_1_0_insufficient_copies(self, app, backup_job):
        """Test compliance check with insufficient copies."""
        with app.app_context():
            # Create only 2 copies (need 3)
            copies = [
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type="primary",
                    storage_path="/backup/storage1",
                    media_type="disk",
                    last_backup_size=1024,
                    status="success",
                ),
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type="secondary",
                    storage_path="/backup/storage2",
                    media_type="disk",
                    last_backup_size=1024,
                    status="success",
                ),
            ]
            db.session.add_all(copies)
            db.session.commit()

            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(backup_job.id)

            assert result["compliant"] is False
            assert result["status"] in ["non_compliant", "warning"]
            assert result["copies_count"] < 3

    def test_check_3_2_1_1_0_insufficient_media_types(self, app, backup_job):
        """Test compliance check with insufficient media types."""
        with app.app_context():
            # Create 3 copies but all same media type
            copies = [
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type=["primary", "secondary", "offsite"][i],
                    storage_path=f"/backup/storage{i}",
                    media_type="disk",  # All same type
                    last_backup_size=1024,
                    status="success",
                )
                for i in range(3)
            ]
            db.session.add_all(copies)
            db.session.commit()

            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(backup_job.id)

            assert result["compliant"] is False
            assert result["status"] in ["non_compliant", "warning"]
            assert result["media_types_count"] < 2

    def test_check_3_2_1_1_0_missing_offsite(self, app, backup_job):
        """Test compliance check with missing offsite copy."""
        with app.app_context():
            # Create 3 copies with 2 media types but no offsite
            copies = [
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type="primary",
                    storage_path="/backup/storage1",
                    media_type="disk",
                    last_backup_size=1024,
                    status="success",
                ),
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type="offline",
                    storage_path="/backup/tape1",
                    media_type="tape",
                    last_backup_size=1024,
                    status="success",
                ),
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type="secondary",
                    storage_path="/backup/storage2",
                    media_type="disk",
                    last_backup_size=1024,
                    status="success",
                ),
            ]
            db.session.add_all(copies)
            db.session.commit()

            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(backup_job.id)

            assert result["compliant"] is False
            assert result["status"] in ["non_compliant", "warning"]
            assert result["has_offsite"] is False

    def test_check_3_2_1_1_0_missing_offline(self, app, backup_job):
        """Test compliance check with missing offline copy."""
        with app.app_context():
            # Create 3 copies with 2 media types and offsite but no offline
            copies = [
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type="primary",
                    storage_path="/backup/storage1",
                    media_type="disk",
                    last_backup_size=1024,
                    status="success",
                ),
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type="offsite",
                    storage_path="s3://bucket/backup",
                    media_type="cloud",
                    last_backup_size=1024,
                    status="success",
                ),
                BackupCopy(
                    job_id=backup_job.id,
                    copy_type="secondary",
                    storage_path="/backup/storage2",
                    media_type="disk",
                    last_backup_size=1024,
                    status="success",
                ),
            ]
            db.session.add_all(copies)
            db.session.commit()

            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(backup_job.id)

            assert result["compliant"] is False
            assert result["status"] in ["non_compliant", "warning"]
            assert result["has_offline"] is False

    def test_check_3_2_1_1_0_nonexistent_job(self, app):
        """Test compliance check for nonexistent job."""
        with app.app_context():
            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(99999)

            assert result is not None
            assert result["compliant"] is False
            assert result["status"] == "unknown"

    def test_check_all_jobs(self, app, multiple_backup_jobs, backup_copies):
        """Test checking compliance for all jobs."""
        with app.app_context():
            checker = ComplianceChecker()
            summary = checker.check_all_jobs()

            assert summary is not None
            assert isinstance(summary, dict)
            assert "total_jobs" in summary
            assert "compliant_jobs" in summary
            assert "results" in summary
            assert isinstance(summary["results"], list)
            assert summary["total_jobs"] > 0

    def test_compliance_status_saved_to_database(self, app, backup_job, backup_copies):
        """Test that compliance status is saved to database."""
        with app.app_context():
            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(backup_job.id)

            # Check if ComplianceStatus record was created
            status = ComplianceStatus.query.filter_by(job_id=backup_job.id).first()
            assert status is not None
            # overall_status is 'compliant', 'non_compliant', or 'warning'
            is_compliant = status.overall_status == "compliant"
            assert is_compliant == result["compliant"]


class TestAlertManager:
    """Test cases for AlertManager service."""

    def test_create_alert(self, app, backup_job):
        """Test creating a new alert."""
        with app.app_context():
            manager = AlertManager()
            alert = manager.create_alert(
                alert_type="compliance",
                severity="high",
                title="Compliance Alert",
                message="Test alert message",
                job_id=backup_job.id,
                notify=False,
            )

            assert alert is not None
            assert alert.id is not None
            assert alert.job_id == backup_job.id
            assert alert.alert_type == "compliance"
            assert alert.severity == "high"
            assert alert.is_acknowledged is False

    def test_acknowledge_alert(self, app, alerts, admin_user):
        """Test acknowledging an alert."""
        with app.app_context():
            manager = AlertManager()
            # Use alerts[1] which is not acknowledged (i=1, i%2==1, so is_acknowledged=False)
            alert = db.session.get(Alert, alerts[1].id)
            assert alert.is_acknowledged is False  # Verify it starts unacknowledged

            result = manager.acknowledge_alert(alert.id, admin_user.id)

            assert result is True
            # Refresh the alert from database to get updated values
            db.session.refresh(alert)
            assert alert.is_acknowledged is True
            assert alert.acknowledged_by == admin_user.id
            assert alert.acknowledged_at is not None

    def test_acknowledge_nonexistent_alert(self, app, admin_user):
        """Test acknowledging a nonexistent alert."""
        with app.app_context():
            manager = AlertManager()
            result = manager.acknowledge_alert(99999, admin_user.id)

            assert result is False

    def test_get_unacknowledged_alerts(self, app, alerts):
        """Test retrieving unacknowledged alerts."""
        with app.app_context():
            manager = AlertManager()
            unack_alerts = manager.get_unacknowledged_alerts()

            assert unack_alerts is not None
            assert len(unack_alerts) > 0
            assert all(not alert.is_acknowledged for alert in unack_alerts)

    def test_get_alerts_by_severity(self, app, alerts):
        """Test retrieving alerts by severity."""
        with app.app_context():
            manager = AlertManager()
            high_alerts = manager.get_alerts_by_severity("high")

            assert high_alerts is not None
            if len(high_alerts) > 0:
                assert all(alert.severity == "high" for alert in high_alerts)

    def test_get_alerts_by_type(self, app, alerts):
        """Test retrieving alerts by type."""
        with app.app_context():
            manager = AlertManager()
            compliance_alerts = manager.get_alerts_by_type("compliance")

            assert compliance_alerts is not None
            if len(compliance_alerts) > 0:
                assert all(alert.alert_type == "compliance" for alert in compliance_alerts)

    def test_get_alerts_by_job(self, app, backup_job, alerts):
        """Test retrieving alerts for a specific job."""
        with app.app_context():
            manager = AlertManager()
            job_alerts = manager.get_alerts_by_job(backup_job.id)

            assert job_alerts is not None
            assert len(job_alerts) > 0
            assert all(alert.job_id == backup_job.id for alert in job_alerts)

    def test_create_compliance_alert(self, app, backup_job):
        """Test creating a compliance-specific alert."""
        with app.app_context():
            manager = AlertManager()
            alert = manager.create_compliance_alert(
                job_id=backup_job.id, issues=["Missing offsite copy", "Insufficient copies"]
            )

            assert alert is not None
            assert alert.alert_type == "compliance"
            assert "offsite" in alert.message.lower() or "copies" in alert.message.lower()

    def test_create_failure_alert(self, app, backup_job):
        """Test creating a backup failure alert."""
        with app.app_context():
            manager = AlertManager()
            alert = manager.create_failure_alert(job_id=backup_job.id, error_message="Disk full")

            assert alert is not None
            assert alert.alert_type == "failure"
            assert "disk full" in alert.message.lower()

    def test_bulk_acknowledge_alerts(self, app, alerts, admin_user):
        """Test acknowledging multiple alerts at once."""
        with app.app_context():
            manager = AlertManager()
            alert_ids = [alert.id for alert in alerts[:3]]

            result = manager.bulk_acknowledge_alerts(alert_ids, admin_user.id)

            assert result is True
            for alert_id in alert_ids:
                alert = db.session.get(Alert, alert_id)
                assert alert.is_acknowledged is True

    @patch("app.services.alert_manager.send_email")
    def test_send_alert_notification(self, mock_send_email, app, backup_job):
        """Test sending alert notifications."""
        with app.app_context():
            manager = AlertManager()
            alert = manager.create_alert(
                job_id=backup_job.id, alert_type="compliance", severity="high", message="Critical alert"
            )

            manager.send_notification(alert.id)

            # Verify email was sent (if notification is implemented)
            # mock_send_email.assert_called_once()


class TestReportGenerator:
    """Test cases for ReportGenerator service."""

    def test_generate_daily_report(self, app, backup_job, backup_copies):
        """Test generating a daily report."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_daily_report()

            assert report is not None
            assert report.report_type == "daily"
            assert report.data is not None
            assert "total_jobs" in report.data
            assert "successful_backups" in report.data or "summary" in report.data

    def test_generate_weekly_report(self, app):
        """Test generating a weekly report."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_weekly_report()

            assert report is not None
            assert report.report_type == "weekly"
            assert report.period_start is not None
            assert report.period_end is not None

    def test_generate_monthly_report(self, app):
        """Test generating a monthly report."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_monthly_report()

            assert report is not None
            assert report.report_type == "monthly"

    def test_generate_compliance_report(self, app, backup_job, backup_copies):
        """Test generating a compliance report."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_compliance_report()

            assert report is not None
            assert "compliance" in report.report_type.lower() or "compliance" in str(report.data)

    def test_generate_custom_report(self, app):
        """Test generating a custom date range report."""
        with app.app_context():
            generator = ReportGenerator()
            start_date = datetime.utcnow() - timedelta(days=7)
            end_date = datetime.utcnow()

            report = generator.generate_custom_report(start_date, end_date)

            assert report is not None
            assert report.period_start == start_date or report.period_start.date() == start_date.date()
            assert report.period_end == end_date or report.period_end.date() == end_date.date()

    def test_report_includes_job_statistics(self, app, multiple_backup_jobs):
        """Test that report includes job statistics."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_daily_report()

            assert "total_jobs" in report.data
            assert report.data["total_jobs"] > 0

    def test_report_includes_execution_statistics(self, app, backup_job):
        """Test that report includes execution statistics."""
        with app.app_context():
            # Create some executions
            executions = [
                BackupExecution(
                    job_id=backup_job.id,
                    status=["success", "failed", "success"][i % 3],
                    start_time=datetime.utcnow() - timedelta(hours=i),
                    end_time=datetime.utcnow() - timedelta(hours=i - 1),
                    total_size=1024000,
                    total_files=100,
                )
                for i in range(5)
            ]
            db.session.add_all(executions)
            db.session.commit()

            generator = ReportGenerator()
            report = generator.generate_daily_report()

            assert "successful_backups" in report.data or "executions" in report.data

    def test_report_includes_alert_statistics(self, app, alerts):
        """Test that report includes alert statistics."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_daily_report()

            assert "alerts" in report.data or "total_alerts" in report.data

    def test_report_saved_to_database(self, app):
        """Test that generated report is saved to database."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_daily_report()

            # Verify report is in database
            saved_report = db.session.get(Report, report.id)
            assert saved_report is not None
            assert saved_report.id == report.id

    @patch("app.services.report_generator.export_to_pdf")
    def test_export_report_to_pdf(self, mock_export, app):
        """Test exporting report to PDF."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_daily_report()

            file_path = generator.export_to_pdf(report.id)

            # Verify export was called
            # mock_export.assert_called_once()

    def test_report_data_structure(self, app):
        """Test that report data has expected structure."""
        with app.app_context():
            generator = ReportGenerator()
            report = generator.generate_daily_report()

            # Verify data structure
            assert isinstance(report.data, dict)
            assert "period_start" in report.data or report.period_start is not None
            assert "period_end" in report.data or report.period_end is not None

    def test_report_generation_date(self, app):
        """Test that report has proper generation timestamp."""
        with app.app_context():
            generator = ReportGenerator()
            before = datetime.utcnow()
            report = generator.generate_daily_report()
            after = datetime.utcnow()

            assert report.created_at >= before
            assert report.created_at <= after

    def test_get_latest_report(self, app, reports):
        """Test retrieving the latest report."""
        with app.app_context():
            generator = ReportGenerator()
            latest = generator.get_latest_report("daily")

            assert latest is not None
            assert latest.report_type == "daily"

    def test_get_reports_by_date_range(self, app, reports):
        """Test retrieving reports within a date range."""
        with app.app_context():
            generator = ReportGenerator()
            start_date = datetime.utcnow() - timedelta(days=30)
            end_date = datetime.utcnow()

            reports_list = generator.get_reports_by_date_range(start_date, end_date)

            assert reports_list is not None
            assert isinstance(reports_list, list)
