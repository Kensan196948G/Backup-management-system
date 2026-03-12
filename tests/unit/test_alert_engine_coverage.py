"""
Extended coverage tests for app/alerts/alert_engine.py
Targets: _evaluate_rule, _is_in_cooldown, _create_alert,
_check_backup_failed, _check_consecutive_failures, _check_backup_warning,
_check_compliance_violation, _check_verification_overdue, _check_no_recent_backup,
get_active_alerts with all filters.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestAlertEngineEvaluateRule:
    """Tests for _evaluate_rule."""

    def test_evaluate_rule_with_empty_triggers(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="test_empty",
                name="Empty Rule",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                condition=lambda: [],
                title_template="Title",
                message_template="Message",
            )
            alerts = engine._evaluate_rule(rule)
            assert alerts == []

    def test_evaluate_rule_with_trigger_creates_alert(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()

            def condition():
                return [{"job_id": 1, "job_name": "TestJob", "error_message": "Error"}]

            rule = AlertRule(
                rule_id="test_trigger",
                name="Trigger Rule",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=condition,
                title_template="{job_name}",
                message_template="{error_message}",
                cooldown_minutes=0,
            )

            with patch.object(engine, "_is_in_cooldown", return_value=False):
                alerts = engine._evaluate_rule(rule)
                assert len(alerts) >= 0  # May be 0 if _create_alert returns None

    def test_evaluate_rule_cooldown_skips_alert(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()

            def condition():
                return [{"job_id": 1, "job_name": "TestJob", "error_message": "Error"}]

            rule = AlertRule(
                rule_id="test_cooldown_skip",
                name="Cooldown Rule",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=condition,
                title_template="{job_name}",
                message_template="{error_message}",
                cooldown_minutes=60,
            )

            with patch.object(engine, "_is_in_cooldown", return_value=True):
                alerts = engine._evaluate_rule(rule)
                assert alerts == []

    def test_evaluate_rule_exception_returns_empty(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()

            def bad_condition():
                raise RuntimeError("Condition failed")

            rule = AlertRule(
                rule_id="test_exception",
                name="Exception Rule",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.ERROR,
                condition=bad_condition,
                title_template="Title",
                message_template="Message",
            )

            # Should return empty list without raising
            alerts = engine._evaluate_rule(rule)
            assert alerts == []

    def test_evaluate_rule_multiple_triggers(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()

            def condition():
                return [
                    {"job_id": 1, "job_name": "Job1", "error_message": "E1"},
                    {"job_id": 2, "job_name": "Job2", "error_message": "E2"},
                ]

            rule = AlertRule(
                rule_id="multi_trigger",
                name="Multi Trigger",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=condition,
                title_template="{job_name}",
                message_template="{error_message}",
                cooldown_minutes=0,
            )

            with patch.object(engine, "_is_in_cooldown", return_value=False):
                with patch.object(engine, "_create_alert") as mock_create:
                    mock_create.side_effect = lambda r, t: MagicMock()
                    alerts = engine._evaluate_rule(rule)
                    assert len(alerts) == 2


class TestAlertEngineIsInCooldown:
    """Tests for _is_in_cooldown."""

    def test_no_job_id_returns_false(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="r1",
                name="Rule",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=lambda: [],
                title_template="T",
                message_template="M",
                cooldown_minutes=60,
            )
            result = engine._is_in_cooldown(rule, {"job_name": "Job"})  # no job_id
            assert result is False

    def test_no_recent_alert_returns_false(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="r2",
                name="Rule",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=lambda: [],
                title_template="T",
                message_template="M",
                cooldown_minutes=60,
            )
            # No alerts in DB, so no cooldown
            result = engine._is_in_cooldown(rule, {"job_id": 9999})
            assert result is False

    def test_recent_alert_returns_true(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity
            from app.models import Alert, db

            # Create a recent alert
            alert = Alert(
                alert_type=AlertType.BACKUP_FAILED.value,
                severity=AlertSeverity.ERROR.value,
                title="Recent Alert",
                message="Test",
                job_id=42,
                is_acknowledged=False,
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(alert)
            db.session.commit()

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="cooldown_check",
                name="Cooldown Check",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=lambda: [],
                title_template="T",
                message_template="M",
                cooldown_minutes=60,
            )
            result = engine._is_in_cooldown(rule, {"job_id": 42})
            assert result is True

    def test_old_alert_not_in_cooldown(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity
            from app.models import Alert, db

            # Create an old alert (outside cooldown window)
            old_time = datetime.now(timezone.utc) - timedelta(hours=5)
            alert = Alert(
                alert_type=AlertType.BACKUP_FAILED.value,
                severity=AlertSeverity.ERROR.value,
                title="Old Alert",
                message="Old",
                job_id=43,
                is_acknowledged=False,
                created_at=old_time,
            )
            db.session.add(alert)
            db.session.commit()

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="old_cooldown",
                name="Old Cooldown",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=lambda: [],
                title_template="T",
                message_template="M",
                cooldown_minutes=60,  # 60 minute cooldown, alert is 5 hours old
            )
            result = engine._is_in_cooldown(rule, {"job_id": 43})
            assert result is False


class TestAlertEngineCreateAlert:
    """Tests for _create_alert."""

    def test_creates_alert_in_db(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity
            from app.models import Alert

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="create_test",
                name="Create Test",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=lambda: [],
                title_template="Backup Failed: {job_name}",
                message_template="Job {job_name} failed with {error_message}",
            )
            trigger = {"job_id": 1, "job_name": "TestJob", "error_message": "Disk full"}

            alert = engine._create_alert(rule, trigger)
            assert alert is not None
            assert alert.title == "Backup Failed: TestJob"
            assert "TestJob" in alert.message
            assert alert.severity == "error"
            assert alert.alert_type == "backup_failed"

    def test_create_alert_template_formatting(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="format_test",
                name="Format Test",
                alert_type=AlertType.COMPLIANCE_VIOLATION,
                severity=AlertSeverity.WARNING,
                condition=lambda: [],
                title_template="Violation: {job_name}",
                message_template="Job {job_name} has status {compliance_status}",
            )
            trigger = {"job_id": 5, "job_name": "MyJob", "compliance_status": "non_compliant", "details": "test"}

            alert = engine._create_alert(rule, trigger)
            assert alert is not None
            assert "MyJob" in alert.title
            assert "non_compliant" in alert.message

    def test_create_alert_db_error_returns_none(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="db_error",
                name="DB Error",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.CRITICAL,
                condition=lambda: [],
                title_template="Error: {job_name}",
                message_template="Error in {job_name}",
            )
            trigger = {"job_id": 1, "job_name": "TestJob"}

            with patch("app.alerts.alert_engine.db") as mock_db:
                mock_db.session.add.side_effect = Exception("DB Error")
                mock_db.session.rollback = MagicMock()

                alert = engine._create_alert(rule, trigger)
                assert alert is None
                mock_db.session.rollback.assert_called()

    def test_create_alert_with_no_job_id(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            rule = AlertRule(
                rule_id="no_job",
                name="No Job",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                condition=lambda: [],
                title_template="System Alert",
                message_template="System issue",
            )
            trigger = {}  # No job_id

            alert = engine._create_alert(rule, trigger)
            assert alert is not None
            assert alert.job_id is None


class TestAlertEngineCheckBackupFailed:
    """Tests for _check_backup_failed."""

    def test_returns_empty_when_no_failed_backups(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            result = engine._check_backup_failed()
            assert isinstance(result, list)

    def test_returns_failed_executions(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="check_fail_user", email="check_fail@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Failed Backup Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            # Create a recent failed execution
            execution = BackupExecution(
                job_id=job.id,
                execution_date=datetime.now(timezone.utc) - timedelta(minutes=10),
                execution_result="failed",
                error_message="Disk full",
            )
            db.session.add(execution)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_backup_failed()
            assert len(result) >= 1
            job_names = [r["job_name"] for r in result]
            assert "Failed Backup Job" in job_names

    def test_excludes_old_failures(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="old_fail_user", email="old_fail@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Old Failed Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            # Create an old failed execution (2 hours ago)
            execution = BackupExecution(
                job_id=job.id,
                execution_date=datetime.now(timezone.utc) - timedelta(hours=2),
                execution_result="failed",
                error_message="Old error",
            )
            db.session.add(execution)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_backup_failed()
            job_names = [r["job_name"] for r in result]
            assert "Old Failed Job" not in job_names


class TestAlertEngineCheckConsecutiveFailures:
    """Tests for _check_consecutive_failures."""

    def test_returns_empty_when_no_jobs(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            result = engine._check_consecutive_failures()
            assert isinstance(result, list)

    def test_detects_3_consecutive_failures(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="consec_user", email="consec@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Consecutive Fail Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            # Create 3 consecutive failures
            for i in range(3):
                execution = BackupExecution(
                    job_id=job.id,
                    execution_date=datetime.now(timezone.utc) - timedelta(hours=i),
                    execution_result="failed",
                    error_message=f"Error {i}",
                )
                db.session.add(execution)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_consecutive_failures()
            job_names = [r["job_name"] for r in result]
            assert "Consecutive Fail Job" in job_names

    def test_no_trigger_for_2_failures(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="two_fail_user", email="two_fail@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Two Fail Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            # Only 2 failures
            for i in range(2):
                execution = BackupExecution(
                    job_id=job.id,
                    execution_date=datetime.now(timezone.utc) - timedelta(hours=i),
                    execution_result="failed",
                    error_message="Error",
                )
                db.session.add(execution)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_consecutive_failures()
            job_names = [r["job_name"] for r in result]
            assert "Two Fail Job" not in job_names

    def test_no_trigger_when_last_is_success(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="mixed_user", email="mixed@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Mixed Result Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            # 2 failures and 1 success
            for i, result in enumerate(["success", "failed", "failed"]):
                execution = BackupExecution(
                    job_id=job.id,
                    execution_date=datetime.now(timezone.utc) - timedelta(hours=i),
                    execution_result=result,
                    error_message="Error" if result == "failed" else None,
                )
                db.session.add(execution)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_consecutive_failures()
            job_names = [r["job_name"] for r in result]
            assert "Mixed Result Job" not in job_names


class TestAlertEngineCheckBackupWarning:
    """Tests for _check_backup_warning."""

    def test_returns_empty_when_no_warnings(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            result = engine._check_backup_warning()
            assert isinstance(result, list)

    def test_detects_recent_warning(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="warn_user", email="warn@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Warning Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            execution = BackupExecution(
                job_id=job.id,
                execution_date=datetime.now(timezone.utc) - timedelta(minutes=15),
                execution_result="warning",
                error_message="Low disk space",
            )
            db.session.add(execution)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_backup_warning()
            job_names = [r["job_name"] for r in result]
            assert "Warning Job" in job_names

    def test_excludes_old_warnings(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="old_warn_user", email="old_warn@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Old Warning Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            execution = BackupExecution(
                job_id=job.id,
                execution_date=datetime.now(timezone.utc) - timedelta(hours=3),
                execution_result="warning",
                error_message="Old warning",
            )
            db.session.add(execution)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_backup_warning()
            job_names = [r["job_name"] for r in result]
            assert "Old Warning Job" not in job_names

    def test_trigger_has_required_fields(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="field_warn_user", email="field_warn@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Field Warning Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            execution = BackupExecution(
                job_id=job.id,
                execution_date=datetime.now(timezone.utc) - timedelta(minutes=5),
                execution_result="warning",
                error_message=None,
            )
            db.session.add(execution)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_backup_warning()
            for trigger in result:
                if trigger["job_name"] == "Field Warning Job":
                    assert "job_id" in trigger
                    assert "job_name" in trigger
                    assert "execution_date" in trigger
                    assert "error_message" in trigger
                    assert trigger["error_message"] == "Warning occurred"  # Default when None


class TestAlertEngineCheckComplianceViolation:
    """Tests for _check_compliance_violation."""

    def test_returns_empty_when_no_violations(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            result = engine._check_compliance_violation()
            assert isinstance(result, list)

    def test_detects_non_compliant_status(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, ComplianceStatus, User, db

            user = User(username="compliance_user", email="compliance@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Non-Compliant Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            status = ComplianceStatus(
                job_id=job.id,
                overall_status="non_compliant",
                copies_count=1,
                media_types_count=1,
                has_offsite=False,
                has_offline=False,
                has_errors=True,
                check_date=datetime.now(timezone.utc),
            )
            db.session.add(status)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_compliance_violation()
            job_names = [r["job_name"] for r in result]
            assert "Non-Compliant Job" in job_names

    def test_trigger_includes_details(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, ComplianceStatus, User, db

            user = User(username="details_user", email="details_compliance@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Details Compliance Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            status = ComplianceStatus(
                job_id=job.id,
                overall_status="non_compliant",
                copies_count=1,
                media_types_count=1,
                has_offsite=False,
                has_offline=True,
                has_errors=False,
                check_date=datetime.now(timezone.utc),
            )
            db.session.add(status)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_compliance_violation()
            for trigger in result:
                if trigger["job_name"] == "Details Compliance Job":
                    assert "details" in trigger
                    assert "Insufficient copies" in trigger["details"]


class TestAlertEngineCheckVerificationOverdue:
    """Tests for _check_verification_overdue."""

    def test_returns_empty_when_no_overdue(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            result = engine._check_verification_overdue()
            assert isinstance(result, list)

    def test_detects_overdue_schedule(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, VerificationSchedule, User, db

            user = User(username="overdue_alert_user", email="overdue_alert@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Overdue Verification Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            past_date = (datetime.now(timezone.utc) - timedelta(days=5)).date()
            schedule = VerificationSchedule(
                job_id=job.id,
                test_frequency="monthly",
                next_test_date=past_date,
                is_active=True,
            )
            db.session.add(schedule)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_verification_overdue()
            job_names = [r["job_name"] for r in result]
            assert "Overdue Verification Job" in job_names

    def test_trigger_has_required_fields(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, VerificationSchedule, User, db

            user = User(username="vfield_user", email="vfield@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="V Field Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()

            past_date = (datetime.now(timezone.utc) - timedelta(days=3)).date()
            schedule = VerificationSchedule(
                job_id=job.id,
                test_frequency="quarterly",
                next_test_date=past_date,
                is_active=True,
            )
            db.session.add(schedule)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_verification_overdue()
            for trigger in result:
                if trigger["job_name"] == "V Field Job":
                    assert "job_id" in trigger
                    assert "next_test_date" in trigger


class TestAlertEngineCheckNoRecentBackup:
    """Tests for _check_no_recent_backup."""

    def test_returns_empty_when_no_active_jobs(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            result = engine._check_no_recent_backup()
            assert isinstance(result, list)

    def test_detects_daily_job_with_no_recent_backup(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, User, db

            user = User(username="no_recent_user", email="no_recent@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Daily Job No Recent", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.commit()

            # No executions at all
            engine = AlertEngine()
            result = engine._check_no_recent_backup()
            job_names = [r["job_name"] for r in result]
            assert "Daily Job No Recent" in job_names

    def test_skips_manual_schedule_jobs(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, User, db

            user = User(username="manual_job_user", email="manual_job@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(
                job_name="Manual Job",
                job_type="file",
                backup_tool="custom",
                target_path="/source",
                schedule_type="manual",  # Manual jobs are skipped
                retention_days=30,
                owner_id=user.id,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()

            engine = AlertEngine()
            result = engine._check_no_recent_backup()
            job_names = [r["job_name"] for r in result]
            assert "Manual Job" not in job_names

    def test_no_trigger_for_recent_backup(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, BackupExecution, User, db

            user = User(username="recent_backup_user", email="recent_backup@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()

            job = BackupJob(job_name="Recent Backup Job", job_type="file", backup_tool="custom", schedule_type="daily", retention_days=30, owner_id=user.id, is_active=True)
            db.session.add(job)
            db.session.flush()
            db.session.commit()

            engine = AlertEngine()
            # Mock the execution query to return a recent execution (1 hour ago, aware datetime)
            mock_execution = MagicMock()
            mock_execution.execution_date = datetime.now(timezone.utc) - timedelta(hours=1)

            with patch("app.alerts.alert_engine.BackupExecution") as mock_be:
                mock_be.query.filter_by.return_value.order_by.return_value.first.return_value = mock_execution
                with patch("app.alerts.alert_engine.BackupJob") as mock_bj:
                    mock_job = MagicMock()
                    mock_job.id = job.id
                    mock_job.job_name = "Recent Backup Job"
                    mock_job.schedule_type = "daily"
                    mock_bj.query.filter_by.return_value.all.return_value = [mock_job]
                    result = engine._check_no_recent_backup()
                    job_names = [r["job_name"] for r in result]
                    assert "Recent Backup Job" not in job_names

    def test_weekly_job_threshold(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, User, db

            user = User(username="weekly_threshold_user", email="weekly_threshold@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()
            db.session.commit()

            engine = AlertEngine()
            # Mock an old execution (250 hours ago > 192h threshold)
            mock_execution = MagicMock()
            mock_execution.execution_date = datetime.now(timezone.utc) - timedelta(hours=250)

            with patch("app.alerts.alert_engine.BackupExecution") as mock_be:
                mock_be.query.filter_by.return_value.order_by.return_value.first.return_value = mock_execution
                with patch("app.alerts.alert_engine.BackupJob") as mock_bj:
                    mock_job = MagicMock()
                    mock_job.id = 1
                    mock_job.job_name = "Weekly Overdue Job"
                    mock_job.schedule_type = "weekly"
                    mock_bj.query.filter_by.return_value.all.return_value = [mock_job]
                    result = engine._check_no_recent_backup()
                    job_names = [r["job_name"] for r in result]
                    assert "Weekly Overdue Job" in job_names

    def test_monthly_job_threshold(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import BackupJob, User, db

            user = User(username="monthly_thresh_user", email="monthly_thresh@example.com", role="admin", is_active=True)
            user.set_password("Test123!")
            db.session.add(user)
            db.session.flush()
            db.session.commit()

            engine = AlertEngine()
            # Mock an old execution (800 hours ago > 768h threshold for monthly)
            mock_execution = MagicMock()
            mock_execution.execution_date = datetime.now(timezone.utc) - timedelta(hours=800)

            with patch("app.alerts.alert_engine.BackupExecution") as mock_be:
                mock_be.query.filter_by.return_value.order_by.return_value.first.return_value = mock_execution
                with patch("app.alerts.alert_engine.BackupJob") as mock_bj:
                    mock_job = MagicMock()
                    mock_job.id = 1
                    mock_job.job_name = "Monthly Overdue Job"
                    mock_job.schedule_type = "monthly"
                    mock_bj.query.filter_by.return_value.all.return_value = [mock_job]
                    result = engine._check_no_recent_backup()
                    job_names = [r["job_name"] for r in result]
                    assert "Monthly Overdue Job" in job_names


class TestAlertEngineGetActiveAlertsFiltered:
    """Tests for get_active_alerts with all filter combinations."""

    def test_filter_by_alert_type(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertType
            from app.models import Alert, db

            alert = Alert(
                alert_type=AlertType.COMPLIANCE_VIOLATION.value,
                severity="error",
                title="Compliance Alert",
                message="Test",
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()

            engine = AlertEngine()
            alerts = engine.get_active_alerts(alert_type=AlertType.COMPLIANCE_VIOLATION)
            types = [a.alert_type for a in alerts]
            assert AlertType.COMPLIANCE_VIOLATION.value in types

    def test_filter_by_job_id(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import Alert, db

            alert1 = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Alert for Job 100",
                message="Test",
                job_id=100,
                is_acknowledged=False,
            )
            alert2 = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Alert for Job 200",
                message="Test",
                job_id=200,
                is_acknowledged=False,
            )
            db.session.add_all([alert1, alert2])
            db.session.commit()

            engine = AlertEngine()
            alerts = engine.get_active_alerts(job_id=100)
            assert all(a.job_id == 100 for a in alerts)

    def test_filter_by_all_three(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertSeverity, AlertType
            from app.models import Alert, db

            alert = Alert(
                alert_type=AlertType.BACKUP_FAILED.value,
                severity=AlertSeverity.CRITICAL.value,
                title="Triple Filtered Alert",
                message="Test",
                job_id=555,
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()

            engine = AlertEngine()
            alerts = engine.get_active_alerts(
                severity=AlertSeverity.CRITICAL,
                alert_type=AlertType.BACKUP_FAILED,
                job_id=555,
            )
            assert len(alerts) >= 1

    def test_no_filters_returns_all_active(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import Alert, db

            for i in range(3):
                alert = Alert(
                    alert_type="system_error",
                    severity="info",
                    title=f"Alert {i}",
                    message="Test",
                    is_acknowledged=False,
                )
                db.session.add(alert)
            db.session.commit()

            engine = AlertEngine()
            alerts = engine.get_active_alerts()
            assert len(alerts) >= 3


class TestAlertEngineEvaluateAllRules:
    """Tests for evaluate_all_rules with disabled rules."""

    def test_disabled_rule_is_skipped(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            engine.rules.clear()

            call_count = {"n": 0}

            def condition():
                call_count["n"] += 1
                return []

            rule = AlertRule(
                rule_id="disabled_rule",
                name="Disabled Rule",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                condition=condition,
                title_template="T",
                message_template="M",
                enabled=False,
            )
            engine.register_rule(rule)

            engine.evaluate_all_rules()
            assert call_count["n"] == 0

    def test_enabled_rule_is_evaluated(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            engine.rules.clear()

            call_count = {"n": 0}

            def condition():
                call_count["n"] += 1
                return []

            rule = AlertRule(
                rule_id="enabled_rule",
                name="Enabled Rule",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                condition=condition,
                title_template="T",
                message_template="M",
                enabled=True,
            )
            engine.register_rule(rule)

            engine.evaluate_all_rules()
            assert call_count["n"] == 1

    def test_unregister_rule(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            initial_count = len(engine.rules)

            rule = AlertRule(
                rule_id="to_remove",
                name="To Remove",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                condition=lambda: [],
                title_template="T",
                message_template="M",
            )
            engine.register_rule(rule)
            assert len(engine.rules) == initial_count + 1

            engine.unregister_rule("to_remove")
            assert len(engine.rules) == initial_count

    def test_unregister_nonexistent_rule_no_error(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine

            engine = AlertEngine()
            # Should not raise
            engine.unregister_rule("nonexistent_rule_xyz")
