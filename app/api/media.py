"""
Offline Media Management API
CRUD operations for offline media (tapes, external HDDs, USB drives)
"""

import logging
from datetime import datetime, timezone

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api.errors import error_response, validation_error_response
from app.auth.decorators import api_token_required, role_required
from app.models import MediaLending, MediaRotationSchedule, OfflineMedia, User, db

logger = logging.getLogger(__name__)


def validate_media_data(data, is_update=False):
    """
    Validate offline media data

    Args:
        data: Request data dictionary
        is_update: True if validating for update

    Returns:
        Dictionary of validation errors (empty if valid)
    """
    errors = {}

    # Required fields for creation
    if not is_update:
        required_fields = ["media_id", "media_type"]
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = f"{field} is required"

    # Validate media_type
    if "media_type" in data:
        valid_types = ["external_hdd", "tape", "usb"]
        if data["media_type"] not in valid_types:
            errors["media_type"] = f'Must be one of: {", ".join(valid_types)}'

    # Validate current_status
    if "current_status" in data:
        valid_statuses = ["in_use", "stored", "retired", "available"]
        if data["current_status"] not in valid_statuses:
            errors["current_status"] = f'Must be one of: {", ".join(valid_statuses)}'

    # Validate capacity_gb
    if "capacity_gb" in data and data["capacity_gb"] is not None:
        try:
            capacity = int(data["capacity_gb"])
            if capacity < 1:
                errors["capacity_gb"] = "Must be at least 1 GB"
        except (ValueError, TypeError):
            errors["capacity_gb"] = "Must be a valid integer"

    # Validate purchase_date
    if "purchase_date" in data and data["purchase_date"]:
        try:
            datetime.strptime(data["purchase_date"], "%Y-%m-%d")
        except ValueError:
            errors["purchase_date"] = "Invalid date format. Use YYYY-MM-DD"

    return errors


