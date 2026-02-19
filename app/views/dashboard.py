"""
Dashboard Views
Main dashboard showing system overview and statistics
"""

from datetime import datetime, timedelta

from flask import current_app, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_

from app.models import (
    Alert,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    OfflineMedia,
    VerificationTest,
    db,
)
from app.services.compliance_checker import ComplianceChecker
from app.views import dashboard_bp


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    """
    Main dashboard page
    Shows 3-2-1-1-0 compliance, backup success rates, storage usage, alerts, and upcoming jobs
    """
    try:
        # Get statistics
        stats = get_dashboard_statistics()

        # Get recent alerts
        recent_alerts = Alert.query.filter_by(is_acknowledged=False).order_by(Alert.created_at.desc()).limit(10).all()

        # Get upcoming jobs (scheduled jobs)
        # Note: BackupJob doesn't have next_run field, sorting by job_name instead
        upcoming_jobs = BackupJob.query.filter_by(is_active=True).order_by(BackupJob.job_name.asc()).limit(5).all()

        # Get recent executions
        recent_executions = BackupExecution.query.order_by(BackupExecution.execution_date.desc()).limit(10).all()

        return render_template(
            "dashboard.html",
            stats=stats,
            recent_alerts=recent_alerts,
            upcoming_jobs=upcoming_jobs,
            recent_executions=recent_executions,
        )

    except Exception as e:
        current_app.logger.error(f"Error loading dashboard: {str(e)}")
        # Return a simple error page without template
        return f"<h1>Error</h1><p>{str(e)}</p>", 500


