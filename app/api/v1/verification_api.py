"""
Verification Management REST API (v1)
Provides RESTful endpoints for backup verification testing

Endpoints:
- POST   /api/v1/verify/{backup_id}        - Start verification test
- GET    /api/v1/verify/{backup_id}/status - Get verification status
- GET    /api/v1/verify/{backup_id}/result - Get verification result
- GET    /api/v1/verify                    - List recent verifications
"""

import logging
from datetime import datetime

from flask import jsonify, request
from pydantic import ValidationError
from sqlalchemy import desc

from app.api import api_bp
from app.api.auth import jwt_required, role_required
from app.api.errors import error_response, validation_error_response
from app.api.schemas import (
    APIResponse,
    PaginatedResponse,
    VerificationResultResponse,
    VerificationStartRequest,
    VerificationStatusResponse,
)
from app.models import BackupCopy, BackupJob, VerificationTest, db

logger = logging.getLogger(__name__)


# ============================================================================
# Verification Operations
# ============================================================================


@api_bp.route("/v1/verify/<int:backup_id>", methods=["POST"])
@jwt_required
@role_required("admin", "operator")
def start_verification(current_user, backup_id):
    """
    Start verification test for a backup

    Path Parameters:
        backup_id (int): Backup copy ID

    Request Body:
    {
        "test_type": "checksum",
        "scope": "full",
        "notify_on_completion": true
    }

    Returns:
        202: Verification test started
        400: Invalid request data
        403: Access denied
        404: Backup not found
    """
    try:
        # Get backup copy
        backup_copy = BackupCopy.query.get(backup_id)

        if not backup_copy:
            return error_response(404, "Backup not found", "NOT_FOUND")

        # Check if user has access to this backup's job
        backup_job = BackupJob.query.get(backup_copy.job_id)
        if not backup_job:
            return error_response(404, "Backup job not found", "NOT_FOUND")

        if not current_user.is_admin() and backup_job.owner_id != current_user.id:
            return error_response(403, "Access denied", "FORBIDDEN")

        # Validate request data
        data = request.get_json() or {}
        verification_data = VerificationStartRequest(**data)

        # Create verification test record
        verification = VerificationTest(
            backup_id=backup_id,
            test_type=verification_data.test_type,
            test_status="pending",
            started_at=datetime.utcnow(),
            tester_id=current_user.id,
        )

        db.session.add(verification)
        db.session.commit()

        logger.info(
            f"Verification test started: Backup {backup_id}, "
            f"Type: {verification_data.test_type}, "
            f"Scope: {verification_data.scope}, "
            f"By: {current_user.username}"
        )

        from app.tasks.verification_tasks import verify_backup

        verify_backup.apply_async(
            kwargs={
                "job_id": backup_copy.job_id,
                "verification_type": verification_data.test_type,
            },
        )

        response = APIResponse(
            success=True,
            message="Verification test started",
            data={
                "verification_id": verification.id,
                "backup_id": backup_id,
                "test_type": verification_data.test_type,
                "test_status": "pending",
                "started_at": verification.started_at.isoformat(),
                "started_by": current_user.username,
            },
        )

        return jsonify(response.model_dump()), 202

    except ValidationError as e:
        logger.warning(f"Validation error in start_verification: {e}")
        return validation_error_response(e.errors())
    except Exception as e:
        logger.error(f"Error starting verification for backup {backup_id}: {e}", exc_info=True)
        return error_response(500, "Failed to start verification", "INTERNAL_ERROR")


@api_bp.route("/v1/verify/<int:backup_id>/status", methods=["GET"])
@jwt_required
def get_verification_status(current_user, backup_id):
    """
    Get current verification status for a backup

    Path Parameters:
        backup_id (int): Backup copy ID

    Returns:
        200: Verification status
        404: Backup or verification not found
    """
    try:
        # Get backup copy
        backup_copy = BackupCopy.query.get(backup_id)

        if not backup_copy:
            return error_response(404, "Backup not found", "NOT_FOUND")

        # Check if user has access to this backup's job
        backup_job = BackupJob.query.get(backup_copy.job_id)
        if not backup_job:
            return error_response(404, "Backup job not found", "NOT_FOUND")

        if not current_user.is_admin() and backup_job.owner_id != current_user.id:
            return error_response(403, "Access denied", "FORBIDDEN")

        # Get most recent verification test
        verification = (
            VerificationTest.query.filter_by(backup_id=backup_id).order_by(desc(VerificationTest.started_at)).first()
        )

        if not verification:
            return error_response(404, "No verification tests found for this backup", "NOT_FOUND")

        # Build response
        response_data = VerificationStatusResponse.model_validate(verification)

        response = APIResponse(success=True, data=response_data.model_dump())

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error getting verification status for backup {backup_id}: {e}", exc_info=True)
        return error_response(500, "Failed to get verification status", "INTERNAL_ERROR")


