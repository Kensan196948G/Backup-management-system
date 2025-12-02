"""
Celery Cleanup Tasks for Backup Management System
Phase 11: Asynchronous Maintenance Tasks

This module provides background maintenance tasks for
log cleanup, database optimization, and system health checks.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.cleanup_old_logs",
    max_retries=1,
    default_retry_delay=300,
)
def cleanup_old_logs(
    self,
    retention_days: int = 90,
) -> Dict[str, Any]:
    """
    Clean up old log files.

    This task removes log files older than the retention period
    to prevent disk space exhaustion.

    Args:
        self: Celery task instance (bound)
        retention_days: Number of days to retain logs

    Returns:
        Dict with cleanup results
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Starting log cleanup (retention: {retention_days} days)")

    result = {
        "task_id": task_id,
        "retention_days": retention_days,
        "status": "processing",
        "deleted_files": [],
        "total_size_freed": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Get logs directory
        logs_dir = Path(__file__).parent.parent.parent / "logs"

        if not logs_dir.exists():
            result["status"] = "skipped"
            result["message"] = "Logs directory does not exist"
            return result

        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        # Find and delete old log files
        for log_file in logs_dir.glob("**/*.log*"):
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff:
                    file_size = log_file.stat().st_size
                    log_file.unlink()

                    result["deleted_files"].append(
                        {
                            "path": str(log_file),
                            "size": file_size,
                            "modified": file_mtime.isoformat(),
                        }
                    )
                    result["total_size_freed"] += file_size

                    logger.debug(f"Deleted old log: {log_file}")

            except Exception as e:
                logger.warning(f"Failed to delete {log_file}: {e}")

        result["status"] = "completed"
        result["files_deleted"] = len(result["deleted_files"])

        logger.info(
            f"[Task {task_id}] Cleaned up {result['files_deleted']} files, "
            f"freed {result['total_size_freed'] / 1024 / 1024:.2f} MB"
        )

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error cleaning up logs: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.cleanup_old_reports",
    max_retries=1,
)
def cleanup_old_reports(
    self,
    retention_days: int = 365,
) -> Dict[str, Any]:
    """
    Clean up old generated reports.

    Args:
        self: Celery task instance (bound)
        retention_days: Number of days to retain reports

    Returns:
        Dict with cleanup results
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Starting report cleanup")

    result = {
        "task_id": task_id,
        "retention_days": retention_days,
        "status": "processing",
        "deleted_files": [],
        "total_size_freed": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        reports_dir = Path(__file__).parent.parent.parent / "reports"

        if not reports_dir.exists():
            result["status"] = "skipped"
            result["message"] = "Reports directory does not exist"
            return result

        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        # Find and delete old reports
        for report_file in reports_dir.glob("**/*.pdf"):
            try:
                file_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                if file_mtime < cutoff:
                    file_size = report_file.stat().st_size
                    report_file.unlink()

                    result["deleted_files"].append(str(report_file))
                    result["total_size_freed"] += file_size

            except Exception as e:
                logger.warning(f"Failed to delete {report_file}: {e}")

        result["status"] = "completed"
        result["files_deleted"] = len(result["deleted_files"])

        logger.info(f"[Task {task_id}] Cleaned up {result['files_deleted']} old reports")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error cleaning up reports: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.cleanup_old_notifications",
    max_retries=1,
)
def cleanup_old_notifications(
    self,
    retention_days: int = 30,
) -> Dict[str, Any]:
    """
    Clean up old notification records from database.

    Args:
        self: Celery task instance (bound)
        retention_days: Number of days to retain notification records

    Returns:
        Dict with cleanup results
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Starting notification cleanup")

    result = {
        "task_id": task_id,
        "retention_days": retention_days,
        "status": "processing",
        "deleted_count": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        from app.models import NotificationLog, db

        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        # Delete old notifications (using sent_at field)
        deleted = NotificationLog.query.filter(NotificationLog.sent_at < cutoff).delete()

        db.session.commit()

        result["status"] = "completed"
        result["deleted_count"] = deleted

        logger.info(f"[Task {task_id}] Deleted {deleted} old notification records")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error cleaning up notifications: {e}")
        db.session.rollback()
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.cleanup_old_alerts",
    max_retries=1,
)
def cleanup_old_alerts(
    self,
    retention_days: int = 90,
    only_read: bool = True,
) -> Dict[str, Any]:
    """
    Clean up old alert records from database.

    Args:
        self: Celery task instance (bound)
        retention_days: Number of days to retain alerts
        only_read: Only delete read alerts if True

    Returns:
        Dict with cleanup results
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Starting alert cleanup")

    result = {
        "task_id": task_id,
        "retention_days": retention_days,
        "only_read": only_read,
        "status": "processing",
        "deleted_count": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        from app.models import Alert, db

        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        query = Alert.query.filter(Alert.created_at < cutoff)

        if only_read:
            query = query.filter(Alert.is_acknowledged.is_(True))

        deleted = query.delete()

        db.session.commit()

        result["status"] = "completed"
        result["deleted_count"] = deleted

        logger.info(f"[Task {task_id}] Deleted {deleted} old alerts")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error cleaning up alerts: {e}")
        db.session.rollback()
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.vacuum_database",
    max_retries=1,
    time_limit=1800,  # 30 minutes max
)
def vacuum_database(self) -> Dict[str, Any]:
    """
    Optimize database by running VACUUM.

    This task reclaims space and optimizes SQLite database.
    For PostgreSQL, it runs VACUUM ANALYZE.

    Returns:
        Dict with optimization results
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Starting database vacuum")

    result = {
        "task_id": task_id,
        "status": "processing",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        from flask import current_app

        from app.models import db

        # Get database URL
        db_url = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")

        if "sqlite" in db_url:
            # SQLite VACUUM - use raw connection for VACUUM which needs AUTOCOMMIT
            connection = db.engine.raw_connection()
            connection.isolation_level = None  # AUTOCOMMIT for SQLite
            cursor = connection.cursor()
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")
            cursor.close()
            connection.close()
            result["database_type"] = "sqlite"
        elif "postgresql" in db_url:
            # PostgreSQL VACUUM
            # Note: VACUUM cannot run in a transaction
            connection = db.engine.raw_connection()
            connection.set_isolation_level(0)  # AUTOCOMMIT
            cursor = connection.cursor()
            cursor.execute("VACUUM ANALYZE")
            cursor.close()
            connection.close()
            result["database_type"] = "postgresql"
        else:
            result["status"] = "skipped"
            result["message"] = "Unsupported database type for vacuum"
            return result

        result["status"] = "completed"

        logger.info(f"[Task {task_id}] Database vacuum completed")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error vacuuming database: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.run_all_maintenance",
    max_retries=1,
)
def run_all_maintenance(self) -> Dict[str, Any]:
    """
    Run all maintenance tasks.

    This task orchestrates all cleanup and maintenance tasks,
    suitable for scheduled daily/weekly execution.

    Returns:
        Dict with overall maintenance status
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Starting full maintenance run")

    result = {
        "task_id": task_id,
        "status": "processing",
        "subtasks": {},
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Queue all maintenance tasks
        tasks = [
            ("cleanup_logs", cleanup_old_logs.apply_async(kwargs={"retention_days": 90})),
            ("cleanup_reports", cleanup_old_reports.apply_async(kwargs={"retention_days": 365})),
            (
                "cleanup_notifications",
                cleanup_old_notifications.apply_async(kwargs={"retention_days": 30}),
            ),
            (
                "cleanup_alerts",
                cleanup_old_alerts.apply_async(kwargs={"retention_days": 90, "only_read": True}),
            ),
            ("vacuum_database", vacuum_database.apply_async()),
        ]

        for name, task in tasks:
            result["subtasks"][name] = {
                "task_id": task.id,
                "status": "queued",
            }

        result["status"] = "queued"
        result["queued_tasks"] = len(tasks)

        logger.info(f"[Task {task_id}] Queued {len(tasks)} maintenance tasks")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error running maintenance: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.check_disk_space",
    max_retries=1,
)
def check_disk_space(
    self,
    warning_threshold_gb: float = 10.0,
    critical_threshold_gb: float = 5.0,
) -> Dict[str, Any]:
    """
    Check available disk space and alert if low.

    Args:
        self: Celery task instance (bound)
        warning_threshold_gb: Warning threshold in GB
        critical_threshold_gb: Critical threshold in GB

    Returns:
        Dict with disk space status
    """
    import shutil

    task_id = self.request.id

    logger.info(f"[Task {task_id}] Checking disk space")

    result = {
        "task_id": task_id,
        "status": "processing",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Check data directory disk space
        data_dir = Path(__file__).parent.parent.parent / "data"
        total, used, free = shutil.disk_usage(data_dir)

        free_gb = free / (1024**3)
        total_gb = total / (1024**3)
        used_percent = (used / total) * 100

        result["disk_space"] = {
            "path": str(data_dir),
            "total_gb": round(total_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_percent": round(used_percent, 1),
        }

        # Determine status
        if free_gb < critical_threshold_gb:
            result["status"] = "critical"
            _create_disk_space_alert(free_gb, "critical")
        elif free_gb < warning_threshold_gb:
            result["status"] = "warning"
            _create_disk_space_alert(free_gb, "warning")
        else:
            result["status"] = "ok"

        logger.info(f"[Task {task_id}] Disk space: {free_gb:.2f} GB free ({result['status']})")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error checking disk space: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


def _create_disk_space_alert(free_gb: float, severity: str):
    """Create disk space alert."""
    try:
        from app.models import Alert, db

        level = "critical" if severity == "critical" else "warning"

        alert = Alert(
            title=f"ディスク容量{'不足' if severity == 'critical' else '警告'}",
            message=f"空きディスク容量が{free_gb:.2f}GBまで減少しています。",
            level=level,
            source="disk_space_check",
            is_read=False,
            created_at=datetime.utcnow(),
        )

        db.session.add(alert)
        db.session.commit()

    except Exception as e:
        logger.warning(f"Failed to create disk space alert: {e}")
        db.session.rollback()
