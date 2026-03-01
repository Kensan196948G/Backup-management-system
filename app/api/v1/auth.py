"""
API v1 Authentication Endpoints
Provides JWT and API key authentication for REST API
"""

import logging

from flask import Blueprint, jsonify, request

from app.api.auth import (
    authenticate_user,
    generate_jwt_token,
    generate_refresh_token,
    jwt_required,
    refresh_access_token,
)
from app.models import db
from app.models_api_key import ApiKey, RefreshToken
from app.utils.rate_limiter import limit_login_attempts

logger = logging.getLogger(__name__)

# Create Blueprint
auth_bp = Blueprint("auth_api", __name__, url_prefix="/api/v1/auth")


# ============================================================================
# Authentication Endpoints
# ============================================================================


@auth_bp.route("/login", methods=["POST"])
@limit_login_attempts("5 per minute")
def login():
    """
    User login endpoint - returns JWT access and refresh tokens.

    Request Body:
        {
            "username": "string",
            "password": "string"
        }

    Returns:
        {
            "success": true,
            "access_token": "string",
            "refresh_token": "string",
            "expires_in": 3600,
            "token_type": "Bearer",  # nosec B105
            "user": {
                "id": 1,
                "username": "string",
                "role": "string"
            }
        }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "INVALID_REQUEST", "message": "Request body is required"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify({"success": False, "error": "MISSING_CREDENTIALS", "message": "Username and password are required"}),
                400,
            )

        # Authenticate user
        user, error = authenticate_user(username, password)

        if error:
            return jsonify({"success": False, "error": "AUTHENTICATION_FAILED", "message": error}), 401

        # Generate tokens
        access_token = generate_jwt_token(user, expires_in=3600)  # 1 hour
        refresh_token_str = generate_refresh_token(user, expires_in=2592000)  # 30 days

        # Store refresh token in database
        RefreshToken.create_refresh_token(user.id, refresh_token_str, expires_in_days=30)

        logger.info(f"User {username} logged in successfully via API")

        return (
            jsonify(
                {
                    "success": True,
                    "access_token": access_token,
                    "refresh_token": refresh_token_str,
                    "expires_in": 3600,
                    "token_type": "Bearer",  # nosec B105 - not a password, OAuth2 token type string
                    "user": {"id": user.id, "username": user.username, "role": user.role, "email": user.email},
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "INTERNAL_ERROR", "message": "An error occurred during login"}), 500


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    Refresh access token using refresh token.

    Request Body:
        {
            "refresh_token": "string"
        }

    Returns:
        {
            "success": true,
            "access_token": "string",
            "expires_in": 3600,
            "token_type": "Bearer"  # nosec B105
        }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "INVALID_REQUEST", "message": "Request body is required"}), 400

        refresh_token_str = data.get("refresh_token")

        if not refresh_token_str:
            return jsonify({"success": False, "error": "MISSING_TOKEN", "message": "Refresh token is required"}), 400

        # Verify refresh token from database
        refresh_token_obj = RefreshToken.verify_token(refresh_token_str)

        if not refresh_token_obj:
            return jsonify({"success": False, "error": "INVALID_TOKEN", "message": "Invalid or expired refresh token"}), 401

        # Verify JWT refresh token
        new_access_token, error = refresh_access_token(refresh_token_str)

        if error:
            return jsonify({"success": False, "error": "TOKEN_REFRESH_FAILED", "message": error}), 401

        logger.info(f"Access token refreshed for user_id={refresh_token_obj.user_id}")

        return jsonify({"success": True, "access_token": new_access_token, "expires_in": 3600, "token_type": "Bearer"}), 200  # nosec B105

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "INTERNAL_ERROR", "message": "An error occurred during token refresh"}), 500


@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout(current_user):
    """
    Logout endpoint - revokes refresh tokens.

    Headers:
        Authorization: Bearer <access_token>

    Request Body:
        {
            "refresh_token": "string"  (optional)
        }

    Returns:
        {
            "success": true,
            "message": "Logged out successfully"
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        refresh_token_str = data.get("refresh_token")

        if refresh_token_str:
            # Revoke specific refresh token
            refresh_token_obj = RefreshToken.verify_token(refresh_token_str)
            if refresh_token_obj and refresh_token_obj.user_id == current_user.id:
                refresh_token_obj.revoke()
                logger.info(f"Refresh token revoked for user {current_user.username}")
        else:
            # Revoke all refresh tokens for this user
            refresh_tokens = RefreshToken.query.filter_by(user_id=current_user.id, is_revoked=False).all()

            for token in refresh_tokens:
                token.revoke()

            logger.info(f"All refresh tokens revoked for user {current_user.username}")

        return jsonify({"success": True, "message": "Logged out successfully"}), 200

    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "INTERNAL_ERROR", "message": "An error occurred during logout"}), 500


