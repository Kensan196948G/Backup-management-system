"""
Dashboard Summary API
Provides summary data for dashboard display
"""

import logging
from datetime import datetime, timedelta, timezone

from flask import jsonify
from sqlalchemy import and_, func

from app.api import api_bp
from app.api.errors import error_response
from app.auth.decorators import api_token_required
from app.models import (
    Alert,
    BackupCopy,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    OfflineMedia,
    db,
)

logger = logging.getLogger(__name__)


@api_bp.route("/dashboard/summary", methods=["GET"])
@api_token_required
def get_dashboard_summary():
    """
    Get dashboard summary statistics

    Returns:
        200: Dashboard summary data
        {
            "jobs": {
                "total": 50,
                "active": 48,
                "inactive": 2
            },
            "compliance": {
                "compliant": 45,
                "non_compliant": 3,
                "warning": 2
            },
            "executions_24h": {
                "total": 120,
                "success": 115,
                "failed": 3,
                "warning": 2
            },
            "alerts": {
                "critical": 2,
                "error": 5,
                "warning": 10,
                "total_unacknowledged": 17
            },
            "verification_tests": {
                "pending": 5,
                "overdue": 2
            },
            "offline_media": {
                "total": 30,
                "in_use": 15,
                "stored": 12,
                "retired": 3
            }
        }
    """
    try:
        summary = {}

        # Jobs statistics
        summary["jobs"] = {
            "total": BackupJob.query.count(),
            "active": BackupJob.query.filter_by(is_active=True).count(),
            "inactive": BackupJob.query.filter_by(is_active=False).count(),
        }

        # Compliance statistics (latest status for each job)
        compliance_subquery = (
            db.session.query(ComplianceStatus.job_id, func.max(ComplianceStatus.check_date).label("latest_check"))
            .group_by(ComplianceStatus.job_id)
            .subquery()
        )

        latest_compliance = (
            db.session.query(ComplianceStatus.overall_status, func.count(ComplianceStatus.id))
            .join(
                compliance_subquery,
                and_(
                    ComplianceStatus.job_id == compliance_subquery.c.job_id,
                    ComplianceStatus.check_date == compliance_subquery.c.latest_check,
                ),
            )
            .group_by(ComplianceStatus.overall_status)
            .all()
        )

        summary["compliance"] = {"compliant": 0, "non_compliant": 0, "warning": 0}
        for status, count in latest_compliance:
            summary["compliance"][status] = count

        # Backup executions in last 24 hours
        last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        executions_24h = (
            db.session.query(BackupExecution.execution_result, func.count(BackupExecution.id))
            .filter(BackupExecution.execution_date >= last_24h)
            .group_by(BackupExecution.execution_result)
            .all()
        )

        summary["executions_24h"] = {"success": 0, "failed": 0, "warning": 0, "total": 0}
        for result, count in executions_24h:
            summary["executions_24h"][result] = count
            summary["executions_24h"]["total"] += count

        # Alerts statistics (unacknowledged only)
        alerts_by_severity = (
            db.session.query(Alert.severity, func.count(Alert.id))
            .filter_by(is_acknowledged=False)
            .group_by(Alert.severity)
            .all()
        )

        summary["alerts"] = {"critical": 0, "error": 0, "warning": 0, "info": 0, "total_unacknowledged": 0}
        for severity, count in alerts_by_severity:
            summary["alerts"][severity] = count
            summary["alerts"]["total_unacknowledged"] += count

        # Verification tests
        from app.models import VerificationSchedule

        today = datetime.now(timezone.utc).date()

        pending_tests = VerificationSchedule.query.filter(
            VerificationSchedule.is_active == True, VerificationSchedule.next_test_date <= today + timedelta(days=7)
        ).count()

        overdue_tests = VerificationSchedule.query.filter(
            VerificationSchedule.is_active == True, VerificationSchedule.next_test_date < today
        ).count()

        summary["verification_tests"] = {"pending": pending_tests, "overdue": overdue_tests}

        # Offline media statistics
        media_by_status = (
            db.session.query(OfflineMedia.current_status, func.count(OfflineMedia.id))
            .group_by(OfflineMedia.current_status)
            .all()
        )

        summary["offline_media"] = {"in_use": 0, "stored": 0, "retired": 0, "total": 0}
        for status, count in media_by_status:
            if status in summary["offline_media"]:
                summary["offline_media"][status] = count
            summary["offline_media"]["total"] += count

        return jsonify(summary), 200

    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get dashboard summary", "QUERY_FAILED")


@api_bp.route("/dashboard/recent-executions", methods=["GET"])
@api_token_required
def get_recent_executions():
    """
    Get recent backup executions for dashboard

    Returns:
        200: Recent executions (last 20)
    """
    try:
        executions = BackupExecution.query.order_by(BackupExecution.execution_date.desc()).limit(20).all()

        result = []
        for execution in executions:
            result.append(
                {
                    "id": execution.id,
                    "job_id": execution.job_id,
                    "job_name": execution.job.job_name if execution.job else None,
                    "execution_date": execution.execution_date.isoformat() + "Z",
                    "execution_result": execution.execution_result,
                    "backup_size_bytes": execution.backup_size_bytes,
                    "duration_seconds": execution.duration_seconds,
                    "error_message": execution.error_message,
                }
            )

        return jsonify({"executions": result}), 200

    except Exception as e:
        logger.error(f"Error getting recent executions: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get recent executions", "QUERY_FAILED")


