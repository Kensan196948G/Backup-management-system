"""
Storage Management REST API (v1)
Provides RESTful endpoints for storage provider management

Endpoints:
- GET    /api/v1/storage/providers       - List storage providers
- GET    /api/v1/storage/providers/{id}  - Get provider details
- POST   /api/v1/storage/test            - Test storage connection
- GET    /api/v1/storage/{id}/space      - Get storage space information
- GET    /api/v1/storage/{id}/backups    - List backups on storage
"""

import logging
import os
from datetime import datetime, timezone

from flask import jsonify, request
from pydantic import ValidationError

from app.api import api_bp
from app.api.auth import jwt_required, role_required
from app.api.errors import error_response, validation_error_response
from app.api.schemas import (
    APIResponse,
    PaginatedResponse,
    StorageProviderResponse,
    StorageSpaceResponse,
    StorageTestRequest,
    StorageTestResponse,
)
from app.models import BackupCopy, db

logger = logging.getLogger(__name__)


# ============================================================================
# Storage Provider Operations
# ============================================================================


@api_bp.route("/v1/storage/providers", methods=["GET"])
@jwt_required
def list_storage_providers(current_user):
    """
    List all storage providers

    Query Parameters:
        provider_type (str): Filter by provider type (local, network, cloud, tape)
        location_type (str): Filter by location type (onsite, offsite, offline)
        is_active (bool): Filter by active status
        is_online (bool): Filter by online status

    Returns:
        200: List of storage providers
        401: Authentication required
    """
    try:
        # Build query to get unique storage providers from BackupCopy
        query = db.session.query(
            BackupCopy.storage_location,
            BackupCopy.location_type,
            db.func.count(BackupCopy.id).label("backup_count"),
            db.func.sum(BackupCopy.backup_size_bytes).label("total_size_bytes"),
            db.func.max(BackupCopy.created_at).label("last_updated"),
        ).group_by(BackupCopy.storage_location, BackupCopy.location_type)

        # Apply filters
        if request.args.get("location_type"):
            query = query.filter(BackupCopy.location_type == request.args.get("location_type"))

        providers = query.all()

        # Convert to response format
        provider_list = []
        for idx, provider in enumerate(providers, start=1):
            provider_data = {
                "id": idx,
                "name": os.path.basename(provider.storage_location) or provider.storage_location,
                "provider_type": "local" if not provider.storage_location.startswith("\\\\") else "network",
                "location_type": provider.location_type,
                "connection_string": provider.storage_location,
                "capacity_bytes": None,
                "used_bytes": provider.total_size_bytes,
                "is_online": True,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "last_verified": provider.last_updated,
            }
            provider_list.append(provider_data)

        response = APIResponse(success=True, data=provider_list)

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error listing storage providers: {e}", exc_info=True)
        return error_response(500, "Failed to list storage providers", "INTERNAL_ERROR")


@api_bp.route("/v1/storage/providers/<int:provider_id>", methods=["GET"])
@jwt_required
def get_storage_provider(current_user, provider_id):
    """
    Get storage provider details

    Path Parameters:
        provider_id (int): Storage provider ID

    Returns:
        200: Storage provider details
        404: Storage provider not found
    """
    try:
        # This is a simplified implementation
        # In production, you would have a proper StorageProvider table
        return error_response(501, "Storage provider details not implemented", "NOT_IMPLEMENTED")

    except Exception as e:
        logger.error(f"Error getting storage provider {provider_id}: {e}", exc_info=True)
        return error_response(500, "Failed to get storage provider", "INTERNAL_ERROR")


# ============================================================================
# Storage Testing
# ============================================================================