@api_bp.route("/v1/verify/<int:backup_id>/result", methods=["GET"])
@jwt_required
def get_verification_result(current_user, backup_id):
    """
    Get verification test result summary

    Path Parameters:
        backup_id (int): Backup copy ID

    Returns:
        200: Verification result summary
        404: Backup or verification not found
    """
    try:
        # Get backup copy
        backup_copy = BackupCopy.query.get(backup_id)

        if not backup_copy:
            return error_response(404, "Backup not found", "NOT_FOUND")

        # Check if user has access to this backup's job
        backup_job = BackupJob.query.get(backup_copy.job_id)
        if not backup_job:
            return error_response(404, "Backup job not found", "NOT_FOUND")

        if not current_user.is_admin() and backup_job.owner_id != current_user.id:
            return error_response(403, "Access denied", "FORBIDDEN")

        # Get most recent completed verification test
        verification = (
            VerificationTest.query.filter_by(backup_id=backup_id)
            .filter(VerificationTest.test_status == "completed")
            .order_by(desc(VerificationTest.completed_at))
            .first()
        )

        if not verification:
            return error_response(404, "No completed verification tests found", "NOT_FOUND")

        # Calculate success rate
        success_rate = None
        if verification.files_tested and verification.files_tested > 0:
            success_rate = (verification.files_passed / verification.files_tested) * 100

        # Build result response
        result_data = {
            "backup_id": backup_id,
            "backup_name": backup_job.name,
            "test_type": verification.test_type,
            "test_status": verification.test_status,
            "test_result": verification.test_result,
            "success_rate": round(success_rate, 2) if success_rate else None,
            "total_files": verification.files_tested,
            "passed_files": verification.files_passed,
            "failed_files": verification.files_failed,
            "duration_seconds": verification.duration_seconds,
            "completed_at": verification.completed_at,
        }

        response = APIResponse(success=True, data=result_data)

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error getting verification result for backup {backup_id}: {e}", exc_info=True)
        return error_response(500, "Failed to get verification result", "INTERNAL_ERROR")


@api_bp.route("/v1/verify", methods=["GET"])
@jwt_required
def list_verifications(current_user):
    """
    List recent verification tests

    Query Parameters:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 20, max: 100)
        test_type (str): Filter by test type
        test_status (str): Filter by status (pending, running, completed, failed)
        backup_id (int): Filter by backup ID

    Returns:
        200: List of verification tests
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        page_size = min(request.args.get("page_size", 20, type=int), 100)

        # Build query
        query = VerificationTest.query

        # Apply filters
        if request.args.get("test_type"):
            query = query.filter_by(test_type=request.args.get("test_type"))

        if request.args.get("test_status"):
            query = query.filter_by(test_status=request.args.get("test_status"))

        if request.args.get("backup_id"):
            query = query.filter_by(backup_id=request.args.get("backup_id", type=int))

        # Filter by user access (non-admin users can only see their own backups)
        if not current_user.is_admin():
            # Join with BackupCopy and BackupJob to filter by owner
            query = query.join(BackupCopy).join(BackupJob).filter(BackupJob.owner_id == current_user.id)

        # Order by started date (descending)
        query = query.order_by(desc(VerificationTest.started_at))

        # Paginate
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        # Convert to response models
        verifications = [VerificationStatusResponse.model_validate(v).model_dump() for v in pagination.items]

        response = PaginatedResponse(
            success=True,
            data=verifications,
            total=pagination.total,
            page=page,
            page_size=page_size,
            total_pages=pagination.pages,
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error listing verifications: {e}", exc_info=True)
        return error_response(500, "Failed to list verifications", "INTERNAL_ERROR")


@api_bp.route("/v1/verify/<int:verification_id>/cancel", methods=["POST"])
@jwt_required
@role_required("admin", "operator")
def cancel_verification(current_user, verification_id):
    """
    Cancel a running verification test

    Path Parameters:
        verification_id (int): Verification test ID

    Returns:
        200: Verification cancelled
        400: Cannot cancel (not running)
        403: Access denied
        404: Verification not found
    """
    try:
        # Get verification test
        verification = VerificationTest.query.get(verification_id)

        if not verification:
            return error_response(404, "Verification test not found", "NOT_FOUND")

        # Check if user has access
        backup_copy = BackupCopy.query.get(verification.backup_id)
        if backup_copy:
            backup_job = BackupJob.query.get(backup_copy.job_id)
            if backup_job and not current_user.is_admin() and backup_job.owner_id != current_user.id:
                return error_response(403, "Access denied", "FORBIDDEN")

        # Check if verification can be cancelled
        if verification.test_status not in ("pending", "running"):
            return error_response(400, f"Cannot cancel verification with status: {verification.test_status}", "INVALID_STATE")

        # Update status
        verification.test_status = "cancelled"
        verification.completed_at = datetime.utcnow()
        verification.test_result = "cancelled"
        db.session.commit()

        logger.info(f"Verification test cancelled: ID {verification_id} by {current_user.username}")

        response = APIResponse(
            success=True,
            message="Verification test cancelled",
            data={
                "verification_id": verification_id,
                "test_status": "cancelled",
                "cancelled_by": current_user.username,
                "cancelled_at": verification.completed_at.isoformat(),
            },
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error cancelling verification {verification_id}: {e}", exc_info=True)
        return error_response(500, "Failed to cancel verification", "INTERNAL_ERROR")
