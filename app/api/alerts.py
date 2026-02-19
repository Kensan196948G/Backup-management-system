"""
Alerts Management API
Retrieve and acknowledge alerts
"""

import logging
from datetime import datetime

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api.errors import error_response, validation_error_response
from app.auth.decorators import api_token_required
from app.models import Alert, db

logger = logging.getLogger(__name__)


@api_bp.route("/alerts", methods=["GET"])
@api_token_required
def list_alerts():
    """
    List alerts with pagination and filtering

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        alert_type: Filter by alert type
        severity: Filter by severity (info/warning/error/critical)
        is_acknowledged: Filter by acknowledgment status (true/false)
        job_id: Filter by related job ID

    Returns:
        200: List of alerts
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Build query
        query = Alert.query

        # Apply filters
        if "alert_type" in request.args:
            query = query.filter_by(alert_type=request.args["alert_type"])

        if "severity" in request.args:
            query = query.filter_by(severity=request.args["severity"])

        if "is_acknowledged" in request.args:
            is_ack = request.args["is_acknowledged"].lower() == "true"
            query = query.filter_by(is_acknowledged=is_ack)

        if "job_id" in request.args:
            query = query.filter_by(job_id=request.args["job_id"])

        # Execute paginated query
        pagination = query.order_by(Alert.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        # Format response
        alerts = []
        for alert in pagination.items:
            alerts.append(
                {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "job_id": alert.job_id,
                    "job_name": alert.job.job_name if alert.job else None,
                    "title": alert.title,
                    "message": alert.message,
                    "is_acknowledged": alert.is_acknowledged,
                    "acknowledged_by": alert.acknowledged_by,
                    "acknowledged_by_name": alert.acknowledger.full_name if alert.acknowledger else None,
                    "acknowledged_at": alert.acknowledged_at.isoformat() + "Z" if alert.acknowledged_at else None,
                    "created_at": alert.created_at.isoformat() + "Z",
                }
            )

        return (
            jsonify(
                {
                    "alerts": alerts,
                    "pagination": {
                        "page": pagination.page,
                        "per_page": pagination.per_page,
                        "total": pagination.total,
                        "pages": pagination.pages,
                        "has_next": pagination.has_next,
                        "has_prev": pagination.has_prev,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error listing alerts: {str(e)}", exc_info=True)
        return error_response(500, "Failed to list alerts", "QUERY_FAILED")


@api_bp.route("/alerts/<int:alert_id>", methods=["GET"])
@api_token_required
def get_alert(alert_id):
    """
    Get detailed information about an alert

    Args:
        alert_id: Alert ID

    Returns:
        200: Alert details
        404: Alert not found
    """
    try:
        alert = Alert.query.get(alert_id)
        if not alert:
            return error_response(404, "Alert not found", "ALERT_NOT_FOUND")

        return (
            jsonify(
                {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "job_id": alert.job_id,
                    "job": (
                        {
                            "id": alert.job.id,
                            "job_name": alert.job.job_name,
                            "job_type": alert.job.job_type,
                            "target_server": alert.job.target_server,
                        }
                        if alert.job
                        else None
                    ),
                    "title": alert.title,
                    "message": alert.message,
                    "is_acknowledged": alert.is_acknowledged,
                    "acknowledged_by": alert.acknowledged_by,
                    "acknowledger": (
                        {
                            "id": alert.acknowledger.id,
                            "username": alert.acknowledger.username,
                            "full_name": alert.acknowledger.full_name,
                        }
                        if alert.acknowledger
                        else None
                    ),
                    "acknowledged_at": alert.acknowledged_at.isoformat() + "Z" if alert.acknowledged_at else None,
                    "created_at": alert.created_at.isoformat() + "Z",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting alert: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get alert details", "QUERY_FAILED")


@api_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@api_token_required
def acknowledge_alert(alert_id):
    """
    Acknowledge an alert

    Args:
        alert_id: Alert ID

    Request Body (optional):
    {
        "note": "Issue resolved"
    }

    Returns:
        200: Alert acknowledged successfully
        404: Alert not found
        409: Alert already acknowledged
    """
    try:
        alert = Alert.query.get(alert_id)
        if not alert:
            return error_response(404, "Alert not found", "ALERT_NOT_FOUND")

        if alert.is_acknowledged:
            return error_response(409, "Alert already acknowledged", "ALREADY_ACKNOWLEDGED")

        # Get authenticated user ID
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id

        # Mark as acknowledged
        alert.is_acknowledged = True
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()

        db.session.commit()

        logger.info(f"Alert acknowledged: alert_id={alert_id}, user_id={user_id}")

        return (
            jsonify(
                {
                    "message": "Alert acknowledged successfully",
                    "alert_id": alert.id,
                    "acknowledged_at": alert.acknowledged_at.isoformat() + "Z",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to acknowledge alert", "UPDATE_FAILED")


@api_bp.route("/alerts/<int:alert_id>/unacknowledge", methods=["POST"])
@api_token_required
def unacknowledge_alert(alert_id):
    """
    Unacknowledge an alert (reopen)

    Args:
        alert_id: Alert ID

    Returns:
        200: Alert unacknowledged successfully
        404: Alert not found
    """
    try:
        alert = Alert.query.get(alert_id)
        if not alert:
            return error_response(404, "Alert not found", "ALERT_NOT_FOUND")

        # Mark as unacknowledged
        alert.is_acknowledged = False
        alert.acknowledged_by = None
        alert.acknowledged_at = None

        db.session.commit()

        logger.info(f"Alert unacknowledged: alert_id={alert_id}")

        return jsonify({"message": "Alert unacknowledged successfully", "alert_id": alert.id}), 200

    except Exception as e:
        logger.error(f"Error unacknowledging alert: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to unacknowledge alert", "UPDATE_FAILED")


@api_bp.route("/alerts/summary", methods=["GET"])
@api_token_required
def get_alerts_summary():
    """
    Get summary of alerts by severity and acknowledgment status

    Returns:
        200: Alerts summary
    """
    try:
        # Count by severity
        severity_counts = {
            "critical": Alert.query.filter_by(severity="critical", is_acknowledged=False).count(),
            "error": Alert.query.filter_by(severity="error", is_acknowledged=False).count(),
            "warning": Alert.query.filter_by(severity="warning", is_acknowledged=False).count(),
            "info": Alert.query.filter_by(severity="info", is_acknowledged=False).count(),
        }

        # Count by type (unacknowledged only)
        type_counts = {}
        alert_types = (
            db.session.query(Alert.alert_type, db.func.count(Alert.id))
            .filter_by(is_acknowledged=False)
            .group_by(Alert.alert_type)
            .all()
        )

        for alert_type, count in alert_types:
            type_counts[alert_type] = count

        # Total counts
        total_unacknowledged = sum(severity_counts.values())
        total_acknowledged = Alert.query.filter_by(is_acknowledged=True).count()

        return (
            jsonify(
                {
                    "unacknowledged": {"total": total_unacknowledged, "by_severity": severity_counts, "by_type": type_counts},
                    "acknowledged": {"total": total_acknowledged},
                    "grand_total": total_unacknowledged + total_acknowledged,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting alerts summary: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get alerts summary", "QUERY_FAILED")


@api_bp.route("/alerts/bulk-acknowledge", methods=["POST"])
@api_token_required
def bulk_acknowledge_alerts():
    """
    Acknowledge multiple alerts at once

    Request Body:
    {
        "alert_ids": [1, 2, 3, 4]
    }

    Returns:
        200: Alerts acknowledged successfully
        400: Invalid request data
    """
    try:
        data = request.get_json()

        # Validate request
        if "alert_ids" not in data or not isinstance(data["alert_ids"], list):
            return validation_error_response({"alert_ids": "Must provide a list of alert IDs"})

        if not data["alert_ids"]:
            return validation_error_response({"alert_ids": "List cannot be empty"})

        # Get authenticated user ID
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id

        # Update alerts
        now = datetime.utcnow()
        updated_count = Alert.query.filter(Alert.id.in_(data["alert_ids"]), Alert.is_acknowledged == False).update(
            {Alert.is_acknowledged: True, Alert.acknowledged_by: user_id, Alert.acknowledged_at: now},
            synchronize_session=False,
        )

        db.session.commit()

        logger.info(f"Bulk acknowledge: {updated_count} alerts acknowledged by user_id={user_id}")

        return (
            jsonify(
                {
                    "message": f"{updated_count} alert(s) acknowledged successfully",
                    "acknowledged_count": updated_count,
                    "acknowledged_at": now.isoformat() + "Z",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error in bulk acknowledge: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to acknowledge alerts", "UPDATE_FAILED")
