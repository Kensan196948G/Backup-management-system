"""
Unit tests for app/alerts/sla_monitor.py
SLAMonitor, SLAMetrics, SLATarget.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone


class TestSLATarget:
    """Tests for SLATarget dataclass"""

    def test_create_target(self):
        from app.alerts.sla_monitor import SLATarget
        target = SLATarget(
            target_id="test_target",
            job_id=None,
            min_success_rate=95.0,
            max_duration_seconds=3600,
            max_age_hours=24,
        )
        assert target.target_id == "test_target"
        assert target.job_id is None
        assert target.min_success_rate == 95.0
        assert target.enabled is True  # default

    def test_target_with_job_id(self):
        from app.alerts.sla_monitor import SLATarget
        target = SLATarget(
            target_id="job_specific",
            job_id=42,
            min_success_rate=99.0,
            max_duration_seconds=None,
            max_age_hours=None,
        )
        assert target.job_id == 42


class TestSLAMetrics:
    """Tests for SLAMetrics dataclass"""

    def test_create_metrics(self):
        from app.alerts.sla_monitor import SLAMetrics
        metrics = SLAMetrics(
            job_id=1,
            job_name="Test Job",
            success_rate=98.5,
            average_duration_seconds=300,
            max_duration_seconds=600,
            last_execution_date=datetime.now(timezone.utc),
            executions_count=20,
            failed_count=0,
            warning_count=1,
            success_count=19,
            is_compliant=True,
            violations=[],
        )
        assert metrics.job_id == 1
        assert metrics.success_rate == 98.5
        assert metrics.is_compliant is True
        assert len(metrics.violations) == 0

    def test_non_compliant_metrics(self):
        from app.alerts.sla_monitor import SLAMetrics
        metrics = SLAMetrics(
            job_id=2,
            job_name="Failing Job",
            success_rate=80.0,
            average_duration_seconds=None,
            max_duration_seconds=None,
            last_execution_date=None,
            executions_count=5,
            failed_count=1,
            warning_count=0,
            success_count=4,
            is_compliant=False,
            violations=["Success rate 80.0% below target 95.0%"],
        )
        assert metrics.is_compliant is False
        assert len(metrics.violations) == 1


class TestSLAMonitorInit:
    """Tests for SLAMonitor initialization"""

    def test_init_registers_default_targets(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            monitor = SLAMonitor()
            assert len(monitor.sla_targets) > 0

    def test_default_success_rate_target_exists(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            monitor = SLAMonitor()
            assert "default_success_rate" in monitor.sla_targets

    def test_default_daily_age_target_exists(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            monitor = SLAMonitor()
            assert "default_daily_age" in monitor.sla_targets

    def test_default_success_rate_is_95(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            monitor = SLAMonitor()
            target = monitor.sla_targets["default_success_rate"]
            assert target.min_success_rate == 95.0


class TestSLAMonitorTargetManagement:
    """Tests for target registration and unregistration"""

    def test_register_custom_target(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor, SLATarget
            monitor = SLAMonitor()
            initial_count = len(monitor.sla_targets)

            custom_target = SLATarget(
                target_id="custom_target",
                job_id=1,
                min_success_rate=99.9,
                max_duration_seconds=1800,
                max_age_hours=12,
            )
            monitor.register_target(custom_target)

            assert len(monitor.sla_targets) == initial_count + 1
            assert "custom_target" in monitor.sla_targets

    def test_unregister_target(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            monitor = SLAMonitor()
            assert "default_success_rate" in monitor.sla_targets

            monitor.unregister_target("default_success_rate")
            assert "default_success_rate" not in monitor.sla_targets

    def test_unregister_nonexistent_target(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            monitor = SLAMonitor()
            # Should not raise
            monitor.unregister_target("does_not_exist")


class TestSLACheckViolations:
    """Tests for _check_violations method"""

    def test_no_violations_when_compliant(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor, SLATarget
            monitor = SLAMonitor()
            monitor.sla_targets.clear()

            # Add a simple target
            monitor.register_target(SLATarget(
                target_id="test",
                job_id=None,
                min_success_rate=90.0,
                max_duration_seconds=None,
                max_age_hours=None,
            ))

            mock_job = MagicMock()
            mock_job.id = 1

            violations = monitor._check_violations(
                job=mock_job,
                success_rate=95.0,  # Above 90%
                max_duration=None,
                last_execution_date=datetime.now(timezone.utc),
            )
            assert violations == []

    def test_success_rate_violation(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor, SLATarget
            monitor = SLAMonitor()
            monitor.sla_targets.clear()

            monitor.register_target(SLATarget(
                target_id="strict",
                job_id=None,
                min_success_rate=99.0,
                max_duration_seconds=None,
                max_age_hours=None,
            ))

            mock_job = MagicMock()
            mock_job.id = 1

            violations = monitor._check_violations(
                job=mock_job,
                success_rate=80.0,  # Below 99%
                max_duration=None,
                last_execution_date=datetime.now(timezone.utc),
            )
            assert len(violations) == 1
            assert "80.0%" in violations[0]
            assert "99.0%" in violations[0]

    def test_duration_violation(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor, SLATarget
            monitor = SLAMonitor()
            monitor.sla_targets.clear()

            monitor.register_target(SLATarget(
                target_id="duration_check",
                job_id=None,
                min_success_rate=0,
                max_duration_seconds=1800,  # 30 minutes
                max_age_hours=None,
            ))

            mock_job = MagicMock()
            mock_job.id = 1

            violations = monitor._check_violations(
                job=mock_job,
                success_rate=100.0,
                max_duration=3600,  # 1 hour - exceeds 30 min limit
                last_execution_date=datetime.now(timezone.utc),
            )
            assert len(violations) == 1
            assert "3600s" in violations[0]

    def test_age_violation(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor, SLATarget
            monitor = SLAMonitor()
            monitor.sla_targets.clear()

            monitor.register_target(SLATarget(
                target_id="age_check",
                job_id=None,
                min_success_rate=0,
                max_duration_seconds=None,
                max_age_hours=24,
            ))

            mock_job = MagicMock()
            mock_job.id = 1

            # Last backup was 48 hours ago
            old_date = datetime.now(timezone.utc) - timedelta(hours=48)
            violations = monitor._check_violations(
                job=mock_job,
                success_rate=100.0,
                max_duration=None,
                last_execution_date=old_date,
            )
            assert len(violations) == 1
            assert "24h" in violations[0]

    def test_job_specific_target_skips_other_jobs(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor, SLATarget
            monitor = SLAMonitor()
            monitor.sla_targets.clear()

            # Target for job_id=5 only
            monitor.register_target(SLATarget(
                target_id="job5_target",
                job_id=5,
                min_success_rate=99.9,
                max_duration_seconds=None,
                max_age_hours=None,
            ))

            mock_job = MagicMock()
            mock_job.id = 1  # Different job

            violations = monitor._check_violations(
                job=mock_job,
                success_rate=50.0,  # Very bad, but target doesn't apply
                max_duration=None,
                last_execution_date=None,
            )
            assert violations == []

    def test_disabled_target_skipped(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor, SLATarget
            monitor = SLAMonitor()
            monitor.sla_targets.clear()

            monitor.register_target(SLATarget(
                target_id="disabled",
                job_id=None,
                min_success_rate=99.9,
                max_duration_seconds=None,
                max_age_hours=None,
                enabled=False,
            ))

            mock_job = MagicMock()
            mock_job.id = 1

            violations = monitor._check_violations(
                job=mock_job,
                success_rate=0.0,
                max_duration=None,
                last_execution_date=None,
            )
            assert violations == []


class TestSLACheckCompliance:
    """Tests for check_sla_compliance"""

    def test_returns_empty_for_no_jobs(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            with patch("app.alerts.sla_monitor.BackupJob") as mock_bj:
                mock_bj.query.filter_by.return_value.all.return_value = []
                monitor = SLAMonitor()
                result = monitor.check_sla_compliance()
                assert result == []

    def test_returns_empty_for_nonexistent_job_id(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            with patch("app.alerts.sla_monitor.db") as mock_db:
                mock_db.session.get.return_value = None
                monitor = SLAMonitor()
                result = monitor.check_sla_compliance(job_id=99999)
                assert result == []


class TestSLAGetReport:
    """Tests for get_sla_report"""

    def test_report_structure(self, app):
        with app.app_context():
            from app.alerts.sla_monitor import SLAMonitor
            with patch("app.alerts.sla_monitor.BackupJob") as mock_bj:
                mock_bj.query.filter_by.return_value.all.return_value = []
                monitor = SLAMonitor()
                report = monitor.get_sla_report(days=7)

                assert "period_days" in report
                assert "total_jobs" in report
                assert "compliant_jobs" in report
                assert "non_compliant_jobs" in report
                assert "overall_success_rate" in report
                assert report["period_days"] == 7
