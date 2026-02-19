"""
Verification Test Management API
CRUD operations for verification tests and schedules
"""

import logging
from datetime import datetime, timedelta

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api.errors import error_response, validation_error_response
from app.auth.decorators import api_token_required, role_required
from app.models import BackupJob, User, VerificationSchedule, VerificationTest, db

logger = logging.getLogger(__name__)


def validate_test_data(data, is_update=False):
    """
    Validate verification test data

    Args:
        data: Request data dictionary
        is_update: True if validating for update

    Returns:
        Dictionary of validation errors (empty if valid)
    """
    errors = {}

    # Required fields for creation
    if not is_update:
        required_fields = ["job_id", "test_type", "test_result"]
        for field in required_fields:
            if field not in data:
                errors[field] = f"{field} is required"

    # Validate test_type
    if "test_type" in data:
        valid_types = ["full_restore", "partial", "integrity"]
        if data["test_type"] not in valid_types:
            errors["test_type"] = f'Must be one of: {", ".join(valid_types)}'

    # Validate test_result
    if "test_result" in data:
        valid_results = ["success", "failed"]
        if data["test_result"] not in valid_results:
            errors["test_result"] = f'Must be one of: {", ".join(valid_results)}'

    # Validate duration_seconds
    if "duration_seconds" in data and data["duration_seconds"] is not None:
        try:
            duration = int(data["duration_seconds"])
            if duration < 0:
                errors["duration_seconds"] = "Must be non-negative"
        except (ValueError, TypeError):
            errors["duration_seconds"] = "Must be a valid integer"

    return errors


def validate_schedule_data(data, is_update=False):
    """
    Validate verification schedule data

    Args:
        data: Request data dictionary
        is_update: True if validating for update

    Returns:
        Dictionary of validation errors (empty if valid)
    """
    errors = {}

    # Required fields for creation
    if not is_update:
        required_fields = ["job_id", "test_frequency", "next_test_date"]
        for field in required_fields:
            if field not in data:
                errors[field] = f"{field} is required"

    # Validate test_frequency
    if "test_frequency" in data:
        valid_frequencies = ["monthly", "quarterly", "semi-annual", "annual"]
        if data["test_frequency"] not in valid_frequencies:
            errors["test_frequency"] = f'Must be one of: {", ".join(valid_frequencies)}'

    # Validate next_test_date
    if "next_test_date" in data:
        try:
            datetime.strptime(data["next_test_date"], "%Y-%m-%d")
        except ValueError:
            errors["next_test_date"] = "Invalid date format. Use YYYY-MM-DD"

    # Validate last_test_date if provided
    if "last_test_date" in data and data["last_test_date"]:
        try:
            datetime.strptime(data["last_test_date"], "%Y-%m-%d")
        except ValueError:
            errors["last_test_date"] = "Invalid date format. Use YYYY-MM-DD"

    return errors


