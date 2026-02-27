"""
SLA Monitoring Service
Tracks backup completion times, success rates, and alerts on SLA violations
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, func

from app.models import Alert, BackupExecution, BackupJob, db

logger = logging.getLogger(__name__)


@dataclass
class SLAMetrics:
    """SLA metrics for a backup job"""

    job_id: int
    job_name: str
    success_rate: float  # Percentage
    average_duration_seconds: Optional[int]
    max_duration_seconds: Optional[int]
    last_execution_date: Optional[datetime]
    executions_count: int
    failed_count: int
    warning_count: int
    success_count: int
    is_compliant: bool
    violations: List[str]


@dataclass
class SLATarget:
    """SLA target definition"""

    target_id: str
    job_id: Optional[int]  # None = applies to all jobs
    min_success_rate: float  # Percentage (0-100)
    max_duration_seconds: Optional[int]  # Maximum allowed duration
    max_age_hours: Optional[int]  # Maximum time since last backup
    enabled: bool = True


class SLAMonitor:
    """
    SLA Monitoring Service
    Tracks and reports on SLA compliance
    """

    def __init__(self):
        self.sla_targets: Dict[str, SLATarget] = {}
        self._register_default_targets()

    def _register_default_targets(self):
        """Register default SLA targets"""

        # Default: 95% success rate for all jobs
        self.register_target(
            SLATarget(
                target_id="default_success_rate",
                job_id=None,
                min_success_rate=95.0,
                max_duration_seconds=None,
                max_age_hours=None,
            )
        )

        # Default: Daily backups should complete within 24 hours
        self.register_target(
            SLATarget(
                target_id="default_daily_age",
                job_id=None,
                min_success_rate=0,
                max_duration_seconds=None,
                max_age_hours=36,  # 1.5 days for daily backups
            )
        )

    def register_target(self, target: SLATarget):
        """Register an SLA target"""
        self.sla_targets[target.target_id] = target
        logger.info(f"Registered SLA target: {target.target_id}")

    def unregister_target(self, target_id: str):
        """Unregister an SLA target"""
        if target_id in self.sla_targets:
            del self.sla_targets[target_id]
            logger.info(f"Unregistered SLA target: {target_id}")

    def check_sla_compliance(self, job_id: Optional[int] = None, days: int = 30) -> List[SLAMetrics]:
        """
        Check SLA compliance for jobs

        Args:
            job_id: Specific job ID, or None for all jobs
            days: Number of days to analyze

        Returns:
            List of SLA metrics for each job
        """
        metrics_list = []

        if job_id:
            jobs = [db.session.get(BackupJob, job_id)]
            if not jobs[0]:
                logger.warning(f"Job {job_id} not found")
                return []
        else:
            jobs = BackupJob.query.filter_by(is_active=True).all()

        for job in jobs:
            metrics = self._calculate_job_metrics(job, days)
            metrics_list.append(metrics)

        return metrics_list

    def _calculate_job_metrics(self, job: BackupJob, days: int) -> SLAMetrics:
        """Calculate SLA metrics for a specific job"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get executions within the period
        executions = (
            BackupExecution.query.filter(
                and_(
                    BackupExecution.job_id == job.id,
                    BackupExecution.execution_date >= start_date,
                )
            )
            .order_by(BackupExecution.execution_date.desc())
            .all()
        )

        # Count by result
        total_count = len(executions)
        success_count = sum(1 for e in executions if e.execution_result == "success")
        failed_count = sum(1 for e in executions if e.execution_result == "failed")
        warning_count = sum(1 for e in executions if e.execution_result == "warning")

        # Calculate success rate
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0.0

        # Calculate duration metrics
        durations = [e.duration_seconds for e in executions if e.duration_seconds]
        avg_duration = int(sum(durations) / len(durations)) if durations else None
        max_duration = max(durations) if durations else None

        # Get last execution
        last_execution = executions[0] if executions else None
        last_execution_date = last_execution.execution_date if last_execution else None

        # Check for violations
        violations = self._check_violations(
            job=job,
            success_rate=success_rate,
            max_duration=max_duration,
            last_execution_date=last_execution_date,
        )

        is_compliant = len(violations) == 0

        return SLAMetrics(
            job_id=job.id,
            job_name=job.job_name,
            success_rate=success_rate,
            average_duration_seconds=avg_duration,
            max_duration_seconds=max_duration,
            last_execution_date=last_execution_date,
            executions_count=total_count,
            failed_count=failed_count,
            warning_count=warning_count,
            success_count=success_count,
            is_compliant=is_compliant,
            violations=violations,
        )

    def _check_violations(
        self,
        job: BackupJob,
        success_rate: float,
        max_duration: Optional[int],
        last_execution_date: Optional[datetime],
    ) -> List[str]:
        """Check for SLA violations"""
        violations = []

        for target_id, target in self.sla_targets.items():
            if not target.enabled:
                continue

            # Skip if target is for a specific job and doesn't match
            if target.job_id is not None and target.job_id != job.id:
                continue

            # Check success rate
            if target.min_success_rate > 0 and success_rate < target.min_success_rate:
                violations.append(f"Success rate {success_rate:.1f}% below target {target.min_success_rate:.1f}%")

            # Check duration
            if target.max_duration_seconds and max_duration and max_duration > target.max_duration_seconds:
                violations.append(f"Max duration {max_duration}s exceeds target {target.max_duration_seconds}s")

            # Check backup age
            if target.max_age_hours and last_execution_date:
                age_hours = (datetime.utcnow() - last_execution_date).total_seconds() / 3600
                if age_hours > target.max_age_hours:
                    violations.append(f"Last backup {age_hours:.1f}h ago exceeds target {target.max_age_hours}h")

        return violations

    def generate_sla_alerts(self, days: int = 30) -> List[Alert]:
        """
        Generate SLA violation alerts

        Args:
            days: Number of days to analyze

        Returns:
            List of generated alerts
        """
        alerts = []
        metrics_list = self.check_sla_compliance(days=days)

        for metrics in metrics_list:
            if not metrics.is_compliant:
                alert = self._create_sla_alert(metrics)
                if alert:
                    alerts.append(alert)

        return alerts

    def _create_sla_alert(self, metrics: SLAMetrics) -> Optional[Alert]:
        """Create an SLA violation alert"""
        try:
            # Check if similar alert exists recently
            one_day_ago = datetime.utcnow() - timedelta(days=1)
            recent_alert = (
                Alert.query.filter(
                    and_(
                        Alert.alert_type == "sla_violation",
                        Alert.job_id == metrics.job_id,
                        Alert.created_at >= one_day_ago,
                        Alert.is_acknowledged == False,  # noqa: E712
                    )
                )
                .order_by(Alert.created_at.desc())
                .first()
            )

            if recent_alert:
                logger.debug(f"Recent SLA alert exists for job {metrics.job_id}")
                return None

            # Create alert
            title = f"SLA Violation: {metrics.job_name}"
            message = (
                f"Backup job '{metrics.job_name}' has violated SLA targets.\n\n"
                f"Success Rate: {metrics.success_rate:.1f}%\n"
                f"Executions: {metrics.executions_count} "
                f"({metrics.success_count} success, {metrics.failed_count} failed, {metrics.warning_count} warning)\n"
                f"Average Duration: {metrics.average_duration_seconds}s\n"
                f"Last Execution: {metrics.last_execution_date.strftime('%Y-%m-%d %H:%M:%S') if metrics.last_execution_date else 'Never'}\n\n"
                f"Violations:\n" + "\n".join(f"- {v}" for v in metrics.violations)
            )

            alert = Alert(
                alert_type="sla_violation",
                severity="error",
                job_id=metrics.job_id,
                title=title,
                message=message,
                is_acknowledged=False,
            )

            db.session.add(alert)
            db.session.commit()

            logger.info(f"Created SLA violation alert for job {metrics.job_id}")
            return alert

        except Exception as e:
            logger.error(f"Error creating SLA alert: {e}", exc_info=True)
            db.session.rollback()
            return None

    def get_sla_report(self, days: int = 30) -> Dict:
        """
        Generate SLA compliance report

        Args:
            days: Number of days to analyze

        Returns:
            SLA report dictionary
        """
        metrics_list = self.check_sla_compliance(days=days)

        compliant_count = sum(1 for m in metrics_list if m.is_compliant)
        non_compliant_count = len(metrics_list) - compliant_count

        overall_success_rate = sum(m.success_rate for m in metrics_list) / len(metrics_list) if metrics_list else 0.0

        job_details = []
        for metrics in metrics_list:
            job_details.append(
                {
                    "job_id": metrics.job_id,
                    "job_name": metrics.job_name,
                    "success_rate": f"{metrics.success_rate:.1f}%",
                    "average_duration": f"{metrics.average_duration_seconds}s" if metrics.average_duration_seconds else "N/A",
                    "executions": metrics.executions_count,
                    "last_execution": (
                        metrics.last_execution_date.strftime("%Y-%m-%d %H:%M:%S") if metrics.last_execution_date else "Never"
                    ),
                    "is_compliant": metrics.is_compliant,
                    "violations": metrics.violations,
                }
            )

        return {
            "report_date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "period_days": days,
            "total_jobs": len(metrics_list),
            "compliant_jobs": compliant_count,
            "non_compliant_jobs": non_compliant_count,
            "overall_success_rate": f"{overall_success_rate:.1f}%",
            "jobs": job_details,
        }

    def get_job_trend(self, job_id: int, days: int = 30, interval_days: int = 7) -> List[Dict]:
        """
        Get success rate trend for a job over time

        Args:
            job_id: Job ID
            days: Total number of days to analyze
            interval_days: Interval size for trend data points

        Returns:
            List of trend data points
        """
        trend_data = []
        job = db.session.get(BackupJob, job_id)

        if not job:
            logger.warning(f"Job {job_id} not found")
            return []

        # Calculate data points
        num_intervals = days // interval_days
        for i in range(num_intervals):
            end_date = datetime.utcnow() - timedelta(days=i * interval_days)
            start_date = end_date - timedelta(days=interval_days)

            # Get executions in interval
            executions = BackupExecution.query.filter(
                and_(
                    BackupExecution.job_id == job_id,
                    BackupExecution.execution_date >= start_date,
                    BackupExecution.execution_date < end_date,
                )
            ).all()

            total = len(executions)
            success = sum(1 for e in executions if e.execution_result == "success")
            success_rate = (success / total * 100) if total > 0 else 0.0

            trend_data.append(
                {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "success_rate": success_rate,
                    "total_executions": total,
                    "successful_executions": success,
                }
            )

        # Reverse to show oldest to newest
        trend_data.reverse()

        return trend_data

    def get_global_statistics(self, days: int = 30) -> Dict:
        """
        Get global backup statistics

        Args:
            days: Number of days to analyze

        Returns:
            Global statistics dictionary
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Total executions
        total_executions = BackupExecution.query.filter(BackupExecution.execution_date >= start_date).count()

        # Count by result
        by_result = (
            db.session.query(BackupExecution.execution_result, func.count(BackupExecution.id).label("count"))
            .filter(BackupExecution.execution_date >= start_date)
            .group_by(BackupExecution.execution_result)
            .all()
        )

        result_counts = {result: count for result, count in by_result}

        # Average duration
        avg_duration = (
            db.session.query(func.avg(BackupExecution.duration_seconds))
            .filter(
                and_(
                    BackupExecution.execution_date >= start_date,
                    BackupExecution.duration_seconds.isnot(None),
                )
            )
            .scalar()
        )

        # Total data backed up
        total_size = (
            db.session.query(func.sum(BackupExecution.backup_size_bytes))
            .filter(
                and_(
                    BackupExecution.execution_date >= start_date,
                    BackupExecution.backup_size_bytes.isnot(None),
                )
            )
            .scalar()
        )

        # Active jobs
        active_jobs = BackupJob.query.filter_by(is_active=True).count()

        return {
            "period_days": days,
            "active_jobs": active_jobs,
            "total_executions": total_executions,
            "successful": result_counts.get("success", 0),
            "failed": result_counts.get("failed", 0),
            "warning": result_counts.get("warning", 0),
            "average_duration_seconds": int(avg_duration) if avg_duration else 0,
            "total_size_gb": round(total_size / (1024**3), 2) if total_size else 0.0,
        }
