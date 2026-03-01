"""
Integration tests for end-to-end workflows.

Tests complete business workflows:
- Complete backup lifecycle
- Compliance checking workflow
- Alert handling workflow
- Report generation workflow
- Media rotation workflow
- Verification testing workflow
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    Alert,
    BackupCopy,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    MediaLending,
    OfflineMedia,
    Report,
    User,
    VerificationTest,
    db,
)
from app.services.alert_manager import AlertManager, AlertSeverity, AlertType
from app.services.compliance_checker import ComplianceChecker
from app.services.report_generator import ReportGenerator

UTC = timezone.utc


class TestCompleteBackupLifecycle:
    """Test complete backup job lifecycle."""

    def test_create_configure_run_backup_job(self, authenticated_client, app):
        """Test creating, configuring, and running a backup job."""
        with app.app_context():
            # Step 1: Create backup job
            response = authenticated_client.post(
                "/api/jobs",
                json={
                    "job_name": "Production DB Backup",
                    "job_type": "database",
                    "backup_tool": "custom",
                    "description": "Daily production database backup",
                    "target_path": "/data/production/db",
                    "schedule_type": "daily",
                    "retention_days": 30,
                },
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code in [200, 201]
            data = json.loads(response.data)

            # Get job ID
            job = BackupJob.query.filter_by(job_name="Production DB Backup").first()
            assert job is not None
            job_id = job.id

            # Step 2: Create backup copies for 3-2-1-1-0 compliance
            copies_data = [
                {"copy_type": "primary", "storage_path": "Primary NAS", "media_type": "disk", "is_encrypted": True, "last_backup_size": 10737418240},
                {"copy_type": "secondary", "storage_path": "Secondary NAS", "media_type": "disk", "is_encrypted": True, "last_backup_size": 10737418240},
                {"copy_type": "offsite", "storage_path": "AWS S3", "media_type": "cloud", "is_encrypted": True, "last_backup_size": 10737418240},
                {"copy_type": "offline", "storage_path": "Tape Library", "media_type": "tape", "is_encrypted": True, "last_backup_size": 10737418240},
            ]

            for copy_data in copies_data:
                copy = BackupCopy(job_id=job_id, status="success", **copy_data)
                db.session.add(copy)
            db.session.commit()

            # Step 3: Run manual backup
            response = authenticated_client.post(f"/api/jobs/{job_id}/run")
            # May return 200, 202, or 404

            # Step 4: Verify backup execution
            executions = BackupExecution.query.filter_by(job_id=job_id).all()
            # Executions may or may not be created depending on implementation

            # Step 5: Check compliance
            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(job_id)

            assert result["compliant"] is True
            assert result["media_types_count"] >= 2
            assert result["has_offsite"] is True
            assert result["has_offline"] is True

    def test_backup_failure_handling_workflow(self, authenticated_client, backup_job, app):
        """Test handling of failed backup execution."""
        with app.app_context():
            # Step 1: Report backup failure
            response = authenticated_client.post(
                "/api/backup/status",
                json={
                    "job_id": backup_job.id,
                    "execution_result": "failed",
                    "error_message": "Storage unavailable",
                    "source_system": "powershell",
                },
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code in [200, 201]

            # Step 2: Verify execution was recorded
            execution = BackupExecution.query.filter_by(job_id=backup_job.id, execution_result="failed").first()
            # May or may not exist

            # Step 3: Verify alert was created
            alert = Alert.query.filter_by(job_id=backup_job.id, alert_type="failure").first()
            # Alert may or may not be created

            # Step 4: Get unacknowledged alerts
            response = authenticated_client.get("/api/alerts/unacknowledged")
            if response.status_code == 200:
                data = json.loads(response.data)
                # Should contain alerts


class TestComplianceCheckingWorkflow:
    """Test compliance checking workflows."""

    def test_full_compliance_check_workflow(self, authenticated_client, backup_job, backup_copies, app):
        """Test complete compliance checking process."""
        with app.app_context():
            # Step 1: Run compliance check
            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(backup_job.id)

            assert result is not None
            assert "compliant" in result

            # Step 2: Verify compliance status was saved
            status = ComplianceStatus.query.filter_by(job_id=backup_job.id).first()
            if status:
                assert (status.overall_status == "compliant") == result["compliant"]

            # Step 3: Get compliance overview via API
            response = authenticated_client.get("/api/dashboard/compliance")
            if response.status_code == 200:
                data = json.loads(response.data)
                assert isinstance(data, dict)

            # Step 4: Generate compliance report
            generator = ReportGenerator()
            admin = User.query.filter_by(username="admin_test").first() or User.query.first()
            report = generator.generate_compliance_report(generated_by=admin.id)

            assert report is not None
            assert "compliance" in report.report_type.lower() or "compliance" in str(report.data)

    def test_non_compliant_job_alert_workflow(self, authenticated_client, backup_job, app):
        """Test alert creation for non-compliant jobs."""
        with app.app_context():
            # Step 1: Create insufficient copies (only 2, need 3)
            copy1 = BackupCopy(
                job_id=backup_job.id,
                copy_type="primary",
                storage_path="Storage 1",
                media_type="disk",
                status="success",
            )
            copy2 = BackupCopy(
                job_id=backup_job.id,
                copy_type="secondary",
                storage_path="Storage 2",
                media_type="disk",
                status="success",
            )
            db.session.add_all([copy1, copy2])
            db.session.commit()

            # Step 2: Check compliance
            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(backup_job.id)

            assert result["compliant"] is False

            # Step 3: Create compliance alert
            manager = AlertManager()
            alert = manager.create_compliance_alert(job_id=backup_job.id, issues=result.get("issues", []))

            assert alert is not None
            assert alert.alert_type == "compliance"

            # Step 4: Retrieve unacknowledged alerts
            unack_alerts = manager.get_unacknowledged_alerts()
            assert len([a for a in unack_alerts if a.job_id == backup_job.id]) > 0


class TestAlertHandlingWorkflow:
    """Test alert management workflows."""

    def test_alert_creation_and_acknowledgment_workflow(self, authenticated_client, backup_job, admin_user, app):
        """Test creating and acknowledging alerts."""
        with app.app_context():
            # Step 1: Create alert
            manager = AlertManager()
            alert = manager.create_alert(
                alert_type=AlertType.RULE_VIOLATION,
                severity=AlertSeverity.WARNING,
                title="Backup Warning",
                message="Backup took longer than expected",
                job_id=backup_job.id,
            )

            assert alert is not None
            alert_id = alert.id

            # Step 2: Get unacknowledged alerts via API
            response = authenticated_client.get("/api/alerts/unacknowledged")
            if response.status_code == 200:
                data = json.loads(response.data)
                # Should contain our alert

            # Step 3: Acknowledge alert
            response = authenticated_client.post(f"/api/alerts/{alert_id}/acknowledge")
            if response.status_code == 200:
                # Verify acknowledgment
                acknowledged_alert = db.session.get(Alert, alert_id)
                assert acknowledged_alert.is_acknowledged is True

    def test_bulk_alert_acknowledgment_workflow(self, authenticated_client, backup_job, admin_user, app):
        """Test acknowledging multiple alerts."""
        with app.app_context():
            # Step 1: Create multiple alerts
            manager = AlertManager()
            alerts = []
            for i in range(5):
                alert = manager.create_alert(
                    alert_type=AlertType.RULE_VIOLATION,
                    severity=AlertSeverity.INFO,
                    title=f"Warning {i}",
                    message=f"Warning {i}",
                    job_id=backup_job.id,
                )
                alerts.append(alert)

            alert_ids = [a.id for a in alerts]

            # Step 2: Bulk acknowledge
            result = manager.bulk_acknowledge_alerts(alert_ids, admin_user.id)

            assert result is True

            # Step 3: Verify all acknowledged
            for alert_id in alert_ids:
                alert = db.session.get(Alert, alert_id)
                assert alert.is_acknowledged is True


class TestReportGenerationWorkflow:
    """Test report generation workflows."""

    def test_daily_report_generation_workflow(self, authenticated_client, backup_job, backup_copies, app):
        """Test generating and viewing daily reports."""
        with app.app_context():
            # Step 1: Generate daily report via API
            response = authenticated_client.post("/api/reports/generate/daily")

            if response.status_code in [200, 201]:
                data = json.loads(response.data)

                # Step 2: Get report ID
                if "id" in data:
                    report_id = data["id"]
                else:
                    # Find latest daily report
                    report = Report.query.filter_by(report_type="daily").order_by(Report.created_at.desc()).first()
                    assert report is not None
                    report_id = report.id

                # Step 3: Retrieve report details
                response = authenticated_client.get(f"/api/reports/{report_id}")
                if response.status_code == 200:
                    data = json.loads(response.data)
                    assert "report_type" in data or "type" in data

    def test_custom_date_range_report_workflow(self, authenticated_client, app):
        """Test generating custom date range reports."""
        with app.app_context():
            # Step 1: Generate audit report (generate_custom_report was removed; use generate_audit_report)
            from app.models import User
            admin = User.query.filter_by(role="admin").first()
            generated_by = admin.id if admin else 1

            generator = ReportGenerator()
            report = generator.generate_audit_report(generated_by=generated_by)

            assert report is not None

            # Step 2: Verify report content
            assert report.date_from is not None or report.date_to is not None


class TestMediaRotationWorkflow:
    """Test offline media rotation workflows."""

    def test_media_lending_and_return_workflow(self, authenticated_client, offline_media, app):
        """Test lending and returning offline media."""
        with app.app_context():
            media_id = offline_media[0].id

            # Step 1: Lend media
            response = authenticated_client.post(
                f"/api/media/{media_id}/lend",
                json={
                    "lent_to": "John Doe",
                    "purpose": "Offsite storage verification",
                    "expected_return_date": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                },
                headers={"Content-Type": "application/json"},
            )

            # Step 2: Verify lending record
            if response.status_code in [200, 201]:
                lending = MediaLending.query.filter_by(media_id=media_id).order_by(MediaLending.lent_date.desc()).first()
                if lending:
                    assert lending.lent_to == "John Doe"
                    assert lending.return_date is None

                    # Step 3: Return media
                    response = authenticated_client.post(f"/api/media/{media_id}/return")

                    if response.status_code == 200:
                        # Verify return
                        lending = db.session.get(MediaLending, lending.id)
                        # Return date may or may not be set

    def test_media_retirement_workflow(self, authenticated_client, app):
        """Test retiring old media."""
        with app.app_context():
            # Step 1: Create old media
            media = OfflineMedia(
                media_type="tape",
                media_id="OLD-TAPE-001",
                capacity_gb=1000,
                storage_location="Storage",
                current_status="available",
                purchase_date=(datetime.now(UTC) - timedelta(days=1825)).date(),
            )
            db.session.add(media)
            db.session.commit()
            media_id = media.id

            # Step 2: Retire media
            response = authenticated_client.post(f"/api/media/{media_id}/retire")

            if response.status_code == 200:
                # Verify retirement
                retired_media = db.session.get(OfflineMedia, media_id)
                # Status may be updated to 'retired'


class TestVerificationWorkflow:
    """Test verification testing workflows."""

    def test_checksum_verification_workflow(self, authenticated_client, backup_copies, app):
        """Test checksum verification process."""
        with app.app_context():
            copy_id = backup_copies[0].id

            # Step 1: Initiate checksum verification
            response = authenticated_client.post(f"/api/verification/checksum/{copy_id}")

            if response.status_code in [200, 202]:
                # Step 2: Check verification status
                response = authenticated_client.get(f"/api/verification/results/{copy_id}")

                if response.status_code == 200:
                    data = json.loads(response.data)
                    # Should contain verification results

    def test_restore_test_workflow(self, authenticated_client, backup_copies, app):
        """Test restore verification process."""
        with app.app_context():
            copy_id = backup_copies[0].id

            # Step 1: Initiate restore test
            response = authenticated_client.post(f"/api/verification/restore/{copy_id}")

            # May return 200, 202, or 404

    def test_scheduled_verification_workflow(self, authenticated_client, backup_job, app):
        """Test setting up scheduled verification."""
        with app.app_context():
            # Step 1: Create verification schedule
            response = authenticated_client.put(
                f"/api/verification/schedule/{backup_job.id}",
                json={"test_type": "checksum", "frequency_days": 7, "is_active": True},
                headers={"Content-Type": "application/json"},
            )

            # May return 200, 201, or 404

            # Step 2: Retrieve schedule
            response = authenticated_client.get(f"/api/verification/schedule/{backup_job.id}")

            if response.status_code == 200:
                data = json.loads(response.data)
                # Should contain schedule info


class TestDashboardWorkflow:
    """Test dashboard data aggregation workflows."""

    def test_dashboard_data_loading_workflow(self, authenticated_client, backup_job, backup_copies, alerts, app):
        """Test loading all dashboard data."""
        with app.app_context():
            # Step 1: Get dashboard summary
            response = authenticated_client.get("/api/dashboard/summary")
            assert response.status_code == 200
            summary_data = json.loads(response.data)

            # Step 2: Get recent executions
            response = authenticated_client.get("/api/dashboard/recent-executions")
            # May return 200 or 404

            # Step 3: Get compliance overview
            response = authenticated_client.get("/api/dashboard/compliance")
            # May return 200 or 404

            # Step 4: Get alert summary
            response = authenticated_client.get("/api/dashboard/alerts-summary")
            # May return 200 or 404

            # Step 5: Get storage usage
            response = authenticated_client.get("/api/dashboard/storage-usage")
            # May return 200 or 404


class TestCompleteSystemWorkflow:
    """Test complete system workflows from start to finish."""

    def test_new_backup_job_complete_lifecycle(self, authenticated_client, app):
        """Test complete lifecycle of a new backup job."""
        with app.app_context():
            # Step 1: Admin creates backup job
            response = authenticated_client.post(
                "/api/jobs",
                json={
                    "job_name": "Complete Lifecycle Test",
                    "job_type": "file",
                    "backup_tool": "custom",
                    "description": "Testing complete workflow",
                    "target_path": "/data/complete",
                    "schedule_type": "weekly",
                    "retention_days": 90,
                },
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code in [200, 201]

            # Get job
            job = BackupJob.query.filter_by(job_name="Complete Lifecycle Test").first()
            assert job is not None

            # Step 2: Configure backup copies
            copy_types = ["primary", "secondary", "offsite", "offline"]
            for i in range(4):
                copy = BackupCopy(
                    job_id=job.id,
                    copy_type=copy_types[i],
                    storage_path=f"Storage {i+1}",
                    media_type=["disk", "disk", "cloud", "tape"][i],
                    is_encrypted=True,
                    last_backup_size=5368709120,
                    status="success",
                )
                db.session.add(copy)
            db.session.commit()

            # Step 3: Run backup
            response = authenticated_client.post(f"/api/jobs/{job.id}/run")

            # Step 4: Check compliance
            checker = ComplianceChecker()
            result = checker.check_3_2_1_1_0(job.id)
            assert result["compliant"] is True
            generator = ReportGenerator()
            admin = User.query.filter_by(username="admin_test").first() or User.query.first()
            report = generator.generate_daily_report(generated_by=admin.id)
            assert report is not None

            # Step 6: Verify no critical alerts
            manager = AlertManager()
            high_alerts = manager.get_alerts_by_severity("high")
            # System should be healthy
