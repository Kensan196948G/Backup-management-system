"""
Backup Jobs Management API
CRUD operations for backup jobs
"""

import logging
from datetime import datetime

from flask import jsonify, request
from sqlalchemy import or_

from app.api import api_bp
from app.api.errors import error_response, validation_error_response
from app.auth.decorators import api_token_required, role_required
from app.models import BackupCopy, BackupJob, User, db

logger = logging.getLogger(__name__)


def validate_job_data(data, is_update=False):
    """
    Validate backup job data

    Args:
        data: Request data dictionary
        is_update: True if validating for update (required fields optional)

    Returns:
        Dictionary of validation errors (empty if valid)
    """
    errors = {}

    # Required fields for creation
    if not is_update:
        required_fields = ["job_name", "job_type", "backup_tool", "schedule_type", "retention_days"]
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = f"{field} is required"

    # Validate job_type
    if "job_type" in data:
        valid_types = ["system_image", "file", "database", "vm"]
        if data["job_type"] not in valid_types:
            errors["job_type"] = f'Must be one of: {", ".join(valid_types)}'

    # Validate backup_tool
    if "backup_tool" in data:
        valid_tools = ["veeam", "wsb", "aomei", "custom"]
        if data["backup_tool"] not in valid_tools:
            errors["backup_tool"] = f'Must be one of: {", ".join(valid_tools)}'

    # Validate schedule_type
    if "schedule_type" in data:
        valid_schedules = ["daily", "weekly", "monthly", "manual"]
        if data["schedule_type"] not in valid_schedules:
            errors["schedule_type"] = f'Must be one of: {", ".join(valid_schedules)}'

    # Validate retention_days
    if "retention_days" in data:
        try:
            retention = int(data["retention_days"])
            if retention < 1:
                errors["retention_days"] = "Must be at least 1 day"
        except (ValueError, TypeError):
            errors["retention_days"] = "Must be a valid integer"

    # Validate owner_id if provided
    if "owner_id" in data:
        owner = User.query.get(data["owner_id"])
        if not owner:
            errors["owner_id"] = "Owner user not found"

    return errors


