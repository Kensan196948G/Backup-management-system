"""
Unit tests for business logic services

Tests for:
- ComplianceChecker: 3-2-1-1-0 rule validation
- AlertManager: Alert generation and management
- ReportGenerator: Report generation (HTML/CSV)
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    Alert,
    BackupCopy,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    OfflineMedia,
    Report,
    User,
    db,
)
from app.services import AlertManager, ComplianceChecker, ReportGenerator
from app.services.alert_manager import AlertSeverity, AlertType


class TestComplianceChecker:
    """Tests for ComplianceChecker service"""

    @pytest.fixture
    def checker(self):
        """Create ComplianceChecker instance"""
        return ComplianceChecker()

    @pytest.fixture
    def sample_job(self, app):
        """Create a sample backup job for testing"""
        with app.app_context():
            user = User(username="testuser", email="test@example.com", password_hash="hashed_password", role="admin")
            db.session.add(user)
            db.session.commit()

            job = BackupJob(
                job_name="Test Backup Job",
                job_type="database",
                target_server="DB-SERVER-01",
                backup_tool="veeam",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()

            yield job
            db.session.delete(job)
            db.session.delete(user)
            db.session.commit()

    def test_check_compliant_job(self, app, checker, sample_job):
        """Test checking a compliant 3-2-1-1-0 job"""
        with app.app_context():
            # Add 3 copies with different media types
            copies = [
                BackupCopy(
                    job_id=sample_job.id,
                    copy_type="primary",
                    media_type="disk",
                    storage_path="/backup/primary",
                    status="success",
                    last_backup_date=datetime.now(timezone.utc),
                ),
                BackupCopy(
                    job_id=sample_job.id,
                    copy_type="offsite",
                    media_type="cloud",
                    storage_path="s3://bucket/backup",
                    status="success",
                    last_backup_date=datetime.now(timezone.utc),
                ),
                BackupCopy(
                    job_id=sample_job.id,
                    copy_type="offline",
                    media_type="tape",
                    storage_path="TAPE-001",
                    status="success",
                    last_backup_date=datetime.now(timezone.utc),
                ),
            ]
            for copy in copies:
                db.session.add(copy)
            db.session.commit()

            # Check compliance
            result = checker.check_3_2_1_1_0(sample_job.id)

            assert result["compliant"] == True
            assert result["status"] == "compliant"
            assert result["copies_count"] == 3
            assert result["media_types_count"] == 3
            assert result["has_offsite"] == True
            assert result["has_offline"] == True
            assert result["has_errors"] == False
            assert len(result["violations"]) == 0

    def test_check_non_compliant_job(self, app, checker, sample_job):
        """Test checking a non-compliant job (only 1 copy)"""
        with app.app_context():
            # Add only 1 copy
            copy = BackupCopy(
                job_id=sample_job.id,
                copy_type="primary",
                media_type="disk",
                storage_path="/backup/primary",
                status="success",
                last_backup_date=datetime.now(timezone.utc),
            )
            db.session.add(copy)
            db.session.commit()

            # Check compliance
            result = checker.check_3_2_1_1_0(sample_job.id)

            assert result["compliant"] == False
            assert result["status"] == "non_compliant"
            assert result["copies_count"] == 1
            assert len(result["violations"]) > 0

    def test_check_warning_job(self, app, checker, sample_job):
        """Test checking a job with warnings (stale offline copy)"""
        with app.app_context():
            # Add 3 copies but offline copy is stale
            copies = [
                BackupCopy(
                    job_id=sample_job.id,
                    copy_type="primary",
                    media_type="disk",
                    storage_path="/backup/primary",
                    status="success",
                    last_backup_date=datetime.now(timezone.utc),
                ),
                BackupCopy(
                    job_id=sample_job.id,
                    copy_type="offsite",
                    media_type="cloud",
                    storage_path="s3://bucket/backup",
                    status="success",
                    last_backup_date=datetime.now(timezone.utc),
                ),
                BackupCopy(
                    job_id=sample_job.id,
                    copy_type="offline",
                    media_type="tape",
                    storage_path="TAPE-001",
                    status="success",
                    # Stale backup (older than warning threshold)
                    last_backup_date=datetime.now(timezone.utc) - timedelta(days=15),
                ),
            ]
            for copy in copies:
                db.session.add(copy)
            db.session.commit()

            # Check compliance
            result = checker.check_3_2_1_1_0(sample_job.id)

            assert result["compliant"] == False
            assert result["status"] == "warning"
            assert len(result["warnings"]) > 0

    def test_check_all_jobs(self, app, checker, sample_job):
        """Test checking compliance for all jobs"""
        with app.app_context():
            # Add a compliant copy
            copy = BackupCopy(
                job_id=sample_job.id,
                copy_type="primary",
                media_type="disk",
                storage_path="/backup/primary",
                status="success",
                last_backup_date=datetime.now(timezone.utc),
            )
            db.session.add(copy)
            db.session.commit()

            # Check all jobs
            result = checker.check_all_jobs()

            assert "total_jobs" in result
            assert "compliance_rate" in result
            assert "results" in result

    def test_compliance_history(self, app, checker, sample_job):
        """Test retrieving compliance history"""
        with app.app_context():
            # Create some history entries
            for i in range(3):
                status = ComplianceStatus(
                    job_id=sample_job.id,
                    check_date=datetime.now(timezone.utc) - timedelta(days=i),
                    copies_count=3,
                    media_types_count=2,
                    has_offsite=True,
                    has_offline=True,
                    has_errors=False,
                    overall_status="compliant",
                )
                db.session.add(status)
            db.session.commit()

            # Get history
            history = checker.get_compliance_history(sample_job.id, days=30)

            assert len(history) == 3


class TestAlertManager:
    """Tests for AlertManager service"""

    @pytest.fixture
    def manager(self):
        """Create AlertManager instance"""
        return AlertManager()

    @pytest.fixture
    def sample_job(self, app):
        """Create a sample backup job for testing"""
        with app.app_context():
            user = User(username="testuser", email="test@example.com", password_hash="hashed_password", role="admin")
            db.session.add(user)
            db.session.commit()

            job = BackupJob(
                job_name="Test Backup Job",
                job_type="database",
                target_server="DB-SERVER-01",
                backup_tool="veeam",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()

            yield job
            db.session.delete(job)
            db.session.delete(user)
            db.session.commit()

    def test_create_alert(self, app, manager, sample_job):
        """Test creating an alert"""
        with app.app_context():
            alert = manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                title="Backup Failed",
                message="Database backup failed due to network timeout",
                job_id=sample_job.id,
                notify=False,
            )

            assert alert.id is not None
            assert alert.alert_type == "backup_failed"
            assert alert.severity == "error"
            assert alert.title == "Backup Failed"
            assert alert.is_acknowledged == False

    def test_acknowledge_alert(self, app, manager, sample_job):
        """Test acknowledging an alert"""
        with app.app_context():
            alert = manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                title="Backup Failed",
                message="Test message",
                job_id=sample_job.id,
                notify=False,
            )

            # Get admin user
            admin = User.query.filter_by(role="admin").first()

            # Acknowledge alert
            acknowledged = manager.acknowledge_alert(alert.id, admin.id)

            assert acknowledged.is_acknowledged == True
            assert acknowledged.acknowledged_by == admin.id
            assert acknowledged.acknowledged_at is not None

    def test_get_unacknowledged_alerts(self, app, manager, sample_job):
        """Test retrieving unacknowledged alerts"""
        with app.app_context():
            # Create multiple alerts
            for i in range(3):
                manager.create_alert(
                    alert_type=AlertType.BACKUP_FAILED,
                    severity=AlertSeverity.ERROR,
                    title=f"Alert {i}",
                    message=f"Test message {i}",
                    job_id=sample_job.id,
                    notify=False,
                )

            # Get unacknowledged alerts
            alerts = manager.get_unacknowledged_alerts(limit=10)

            assert len(alerts) >= 3

    def test_get_alerts_by_job(self, app, manager, sample_job):
        """Test retrieving alerts for a specific job"""
        with app.app_context():
            # Create alerts for the job
            for i in range(2):
                manager.create_alert(
                    alert_type=AlertType.BACKUP_FAILED,
                    severity=AlertSeverity.ERROR,
                    title=f"Alert {i}",
                    message=f"Test message {i}",
                    job_id=sample_job.id,
                    notify=False,
                )

            # Get alerts for job
            alerts = manager.get_alerts_by_job(sample_job.id, days=30, limit=10)

            assert len(alerts) >= 2
            assert all(alert.job_id == sample_job.id for alert in alerts)

    @pytest.mark.skip(reason="_build_adaptive_card is in TeamsNotificationService, not AlertManager")
    def test_adaptive_card_generation(self, app, manager, sample_job):
        """Test Microsoft Teams Adaptive Card generation"""
        with app.app_context():
            alert = manager.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                title="Backup Failed",
                message="Test message",
                job_id=sample_job.id,
                notify=False,
            )

            card = manager._build_adaptive_card(alert)

            assert card["type"] == "AdaptiveCard"
            assert "body" in card
            assert len(card["body"]) > 0


class TestReportGenerator:
    """Tests for ReportGenerator service"""

    @pytest.fixture
    def generator(self, app):
        """Create ReportGenerator instance"""
        with app.app_context():
            return ReportGenerator()

    @pytest.fixture
    def sample_job(self, app):
        """Create a sample backup job for testing"""
        with app.app_context():
            user = User(username="testuser", email="test@example.com", password_hash="hashed_password", role="admin")
            db.session.add(user)
            db.session.commit()

            job = BackupJob(
                job_name="Test Backup Job",
                job_type="database",
                target_server="DB-SERVER-01",
                backup_tool="veeam",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()

            yield job
            # Delete reports before user (FK: reports.generated_by NOT NULL)
            Report.query.filter_by(generated_by=user.id).delete()
            db.session.delete(job)
            db.session.delete(user)
            db.session.commit()

    def test_generate_daily_html_report(self, app, generator, sample_job):
        """Test generating daily HTML report"""
        with app.app_context():
            # Add an execution record
            execution = BackupExecution(
                job_id=sample_job.id,
                execution_date=datetime.now(timezone.utc),
                execution_result="success",
                backup_size_bytes=1000000,
                duration_seconds=3600,
            )
            db.session.add(execution)
            db.session.commit()

            # Get admin user
            admin = User.query.filter_by(role="admin").first()

            # Generate report
            report = generator.generate_daily_report(generated_by=admin.id, format="html")

            assert report.id is not None
            assert report.report_type == "daily"
            assert report.file_format == "html"

    def test_generate_daily_csv_report(self, app, generator, sample_job):
        """Test generating daily CSV report"""
        with app.app_context():
            # Add an execution record
            execution = BackupExecution(
                job_id=sample_job.id,
                execution_date=datetime.now(timezone.utc),
                execution_result="success",
                backup_size_bytes=1000000,
                duration_seconds=3600,
            )
            db.session.add(execution)
            db.session.commit()

            # Get admin user
            admin = User.query.filter_by(role="admin").first()

            # Generate report
            report = generator.generate_daily_report(generated_by=admin.id, format="csv")

            assert report.id is not None
            assert report.report_type == "daily"
            assert report.file_format == "csv"

    def test_generate_compliance_report(self, app, generator, sample_job):
        """Test generating compliance report"""
        with app.app_context():
            # Add compliance status
            status = ComplianceStatus(
                job_id=sample_job.id,
                check_date=datetime.now(timezone.utc),
                copies_count=3,
                media_types_count=2,
                has_offsite=True,
                has_offline=True,
                has_errors=False,
                overall_status="compliant",
            )
            db.session.add(status)
            db.session.commit()

            # Get admin user
            admin = User.query.filter_by(role="admin").first()

            # Generate report
            report = generator.generate_compliance_report(generated_by=admin.id, format="html")

            assert report.id is not None
            assert report.report_type == "compliance"

    def test_cleanup_old_reports(self, app, generator):
        """Test cleaning up old reports"""
        with app.app_context():
            # Create admin user for this test
            user = User(username="cleanup_admin", email="cleanup@example.com", password_hash="hash", role="admin")
            db.session.add(user)
            db.session.commit()

            # Create old report
            old_report = Report(
                report_type="daily",
                report_title="Old Report",
                date_from=datetime.now(timezone.utc).date() - timedelta(days=120),
                date_to=datetime.now(timezone.utc).date() - timedelta(days=120),
                file_format="html",
                generated_by=user.id,
                created_at=datetime.now(timezone.utc) - timedelta(days=120),
            )
            db.session.add(old_report)
            db.session.commit()

            # Cleanup
            count = generator.cleanup_old_reports(days=90)

            # Old report should be deleted
            assert count >= 1
            db.session.delete(user)
            db.session.commit()


# Integration tests


class TestServiceIntegration:
    """Integration tests for multiple services"""

    def test_compliance_and_alert_workflow(self, app):
        """Test workflow: Check compliance -> Generate alert if non-compliant"""
        with app.app_context():
            checker = ComplianceChecker()
            manager = AlertManager()

            # Create test data
            user = User(username="testuser", email="test@example.com", password_hash="hashed_password", role="admin")
            db.session.add(user)
            db.session.commit()

            job = BackupJob(
                job_name="Test Backup Job",
                job_type="database",
                target_server="DB-SERVER-01",
                backup_tool="veeam",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()

            # Check compliance (should be non-compliant - no copies)
            result = checker.check_3_2_1_1_0(job.id)

            # Generate alert if non-compliant
            if not result["compliant"]:
                alert = manager.create_alert(
                    alert_type=AlertType.RULE_VIOLATION,
                    severity=AlertSeverity.WARNING,
                    title="3-2-1-1-0 Rule Violation",
                    message="Job does not meet 3-2-1-1-0 backup rule requirements",
                    job_id=job.id,
                    notify=False,
                )

                assert alert.id is not None
                assert alert.job_id == job.id
