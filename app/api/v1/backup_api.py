"""
Backup Operations REST API (v1)
Provides RESTful endpoints for backup job management

Endpoints:
- POST   /api/v1/backups          - Create new backup job
- GET    /api/v1/backups          - List all backup jobs (paginated)
- GET    /api/v1/backups/{id}     - Get backup job details
- PUT    /api/v1/backups/{id}     - Update backup job
- DELETE /api/v1/backups/{id}     - Delete backup job
- POST   /api/v1/backups/{id}/run - Trigger manual backup
- GET    /api/v1/backups/{id}/executions - Get execution history
"""

import logging
from datetime import datetime, timezone

from flask import jsonify, request
from pydantic import ValidationError
from sqlalchemy import desc

from app.api import api_bp
from app.api.auth import jwt_required, role_required
from app.api.errors import error_response, validation_error_response
from app.api.schemas import (
    APIResponse,
    BackupExecutionResponse,
    BackupJobCreate,
    BackupJobResponse,
    BackupJobUpdate,
    BackupTrigger,
    PaginatedResponse,
)
from app.models import BackupExecution, BackupJob, db
from app.services.backup_service import BackupService

logger = logging.getLogger(__name__)


# ============================================================================
# Backup Job CRUD Operations
# ============================================================================


@api_bp.route("/v1/backups", methods=["POST"])
@jwt_required
@role_required("admin", "operator")
def create_backup_job(current_user):
    """
    Create new backup job

    Request Body:
    {
        "name": "Daily Database Backup",
        "description": "PostgreSQL database backup",
        "source_path": "/var/lib/postgresql/data",
        "backup_type": "full",
        "schedule_type": "daily",
        "schedule_time": "03:00",
        "retention_days": 30,
        "is_active": true,
        "priority": 5,
        "notification_email": "admin@example.com",
        "tags": "database,critical"
    }

    Returns:
        201: Backup job created successfully
        400: Invalid request data
        401: Authentication required
        403: Insufficient permissions
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return validation_error_response({"_error": "Request body is required"})

        backup_data = BackupJobCreate(**data)

        # Create backup job
        backup_job = BackupJob(
            name=backup_data.name,
            description=backup_data.description,
            source_path=backup_data.source_path,
            backup_type=backup_data.backup_type,
            schedule_type=backup_data.schedule_type,
            schedule_time=backup_data.schedule_time,
            schedule_days=backup_data.schedule_days,
            retention_days=backup_data.retention_days,
            is_active=backup_data.is_active,
            priority=backup_data.priority,
            notification_email=backup_data.notification_email,
            tags=backup_data.tags,
            owner_id=current_user.id,
        )

        db.session.add(backup_job)
        db.session.commit()

        logger.info(f"Backup job created: {backup_job.name} (ID: {backup_job.id}) by {current_user.username}")

        # Return created job
        response = BackupJobResponse.model_validate(backup_job)
        return (
            jsonify(
                APIResponse(success=True, message="Backup job created successfully", data=response.model_dump()).model_dump()
            ),
            201,
        )

    except ValidationError as e:
        logger.warning(f"Validation error in create_backup_job: {e}")
        return validation_error_response(e.errors())
    except Exception as e:
        logger.error(f"Error creating backup job: {e}", exc_info=True)
        return error_response(500, "Failed to create backup job", "INTERNAL_ERROR")


@api_bp.route("/v1/backups", methods=["GET"])
@jwt_required
def list_backup_jobs(current_user):
    """
    List all backup jobs with pagination and filtering

    Query Parameters:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 20, max: 100)
        is_active (bool): Filter by active status
        backup_type (str): Filter by backup type
        owner_id (int): Filter by owner (admin only)
        search (str): Search in name and description

    Returns:
        200: List of backup jobs
        401: Authentication required
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        page_size = min(request.args.get("page_size", 20, type=int), 100)

        # Build query
        query = BackupJob.query

        # Apply filters
        if not current_user.is_admin():
            # Non-admin users can only see their own jobs
            query = query.filter_by(owner_id=current_user.id)
        elif request.args.get("owner_id"):
            query = query.filter_by(owner_id=request.args.get("owner_id", type=int))

        if request.args.get("is_active") is not None:
            is_active = request.args.get("is_active", "true").lower() == "true"
            query = query.filter_by(is_active=is_active)

        if request.args.get("backup_type"):
            query = query.filter_by(backup_type=request.args.get("backup_type"))

        if request.args.get("search"):
            search_term = f"%{request.args.get('search')}%"
            query = query.filter(db.or_(BackupJob.name.ilike(search_term), BackupJob.description.ilike(search_term)))

        # Order by priority (descending) and name
        query = query.order_by(desc(BackupJob.priority), BackupJob.name)

        # Paginate
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        # Convert to response models
        jobs = [BackupJobResponse.model_validate(job).model_dump() for job in pagination.items]

        response = PaginatedResponse(
            success=True, data=jobs, total=pagination.total, page=page, page_size=page_size, total_pages=pagination.pages
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error listing backup jobs: {e}", exc_info=True)
        return error_response(500, "Failed to list backup jobs", "INTERNAL_ERROR")


@api_bp.route("/v1/backups/<int:backup_id>", methods=["GET"])
@jwt_required
def get_backup_job(current_user, backup_id):
    """
    Get backup job details by ID

    Path Parameters:
        backup_id (int): Backup job ID

    Returns:
        200: Backup job details
        403: Access denied
        404: Backup job not found
    """
    try:
        backup_job = db.session.get(BackupJob, backup_id)

        if not backup_job:
            return error_response(404, "Backup job not found", "NOT_FOUND")

        # Check permissions
        if not current_user.is_admin() and backup_job.owner_id != current_user.id:
            return error_response(403, "Access denied", "FORBIDDEN")

        response = BackupJobResponse.model_validate(backup_job)
        return jsonify(APIResponse(success=True, data=response.model_dump()).model_dump()), 200

    except Exception as e:
        logger.error(f"Error getting backup job {backup_id}: {e}", exc_info=True)
        return error_response(500, "Failed to get backup job", "INTERNAL_ERROR")


@api_bp.route("/v1/backups/<int:backup_id>", methods=["PUT"])
@jwt_required
@role_required("admin", "operator")
def update_backup_job(current_user, backup_id):
    """
    Update backup job

    Path Parameters:
        backup_id (int): Backup job ID

    Request Body: Partial update allowed
    {
        "name": "Updated Name",
        "is_active": false
    }

    Returns:
        200: Backup job updated successfully
        400: Invalid request data
        403: Access denied
        404: Backup job not found
    """
    try:
        backup_job = db.session.get(BackupJob, backup_id)

        if not backup_job:
            return error_response(404, "Backup job not found", "NOT_FOUND")

        # Check permissions
        if not current_user.is_admin() and backup_job.owner_id != current_user.id:
            return error_response(403, "Access denied", "FORBIDDEN")

        # Validate request data
        data = request.get_json()
        if not data:
            return validation_error_response({"_error": "Request body is required"})

        update_data = BackupJobUpdate(**data)

        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(backup_job, field, value)

        backup_job.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(f"Backup job updated: {backup_job.name} (ID: {backup_job.id}) by {current_user.username}")

        response = BackupJobResponse.model_validate(backup_job)
        return (
            jsonify(
                APIResponse(success=True, message="Backup job updated successfully", data=response.model_dump()).model_dump()
            ),
            200,
        )

    except ValidationError as e:
        logger.warning(f"Validation error in update_backup_job: {e}")
        return validation_error_response(e.errors())
    except Exception as e:
        logger.error(f"Error updating backup job {backup_id}: {e}", exc_info=True)
        return error_response(500, "Failed to update backup job", "INTERNAL_ERROR")


@api_bp.route("/v1/backups/<int:backup_id>", methods=["DELETE"])
@jwt_required
@role_required("admin", "operator")
def delete_backup_job(current_user, backup_id):
    """
    Delete backup job

    Path Parameters:
        backup_id (int): Backup job ID

    Returns:
        200: Backup job deleted successfully
        403: Access denied
        404: Backup job not found
    """
    try:
        backup_job = db.session.get(BackupJob, backup_id)

        if not backup_job:
            return error_response(404, "Backup job not found", "NOT_FOUND")

        # Check permissions
        if not current_user.is_admin() and backup_job.owner_id != current_user.id:
            return error_response(403, "Access denied", "FORBIDDEN")

        job_name = backup_job.name
        db.session.delete(backup_job)
        db.session.commit()

        logger.info(f"Backup job deleted: {job_name} (ID: {backup_id}) by {current_user.username}")

        return jsonify(APIResponse(success=True, message="Backup job deleted successfully").model_dump()), 200

    except Exception as e:
        logger.error(f"Error deleting backup job {backup_id}: {e}", exc_info=True)
        return error_response(500, "Failed to delete backup job", "INTERNAL_ERROR")


# ============================================================================
# Backup Execution Operations
# ============================================================================


@api_bp.route("/v1/backups/<int:backup_id>/run", methods=["POST"])
@jwt_required
@role_required("admin", "operator")
def trigger_backup(current_user, backup_id):
    """
    Trigger manual backup execution

    Path Parameters:
        backup_id (int): Backup job ID

    Request Body (optional):
    {
        "backup_type": "full",
        "notify": true
    }

    Returns:
        202: Backup triggered successfully
        403: Access denied
        404: Backup job not found
    """
    try:
        backup_job = db.session.get(BackupJob, backup_id)

        if not backup_job:
            return error_response(404, "Backup job not found", "NOT_FOUND")

        # Check permissions
        if not current_user.is_admin() and backup_job.owner_id != current_user.id:
            return error_response(403, "Access denied", "FORBIDDEN")

        # Parse trigger options
        data = request.get_json() or {}
        trigger_data = BackupTrigger(**data)

        from app.tasks.notification_tasks import send_backup_status_update

        send_backup_status_update.apply_async(
            kwargs={"job_id": backup_id, "status": "running"},
        )
        logger.info(
            f"Manual backup triggered: {backup_job.name} (ID: {backup_id}) "
            f"by {current_user.username}, type: {trigger_data.backup_type}"
        )

        return (
            jsonify(
                APIResponse(
                    success=True,
                    message="Backup triggered successfully",
                    data={
                        "job_id": backup_id,
                        "job_name": backup_job.name,
                        "backup_type": trigger_data.backup_type,
                        "triggered_by": current_user.username,
                        "triggered_at": datetime.now(timezone.utc).isoformat(),
                    },
                ).model_dump()
            ),
            202,
        )

    except ValidationError as e:
        logger.warning(f"Validation error in trigger_backup: {e}")
        return validation_error_response(e.errors())
    except Exception as e:
        logger.error(f"Error triggering backup {backup_id}: {e}", exc_info=True)
        return error_response(500, "Failed to trigger backup", "INTERNAL_ERROR")


@api_bp.route("/v1/backups/<int:backup_id>/executions", methods=["GET"])
@jwt_required
def get_backup_executions(current_user, backup_id):
    """
    Get backup execution history

    Path Parameters:
        backup_id (int): Backup job ID

    Query Parameters:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 20, max: 100)
        result (str): Filter by result (success, failed, warning)

    Returns:
        200: List of backup executions
        403: Access denied
        404: Backup job not found
    """
    try:
        backup_job = db.session.get(BackupJob, backup_id)

        if not backup_job:
            return error_response(404, "Backup job not found", "NOT_FOUND")

        # Check permissions
        if not current_user.is_admin() and backup_job.owner_id != current_user.id:
            return error_response(403, "Access denied", "FORBIDDEN")

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        page_size = min(request.args.get("page_size", 20, type=int), 100)

        # Build query
        query = BackupExecution.query.filter_by(job_id=backup_id)

        # Apply filters
        if request.args.get("result"):
            query = query.filter_by(execution_result=request.args.get("result"))

        # Order by execution date (descending)
        query = query.order_by(desc(BackupExecution.execution_date))

        # Paginate
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        # Convert to response models
        executions = [BackupExecutionResponse.model_validate(execution).model_dump() for execution in pagination.items]

        response = PaginatedResponse(
            success=True, data=executions, total=pagination.total, page=page, page_size=page_size, total_pages=pagination.pages
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error getting backup executions for job {backup_id}: {e}", exc_info=True)
        return error_response(500, "Failed to get backup executions", "INTERNAL_ERROR")
