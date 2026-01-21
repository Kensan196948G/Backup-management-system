"""
Backup Status Update API
Endpoint for PowerShell scripts to update backup status
"""

import logging
from datetime import datetime

from flask import jsonify, request

from app.api import api_bp
from app.api.errors import error_response, validation_error_response
from app.auth.decorators import api_token_required
from app.models import BackupCopy, BackupExecution, BackupJob, db
from app.services.alert_manager import AlertManager
from app.services.compliance_checker import ComplianceChecker

logger = logging.getLogger(__name__)


@api_bp.route("/backup/status", methods=["POST"])
@api_token_required
def update_backup_status():
    """
    Update backup execution status from PowerShell scripts

    Request Body:
    {
        "job_id": 1,
        "execution_date": "2025-10-30T03:00:00Z",
        "execution_result": "success",
        "backup_size_bytes": 1073741824,
        "duration_seconds": 300,
        "error_message": null,
        "source_system": "powershell"
    }

    Returns:
        201: Backup status updated successfully
        400: Invalid request data
        404: Backup job not found
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["job_id", "execution_result"]
        errors = {}

        for field in required_fields:
            if field not in data:
                errors[field] = f"{field} is required"

        if errors:
            return validation_error_response(errors)

        # Validate job exists
        job = BackupJob.query.get(data["job_id"])
        if not job:
            return error_response(404, "Backup job not found", "JOB_NOT_FOUND")

        # Validate execution_result
        valid_results = ["success", "failed", "warning"]
        if data["execution_result"] not in valid_results:
            return validation_error_response({"execution_result": f'Must be one of: {", ".join(valid_results)}'})

        # Parse execution date
        execution_date = datetime.utcnow()
        if "execution_date" in data:
            try:
                execution_date = datetime.fromisoformat(data["execution_date"].replace("Z", "+00:00"))
            except ValueError:
                return validation_error_response({"execution_date": "Invalid date format. Use ISO 8601 format"})

        # Create backup execution record
        execution = BackupExecution(
            job_id=data["job_id"],
            execution_date=execution_date,
            execution_result=data["execution_result"],
            error_message=data.get("error_message"),
            backup_size_bytes=data.get("backup_size_bytes"),
            duration_seconds=data.get("duration_seconds"),
            source_system=data.get("source_system", "powershell"),
        )

        db.session.add(execution)
        db.session.commit()

        logger.info(f"Backup execution recorded: job_id={data['job_id']}, result={data['execution_result']}")

        # Generate alerts for failed backups
        if data["execution_result"] in ["failed", "warning"]:
            alert_manager = AlertManager()
            alert_manager.create_backup_failure_alert(
                job_id=data["job_id"], execution_id=execution.id, error_message=data.get("error_message")
            )

        # Check compliance and generate alerts if needed
        compliance_checker = ComplianceChecker()
        compliance_result = compliance_checker.check_3_2_1_1_0(data["job_id"])

        return (
            jsonify(
                {
                    "message": "Backup status updated successfully",
                    "execution_id": execution.id,
                    "compliance_status": compliance_result.get("status", "unknown"),
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error updating backup status: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to update backup status", "UPDATE_FAILED")


@api_bp.route("/backup/copy-status", methods=["POST"])
@api_token_required
def update_copy_status():
    """
    Update backup copy status

    Request Body:
    {
        "copy_id": 1,
        "status": "success",
        "last_backup_date": "2025-10-30T03:00:00Z",
        "last_backup_size": 1073741824
    }

    Returns:
        200: Copy status updated successfully
        400: Invalid request data
        404: Backup copy not found
    """
    try:
        data = request.get_json()

        # Validate required fields
        if "copy_id" not in data:
            return validation_error_response({"copy_id": "copy_id is required"})

        # Find the copy
        copy = BackupCopy.query.get(data["copy_id"])
        if not copy:
            return error_response(404, "Backup copy not found", "COPY_NOT_FOUND")

        # Update fields if provided
        if "status" in data:
            valid_statuses = ["success", "failed", "warning", "unknown"]
            if data["status"] not in valid_statuses:
                return validation_error_response({"status": f'Must be one of: {", ".join(valid_statuses)}'})
            copy.status = data["status"]

        if "last_backup_date" in data:
            try:
                copy.last_backup_date = datetime.fromisoformat(data["last_backup_date"].replace("Z", "+00:00"))
            except ValueError:
                return validation_error_response({"last_backup_date": "Invalid date format. Use ISO 8601 format"})

        if "last_backup_size" in data:
            if not isinstance(data["last_backup_size"], (int, float)) or data["last_backup_size"] < 0:
                return validation_error_response({"last_backup_size": "Must be a non-negative number"})
            copy.last_backup_size = int(data["last_backup_size"])

        copy.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Backup copy status updated: copy_id={data['copy_id']}")

        return jsonify({"message": "Copy status updated successfully", "copy_id": copy.id, "status": copy.status}), 200

    except Exception as e:
        logger.error(f"Error updating copy status: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to update copy status", "UPDATE_FAILED")


@api_bp.route("/backup/jobs/<int:job_id>/last-execution", methods=["GET"])
@api_token_required
def get_last_execution(job_id):
    """
    Get last execution information for a backup job

    Args:
        job_id: Backup job ID

    Returns:
        200: Last execution information
        404: Backup job not found or no executions
    """
    try:
        # Validate job exists
        job = BackupJob.query.get(job_id)
        if not job:
            return error_response(404, "Backup job not found", "JOB_NOT_FOUND")

        # Get last execution
        last_execution = BackupExecution.query.filter_by(job_id=job_id).order_by(BackupExecution.execution_date.desc()).first()

        if not last_execution:
            return error_response(404, "No executions found for this job", "NO_EXECUTIONS")

        return (
            jsonify(
                {
                    "execution_id": last_execution.id,
                    "job_id": last_execution.job_id,
                    "execution_date": last_execution.execution_date.isoformat() + "Z",
                    "execution_result": last_execution.execution_result,
                    "backup_size_bytes": last_execution.backup_size_bytes,
                    "duration_seconds": last_execution.duration_seconds,
                    "error_message": last_execution.error_message,
                    "source_system": last_execution.source_system,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting last execution: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get last execution", "QUERY_FAILED")