@auth_bp.route("/verify", methods=["GET"])
@jwt_required
def verify(current_user):
    """
    Verify current access token and return user info.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        {
            "success": true,
            "valid": true,
            "user": {
                "id": 1,
                "username": "string",
                "role": "string",
                "email": "string"
            }
        }
    """
    try:
        return (
            jsonify(
                {
                    "success": True,
                    "valid": True,
                    "user": {
                        "id": current_user.id,
                        "username": current_user.username,
                        "role": current_user.role,
                        "email": current_user.email,
                        "is_active": current_user.is_active,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Token verification error: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "INTERNAL_ERROR", "message": "An error occurred during verification"}), 500


# ============================================================================
# API Key Management Endpoints
# ============================================================================


@auth_bp.route("/api-keys", methods=["GET"])
@jwt_required
def list_api_keys(current_user):
    """
    List all API keys for the current user.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        {
            "success": true,
            "api_keys": [
                {
                    "id": 1,
                    "name": "string",
                    "key_prefix": "bms_xxxxx...",
                    "is_active": true,
                    "expires_at": "2025-12-31T23:59:59",
                    "last_used_at": "2025-11-02T10:30:00",
                    "created_at": "2025-11-01T00:00:00"
                }
            ]
        }
    """
    try:
        api_keys = ApiKey.query.filter_by(user_id=current_user.id).order_by(ApiKey.created_at.desc()).all()

        return jsonify({"success": True, "api_keys": [key.to_dict(include_key=True) for key in api_keys]}), 200

    except Exception as e:
        logger.error(f"Error listing API keys: {str(e)}", exc_info=True)
        return (
            jsonify({"success": False, "error": "INTERNAL_ERROR", "message": "An error occurred while listing API keys"}),
            500,
        )


@auth_bp.route("/api-keys", methods=["POST"])
@jwt_required
def create_api_key(current_user):
    """
    Create a new API key for the current user.

    Headers:
        Authorization: Bearer <access_token>

    Request Body:
        {
            "name": "string",
            "expires_in_days": 365  (optional, null for no expiration)
        }

    Returns:
        {
            "success": true,
            "message": "API key created successfully",
            "api_key": "bms_xxxxx...",  # ONLY SHOWN ONCE
            "key_info": {
                "id": 1,
                "name": "string",
                "key_prefix": "bms_xxxxx...",
                "expires_at": "2026-11-02T00:00:00",
                "created_at": "2025-11-02T00:00:00"
            }
        }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "INVALID_REQUEST", "message": "Request body is required"}), 400

        name = data.get("name")
        expires_in_days = data.get("expires_in_days")

        if not name:
            return jsonify({"success": False, "error": "MISSING_NAME", "message": "API key name is required"}), 400

        # Validate expiration days
        if expires_in_days is not None:
            try:
                expires_in_days = int(expires_in_days)
                if expires_in_days < 1 or expires_in_days > 3650:  # Max 10 years
                    raise ValueError()
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "INVALID_EXPIRATION",
                            "message": "Expiration must be between 1 and 3650 days",
                        }
                    ),
                    400,
                )

        # Create API key
        plaintext_key, api_key_obj = ApiKey.create_api_key(user_id=current_user.id, name=name, expires_in_days=expires_in_days)

        logger.info(f"API key '{name}' created for user {current_user.username}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "API key created successfully. Please save it securely - it will not be shown again.",
                    "api_key": plaintext_key,  # ONLY SHOWN ONCE
                    "key_info": api_key_obj.to_dict(include_key=True),
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}", exc_info=True)
        db.session.rollback()
        return (
            jsonify({"success": False, "error": "INTERNAL_ERROR", "message": "An error occurred while creating API key"}),
            500,
        )


@auth_bp.route("/api-keys/<int:key_id>", methods=["DELETE"])
@jwt_required
def revoke_api_key(current_user, key_id):
    """
    Revoke (deactivate) an API key.

    Headers:
        Authorization: Bearer <access_token>

    Path Parameters:
        key_id: API key ID

    Returns:
        {
            "success": true,
            "message": "API key revoked successfully"
        }
    """
    try:
        api_key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first()

        if not api_key:
            return jsonify({"success": False, "error": "NOT_FOUND", "message": "API key not found"}), 404

        api_key.revoke()

        logger.info(f"API key '{api_key.name}' (ID: {key_id}) revoked by user {current_user.username}")

        return jsonify({"success": True, "message": "API key revoked successfully"}), 200

    except Exception as e:
        logger.error(f"Error revoking API key: {str(e)}", exc_info=True)
        return (
            jsonify({"success": False, "error": "INTERNAL_ERROR", "message": "An error occurred while revoking API key"}),
            500,
        )


# ============================================================================
# Password Management Endpoints
# ============================================================================


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required
def change_password(current_user):
    """
    Change password for the current user.

    Headers:
        Authorization: Bearer <access_token>

    Request Body:
        {
            "current_password": "string",
            "new_password": "string"
        }

    Returns:
        {
            "success": true,
            "message": "Password changed successfully"
        }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "INVALID_REQUEST", "message": "Request body is required"}), 400

        current_password = data.get("current_password")
        new_password = data.get("new_password")

        if not current_password or not new_password:
            return (
                jsonify({"success": False, "error": "MISSING_PASSWORDS", "message": "Current and new passwords are required"}),
                400,
            )

        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({"success": False, "error": "INVALID_PASSWORD", "message": "Current password is incorrect"}), 401

        # Validate new password strength
        if len(new_password) < 8:
            return (
                jsonify(
                    {"success": False, "error": "WEAK_PASSWORD", "message": "New password must be at least 8 characters long"}
                ),
                400,
            )

        # Set new password
        current_user.set_password(new_password)
        db.session.commit()

        # Revoke all refresh tokens (force re-login)
        refresh_tokens = RefreshToken.query.filter_by(user_id=current_user.id, is_revoked=False).all()

        for token in refresh_tokens:
            token.revoke()

        logger.info(f"Password changed for user {current_user.username}")

        return (
            jsonify(
                {"success": True, "message": "Password changed successfully. Please log in again with your new password."}
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        db.session.rollback()
        return (
            jsonify({"success": False, "error": "INTERNAL_ERROR", "message": "An error occurred while changing password"}),
            500,
        )