@api_bp.route("/dashboard/recent-alerts", methods=["GET"])
@api_token_required
def get_recent_alerts():
    """
    Get recent unacknowledged alerts for dashboard

    Returns:
        200: Recent alerts (last 20 unacknowledged)
    """
    try:
        alerts = Alert.query.filter_by(is_acknowledged=False).order_by(Alert.created_at.desc()).limit(20).all()

        result = []
        for alert in alerts:
            result.append(
                {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "job_id": alert.job_id,
                    "job_name": alert.job.job_name if alert.job else None,
                    "title": alert.title,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat() + "Z",
                }
            )

        return jsonify({"alerts": result}), 200

    except Exception as e:
        logger.error(f"Error getting recent alerts: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get recent alerts", "QUERY_FAILED")


@api_bp.route("/dashboard/compliance-trend", methods=["GET"])
@api_token_required
def get_compliance_trend():
    """
    Get compliance status trend for the last 30 days

    Returns:
        200: Compliance trend data
        {
            "dates": ["2025-10-01", "2025-10-02", ...],
            "compliant": [45, 46, 45, ...],
            "non_compliant": [3, 2, 3, ...],
            "warning": [2, 2, 2, ...]
        }
    """
    try:
        # Get data for last 30 days
        last_30_days = datetime.now(timezone.utc) - timedelta(days=30)

        # Get daily compliance snapshots
        daily_compliance = (
            db.session.query(
                func.date(ComplianceStatus.check_date).label("date"),
                ComplianceStatus.overall_status,
                func.count(func.distinct(ComplianceStatus.job_id)).label("count"),
            )
            .filter(ComplianceStatus.check_date >= last_30_days)
            .group_by(func.date(ComplianceStatus.check_date), ComplianceStatus.overall_status)
            .order_by("date")
            .all()
        )

        # Organize data by date
        trend_data = {}
        for date_val, status, count in daily_compliance:
            date_str = date_val.isoformat()
            if date_str not in trend_data:
                trend_data[date_str] = {"compliant": 0, "non_compliant": 0, "warning": 0}
            trend_data[date_str][status] = count

        # Format response
        dates = sorted(trend_data.keys())
        result = {
            "dates": dates,
            "compliant": [trend_data[d]["compliant"] for d in dates],
            "non_compliant": [trend_data[d]["non_compliant"] for d in dates],
            "warning": [trend_data[d]["warning"] for d in dates],
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting compliance trend: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get compliance trend", "QUERY_FAILED")


@api_bp.route("/dashboard/execution-statistics", methods=["GET"])
@api_token_required
def get_execution_statistics():
    """
    Get backup execution statistics for the last 7 days

    Returns:
        200: Execution statistics
        {
            "dates": ["2025-10-24", "2025-10-25", ...],
            "success": [45, 48, 47, ...],
            "failed": [2, 1, 1, ...],
            "warning": [1, 2, 1, ...]
        }
    """
    try:
        # Get data for last 7 days
        last_7_days = datetime.now(timezone.utc) - timedelta(days=7)

        # Get daily execution statistics
        daily_stats = (
            db.session.query(
                func.date(BackupExecution.execution_date).label("date"),
                BackupExecution.execution_result,
                func.count(BackupExecution.id).label("count"),
            )
            .filter(BackupExecution.execution_date >= last_7_days)
            .group_by(func.date(BackupExecution.execution_date), BackupExecution.execution_result)
            .order_by("date")
            .all()
        )

        # Organize data by date
        stats_data = {}
        for date_val, result, count in daily_stats:
            date_str = date_val.isoformat()
            if date_str not in stats_data:
                stats_data[date_str] = {"success": 0, "failed": 0, "warning": 0}
            stats_data[date_str][result] = count

        # Format response
        dates = sorted(stats_data.keys())
        result = {
            "dates": dates,
            "success": [stats_data[d]["success"] for d in dates],
            "failed": [stats_data[d]["failed"] for d in dates],
            "warning": [stats_data[d]["warning"] for d in dates],
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting execution statistics: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get execution statistics", "QUERY_FAILED")


@api_bp.route("/dashboard/storage-usage", methods=["GET"])
@api_token_required
def get_storage_usage():
    """
    Get storage usage statistics by media type

    Returns:
        200: Storage usage data
    """
    try:
        # Get total size by media type from latest backups
        storage_stats = (
            db.session.query(
                BackupCopy.media_type,
                func.sum(BackupCopy.last_backup_size).label("total_size"),
                func.count(BackupCopy.id).label("copy_count"),
            )
            .filter(BackupCopy.last_backup_size.isnot(None))
            .group_by(BackupCopy.media_type)
            .all()
        )

        result = []
        total_size = 0

        for media_type, size, count in storage_stats:
            total_size += size or 0
            result.append({"media_type": media_type, "total_size_bytes": int(size) if size else 0, "copy_count": count})

        return jsonify({"storage_by_media": result, "total_size_bytes": int(total_size)}), 200

    except Exception as e:
        logger.error(f"Error getting storage usage: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get storage usage", "QUERY_FAILED")
