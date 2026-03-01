"""
AOMEI Backupper Integration REST API (v1)
Provides endpoints for AOMEI Backupper PowerShell script integration

Endpoints:
- POST   /api/v1/aomei/register      - Register AOMEI backup job
- POST   /api/v1/aomei/status        - Receive status update from PowerShell
- POST   /api/v1/aomei/log-analysis  - Process log analysis results
- GET    /api/v1/aomei/jobs          - List all AOMEI jobs
- GET    /api/v1/aomei/jobs/{id}     - Get AOMEI job status

Authentication:
- All POST endpoints require API key authentication (X-API-Key header)
- GET endpoints require JWT authentication
"""

import logging
from datetime import datetime
from functools import wraps

from flask import jsonify, request
from pydantic import ValidationError

from app.api import api_bp
from app.api.auth import jwt_required
from app.api.errors import error_response, validation_error_response
from app.api.schemas import (
    AOMEIJobRegisterRequest,
    AOMEILogAnalysisRequest,
    AOMEIStatusRequest,
)
from app.services.aomei_service import AOMEIService

logger = logging.getLogger(__name__)


# ============================================================================
# API Key Authentication for AOMEI Integration
# ============================================================================


def aomei_api_key_required(f):
    """
    Decorator to require API key authentication for AOMEI endpoints

    Checks for X-API-Key header and validates against configured key
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            logger.warning("AOMEI API request without API key")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "API_KEY_REQUIRED",
                        "message": "API key is required in X-API-Key header",
                    }
                ),
                401,
            )

        if not AOMEIService.validate_api_key(api_key):
            logger.warning(f"AOMEI API request with invalid API key")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "INVALID_API_KEY",
                        "message": "Invalid API key",
                    }
                ),
                401,
            )

        return f(*args, **kwargs)

    return decorated_function


# ============================================================================
# AOMEI Integration Endpoints
# ============================================================================


@api_bp.route("/v1/aomei/register", methods=["POST"])
@aomei_api_key_required
def aomei_register_job():
    """
    Register or update AOMEI backup job

    Request Body:
    {
        "job_id": 0,
        "task_name": "System Backup Daily",
        "job_type": "system_image",
        "target_server": "SERVER01",
        "target_path": "D:\\Backups\\System",
        "description": "Daily system image backup"
    }

    Response:
    {
        "success": true,
        "message": "Job registered successfully with ID 123",
        "data": {
            "job_id": 123,
            "job_name": "System Backup Daily",
            "backup_tool": "aomei"
        }
    }

    Returns:
        200: Job registered/updated successfully
        400: Invalid request data
        401: Invalid API key
    """
    try:
        data = request.get_json()
        if not data:
            return validation_error_response({"_error": "Request body is required"})

        # Validate request data
        register_data = AOMEIJobRegisterRequest(**data)

        # Register job
        success, message, job = AOMEIService.register_job(
            job_id=register_data.job_id,
            task_name=register_data.task_name,
            job_type=register_data.job_type,
            target_server=register_data.target_server,
            target_path=register_data.target_path,
            description=register_data.description,
        )

        if not success:
            return error_response("JOB_REGISTRATION_FAILED", message), 400

        logger.info(f"AOMEI job registered: {register_data.task_name} (ID: {job.id if job else 'N/A'})")

        return (
            jsonify(
                {
                    "success": True,
                    "message": message,
                    "data": {
                        "job_id": job.id if job else None,
                        "job_name": job.job_name if job else None,
                        "backup_tool": AOMEIService.BACKUP_TOOL,
                    },
                }
            ),
            200,
        )

    except ValidationError as e:
        return validation_error_response(e.errors()), 400
    except Exception as e:
        logger.error(f"AOMEI job registration error: {e}")
        return error_response("INTERNAL_ERROR", str(e)), 500


@api_bp.route("/v1/aomei/status", methods=["POST"])
@aomei_api_key_required
def aomei_receive_status():
    """
    Receive backup status update from AOMEI PowerShell script

    Request Body:
    {
        "job_id": 123,
        "status": "success",
        "backup_size": 10737418240,
        "duration": 3600,
        "error_message": null,
        "task_name": "System Backup Daily",
        "start_time": "2025-11-02T01:00:00",
        "end_time": "2025-11-02T02:00:00",
        "details": "AOMEI Task: System Backup Daily | Log: backup_20251102.log",
        "copy_type": "primary",
        "storage_path": "D:\\Backups\\System\\2025-11-02"
    }

    Response:
    {
        "success": true,
        "message": "Status updated successfully for job 123"
    }

    Returns:
        200: Status updated successfully
        400: Invalid request data or job not found
        401: Invalid API key
    """
    try:
        data = request.get_json()
        if not data:
            return validation_error_response({"_error": "Request body is required"})

        # Validate request data
        status_data = AOMEIStatusRequest(**data)

        # Parse datetime strings if provided
        start_time = None
        end_time = None

        if status_data.start_time:
            try:
                if isinstance(status_data.start_time, str):
                    start_time = datetime.fromisoformat(status_data.start_time.replace("Z", "+00:00"))
                else:
                    start_time = status_data.start_time
            except Exception as e:
                logger.warning(f"Failed to parse start_time: {e}")

        if status_data.end_time:
            try:
                if isinstance(status_data.end_time, str):
                    end_time = datetime.fromisoformat(status_data.end_time.replace("Z", "+00:00"))
                else:
                    end_time = status_data.end_time
            except Exception as e:
                logger.warning(f"Failed to parse end_time: {e}")

        # Update status
        success, message = AOMEIService.receive_status(
            job_id=status_data.job_id,
            status=status_data.status,
            backup_size=status_data.backup_size,
            duration=status_data.duration,
            error_message=status_data.error_message,
            task_name=status_data.task_name,
            start_time=start_time,
            end_time=end_time,
            details=status_data.details,
            copy_type=status_data.copy_type,
            storage_path=status_data.storage_path,
        )

        if not success:
            return error_response("STATUS_UPDATE_FAILED", message), 400

        logger.info(f"AOMEI status updated for job {status_data.job_id}: {status_data.status}")

        return jsonify({"success": True, "message": message}), 200

    except ValidationError as e:
        return validation_error_response(e.errors()), 400
    except Exception as e:
        logger.error(f"AOMEI status update error: {e}")
        return error_response("INTERNAL_ERROR", str(e)), 500


@api_bp.route("/v1/aomei/log-analysis", methods=["POST"])
@aomei_api_key_required
def aomei_log_analysis():
    """
    Process AOMEI log analysis results from PowerShell script

    Request Body:
    {
        "job_id": 123,
        "log_file_path": "C:\\Program Files\\AOMEI\\Backupper\\log\\backup_20251102.log",
        "parsed_data": {
            "task_name": "System Backup Daily",
            "status": "success",
            "start_time": "2025-11-02T01:00:00",
            "end_time": "2025-11-02T02:00:00",
            "duration": 3600,
            "backup_size": 10737418240,
            "error_message": "",
            "details": "Backup completed successfully"
        }
    }

    Response:
    {
        "success": true,
        "message": "Log analysis processed successfully"
    }

    Returns:
        200: Log analysis processed successfully
        400: Invalid request data or processing failed
        401: Invalid API key
    """
    try:
        data = request.get_json()
        if not data:
            return validation_error_response({"_error": "Request body is required"})

        # Validate request data
        log_data = AOMEILogAnalysisRequest(**data)

        # Parse datetime strings in parsed_data
        parsed_data = log_data.parsed_data.copy()

        if "start_time" in parsed_data and isinstance(parsed_data["start_time"], str):
            try:
                parsed_data["start_time"] = datetime.fromisoformat(parsed_data["start_time"].replace("Z", "+00:00"))
            except Exception as e:
                logger.warning(f"Failed to parse start_time in log data: {e}")

        if "end_time" in parsed_data and isinstance(parsed_data["end_time"], str):
            try:
                parsed_data["end_time"] = datetime.fromisoformat(parsed_data["end_time"].replace("Z", "+00:00"))
            except Exception as e:
                logger.warning(f"Failed to parse end_time in log data: {e}")

        # Process log analysis
        success, message = AOMEIService.process_log_analysis(
            job_id=log_data.job_id,
            log_file_path=log_data.log_file_path,
            parsed_data=parsed_data,
        )

        if not success:
            return error_response("LOG_ANALYSIS_FAILED", message), 400

        logger.info(f"AOMEI log analysis processed for job {log_data.job_id}: {log_data.log_file_path}")

        return jsonify({"success": True, "message": message}), 200

    except ValidationError as e:
        return validation_error_response(e.errors()), 400
    except Exception as e:
        logger.error(f"AOMEI log analysis error: {e}")
        return error_response("INTERNAL_ERROR", str(e)), 500


@api_bp.route("/v1/aomei/jobs", methods=["GET"])
@jwt_required
def aomei_list_jobs(current_user):
    """
    List all AOMEI backup jobs

    Query Parameters:
    - active_only: boolean (default: true) - Return only active jobs
    - include_executions: boolean (default: false) - Include execution history

    Response:
    {
        "success": true,
        "data": [
            {
                "id": 123,
                "job_name": "System Backup Daily",
                "job_type": "system_image",
                "is_active": true,
                "created_at": "2025-11-01T00:00:00",
                "updated_at": "2025-11-02T02:00:00"
            }
        ],
        "total": 1
    }

    Returns:
        200: Success
        401: Authentication required
    """
    try:
        active_only = request.args.get("active_only", "true").lower() == "true"
        include_executions = request.args.get("include_executions", "false").lower() == "true"

        jobs = AOMEIService.get_aomei_jobs(
            active_only=active_only,
            include_executions=include_executions,
        )

        jobs_data = [
            {
                "id": job.id,
                "job_name": job.job_name,
                "job_type": job.job_type,
                "target_server": job.target_server,
                "target_path": job.target_path,
                "is_active": job.is_active,
                "schedule_type": job.schedule_type,
                "retention_days": job.retention_days,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
            }
            for job in jobs
        ]

        return (
            jsonify(
                {
                    "success": True,
                    "data": jobs_data,
                    "total": len(jobs_data),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"AOMEI jobs list error: {e}")
        return error_response("INTERNAL_ERROR", str(e)), 500


@api_bp.route("/v1/aomei/jobs/<int:job_id>", methods=["GET"])
@jwt_required
def aomei_get_job_status(current_user, job_id):
    """
    Get AOMEI job status and details

    Response:
    {
        "success": true,
        "data": {
            "job_id": 123,
            "job_name": "System Backup Daily",
            "job_type": "system_image",
            "is_active": true,
            "latest_execution": {
                "date": "2025-11-02T02:00:00",
                "result": "success",
                "size": 10737418240,
                "duration": 3600,
                "error": null
            },
            "copies": [
                {
                    "type": "primary",
                    "media": "disk",
                    "status": "success",
                    "last_backup": "2025-11-02T02:00:00",
                    "size": 10737418240,
                    "path": "D:\\Backups\\System\\2025-11-02"
                }
            ],
            "updated_at": "2025-11-02T02:00:00"
        }
    }

    Returns:
        200: Success
        404: Job not found
        401: Authentication required
    """
    try:
        job_status = AOMEIService.get_job_status(job_id)

        if not job_status:
            return error_response("JOB_NOT_FOUND", f"AOMEI job {job_id} not found"), 404

        # Convert datetime objects to ISO format
        if job_status.get("updated_at"):
            job_status["updated_at"] = job_status["updated_at"].isoformat()

        if job_status.get("latest_execution"):
            if job_status["latest_execution"].get("date"):
                job_status["latest_execution"]["date"] = job_status["latest_execution"]["date"].isoformat()

        if job_status.get("copies"):
            for copy in job_status["copies"]:
                if copy.get("last_backup"):
                    copy["last_backup"] = copy["last_backup"].isoformat()

        return (
            jsonify(
                {
                    "success": True,
                    "data": job_status,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"AOMEI job status error: {e}")
        return error_response("INTERNAL_ERROR", str(e)), 500