@api_bp.route("/jobs", methods=["GET"])
@api_token_required
def list_jobs():
    """
    List backup jobs with pagination and filtering

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        search: Search term for job_name, target_server, target_path
        job_type: Filter by job type
        backup_tool: Filter by backup tool
        status: Filter by active status (active/inactive)
        owner_id: Filter by owner user ID

    Returns:
        200: List of backup jobs
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Build query
        query = BackupJob.query

        # Apply filters
        if "search" in request.args:
            search_term = f"%{request.args['search']}%"
            query = query.filter(
                or_(
                    BackupJob.job_name.ilike(search_term),
                    BackupJob.target_server.ilike(search_term),
                    BackupJob.target_path.ilike(search_term),
                )
            )

        if "job_type" in request.args:
            query = query.filter_by(job_type=request.args["job_type"])

        if "backup_tool" in request.args:
            query = query.filter_by(backup_tool=request.args["backup_tool"])

        if "status" in request.args:
            is_active = request.args["status"] == "active"
            query = query.filter_by(is_active=is_active)

        if "owner_id" in request.args:
            query = query.filter_by(owner_id=request.args["owner_id"])

        # Execute paginated query
        pagination = query.order_by(BackupJob.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        # Format response
        jobs = []
        for job in pagination.items:
            # Get latest execution
            last_execution = job.executions.order_by(db.desc("execution_date")).first() if job.executions.count() > 0 else None

            # Get compliance status
            compliance = (
                job.compliance_statuses.order_by(db.desc("check_date")).first()
                if job.compliance_statuses.count() > 0
                else None
            )

            jobs.append(
                {
                    "id": job.id,
                    "job_name": job.job_name,
                    "job_type": job.job_type,
                    "target_server": job.target_server,
                    "target_path": job.target_path,
                    "backup_tool": job.backup_tool,
                    "schedule_type": job.schedule_type,
                    "retention_days": job.retention_days,
                    "owner_id": job.owner_id,
                    "owner_name": job.owner.full_name if job.owner else None,
                    "description": job.description,
                    "is_active": job.is_active,
                    "copies_count": job.copies.count(),
                    "last_execution": (
                        {
                            "date": last_execution.execution_date.isoformat() + "Z",
                            "result": last_execution.execution_result,
                        }
                        if last_execution
                        else None
                    ),
                    "compliance_status": compliance.overall_status if compliance else "unknown",
                    "created_at": job.created_at.isoformat() + "Z",
                    "updated_at": job.updated_at.isoformat() + "Z",
                }
            )

        return (
            jsonify(
                {
                    "jobs": jobs,
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
        logger.error(f"Error listing jobs: {str(e)}", exc_info=True)
        return error_response(500, "Failed to list jobs", "QUERY_FAILED")


@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
@api_token_required
def get_job(job_id):
    """
    Get detailed information about a backup job

    Args:
        job_id: Backup job ID

    Returns:
        200: Job details
        404: Job not found
    """
    try:
        job = BackupJob.query.get(job_id)
        if not job:
            return error_response(404, "Backup job not found", "JOB_NOT_FOUND")

        # Get copies
        copies = []
        for copy in job.copies:
            copies.append(
                {
                    "id": copy.id,
                    "copy_type": copy.copy_type,
                    "media_type": copy.media_type,
                    "storage_path": copy.storage_path,
                    "is_encrypted": copy.is_encrypted,
                    "is_compressed": copy.is_compressed,
                    "last_backup_date": copy.last_backup_date.isoformat() + "Z" if copy.last_backup_date else None,
                    "last_backup_size": copy.last_backup_size,
                    "status": copy.status,
                    "offline_media_id": copy.offline_media_id,
                    "created_at": copy.created_at.isoformat() + "Z",
                }
            )

        # Get recent executions
        recent_executions = []
        for execution in job.executions.order_by(db.desc("execution_date")).limit(10):
            recent_executions.append(
                {
                    "id": execution.id,
                    "execution_date": execution.execution_date.isoformat() + "Z",
                    "execution_result": execution.execution_result,
                    "backup_size_bytes": execution.backup_size_bytes,
                    "duration_seconds": execution.duration_seconds,
                    "error_message": execution.error_message,
                }
            )

        # Get compliance status
        compliance = job.compliance_statuses.order_by(db.desc("check_date")).first()

        return (
            jsonify(
                {
                    "id": job.id,
                    "job_name": job.job_name,
                    "job_type": job.job_type,
                    "target_server": job.target_server,
                    "target_path": job.target_path,
                    "backup_tool": job.backup_tool,
                    "schedule_type": job.schedule_type,
                    "retention_days": job.retention_days,
                    "owner_id": job.owner_id,
                    "owner": (
                        {
                            "id": job.owner.id,
                            "username": job.owner.username,
                            "full_name": job.owner.full_name,
                            "email": job.owner.email,
                        }
                        if job.owner
                        else None
                    ),
                    "description": job.description,
                    "is_active": job.is_active,
                    "copies": copies,
                    "recent_executions": recent_executions,
                    "compliance_status": (
                        {
                            "status": compliance.overall_status,
                            "check_date": compliance.check_date.isoformat() + "Z",
                            "copies_count": compliance.copies_count,
                            "media_types_count": compliance.media_types_count,
                            "has_offsite": compliance.has_offsite,
                            "has_offline": compliance.has_offline,
                            "has_errors": compliance.has_errors,
                        }
                        if compliance
                        else None
                    ),
                    "created_at": job.created_at.isoformat() + "Z",
                    "updated_at": job.updated_at.isoformat() + "Z",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting job: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get job details", "QUERY_FAILED")


@api_bp.route("/jobs", methods=["POST"])
@api_token_required
@role_required("admin", "operator")
def create_job():
    """
    Create a new backup job

    Request Body:
    {
        "job_name": "Daily DB Backup",
        "job_type": "database",
        "target_server": "DB-SERVER-01",
        "target_path": "C:\\Databases",
        "backup_tool": "veeam",
        "schedule_type": "daily",
        "retention_days": 30,
        "owner_id": 1,
        "description": "Daily backup of production database"
    }

    Returns:
        201: Job created successfully
        400: Invalid request data
    """
    try:
        data = request.get_json()

        # Validate data
        errors = validate_job_data(data)
        if errors:
            return validation_error_response(errors)

        # Create job
        job = BackupJob(
            job_name=data["job_name"],
            job_type=data["job_type"],
            target_server=data.get("target_server"),
            target_path=data.get("target_path"),
            backup_tool=data["backup_tool"],
            schedule_type=data["schedule_type"],
            retention_days=data["retention_days"],
            owner_id=data.get("owner_id"),
            description=data.get("description"),
            is_active=data.get("is_active", True),
        )

        db.session.add(job)
        db.session.commit()

        logger.info(f"Backup job created: {job.job_name} (ID: {job.id})")

        return jsonify({"message": "Backup job created successfully", "job_id": job.id, "job_name": job.job_name}), 201

    except Exception as e:
        logger.error(f"Error creating job: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to create backup job", "CREATE_FAILED")


@api_bp.route("/jobs/<int:job_id>", methods=["PUT"])
@api_token_required
@role_required("admin", "operator")
def update_job(job_id):
    """
    Update an existing backup job

    Args:
        job_id: Backup job ID

    Request Body: Same as create_job (all fields optional)

    Returns:
        200: Job updated successfully
        400: Invalid request data
        404: Job not found
    """
    try:
        job = BackupJob.query.get(job_id)
        if not job:
            return error_response(404, "Backup job not found", "JOB_NOT_FOUND")

        data = request.get_json()

        # Validate data
        errors = validate_job_data(data, is_update=True)
        if errors:
            return validation_error_response(errors)

        # Update fields
        if "job_name" in data:
            job.job_name = data["job_name"]
        if "job_type" in data:
            job.job_type = data["job_type"]
        if "target_server" in data:
            job.target_server = data["target_server"]
        if "target_path" in data:
            job.target_path = data["target_path"]
        if "backup_tool" in data:
            job.backup_tool = data["backup_tool"]
        if "schedule_type" in data:
            job.schedule_type = data["schedule_type"]
        if "retention_days" in data:
            job.retention_days = int(data["retention_days"])
        if "owner_id" in data:
            job.owner_id = data["owner_id"]
        if "description" in data:
            job.description = data["description"]
        if "is_active" in data:
            job.is_active = bool(data["is_active"])

        job.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Backup job updated: {job.job_name} (ID: {job.id})")

        return jsonify({"message": "Backup job updated successfully", "job_id": job.id, "job_name": job.job_name}), 200

    except Exception as e:
        logger.error(f"Error updating job: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to update backup job", "UPDATE_FAILED")


@api_bp.route("/jobs/<int:job_id>", methods=["DELETE"])
@api_token_required
@role_required("admin")
def delete_job(job_id):
    """
    Delete a backup job (admin only)

    Args:
        job_id: Backup job ID

    Returns:
        200: Job deleted successfully
        404: Job not found
    """
    try:
        job = BackupJob.query.get(job_id)
        if not job:
            return error_response(404, "Backup job not found", "JOB_NOT_FOUND")

        job_name = job.job_name

        # Delete job (cascades to related records)
        db.session.delete(job)
        db.session.commit()

        logger.info(f"Backup job deleted: {job_name} (ID: {job_id})")

        return jsonify({"message": "Backup job deleted successfully", "job_id": job_id, "job_name": job_name}), 200

    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to delete backup job", "DELETE_FAILED")


@api_bp.route("/jobs/<int:job_id>/copies", methods=["POST"])
@api_token_required
@role_required("admin", "operator")
def add_copy(job_id):
    """
    Add a backup copy to a job

    Args:
        job_id: Backup job ID

    Request Body:
    {
        "copy_type": "secondary",
        "media_type": "disk",
        "storage_path": "\\\\NAS02\\Backup",
        "is_encrypted": true,
        "is_compressed": true,
        "offline_media_id": null
    }

    Returns:
        201: Copy added successfully
        400: Invalid request data
        404: Job not found
    """
    try:
        job = BackupJob.query.get(job_id)
        if not job:
            return error_response(404, "Backup job not found", "JOB_NOT_FOUND")

        data = request.get_json()

        # Validate required fields
        errors = {}
        required_fields = ["copy_type", "media_type"]
        for field in required_fields:
            if field not in data:
                errors[field] = f"{field} is required"

        # Validate copy_type
        if "copy_type" in data:
            valid_types = ["primary", "secondary", "offsite", "offline"]
            if data["copy_type"] not in valid_types:
                errors["copy_type"] = f'Must be one of: {", ".join(valid_types)}'

        # Validate media_type
        if "media_type" in data:
            valid_media = ["disk", "tape", "cloud", "external_hdd"]
            if data["media_type"] not in valid_media:
                errors["media_type"] = f'Must be one of: {", ".join(valid_media)}'

        if errors:
            return validation_error_response(errors)

        # Create copy
        copy = BackupCopy(
            job_id=job_id,
            copy_type=data["copy_type"],
            media_type=data["media_type"],
            storage_path=data.get("storage_path"),
            is_encrypted=data.get("is_encrypted", False),
            is_compressed=data.get("is_compressed", False),
            offline_media_id=data.get("offline_media_id"),
            status="unknown",
        )

        db.session.add(copy)
        db.session.commit()

        logger.info(f"Backup copy added: job_id={job_id}, copy_type={data['copy_type']}")

        return jsonify({"message": "Backup copy added successfully", "copy_id": copy.id, "job_id": job_id}), 201

    except Exception as e:
        logger.error(f"Error adding copy: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to add backup copy", "CREATE_FAILED")