@dashboard_bp.route("/api/dashboard/stats")
@login_required
def api_dashboard_stats():
    """
    API endpoint for dashboard statistics
    Returns JSON data for dashboard widgets
    """
    try:
        stats = get_dashboard_statistics()
        return jsonify(stats), 200
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@dashboard_bp.route("/api/dashboard/compliance-chart")
@login_required
def api_compliance_chart():
    """
    API endpoint for compliance chart data
    Returns data for pie chart showing 3-2-1-1-0 rule compliance
    """
    try:
        # Get compliance status counts
        compliant = ComplianceStatus.query.filter_by(overall_status="compliant").count()
        non_compliant = ComplianceStatus.query.filter_by(overall_status="non_compliant").count()

        # Get warning count (jobs with some violations but not critical)
        warning = ComplianceStatus.query.filter_by(overall_status="warning").count()

        chart_data = {
            "labels": ["準拠", "非準拠", "警告"],
            "datasets": [
                {
                    "data": [compliant, max(0, non_compliant - warning), warning],
                    "backgroundColor": ["#28a745", "#dc3545", "#ffc107"],
                    "borderWidth": 2,
                }
            ],
        }

        return jsonify(chart_data), 200

    except Exception as e:
        current_app.logger.error(f"Error getting compliance chart data: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@dashboard_bp.route("/api/dashboard/success-rate-chart")
@login_required
def api_success_rate_chart():
    """
    API endpoint for success rate chart data
    Returns data for line chart showing backup success rate over last 7 days
    """
    try:
        # Get last 7 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=6)

        labels = []
        success_data = []
        failure_data = []

        for i in range(7):
            date = start_date + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            labels.append(date.strftime("%m/%d"))

            # Count success and failures for this date
            success_count = BackupExecution.query.filter(
                and_(func.date(BackupExecution.execution_date) == date.date(), BackupExecution.execution_result == "success")
            ).count()

            failure_count = BackupExecution.query.filter(
                and_(
                    func.date(BackupExecution.execution_date) == date.date(),
                    BackupExecution.execution_result.in_(["failed", "error"]),
                )
            ).count()

            success_data.append(success_count)
            failure_data.append(failure_count)

        chart_data = {
            "labels": labels,
            "datasets": [
                {
                    "label": "成功",
                    "data": success_data,
                    "borderColor": "#28a745",
                    "backgroundColor": "rgba(40, 167, 69, 0.1)",
                    "tension": 0.4,
                },
                {
                    "label": "失敗",
                    "data": failure_data,
                    "borderColor": "#dc3545",
                    "backgroundColor": "rgba(220, 53, 69, 0.1)",
                    "tension": 0.4,
                },
            ],
        }

        return jsonify(chart_data), 200

    except Exception as e:
        current_app.logger.error(f"Error getting success rate chart data: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@dashboard_bp.route("/api/dashboard/storage-chart")
@login_required
def api_storage_chart():
    """
    API endpoint for storage usage chart data
    Returns data for bar chart showing storage usage by type
    """
    try:
        # Calculate storage usage by copy type
        # This is a simplified version - you may want to add actual storage calculation
        from sqlalchemy import case

        storage_stats = db.session.query(func.count(BackupJob.id).label("count")).filter(BackupJob.is_active == True).first()

        # For demonstration, using job counts as proxy
        # In production, you would calculate actual storage from BackupCopy table
        onsite = BackupJob.query.filter_by(is_active=True).count() * 70  # Mock data
        offsite = BackupJob.query.filter_by(is_active=True).count() * 60
        offline = OfflineMedia.query.filter_by(current_status="in_use").count() * 50

        chart_data = {
            "labels": ["オンサイト", "オフサイト", "オフライン"],
            "datasets": [
                {
                    "label": "使用率 (%)",
                    "data": [min(onsite, 100), min(offsite, 100), min(offline, 100)],
                    "backgroundColor": ["#17a2b8", "#007bff", "#6c757d"],
                    "borderWidth": 1,
                }
            ],
        }

        return jsonify(chart_data), 200

    except Exception as e:
        current_app.logger.error(f"Error getting storage chart data: {str(e)}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


def get_dashboard_statistics():
    """
    Get dashboard statistics

    Returns:
        dict: Dashboard statistics
    """
    # Total backup jobs
    total_jobs = BackupJob.query.filter_by(is_active=True).count()

    # Compliance statistics
    compliant_jobs = ComplianceStatus.query.filter_by(overall_status="compliant").count()
    compliance_rate = round((compliant_jobs / total_jobs * 100) if total_jobs > 0 else 0, 1)

    # Backup success rate (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    total_executions = BackupExecution.query.filter(BackupExecution.execution_date >= seven_days_ago).count()

    successful_executions = BackupExecution.query.filter(
        and_(BackupExecution.execution_date >= seven_days_ago, BackupExecution.execution_result == "success")
    ).count()

    success_rate = round((successful_executions / total_executions * 100) if total_executions > 0 else 0, 1)

    # Alert counts
    critical_alerts = Alert.query.filter_by(severity="critical", is_acknowledged=False).count()

    warning_alerts = Alert.query.filter_by(severity="warning", is_acknowledged=False).count()

    info_alerts = Alert.query.filter_by(severity="info", is_acknowledged=False).count()

    total_alerts = critical_alerts + warning_alerts + info_alerts

    # Offline media statistics
    total_media = OfflineMedia.query.count()
    in_use_media = OfflineMedia.query.filter_by(current_status="in_use").count()
    available_media = OfflineMedia.query.filter_by(current_status="available").count()

    # Recent verification tests
    verification_passed = VerificationTest.query.filter_by(test_result="success").count()

    verification_failed = VerificationTest.query.filter_by(test_result="failed").count()

    return {
        "total_jobs": total_jobs,
        "compliant_jobs": compliant_jobs,
        "compliance_rate": compliance_rate,
        "success_rate": success_rate,
        "total_executions": total_executions,
        "successful_executions": successful_executions,
        "critical_alerts": critical_alerts,
        "warning_alerts": warning_alerts,
        "info_alerts": info_alerts,
        "total_alerts": total_alerts,
        "total_media": total_media,
        "in_use_media": in_use_media,
        "available_media": available_media,
        "verification_passed": verification_passed,
        "verification_failed": verification_failed,
    }
