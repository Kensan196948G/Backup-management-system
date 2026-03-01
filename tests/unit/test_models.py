"""
Unit tests for database models.

Tests all 14 models with focus on:
- CRUD operations
- Relationships
- Model methods
- Field validations
- Default values
"""

from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.security import check_password_hash

from app.models import (
    Alert,
    AuditLog,
    BackupCopy,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    MediaLending,
    MediaRotationSchedule,
    OfflineMedia,
    Report,
    SystemSetting,
    User,
    VerificationSchedule,
    VerificationTest,
    db,
)


class TestUserModel:
    """Test cases for User model."""

    def test_create_user(self, app):
        """Test creating a new user."""
        with app.app_context():
            user = User(username="testuser", email="test@example.com", full_name="Test User", role="operator", is_active=True)
            user.set_password("Test123!@#")
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.role == "operator"
            assert user.is_active is True
            assert user.created_at is not None
            assert user.updated_at is not None

    def test_password_hashing(self, app):
        """Test password hashing and verification."""
        with app.app_context():
            user = User(username="testuser", email="test@example.com", full_name="Test User", role="viewer", is_active=True)
            user.set_password("MyPass123!@#")
            db.session.add(user)
            db.session.commit()

            assert user.password_hash is not None
            assert user.password_hash != "MyPass123!@#"
            assert user.check_password("MyPass123!@#") is True
            assert user.check_password("wrongpassword") is False

    def test_user_roles(self, app, admin_user, operator_user, auditor_user):
        """Test user role checking methods."""
        with app.app_context():
            # Refresh objects from database
            admin = db.session.get(User, admin_user.id)
            operator = db.session.get(User, operator_user.id)
            auditor = db.session.get(User, auditor_user.id)

            # Test admin
            assert admin.is_admin() is True
            assert admin.is_operator() is True  # Admin has operator permissions
            assert admin.is_auditor() is False
            assert admin.can_edit() is True
            assert admin.can_view() is True

            # Test operator
            assert operator.is_admin() is False
            assert operator.is_operator() is True
            assert operator.is_auditor() is False
            assert operator.can_edit() is True
            assert operator.can_view() is True

            # Test auditor
            assert auditor.is_admin() is False
            assert auditor.is_operator() is False
            assert auditor.is_auditor() is True
            assert auditor.can_edit() is False
            assert auditor.can_view() is True

    def test_user_repr(self, app, admin_user):
        """Test user string representation."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)
            assert repr(user) == f"<User {user.username} ({user.role})>"

    def test_inactive_user(self, app):
        """Test inactive user creation."""
        with app.app_context():
            user = User(
                username="inactive", email="inactive@example.com", full_name="Inactive User", role="operator", is_active=False
            )
            user.set_password("Inactive123!@#")
            db.session.add(user)
            db.session.commit()

            assert user.is_active is False


class TestBackupJobModel:
    """Test cases for BackupJob model."""

    def test_create_backup_job(self, app, admin_user):
        """Test creating a backup job."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)

            job = BackupJob(
                job_name="Test Job",
                job_type="file",
                backup_tool="custom",
                description="Test Description",
                target_path="/data/test",
                schedule_type="daily",
                retention_days=30,
                owner_id=user.id,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()

            assert job.id is not None
            assert job.job_name == "Test Job"
            assert job.target_path == "/data/test"
            assert job.schedule_type == "daily"
            assert job.is_active is True

    def test_backup_job_relationships(self, app, backup_job, backup_copies):
        """Test BackupJob relationships."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)

            assert len(list(job.copies)) == 4
            assert all(copy.job_id == job.id for copy in job.copies)

    def test_backup_job_default_values(self, app, admin_user):
        """Test BackupJob default values."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)

            job = BackupJob(
                job_name="Minimal Job",
                job_type="file",
                backup_tool="custom",
                target_path="/data/minimal",
                schedule_type="manual",
                retention_days=30,
                owner_id=user.id,
            )
            db.session.add(job)
            db.session.commit()

            assert job.is_active is True
            assert job.created_at is not None
            assert job.updated_at is not None

    def test_backup_job_repr(self, app, backup_job):
        """Test BackupJob string representation."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)
            assert repr(job) == f"<BackupJob {job.job_name} ({job.job_type})>"


class TestBackupCopyModel:
    """Test cases for BackupCopy model."""

    def test_create_backup_copy(self, app, backup_job):
        """Test creating a backup copy."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)

            copy = BackupCopy(
                job_id=job.id,
                copy_type="primary",
                storage_path="Test Storage",
                media_type="disk",
                is_encrypted=True,
                is_compressed=True,
                last_backup_size=1024,
                status="success",
            )
            db.session.add(copy)
            db.session.commit()

            assert copy.id is not None
            assert copy.job_id == job.id
            assert copy.copy_type == "primary"
            assert copy.is_encrypted is True

    def test_backup_copy_3_2_1_1_0_fields(self, app, backup_copies):
        """Test 3-2-1-1-0 rule specific fields."""
        with app.app_context():
            copies = [db.session.get(BackupCopy, c.id) for c in backup_copies]

            # Check media types (requirement: 2 different types)
            media_types = set(c.media_type for c in copies)
            assert len(media_types) >= 2

            # Check offsite copy (requirement: 1 offsite)
            offsite_copies = [c for c in copies if c.copy_type == "offsite"]
            assert len(offsite_copies) >= 1

            # Check offline copy (requirement: 1 offline)
            offline_copies = [c for c in copies if c.copy_type == "offline"]
            assert len(offline_copies) >= 1

    def test_backup_copy_relationship(self, app, backup_job, backup_copies):
        """Test BackupCopy relationship with BackupJob."""
        with app.app_context():
            copy = db.session.get(BackupCopy, backup_copies[0].id)
            assert copy.job is not None
            assert copy.job.id == backup_job.id

    def test_backup_copy_repr(self, app, backup_copies):
        """Test BackupCopy string representation."""
        with app.app_context():
            copy = db.session.get(BackupCopy, backup_copies[0].id)
            expected = f"<BackupCopy job_id={copy.job_id} type={copy.copy_type} media={copy.media_type}>"
            assert repr(copy) == expected


class TestOfflineMediaModel:
    """Test cases for OfflineMedia model."""

    def test_create_offline_media(self, app):
        """Test creating offline media."""
        with app.app_context():
            media = OfflineMedia(
                media_type="tape",
                media_id="TAPE-001",
                capacity_gb=2000,
                storage_location="Vault A",
                current_status="available",
            )
            db.session.add(media)
            db.session.commit()

            assert media.id is not None
            assert media.media_type == "tape"
            assert media.current_status == "available"

    def test_offline_media_capacity_tracking(self, app, offline_media):
        """Test media capacity and usage tracking."""
        with app.app_context():
            media = db.session.get(OfflineMedia, offline_media[0].id)

            assert media.capacity_gb > 0
            # Test that media exists and has expected attributes
            assert media.media_type == "tape"

    def test_offline_media_repr(self, app, offline_media):
        """Test OfflineMedia string representation."""
        with app.app_context():
            media = db.session.get(OfflineMedia, offline_media[0].id)
            assert repr(media) == f"<OfflineMedia {media.media_id} ({media.media_type})>"


class TestMediaRotationScheduleModel:
    """Test cases for MediaRotationSchedule model."""

    def test_create_rotation_schedule(self, app, offline_media):
        """Test creating a media rotation schedule."""
        with app.app_context():
            schedule = MediaRotationSchedule(
                offline_media_id=offline_media[0].id,
                rotation_type="gfs",
                rotation_cycle="weekly",
                next_rotation_date=(datetime.now(timezone.utc) + timedelta(days=7)).date(),
            )
            db.session.add(schedule)
            db.session.commit()

            assert schedule.id is not None
            assert schedule.rotation_type == "gfs"
            assert schedule.is_active is True

    def test_rotation_schedule_relationship(self, app, offline_media):
        """Test MediaRotationSchedule relationship with OfflineMedia."""
        with app.app_context():
            schedule = MediaRotationSchedule(
                offline_media_id=offline_media[0].id,
                rotation_type="gfs",
                rotation_cycle="weekly",
                next_rotation_date=(datetime.now(timezone.utc) + timedelta(days=1)).date(),
            )
            db.session.add(schedule)
            db.session.commit()

            assert schedule.media is not None
            assert schedule.media.id == offline_media[0].id


class TestMediaLendingModel:
    """Test cases for MediaLending model."""

    def test_create_media_lending(self, app, offline_media, admin_user):
        """Test creating a media lending record."""
        with app.app_context():
            lending = MediaLending(
                offline_media_id=offline_media[0].id,
                borrower_id=admin_user.id,
                borrow_date=datetime.now(timezone.utc),
                borrow_purpose="Backup verification",
                expected_return=(datetime.now(timezone.utc) + timedelta(days=7)).date(),
            )
            db.session.add(lending)
            db.session.commit()

            assert lending.id is not None
            assert lending.borrower_id == admin_user.id
            assert lending.actual_return is None

    def test_media_lending_return(self, app, offline_media, admin_user):
        """Test returning lent media."""
        with app.app_context():
            lending = MediaLending(
                offline_media_id=offline_media[0].id,
                borrower_id=admin_user.id,
                borrow_date=datetime.now(timezone.utc),
                borrow_purpose="Testing",
                expected_return=(datetime.now(timezone.utc) + timedelta(days=1)).date(),
            )
            db.session.add(lending)
            db.session.commit()

            # Return the media
            lending.actual_return = datetime.now(timezone.utc)
            db.session.commit()

            assert lending.actual_return is not None


class TestVerificationTestModel:
    """Test cases for VerificationTest model."""

    def test_create_verification_test(self, app, backup_job, admin_user):
        """Test creating a verification test."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)
            user = db.session.get(User, admin_user.id)

            test = VerificationTest(
                job_id=job.id,
                test_type="integrity",
                test_date=datetime.now(timezone.utc),
                tester_id=user.id,
                test_result="success",
            )
            db.session.add(test)
            db.session.commit()

            assert test.id is not None
            assert test.test_type == "integrity"
            assert test.test_result == "success"

    def test_verification_test_with_error(self, app, backup_job, admin_user):
        """Test verification test with error details."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)
            user = db.session.get(User, admin_user.id)

            test = VerificationTest(
                job_id=job.id,
                test_type="full_restore",
                test_date=datetime.now(timezone.utc),
                tester_id=user.id,
                test_result="failed",
                issues_found="Checksum mismatch detected",
            )
            db.session.add(test)
            db.session.commit()

            assert test.test_result == "failed"
            assert test.issues_found is not None


class TestVerificationScheduleModel:
    """Test cases for VerificationSchedule model."""

    def test_create_verification_schedule(self, app, backup_job):
        """Test creating a verification schedule."""
        with app.app_context():
            schedule = VerificationSchedule(
                job_id=backup_job.id, test_frequency="weekly", next_test_date=(datetime.now(timezone.utc) + timedelta(days=7)).date()
            )
            db.session.add(schedule)
            db.session.commit()

            assert schedule.id is not None
            assert schedule.test_frequency == "weekly"
            assert schedule.is_active is True


class TestBackupExecutionModel:
    """Test cases for BackupExecution model."""

    def test_create_backup_execution(self, app, backup_job):
        """Test creating a backup execution record."""
        with app.app_context():
            execution = BackupExecution(
                job_id=backup_job.id,
                execution_result="success",
                execution_date=datetime.now(timezone.utc),
                backup_size_bytes=1024000,
                duration_seconds=3600,
            )
            db.session.add(execution)
            db.session.commit()

            assert execution.id is not None
            assert execution.execution_result == "success"
            assert execution.backup_size_bytes == 1024000

    def test_backup_execution_with_error(self, app, backup_job):
        """Test backup execution with error."""
        with app.app_context():
            execution = BackupExecution(
                job_id=backup_job.id, execution_result="failed", execution_date=datetime.now(timezone.utc), error_message="Disk full"
            )
            db.session.add(execution)
            db.session.commit()

            assert execution.execution_result == "failed"
            assert execution.error_message is not None


class TestComplianceStatusModel:
    """Test cases for ComplianceStatus model."""

    def test_create_compliance_status(self, app, backup_job):
        """Test creating a compliance status record."""
        with app.app_context():
            status = ComplianceStatus(
                job_id=backup_job.id,
                check_date=datetime.now(timezone.utc),
                copies_count=4,
                media_types_count=3,
                has_offsite=True,
                has_offline=True,
                has_errors=False,
                overall_status="compliant",
            )
            db.session.add(status)
            db.session.commit()

            assert status.id is not None
            assert status.overall_status == "compliant"
            assert status.copies_count == 4

    def test_non_compliant_status(self, app, backup_job):
        """Test non-compliant status."""
        with app.app_context():
            status = ComplianceStatus(
                job_id=backup_job.id,
                check_date=datetime.now(timezone.utc),
                copies_count=2,
                media_types_count=1,
                has_offsite=False,
                has_offline=False,
                has_errors=True,
                overall_status="non_compliant",
            )
            db.session.add(status)
            db.session.commit()

            assert status.overall_status == "non_compliant"
            assert status.has_offsite is False


class TestAlertModel:
    """Test cases for Alert model."""

    def test_create_alert(self, app, backup_job):
        """Test creating an alert."""
        with app.app_context():
            alert = Alert(
                job_id=backup_job.id,
                alert_type="compliance",
                severity="high",
                title="Compliance Violation",
                message="Backup compliance violation: Missing offsite copy",
            )
            db.session.add(alert)
            db.session.commit()

            assert alert.id is not None
            assert alert.alert_type == "compliance"
            assert alert.is_acknowledged is False

    def test_acknowledge_alert(self, app, backup_job):
        """Test acknowledging an alert."""
        with app.app_context():
            alert = Alert(
                job_id=backup_job.id,
                alert_type="warning",
                severity="medium",
                title="Low Disk Space",
                message="Low disk space detected on backup storage",
            )
            db.session.add(alert)
            db.session.commit()

            # Acknowledge the alert
            alert.is_acknowledged = True
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.acknowledged_by = 1
            db.session.commit()

            assert alert.is_acknowledged is True
            assert alert.acknowledged_at is not None


class TestAuditLogModel:
    """Test cases for AuditLog model."""

    def test_create_audit_log(self, app, admin_user):
        """Test creating an audit log entry."""
        with app.app_context():
            log = AuditLog(
                user_id=admin_user.id,
                action_type="create",
                resource_type="BackupJob",
                resource_id=1,
                action_result="success",
                details='{"job_name": "Test Job"}',
                ip_address="192.168.1.1",
            )
            db.session.add(log)
            db.session.commit()

            assert log.id is not None
            assert log.action_type == "create"
            assert log.user_id == admin_user.id

    def test_audit_log_without_user(self, app):
        """Test audit log for system actions."""
        with app.app_context():
            log = AuditLog(
                action_type="backup", resource_type="System", action_result="success", details='{"automated": true}'
            )
            db.session.add(log)
            db.session.commit()

            assert log.user_id is None


class TestReportModel:
    """Test cases for Report model."""

    def test_create_report(self, app, admin_user):
        """Test creating a report."""
        with app.app_context():
            report = Report(
                report_type="daily",
                report_title="Daily Backup Report",
                date_from=(datetime.now(timezone.utc) - timedelta(days=1)).date(),
                date_to=datetime.now(timezone.utc).date(),
                file_path="/reports/daily_2025.pdf",
                file_format="pdf",
                generated_by=admin_user.id,
            )
            db.session.add(report)
            db.session.commit()

            assert report.id is not None
            assert report.report_type == "daily"
            assert report.report_title == "Daily Backup Report"

    def test_report_repr(self, app, admin_user):
        """Test Report string representation."""
        with app.app_context():
            report = Report(
                report_type="weekly",
                report_title="Weekly Report",
                date_from=datetime.now(timezone.utc).date(),
                date_to=datetime.now(timezone.utc).date(),
                file_format="html",
                generated_by=admin_user.id,
            )
            db.session.add(report)
            db.session.commit()

            assert repr(report) == f"<Report {report.report_type} from={report.date_from} to={report.date_to}>"


class TestSystemSettingModel:
    """Test cases for SystemSetting model."""

    def test_create_system_setting(self, app):
        """Test creating a system setting."""
        with app.app_context():
            setting = SystemSetting(
                setting_key="backup.min_copies",
                setting_value="3",
                value_type="int",
                description="Minimum number of backup copies",
            )
            db.session.add(setting)
            db.session.commit()

            assert setting.id is not None
            assert setting.setting_key == "backup.min_copies"
            assert setting.setting_value == "3"

    def test_encrypted_setting(self, app):
        """Test encrypted system setting."""
        with app.app_context():
            setting = SystemSetting(
                setting_key="credentials.api_key", setting_value="secret_key_value", value_type="string", is_encrypted=True
            )
            db.session.add(setting)
            db.session.commit()

            assert setting.is_encrypted is True

    def test_system_setting_repr(self, app):
        """Test SystemSetting string representation."""
        with app.app_context():
            setting = SystemSetting(setting_key="test.test_key", setting_value="test_value", value_type="string")
            db.session.add(setting)
            db.session.commit()

            expected = f"<SystemSetting {setting.setting_key}={setting.setting_value}>"
            assert repr(setting) == expected
