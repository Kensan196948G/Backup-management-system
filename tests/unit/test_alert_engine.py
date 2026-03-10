"""
Unit tests for app/alerts/alert_engine.py
AlertEngine, AlertSeverity, AlertType, AlertRule.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta, timezone


class TestAlertSeverity:
    """Tests for AlertSeverity enum"""

    def test_severity_values(self):
        from app.alerts.alert_engine import AlertSeverity
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_all_severities_present(self):
        from app.alerts.alert_engine import AlertSeverity
        values = [s.value for s in AlertSeverity]
        assert set(values) == {"info", "warning", "error", "critical"}


class TestAlertType:
    """Tests for AlertType enum"""

    def test_alert_type_values(self):
        from app.alerts.alert_engine import AlertType
        assert AlertType.BACKUP_FAILED.value == "backup_failed"
        assert AlertType.COMPLIANCE_VIOLATION.value == "compliance_violation"
        assert AlertType.SLA_VIOLATION.value == "sla_violation"

    def test_all_types_present(self):
        from app.alerts.alert_engine import AlertType
        expected = {
            "backup_failed", "backup_warning", "compliance_violation",
            "verification_overdue", "media_error", "sla_violation",
            "storage_capacity", "system_error"
        }
        values = {t.value for t in AlertType}
        assert values == expected


class TestAlertEngineInit:
    """Tests for AlertEngine initialization"""

    def test_init_registers_default_rules(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            assert len(engine.rules) > 0

    def test_default_rules_include_backup_failed(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            assert "backup_failed" in engine.rules

    def test_default_rules_include_compliance(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            assert "compliance_violation" in engine.rules

    def test_default_rules_include_no_recent_backup(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            assert "no_recent_backup" in engine.rules


class TestAlertEngineRuleManagement:
    """Tests for rule registration and unregistration"""

    def test_register_custom_rule(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity
            engine = AlertEngine()
            initial_count = len(engine.rules)

            custom_rule = AlertRule(
                rule_id="custom_test",
                name="Custom Test Rule",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                condition=lambda: [],
                title_template="Test: {job_name}",
                message_template="Test message",
            )
            engine.register_rule(custom_rule)

            assert len(engine.rules) == initial_count + 1
            assert "custom_test" in engine.rules

    def test_unregister_rule(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            assert "backup_failed" in engine.rules

            engine.unregister_rule("backup_failed")
            assert "backup_failed" not in engine.rules

    def test_unregister_nonexistent_rule(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            # Should not raise
            engine.unregister_rule("nonexistent_rule_id")

    def test_disabled_rule_not_evaluated(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity
            condition_called = []

            def condition():
                condition_called.append(True)
                return []

            engine = AlertEngine()
            # Clear existing rules
            engine.rules.clear()

            rule = AlertRule(
                rule_id="disabled_rule",
                name="Disabled Rule",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                condition=condition,
                title_template="Test",
                message_template="Test",
                enabled=False,
            )
            engine.register_rule(rule)
            engine.evaluate_all_rules()

            assert len(condition_called) == 0


class TestAlertEngineEvaluateRules:
    """Tests for rule evaluation logic"""

    def test_evaluate_all_rules_returns_list(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            # Mock all rule conditions to return empty
            for rule in engine.rules.values():
                rule.condition = lambda: []

            result = engine.evaluate_all_rules()
            assert isinstance(result, list)

    def test_evaluate_rule_error_handled_gracefully(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            def bad_condition():
                raise RuntimeError("Condition error")

            engine = AlertEngine()
            engine.rules.clear()

            rule = AlertRule(
                rule_id="error_rule",
                name="Error Rule",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.ERROR,
                condition=bad_condition,
                title_template="Test",
                message_template="Test",
            )
            engine.register_rule(rule)

            # Should not raise despite condition error
            result = engine.evaluate_all_rules()
            assert isinstance(result, list)

    def test_cooldown_prevents_duplicate_alerts(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity

            engine = AlertEngine()
            engine.rules.clear()

            def condition():
                return [{"job_id": 1, "job_name": "Test Job", "error": "error"}]

            rule = AlertRule(
                rule_id="test_cooldown",
                name="Cooldown Test",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=condition,
                title_template="{job_name}",
                message_template="{error}",
                cooldown_minutes=60,
            )
            engine.register_rule(rule)

            # Mock _is_in_cooldown to return True
            with patch.object(engine, "_is_in_cooldown", return_value=True):
                result = engine.evaluate_all_rules()
                assert len(result) == 0


class TestAlertEngineAcknowledge:
    """Tests for acknowledgeAlert"""

    def test_acknowledge_existing_alert(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import Alert, db

            # Create a real alert
            alert = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Test Alert",
                message="Test",
                is_acknowledged=False,
            )
            db.session.add(alert)
            db.session.commit()
            alert_id = alert.id

            engine = AlertEngine()
            result = engine.acknowledge_alert(alert_id, user_id=1)

            assert result is True
            updated = db.session.get(Alert, alert_id)
            assert updated.is_acknowledged is True
            assert updated.acknowledged_by == 1

    def test_acknowledge_nonexistent_alert(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            result = engine.acknowledge_alert(99999, user_id=1)
            assert result is False

    def test_acknowledge_already_acknowledged_alert(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import Alert, db

            alert = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Already Acked",
                message="Test",
                is_acknowledged=True,
                acknowledged_by=1,
            )
            db.session.add(alert)
            db.session.commit()
            alert_id = alert.id

            engine = AlertEngine()
            result = engine.acknowledge_alert(alert_id, user_id=2)
            assert result is True


class TestAlertEngineGetActiveAlerts:
    """Tests for get_active_alerts"""

    def test_returns_unacknowledged_alerts(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            from app.models import Alert, db

            # Create alerts
            active_alert = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Active Alert",
                message="Test",
                is_acknowledged=False,
            )
            acked_alert = Alert(
                alert_type="backup_failed",
                severity="error",
                title="Acked Alert",
                message="Test",
                is_acknowledged=True,
            )
            db.session.add_all([active_alert, acked_alert])
            db.session.commit()

            engine = AlertEngine()
            alerts = engine.get_active_alerts()
            titles = [a.title for a in alerts]
            assert "Active Alert" in titles
            assert "Acked Alert" not in titles

    def test_filter_by_severity(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine, AlertSeverity
            from app.models import Alert, db

            critical_alert = Alert(
                alert_type="backup_failed",
                severity="critical",
                title="Critical",
                message="Test",
                is_acknowledged=False,
            )
            db.session.add(critical_alert)
            db.session.commit()

            engine = AlertEngine()
            alerts = engine.get_active_alerts(severity=AlertSeverity.CRITICAL)
            for alert in alerts:
                assert alert.severity == "critical"


class TestAlertEngineStatistics:
    """Tests for get_alert_statistics"""

    def test_returns_statistics_structure(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            stats = engine.get_alert_statistics(days=30)

            assert "period_days" in stats
            assert "total_alerts" in stats
            assert "acknowledged" in stats
            assert "unacknowledged" in stats
            assert "by_severity" in stats
            assert "by_type" in stats
            assert stats["period_days"] == 30

    def test_unacknowledged_equals_total_minus_acknowledged(self, app):
        with app.app_context():
            from app.alerts.alert_engine import AlertEngine
            engine = AlertEngine()
            stats = engine.get_alert_statistics()

            assert stats["unacknowledged"] == stats["total_alerts"] - stats["acknowledged"]