@api_bp.route("/verification/tests", methods=["GET"])
@api_token_required
def list_tests():
    """
    List verification tests with pagination and filtering

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        job_id: Filter by job ID
        test_type: Filter by test type
        test_result: Filter by test result
        tester_id: Filter by tester user ID

    Returns:
        200: List of verification tests
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Build query
        query = VerificationTest.query

        # Apply filters
        if "job_id" in request.args:
            query = query.filter_by(job_id=request.args["job_id"])

        if "test_type" in request.args:
            query = query.filter_by(test_type=request.args["test_type"])

        if "test_result" in request.args:
            query = query.filter_by(test_result=request.args["test_result"])

        if "tester_id" in request.args:
            query = query.filter_by(tester_id=request.args["tester_id"])

        # Execute paginated query
        pagination = query.order_by(VerificationTest.test_date.desc()).paginate(page=page, per_page=per_page, error_out=False)

        # Format response
        tests = []
        for test in pagination.items:
            tests.append(
                {
                    "id": test.id,
                    "job_id": test.job_id,
                    "job_name": test.job.job_name if test.job else None,
                    "test_type": test.test_type,
                    "test_date": test.test_date.isoformat() + "Z",
                    "tester_id": test.tester_id,
                    "tester_name": test.tester.full_name if test.tester else None,
                    "restore_target": test.restore_target,
                    "test_result": test.test_result,
                    "duration_seconds": test.duration_seconds,
                    "issues_found": test.issues_found,
                    "created_at": test.created_at.isoformat() + "Z",
                }
            )

        return (
            jsonify(
                {
                    "tests": tests,
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
        logger.error(f"Error listing tests: {str(e)}", exc_info=True)
        return error_response(500, "Failed to list tests", "QUERY_FAILED")


@api_bp.route("/verification/tests/<int:test_id>", methods=["GET"])
@api_token_required
def get_test(test_id):
    """
    Get detailed information about a verification test

    Args:
        test_id: Verification test ID

    Returns:
        200: Test details
        404: Test not found
    """
    try:
        test = VerificationTest.query.get(test_id)
        if not test:
            return error_response(404, "Verification test not found", "TEST_NOT_FOUND")

        return (
            jsonify(
                {
                    "id": test.id,
                    "job_id": test.job_id,
                    "job": (
                        {
                            "id": test.job.id,
                            "job_name": test.job.job_name,
                            "job_type": test.job.job_type,
                            "target_server": test.job.target_server,
                        }
                        if test.job
                        else None
                    ),
                    "test_type": test.test_type,
                    "test_date": test.test_date.isoformat() + "Z",
                    "tester_id": test.tester_id,
                    "tester": (
                        {"id": test.tester.id, "username": test.tester.username, "full_name": test.tester.full_name}
                        if test.tester
                        else None
                    ),
                    "restore_target": test.restore_target,
                    "test_result": test.test_result,
                    "duration_seconds": test.duration_seconds,
                    "issues_found": test.issues_found,
                    "notes": test.notes,
                    "created_at": test.created_at.isoformat() + "Z",
                    "updated_at": test.updated_at.isoformat() + "Z",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting test: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get test details", "QUERY_FAILED")


@api_bp.route("/verification/tests", methods=["POST"])
@api_token_required
@role_required("admin", "operator")
def create_test():
    """
    Record a new verification test

    Request Body:
    {
        "job_id": 1,
        "test_type": "full_restore",
        "test_result": "success",
        "restore_target": "TEST-SERVER-01",
        "duration_seconds": 1800,
        "issues_found": null,
        "notes": "Successful restore test"
    }

    Returns:
        201: Test recorded successfully
        400: Invalid request data
        404: Job not found
    """
    try:
        data = request.get_json()

        # Validate data
        errors = validate_test_data(data)
        if errors:
            return validation_error_response(errors)

        # Validate job exists
        job = BackupJob.query.get(data["job_id"])
        if not job:
            return error_response(404, "Backup job not found", "JOB_NOT_FOUND")

        # Get current user as tester
        tester_id = data.get("tester_id")
        if not tester_id and current_user.is_authenticated:
            tester_id = current_user.id

        # Parse test_date
        test_date = datetime.utcnow()
        if "test_date" in data:
            try:
                test_date = datetime.fromisoformat(data["test_date"].replace("Z", "+00:00"))
            except ValueError:
                return validation_error_response({"test_date": "Invalid date format. Use ISO 8601 format"})

        # Create test
        test = VerificationTest(
            job_id=data["job_id"],
            test_type=data["test_type"],
            test_date=test_date,
            tester_id=tester_id,
            restore_target=data.get("restore_target"),
            test_result=data["test_result"],
            duration_seconds=data.get("duration_seconds"),
            issues_found=data.get("issues_found"),
            notes=data.get("notes"),
        )

        db.session.add(test)

        # Update verification schedule's last_test_date
        schedule = VerificationSchedule.query.filter_by(job_id=data["job_id"], is_active=True).first()

        if schedule:
            schedule.last_test_date = test_date.date()

            # Calculate next test date based on frequency
            if schedule.test_frequency == "monthly":
                schedule.next_test_date = (test_date + timedelta(days=30)).date()
            elif schedule.test_frequency == "quarterly":
                schedule.next_test_date = (test_date + timedelta(days=90)).date()
            elif schedule.test_frequency == "semi-annual":
                schedule.next_test_date = (test_date + timedelta(days=180)).date()
            elif schedule.test_frequency == "annual":
                schedule.next_test_date = (test_date + timedelta(days=365)).date()

        db.session.commit()

        logger.info(f"Verification test recorded: job_id={data['job_id']}, result={data['test_result']}")

        return (
            jsonify(
                {
                    "message": "Verification test recorded successfully",
                    "test_id": test.id,
                    "job_id": data["job_id"],
                    "test_result": test.test_result,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating test: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to record test", "CREATE_FAILED")


@api_bp.route("/verification/tests/<int:test_id>", methods=["PUT"])
@api_token_required
@role_required("admin", "operator")
def update_test(test_id):
    """
    Update a verification test record

    Args:
        test_id: Verification test ID

    Request Body: Same as create_test (all fields optional)

    Returns:
        200: Test updated successfully
        400: Invalid request data
        404: Test not found
    """
    try:
        test = VerificationTest.query.get(test_id)
        if not test:
            return error_response(404, "Verification test not found", "TEST_NOT_FOUND")

        data = request.get_json()

        # Validate data
        errors = validate_test_data(data, is_update=True)
        if errors:
            return validation_error_response(errors)

        # Update fields
        if "test_type" in data:
            test.test_type = data["test_type"]
        if "test_result" in data:
            test.test_result = data["test_result"]
        if "restore_target" in data:
            test.restore_target = data["restore_target"]
        if "duration_seconds" in data:
            test.duration_seconds = data["duration_seconds"]
        if "issues_found" in data:
            test.issues_found = data["issues_found"]
        if "notes" in data:
            test.notes = data["notes"]

        test.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Verification test updated: test_id={test_id}")

        return jsonify({"message": "Verification test updated successfully", "test_id": test.id}), 200

    except Exception as e:
        logger.error(f"Error updating test: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to update test", "UPDATE_FAILED")


@api_bp.route("/verification/schedules", methods=["GET"])
@api_token_required
def list_schedules():
    """
    List verification schedules with pagination

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        job_id: Filter by job ID
        test_frequency: Filter by frequency
        overdue: Filter overdue schedules (true/false)

    Returns:
        200: List of verification schedules
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Build query
        query = VerificationSchedule.query.filter_by(is_active=True)

        # Apply filters
        if "job_id" in request.args:
            query = query.filter_by(job_id=request.args["job_id"])

        if "test_frequency" in request.args:
            query = query.filter_by(test_frequency=request.args["test_frequency"])

        if "overdue" in request.args and request.args["overdue"].lower() == "true":
            today = datetime.utcnow().date()
            query = query.filter(VerificationSchedule.next_test_date < today)

        # Execute paginated query
        pagination = query.order_by(VerificationSchedule.next_test_date).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Format response
        schedules = []
        today = datetime.utcnow().date()

        for schedule in pagination.items:
            is_overdue = schedule.next_test_date < today
            days_until = (schedule.next_test_date - today).days

            schedules.append(
                {
                    "id": schedule.id,
                    "job_id": schedule.job_id,
                    "job_name": schedule.job.job_name if schedule.job else None,
                    "test_frequency": schedule.test_frequency,
                    "next_test_date": schedule.next_test_date.isoformat(),
                    "last_test_date": schedule.last_test_date.isoformat() if schedule.last_test_date else None,
                    "assigned_to": schedule.assigned_to,
                    "assignee_name": schedule.assignee.full_name if schedule.assignee else None,
                    "is_overdue": is_overdue,
                    "days_until_test": days_until,
                    "created_at": schedule.created_at.isoformat() + "Z",
                }
            )

        return (
            jsonify(
                {
                    "schedules": schedules,
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
        logger.error(f"Error listing schedules: {str(e)}", exc_info=True)
        return error_response(500, "Failed to list schedules", "QUERY_FAILED")


@api_bp.route("/verification/schedules", methods=["POST"])
@api_token_required
@role_required("admin", "operator")
def create_schedule():
    """
    Create a verification test schedule

    Request Body:
    {
        "job_id": 1,
        "test_frequency": "quarterly",
        "next_test_date": "2025-12-01",
        "assigned_to": 2
    }

    Returns:
        201: Schedule created successfully
        400: Invalid request data
        404: Job not found
        409: Schedule already exists for this job
    """
    try:
        data = request.get_json()

        # Validate data
        errors = validate_schedule_data(data)
        if errors:
            return validation_error_response(errors)

        # Validate job exists
        job = BackupJob.query.get(data["job_id"])
        if not job:
            return error_response(404, "Backup job not found", "JOB_NOT_FOUND")

        # Check if active schedule already exists
        existing = VerificationSchedule.query.filter_by(job_id=data["job_id"], is_active=True).first()

        if existing:
            return error_response(409, "Active verification schedule already exists for this job", "SCHEDULE_EXISTS")

        # Parse dates
        next_test_date = datetime.strptime(data["next_test_date"], "%Y-%m-%d").date()
        last_test_date = None
        if "last_test_date" in data and data["last_test_date"]:
            last_test_date = datetime.strptime(data["last_test_date"], "%Y-%m-%d").date()

        # Create schedule
        schedule = VerificationSchedule(
            job_id=data["job_id"],
            test_frequency=data["test_frequency"],
            next_test_date=next_test_date,
            last_test_date=last_test_date,
            assigned_to=data.get("assigned_to"),
            is_active=True,
        )

        db.session.add(schedule)
        db.session.commit()

        logger.info(f"Verification schedule created: job_id={data['job_id']}, frequency={data['test_frequency']}")

        return (
            jsonify(
                {"message": "Verification schedule created successfully", "schedule_id": schedule.id, "job_id": data["job_id"]}
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating schedule: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to create schedule", "CREATE_FAILED")


@api_bp.route("/verification/schedules/<int:schedule_id>", methods=["PUT"])
@api_token_required
@role_required("admin", "operator")
def update_schedule(schedule_id):
    """
    Update a verification schedule

    Args:
        schedule_id: Schedule ID

    Request Body: Same as create_schedule (all fields optional)

    Returns:
        200: Schedule updated successfully
        400: Invalid request data
        404: Schedule not found
    """
    try:
        schedule = VerificationSchedule.query.get(schedule_id)
        if not schedule:
            return error_response(404, "Verification schedule not found", "SCHEDULE_NOT_FOUND")

        data = request.get_json()

        # Validate data
        errors = validate_schedule_data(data, is_update=True)
        if errors:
            return validation_error_response(errors)

        # Update fields
        if "test_frequency" in data:
            schedule.test_frequency = data["test_frequency"]
        if "next_test_date" in data:
            schedule.next_test_date = datetime.strptime(data["next_test_date"], "%Y-%m-%d").date()
        if "last_test_date" in data:
            if data["last_test_date"]:
                schedule.last_test_date = datetime.strptime(data["last_test_date"], "%Y-%m-%d").date()
            else:
                schedule.last_test_date = None
        if "assigned_to" in data:
            schedule.assigned_to = data["assigned_to"]
        if "is_active" in data:
            schedule.is_active = bool(data["is_active"])

        schedule.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Verification schedule updated: schedule_id={schedule_id}")

        return jsonify({"message": "Verification schedule updated successfully", "schedule_id": schedule.id}), 200

    except Exception as e:
        logger.error(f"Error updating schedule: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to update schedule", "UPDATE_FAILED")


@api_bp.route("/verification/schedules/<int:schedule_id>", methods=["DELETE"])
@api_token_required
@role_required("admin")
def delete_schedule(schedule_id):
    """
    Delete (deactivate) a verification schedule

    Args:
        schedule_id: Schedule ID

    Returns:
        200: Schedule deleted successfully
        404: Schedule not found
    """
    try:
        schedule = VerificationSchedule.query.get(schedule_id)
        if not schedule:
            return error_response(404, "Verification schedule not found", "SCHEDULE_NOT_FOUND")

        # Deactivate instead of deleting
        schedule.is_active = False
        db.session.commit()

        logger.info(f"Verification schedule deactivated: schedule_id={schedule_id}")

        return jsonify({"message": "Verification schedule deleted successfully", "schedule_id": schedule_id}), 200

    except Exception as e:
        logger.error(f"Error deleting schedule: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to delete schedule", "DELETE_FAILED")
