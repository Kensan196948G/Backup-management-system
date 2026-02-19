"""
Alert Rules Engine
Defines alert rules, severity levels, and alert generation logic
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import and_, func, or_

from app.models import (
    Alert,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    VerificationSchedule,
    db,
)

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Alert types"""

    BACKUP_FAILED = "backup_failed"
    BACKUP_WARNING = "backup_warning"
    COMPLIANCE_VIOLATION = "compliance_violation"
    VERIFICATION_OVERDUE = "verification_overdue"
    MEDIA_ERROR = "media_error"
    SLA_VIOLATION = "sla_violation"
    STORAGE_CAPACITY = "storage_capacity"
    SYSTEM_ERROR = "system_error"


@dataclass
class AlertRule:
    """
    Alert rule definition
    """

    rule_id: str
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: Callable
    title_template: str
    message_template: str
    cooldown_minutes: int = 60  # Minimum time between same alerts
    enabled: bool = True


class AlertEngine:
    """
    Alert Rules Engine
    Evaluates conditions and generates alerts
    """

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        """Register default alert rules"""

        # Rule: Backup Failed
        self.register_rule(
            AlertRule(
                rule_id="backup_failed",
                name="Backup Job Failed",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.ERROR,
                condition=self._check_backup_failed,
                title_template="Backup Failed: {job_name}",
                message_template="Backup job '{job_name}' failed at {execution_date}. Error: {error_message}",
                cooldown_minutes=30,
            )
        )

        # Rule: Multiple Consecutive Failures
        self.register_rule(
            AlertRule(
                rule_id="backup_consecutive_failures",
                name="Multiple Consecutive Backup Failures",
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.CRITICAL,
                condition=self._check_consecutive_failures,
                title_template="Critical: {job_name} Failed {failure_count} Times",
                message_template="Backup job '{job_name}' has failed {failure_count} consecutive times. Last error: {error_message}",
                cooldown_minutes=60,
            )
        )

        # Rule: Backup Warning
        self.register_rule(
            AlertRule(
                rule_id="backup_warning",
                name="Backup Job Warning",
                alert_type=AlertType.BACKUP_WARNING,
                severity=AlertSeverity.WARNING,
                condition=self._check_backup_warning,
                title_template="Backup Warning: {job_name}",
                message_template="Backup job '{job_name}' completed with warnings at {execution_date}. Details: {error_message}",
                cooldown_minutes=30,
            )
        )

        # Rule: Compliance Violation
        self.register_rule(
            AlertRule(
                rule_id="compliance_violation",
                name="3-2-1-1-0 Rule Violation",
                alert_type=AlertType.COMPLIANCE_VIOLATION,
                severity=AlertSeverity.ERROR,
                condition=self._check_compliance_violation,
                title_template="Compliance Violation: {job_name}",
                message_template="Backup job '{job_name}' violates 3-2-1-1-0 rule. Status: {compliance_status}. Details: {details}",
                cooldown_minutes=120,
            )
        )

        # Rule: Verification Overdue
        self.register_rule(
            AlertRule(
                rule_id="verification_overdue",
                name="Verification Test Overdue",
                alert_type=AlertType.VERIFICATION_OVERDUE,
                severity=AlertSeverity.WARNING,
                condition=self._check_verification_overdue,
                title_template="Verification Overdue: {job_name}",
                message_template="Verification test for '{job_name}' is overdue. Next test date: {next_test_date}",
                cooldown_minutes=1440,  # 24 hours
            )
        )

        # Rule: No Recent Backup
        self.register_rule(
            AlertRule(
                rule_id="no_recent_backup",
                name="No Recent Backup Execution",
                alert_type=AlertType.BACKUP_WARNING,
                severity=AlertSeverity.WARNING,
                condition=self._check_no_recent_backup,
                title_template="No Recent Backup: {job_name}",
                message_template="Backup job '{job_name}' has not executed in the last {hours} hours. Last execution: {last_execution}",
                cooldown_minutes=360,  # 6 hours
            )
        )

    def register_rule(self, rule: AlertRule):
        """Register an alert rule"""
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered alert rule: {rule.name} (ID: {rule.rule_id})")

    def unregister_rule(self, rule_id: str):
        """Unregister an alert rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Unregistered alert rule: {rule_id}")

    def evaluate_all_rules(self) -> List[Alert]:
        """
        Evaluate all enabled rules and generate alerts
        Returns list of newly created alerts
        """
        new_alerts = []

        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue

            try:
                alerts = self._evaluate_rule(rule)
                new_alerts.extend(alerts)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_id}: {e}", exc_info=True)

        return new_alerts

    def _evaluate_rule(self, rule: AlertRule) -> List[Alert]:
        """Evaluate a single rule"""
        alerts = []

        try:
            # Get conditions that trigger the rule
            triggers = rule.condition()

            if not triggers:
                return alerts

            # Generate alerts for each trigger
            for trigger in triggers:
                # Check cooldown period
                if self._is_in_cooldown(rule, trigger):
                    logger.debug(f"Alert in cooldown period: {rule.rule_id} for {trigger.get('job_id')}")
                    continue

                # Create alert
                alert = self._create_alert(rule, trigger)
                if alert:
                    alerts.append(alert)
                    logger.info(f"Created alert: {rule.name} for job {trigger.get('job_id')}")

        except Exception as e:
            logger.error(f"Error in rule evaluation {rule.rule_id}: {e}", exc_info=True)

        return alerts

    def _is_in_cooldown(self, rule: AlertRule, trigger: Dict[str, Any]) -> bool:
        """Check if alert is in cooldown period"""
        job_id = trigger.get("job_id")
        if not job_id:
            return False

        cooldown_time = datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)

        # Check for recent similar alerts
        recent_alert = (
            Alert.query.filter(
                and_(
                    Alert.alert_type == rule.alert_type.value,
                    Alert.job_id == job_id,
                    Alert.created_at >= cooldown_time,
                )
            )
            .order_by(Alert.created_at.desc())
            .first()
        )

        return recent_alert is not None

    def _create_alert(self, rule: AlertRule, trigger: Dict[str, Any]) -> Optional[Alert]:
        """Create an alert from a rule and trigger data"""
        try:
            # Format title and message
            title = rule.title_template.format(**trigger)
            message = rule.message_template.format(**trigger)

            # Create alert object
            alert = Alert(
                alert_type=rule.alert_type.value,
                severity=rule.severity.value,
                job_id=trigger.get("job_id"),
                title=title,
                message=message,
                is_acknowledged=False,
            )

            db.session.add(alert)
            db.session.commit()

            return alert

        except Exception as e:
            logger.error(f"Error creating alert: {e}", exc_info=True)
            db.session.rollback()
            return None

    # ==================== Rule Condition Functions ====================

    def _check_backup_failed(self) -> List[Dict[str, Any]]:
        """Check for failed backups in the last hour"""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        failed_executions = (
            BackupExecution.query.filter(
                and_(BackupExecution.execution_result == "failed", BackupExecution.execution_date >= one_hour_ago)
            )
            .order_by(BackupExecution.execution_date.desc())
            .all()
        )

        triggers = []
        for execution in failed_executions:
            job = execution.job
            triggers.append(
                {
                    "job_id": job.id,
                    "job_name": job.job_name,
                    "execution_date": execution.execution_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "error_message": execution.error_message or "Unknown error",
                }
            )

        return triggers

    def _check_consecutive_failures(self) -> List[Dict[str, Any]]:
        """Check for multiple consecutive failures (3 or more)"""
        threshold = 3
        triggers = []

        # Get all active jobs
        active_jobs = BackupJob.query.filter_by(is_active=True).all()

        for job in active_jobs:
            # Get last N executions
            recent_executions = (
                BackupExecution.query.filter_by(job_id=job.id)
                .order_by(BackupExecution.execution_date.desc())
                .limit(threshold)
                .all()
            )

            if len(recent_executions) >= threshold:
                # Check if all are failures
                if all(exec.execution_result == "failed" for exec in recent_executions):
                    triggers.append(
                        {
                            "job_id": job.id,
                            "job_name": job.job_name,
                            "failure_count": threshold,
                            "error_message": recent_executions[0].error_message or "Multiple failures detected",
                        }
                    )

        return triggers

    def _check_backup_warning(self) -> List[Dict[str, Any]]:
        """Check for backup warnings in the last hour"""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        warning_executions = (
            BackupExecution.query.filter(
                and_(BackupExecution.execution_result == "warning", BackupExecution.execution_date >= one_hour_ago)
            )
            .order_by(BackupExecution.execution_date.desc())
            .all()
        )

        triggers = []
        for execution in warning_executions:
            job = execution.job
            triggers.append(
                {
                    "job_id": job.id,
                    "job_name": job.job_name,
                    "execution_date": execution.execution_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "error_message": execution.error_message or "Warning occurred",
                }
            )

        return triggers

    def _check_compliance_violation(self) -> List[Dict[str, Any]]:
        """Check for compliance rule violations"""
        triggers = []

        # Get latest compliance status for each job
        subquery = (
            db.session.query(ComplianceStatus.job_id, func.max(ComplianceStatus.check_date).label("max_date"))
            .group_by(ComplianceStatus.job_id)
            .subquery()
        )

        non_compliant = (
            db.session.query(ComplianceStatus)
            .join(
                subquery,
                and_(ComplianceStatus.job_id == subquery.c.job_id, ComplianceStatus.check_date == subquery.c.max_date),
            )
            .filter(ComplianceStatus.overall_status == "non_compliant")
            .all()
        )

        for status in non_compliant:
            job = status.job
            details = []
            if status.copies_count < 3:
                details.append(f"Insufficient copies: {status.copies_count}/3")
            if status.media_types_count < 2:
                details.append(f"Insufficient media types: {status.media_types_count}/2")
            if not status.has_offsite:
                details.append("No offsite backup")
            if not status.has_offline:
                details.append("No offline backup")
            if status.has_errors:
                details.append("Backup errors detected")

            triggers.append(
                {
                    "job_id": job.id,
                    "job_name": job.job_name,
                    "compliance_status": status.overall_status,
                    "details": "; ".join(details),
                }
            )

        return triggers

    def _check_verification_overdue(self) -> List[Dict[str, Any]]:
        """Check for overdue verification tests"""
        today = datetime.utcnow().date()
        triggers = []

        overdue_schedules = (
            VerificationSchedule.query.filter(
                and_(VerificationSchedule.is_active == True, VerificationSchedule.next_test_date < today)  # noqa: E712
            )
            .order_by(VerificationSchedule.next_test_date.asc())
            .all()
        )

        for schedule in overdue_schedules:
            job = schedule.job
            triggers.append(
                {
                    "job_id": job.id,
                    "job_name": job.job_name,
                    "next_test_date": schedule.next_test_date.strftime("%Y-%m-%d"),
                }
            )

        return triggers

    def _check_no_recent_backup(self) -> List[Dict[str, Any]]:
        """Check for jobs without recent backups (based on schedule)"""
        triggers = []
        threshold_hours = 48  # Default threshold

        active_jobs = BackupJob.query.filter_by(is_active=True).all()

        for job in active_jobs:
            # Get threshold based on schedule type
            if job.schedule_type == "daily":
                threshold_hours = 36  # 1.5 days
            elif job.schedule_type == "weekly":
                threshold_hours = 192  # 8 days
            elif job.schedule_type == "monthly":
                threshold_hours = 768  # 32 days
            else:
                continue  # Skip manual jobs

            threshold_time = datetime.utcnow() - timedelta(hours=threshold_hours)

            # Get last successful execution
            last_execution = (
                BackupExecution.query.filter_by(job_id=job.id).order_by(BackupExecution.execution_date.desc()).first()
            )

            if not last_execution or last_execution.execution_date < threshold_time:
                last_exec_str = last_execution.execution_date.strftime("%Y-%m-%d %H:%M:%S") if last_execution else "Never"

                triggers.append(
                    {
                        "job_id": job.id,
                        "job_name": job.job_name,
                        "hours": threshold_hours,
                        "last_execution": last_exec_str,
                    }
                )

        return triggers

    def acknowledge_alert(self, alert_id: int, user_id: int) -> bool:
        """Acknowledge an alert"""
        try:
            alert = Alert.query.get(alert_id)
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return False

            if alert.is_acknowledged:
                logger.info(f"Alert {alert_id} already acknowledged")
                return True

            alert.is_acknowledged = True
            alert.acknowledged_by = user_id
            alert.acknowledged_at = datetime.utcnow()

            db.session.commit()
            logger.info(f"Alert {alert_id} acknowledged by user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}", exc_info=True)
            db.session.rollback()
            return False

    def get_active_alerts(
        self, severity: Optional[AlertSeverity] = None, alert_type: Optional[AlertType] = None, job_id: Optional[int] = None
    ) -> List[Alert]:
        """Get active (unacknowledged) alerts with optional filters"""
        query = Alert.query.filter_by(is_acknowledged=False)

        if severity:
            query = query.filter_by(severity=severity.value)

        if alert_type:
            query = query.filter_by(alert_type=alert_type.value)

        if job_id:
            query = query.filter_by(job_id=job_id)

        return query.order_by(Alert.created_at.desc()).all()

    def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert statistics for the specified period"""
        start_date = datetime.utcnow() - timedelta(days=days)

        total_alerts = Alert.query.filter(Alert.created_at >= start_date).count()

        by_severity = (
            db.session.query(Alert.severity, func.count(Alert.id).label("count"))
            .filter(Alert.created_at >= start_date)
            .group_by(Alert.severity)
            .all()
        )

        by_type = (
            db.session.query(Alert.alert_type, func.count(Alert.id).label("count"))
            .filter(Alert.created_at >= start_date)
            .group_by(Alert.alert_type)
            .all()
        )

        acknowledged = Alert.query.filter(
            and_(Alert.created_at >= start_date, Alert.is_acknowledged == True)
        ).count()  # noqa: E712

        return {
            "period_days": days,
            "total_alerts": total_alerts,
            "acknowledged": acknowledged,
            "unacknowledged": total_alerts - acknowledged,
            "by_severity": {sev: count for sev, count in by_severity},
            "by_type": {typ: count for typ, count in by_type},
        }