@api_bp.route("/v1/storage/test", methods=["POST"])
@jwt_required
@role_required("admin", "operator")
def test_storage_connection(current_user):
    """
    Test storage connection

    Request Body:
    {
        "provider_type": "network",
        "connection_string": "\\\\server\\backup",
        "credentials": {
            "username": "backup_user",
            "password": "password"
        }
    }

    Returns:
        200: Test completed (check success field in response)
        400: Invalid request data
        401: Authentication required
        403: Insufficient permissions
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return validation_error_response({"_error": "Request body is required"})

        test_data = StorageTestRequest(**data)

        # Perform connection test
        test_result = _perform_storage_test(test_data)

        logger.info(
            f"Storage connection test by {current_user.username}: "
            f"{test_data.provider_type} - {test_data.connection_string} - "
            f"Result: {'Success' if test_result.success else 'Failed'}"
        )

        response = APIResponse(success=True, message="Storage connection test completed", data=test_result.model_dump())

        return jsonify(response.model_dump()), 200

    except ValidationError as e:
        logger.warning(f"Validation error in test_storage_connection: {e}")
        return validation_error_response(e.errors())
    except Exception as e:
        logger.error(f"Error testing storage connection: {e}", exc_info=True)
        return error_response(500, "Failed to test storage connection", "INTERNAL_ERROR")


def _perform_storage_test(test_data: StorageTestRequest) -> StorageTestResponse:
    """
    Perform actual storage connection test

    Args:
        test_data: Storage test request data

    Returns:
        Storage test response
    """
    import time

    start_time = time.time()
    result = StorageTestResponse(
        success=False,
        provider_type=test_data.provider_type,
        connection_string=test_data.connection_string,
        accessible=False,
        writable=False,
        total_space_bytes=None,
        free_space_bytes=None,
        latency_ms=None,
        error_message=None,
    )

    try:
        path = test_data.connection_string

        # Test accessibility
        if os.path.exists(path):
            result.accessible = True

            # Test writability
            test_file = os.path.join(path, ".storage_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                result.writable = True
            except Exception as e:
                logger.warning(f"Storage write test failed: {e}")
                result.writable = False

            # Get space information
            try:
                stat = os.statvfs(path)
                result.total_space_bytes = stat.f_blocks * stat.f_frsize
                result.free_space_bytes = stat.f_bavail * stat.f_frsize
            except Exception as e:
                logger.warning(f"Failed to get storage space info: {e}")

            result.success = True

        else:
            result.error_message = "Storage path does not exist or is not accessible"

    except Exception as e:
        result.error_message = str(e)
        logger.error(f"Storage test error: {e}", exc_info=True)

    # Calculate latency
    result.latency_ms = (time.time() - start_time) * 1000

    return result


# ============================================================================
# Storage Space Information
# ============================================================================


@api_bp.route("/v1/storage/<int:storage_id>/space", methods=["GET"])
@jwt_required
def get_storage_space(current_user, storage_id):
    """
    Get storage space information

    Path Parameters:
        storage_id (int): Storage ID (simplified - uses backup copy location)

    Returns:
        200: Storage space information
        404: Storage not found
    """
    try:
        # Get storage location from BackupCopy
        backup_copy = db.session.get(BackupCopy, storage_id)

        if not backup_copy:
            return error_response(404, "Storage not found", "NOT_FOUND")

        # Get space information
        storage_path = backup_copy.storage_location
        backup_count = BackupCopy.query.filter_by(storage_location=storage_path).count()
        total_used = (
            db.session.query(db.func.sum(BackupCopy.backup_size_bytes)).filter_by(storage_location=storage_path).scalar() or 0
        )

        # Get filesystem space information
        total_bytes = None
        free_bytes = None
        try:
            if os.path.exists(storage_path):
                stat = os.statvfs(storage_path)
                total_bytes = stat.f_blocks * stat.f_frsize
                free_bytes = stat.f_bavail * stat.f_frsize
        except Exception as e:
            logger.warning(f"Failed to get filesystem space info: {e}")

        # Calculate utilization
        utilization = None
        if total_bytes and total_bytes > 0:
            utilization = ((total_bytes - free_bytes) / total_bytes) * 100

        response_data = {
            "id": storage_id,
            "name": os.path.basename(storage_path) or storage_path,
            "provider_type": "local" if not storage_path.startswith("\\\\") else "network",
            "total_bytes": total_bytes,
            "used_bytes": total_used,
            "free_bytes": free_bytes,
            "utilization_percent": round(utilization, 2) if utilization else None,
            "backup_count": backup_count,
            "last_updated": datetime.now(timezone.utc),
        }

        response = APIResponse(success=True, data=response_data)

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error getting storage space for storage {storage_id}: {e}", exc_info=True)
        return error_response(500, "Failed to get storage space information", "INTERNAL_ERROR")


@api_bp.route("/v1/storage/<int:storage_id>/backups", methods=["GET"])
@jwt_required
def list_storage_backups(current_user, storage_id):
    """
    List backups on specific storage

    Path Parameters:
        storage_id (int): Storage ID

    Query Parameters:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 20, max: 100)

    Returns:
        200: List of backups on storage
        404: Storage not found
    """
    try:
        # Get storage location from BackupCopy
        storage_ref = db.session.get(BackupCopy, storage_id)

        if not storage_ref:
            return error_response(404, "Storage not found", "NOT_FOUND")

        storage_path = storage_ref.storage_location

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        page_size = min(request.args.get("page_size", 20, type=int), 100)

        # Query backups on this storage
        query = BackupCopy.query.filter_by(storage_location=storage_path)

        # Order by creation date (descending)
        query = query.order_by(db.desc(BackupCopy.created_at))

        # Paginate
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        # Convert to response format
        backups = []
        for backup in pagination.items:
            backup_data = {
                "id": backup.id,
                "job_id": backup.job_id,
                "copy_type": backup.copy_type,
                "location_type": backup.location_type,
                "storage_location": backup.storage_location,
                "backup_size_bytes": backup.backup_size_bytes,
                "created_at": backup.created_at.isoformat() if backup.created_at else None,
                "verified_at": backup.verified_at.isoformat() if backup.verified_at else None,
            }
            backups.append(backup_data)

        response = PaginatedResponse(
            success=True, data=backups, total=pagination.total, page=page, page_size=page_size, total_pages=pagination.pages
        )

        return jsonify(response.model_dump()), 200

    except Exception as e:
        logger.error(f"Error listing backups for storage {storage_id}: {e}", exc_info=True)
        return error_response(500, "Failed to list storage backups", "INTERNAL_ERROR")