@api_bp.route("/media", methods=["GET"])
@api_token_required
def list_media():
    """
    List offline media with pagination and filtering

    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        media_type: Filter by media type
        current_status: Filter by status
        owner_id: Filter by owner

    Returns:
        200: List of offline media
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Build query
        query = OfflineMedia.query

        # Apply filters
        if "media_type" in request.args:
            query = query.filter_by(media_type=request.args["media_type"])

        if "current_status" in request.args:
            query = query.filter_by(current_status=request.args["current_status"])

        if "owner_id" in request.args:
            query = query.filter_by(owner_id=request.args["owner_id"])

        # Execute paginated query
        pagination = query.order_by(OfflineMedia.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        # Format response
        media_list = []
        for media in pagination.items:
            # Check if currently borrowed
            active_lending = media.lending_records.filter_by(actual_return=None).first()

            media_list.append(
                {
                    "id": media.id,
                    "media_id": media.media_id,
                    "media_type": media.media_type,
                    "capacity_gb": media.capacity_gb,
                    "purchase_date": media.purchase_date.isoformat() if media.purchase_date else None,
                    "storage_location": media.storage_location,
                    "current_status": media.current_status,
                    "owner_id": media.owner_id,
                    "owner_name": media.owner.full_name if media.owner else None,
                    "is_borrowed": bool(active_lending),
                    "borrowed_by": active_lending.borrower.full_name if active_lending else None,
                    "notes": media.notes,
                    "created_at": media.created_at.isoformat() + "Z",
                    "updated_at": media.updated_at.isoformat() + "Z",
                }
            )

        return (
            jsonify(
                {
                    "media": media_list,
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
        logger.error(f"Error listing media: {str(e)}", exc_info=True)
        return error_response(500, "Failed to list media", "QUERY_FAILED")


@api_bp.route("/media/<int:media_id>", methods=["GET"])
@api_token_required
def get_media(media_id):
    """
    Get detailed information about offline media

    Args:
        media_id: Offline media ID

    Returns:
        200: Media details
        404: Media not found
    """
    try:
        media = db.session.get(OfflineMedia, media_id)
        if not media:
            return error_response(404, "Offline media not found", "MEDIA_NOT_FOUND")

        # Get backup copies using this media
        copies = []
        for copy in media.backup_copies:
            copies.append(
                {
                    "id": copy.id,
                    "job_id": copy.job_id,
                    "job_name": copy.job.job_name if copy.job else None,
                    "copy_type": copy.copy_type,
                    "last_backup_date": copy.last_backup_date.isoformat() + "Z" if copy.last_backup_date else None,
                    "last_backup_size": copy.last_backup_size,
                    "status": copy.status,
                }
            )

        # Get lending history
        lending_history = []
        for lending in media.lending_records.order_by(db.desc("borrow_date")).limit(10):
            lending_history.append(
                {
                    "id": lending.id,
                    "borrower_id": lending.borrower_id,
                    "borrower_name": lending.borrower.full_name if lending.borrower else None,
                    "borrow_purpose": lending.borrow_purpose,
                    "borrow_date": lending.borrow_date.isoformat() + "Z",
                    "expected_return": lending.expected_return.isoformat(),
                    "actual_return": lending.actual_return.isoformat() + "Z" if lending.actual_return else None,
                    "return_condition": lending.return_condition,
                    "is_returned": bool(lending.actual_return),
                }
            )

        # Get rotation schedule
        rotation = media.rotation_schedules.filter_by(is_active=True).first()
        rotation_info = None
        if rotation:
            rotation_info = {
                "id": rotation.id,
                "rotation_type": rotation.rotation_type,
                "rotation_cycle": rotation.rotation_cycle,
                "next_rotation_date": rotation.next_rotation_date.isoformat(),
                "last_rotation_date": rotation.last_rotation_date.isoformat() if rotation.last_rotation_date else None,
            }

        return (
            jsonify(
                {
                    "id": media.id,
                    "media_id": media.media_id,
                    "media_type": media.media_type,
                    "capacity_gb": media.capacity_gb,
                    "purchase_date": media.purchase_date.isoformat() if media.purchase_date else None,
                    "storage_location": media.storage_location,
                    "current_status": media.current_status,
                    "owner_id": media.owner_id,
                    "owner": (
                        {"id": media.owner.id, "username": media.owner.username, "full_name": media.owner.full_name}
                        if media.owner
                        else None
                    ),
                    "qr_code": media.qr_code,
                    "notes": media.notes,
                    "backup_copies": copies,
                    "lending_history": lending_history,
                    "rotation_schedule": rotation_info,
                    "created_at": media.created_at.isoformat() + "Z",
                    "updated_at": media.updated_at.isoformat() + "Z",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting media: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get media details", "QUERY_FAILED")


@api_bp.route("/media", methods=["POST"])
@api_token_required
@role_required("admin", "operator")
def create_media():
    """
    Create new offline media record

    Request Body:
    {
        "media_id": "TAPE-001",
        "media_type": "tape",
        "capacity_gb": 1000,
        "purchase_date": "2025-10-01",
        "storage_location": "Fireproof Safe A",
        "current_status": "stored",
        "owner_id": 1,
        "notes": "LTO-7 tape"
    }

    Returns:
        201: Media created successfully
        400: Invalid request data
        409: Media ID already exists
    """
    try:
        data = request.get_json()

        # Validate data
        errors = validate_media_data(data)
        if errors:
            return validation_error_response(errors)

        # Check if media_id already exists
        existing = OfflineMedia.query.filter_by(media_id=data["media_id"]).first()
        if existing:
            return error_response(409, "Media ID already exists", "MEDIA_ID_EXISTS")

        # Parse purchase_date
        purchase_date = None
        if "purchase_date" in data and data["purchase_date"]:
            purchase_date = datetime.strptime(data["purchase_date"], "%Y-%m-%d").date()

        # Create media
        media = OfflineMedia(
            media_id=data["media_id"],
            media_type=data["media_type"],
            capacity_gb=data.get("capacity_gb"),
            purchase_date=purchase_date,
            storage_location=data.get("storage_location"),
            current_status=data.get("current_status", "available"),
            owner_id=data.get("owner_id"),
            qr_code=data.get("qr_code"),
            notes=data.get("notes"),
        )

        db.session.add(media)
        db.session.commit()

        logger.info(f"Offline media created: {media.media_id} (ID: {media.id})")

        return (
            jsonify(
                {"message": "Offline media created successfully", "media_id": media.id, "media_identifier": media.media_id}
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating media: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to create media", "CREATE_FAILED")


@api_bp.route("/media/<int:media_id>", methods=["PUT"])
@api_token_required
@role_required("admin", "operator")
def update_media(media_id):
    """
    Update offline media record

    Args:
        media_id: Offline media ID

    Request Body: Same as create_media (all fields optional)

    Returns:
        200: Media updated successfully
        400: Invalid request data
        404: Media not found
    """
    try:
        media = db.session.get(OfflineMedia, media_id)
        if not media:
            return error_response(404, "Offline media not found", "MEDIA_NOT_FOUND")

        data = request.get_json()

        # Validate data
        errors = validate_media_data(data, is_update=True)
        if errors:
            return validation_error_response(errors)

        # Update fields
        if "media_type" in data:
            media.media_type = data["media_type"]
        if "capacity_gb" in data:
            media.capacity_gb = data["capacity_gb"]
        if "purchase_date" in data:
            if data["purchase_date"]:
                media.purchase_date = datetime.strptime(data["purchase_date"], "%Y-%m-%d").date()
            else:
                media.purchase_date = None
        if "storage_location" in data:
            media.storage_location = data["storage_location"]
        if "current_status" in data:
            media.current_status = data["current_status"]
        if "owner_id" in data:
            media.owner_id = data["owner_id"]
        if "qr_code" in data:
            media.qr_code = data["qr_code"]
        if "notes" in data:
            media.notes = data["notes"]

        media.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(f"Offline media updated: {media.media_id} (ID: {media.id})")

        return (
            jsonify(
                {"message": "Offline media updated successfully", "media_id": media.id, "media_identifier": media.media_id}
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error updating media: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to update media", "UPDATE_FAILED")


@api_bp.route("/media/<int:media_id>", methods=["DELETE"])
@api_token_required
@role_required("admin")
def delete_media(media_id):
    """
    Delete offline media (admin only)

    Args:
        media_id: Offline media ID

    Returns:
        200: Media deleted successfully
        404: Media not found
        409: Media is in use (has active backups)
    """
    try:
        media = db.session.get(OfflineMedia, media_id)
        if not media:
            return error_response(404, "Offline media not found", "MEDIA_NOT_FOUND")

        # Check if media has active backup copies
        if media.backup_copies.count() > 0:
            return error_response(409, "Cannot delete media with active backup copies", "MEDIA_IN_USE")

        media_identifier = media.media_id

        # Delete media (cascades to related records)
        db.session.delete(media)
        db.session.commit()

        logger.info(f"Offline media deleted: {media_identifier} (ID: {media_id})")

        return (
            jsonify(
                {"message": "Offline media deleted successfully", "media_id": media_id, "media_identifier": media_identifier}
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error deleting media: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to delete media", "DELETE_FAILED")


@api_bp.route("/media/<int:media_id>/borrow", methods=["POST"])
@api_token_required
@role_required("admin", "operator")
def borrow_media(media_id):
    """
    Record media lending/borrowing

    Args:
        media_id: Offline media ID

    Request Body:
    {
        "borrower_id": 2,
        "borrow_purpose": "Restore test",
        "expected_return": "2025-11-10"
    }

    Returns:
        201: Lending recorded successfully
        400: Invalid request data
        404: Media not found
        409: Media already borrowed
    """
    try:
        media = db.session.get(OfflineMedia, media_id)
        if not media:
            return error_response(404, "Offline media not found", "MEDIA_NOT_FOUND")

        # Check if media is already borrowed
        active_lending = media.lending_records.filter_by(actual_return=None).first()
        if active_lending:
            return error_response(409, "Media is already borrowed", "MEDIA_ALREADY_BORROWED")

        data = request.get_json()

        # Validate required fields
        errors = {}
        if "expected_return" not in data:
            errors["expected_return"] = "expected_return is required"

        # Use current user as borrower if not specified
        borrower_id = data.get("borrower_id")
        if not borrower_id and current_user.is_authenticated:
            borrower_id = current_user.id

        if not borrower_id:
            errors["borrower_id"] = "borrower_id is required"

        # Validate expected_return date
        try:
            expected_return = datetime.strptime(data["expected_return"], "%Y-%m-%d").date()
        except ValueError:
            errors["expected_return"] = "Invalid date format. Use YYYY-MM-DD"
            expected_return = None

        if errors:
            return validation_error_response(errors)

        # Create lending record
        lending = MediaLending(
            offline_media_id=media_id,
            borrower_id=borrower_id,
            borrow_purpose=data.get("borrow_purpose"),
            borrow_date=datetime.now(timezone.utc),
            expected_return=expected_return,
        )

        # Update media status
        media.current_status = "in_use"

        db.session.add(lending)
        db.session.commit()

        logger.info(f"Media borrowed: media_id={media_id}, borrower_id={borrower_id}")

        return jsonify({"message": "Media lending recorded successfully", "lending_id": lending.id, "media_id": media_id}), 201

    except Exception as e:
        logger.error(f"Error borrowing media: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to record lending", "CREATE_FAILED")


@api_bp.route("/media/<int:media_id>/return", methods=["POST"])
@api_token_required
@role_required("admin", "operator")
def return_media(media_id):
    """
    Record media return

    Args:
        media_id: Offline media ID

    Request Body:
    {
        "return_condition": "normal",
        "notes": "Returned in good condition"
    }

    Returns:
        200: Return recorded successfully
        404: Media not found or not borrowed
    """
    try:
        media = db.session.get(OfflineMedia, media_id)
        if not media:
            return error_response(404, "Offline media not found", "MEDIA_NOT_FOUND")

        # Find active lending
        active_lending = media.lending_records.filter_by(actual_return=None).first()
        if not active_lending:
            return error_response(404, "No active lending found for this media", "NOT_BORROWED")

        data = request.get_json() or {}

        # Update lending record
        active_lending.actual_return = datetime.now(timezone.utc)
        active_lending.return_condition = data.get("return_condition", "normal")

        if "notes" in data:
            active_lending.notes = data["notes"]

        # Update media status
        media.current_status = "stored"

        db.session.commit()

        logger.info(f"Media returned: media_id={media_id}, lending_id={active_lending.id}")

        return (
            jsonify(
                {
                    "message": "Media return recorded successfully",
                    "lending_id": active_lending.id,
                    "media_id": media_id,
                    "return_condition": active_lending.return_condition,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error returning media: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to record return", "UPDATE_FAILED")
