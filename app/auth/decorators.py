"""
Authentication and Authorization Decorators
Role-based access control decorators for views and API endpoints
"""

from datetime import datetime, timezone
from functools import wraps

import jwt
from flask import abort, jsonify, request
from flask_login import current_user, login_user


def login_required(f):
    """
    Require user to be logged in
    Flask-Login already provides this, but we customize for API support
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Check if it's an API request
            if request.path.startswith("/api/"):
                return jsonify({"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Authentication required"}}), 401
            abort(401)
        return f(*args, **kwargs)

    return decorated_function


def role_required(*roles):
    """
    Require user to have one of the specified roles

    Usage:
        @role_required('admin', 'operator')
        def some_view():
            pass

    Args:
        *roles: Variable number of role names (admin, operator, viewer, auditor)
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.path.startswith("/api/"):
                    return jsonify({"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Authentication required"}}), 401
                abort(401)

            if not current_user.has_any_role(*roles):
                if request.path.startswith("/api/"):
                    return (
                        jsonify(
                            {
                                "error": {
                                    "code": "AUTHORIZATION_FAILED",
                                    "message": f'Insufficient permissions. Required roles: {", ".join(roles)}',
                                }
                            }
                        ),
                        403,
                    )
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    """
    Require user to be an admin

    Usage:
        @admin_required
        def admin_only_view():
            pass
    """
    return role_required("admin")(f)


def operator_required(f):
    """
    Require user to be operator or admin

    Usage:
        @operator_required
        def operator_view():
            pass
    """
    return role_required("admin", "operator")(f)


def viewer_required(f):
    """
    Require user to be viewer or above (viewer, operator, admin)

    Usage:
        @viewer_required
        def viewer_view():
            pass
    """
    return role_required("admin", "operator", "viewer")(f)


def auditor_required(f):
    """
    Require user to be auditor or admin

    Usage:
        @auditor_required
        def audit_view():
            pass
    """
    return role_required("admin", "auditor")(f)


def api_token_required(f):
    """
    Require valid API token for API endpoints
    Supports both JWT and session authentication

    Usage:
        @api_token_required
        def api_endpoint():
            pass
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First try session authentication (for web app API calls)
        if current_user.is_authenticated:
            return f(*args, **kwargs)

        # Then try JWT token authentication (for external API calls)
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Authorization header required"}}), 401

        try:
            # Extract token from "Bearer <token>" format
            token_type, token = auth_header.split(" ", 1)
            if token_type.lower() != "bearer":
                return jsonify({"error": {"code": "INVALID_TOKEN_TYPE", "message": "Token type must be Bearer"}}), 401

            # Verify JWT token
            from app.api.auth import verify_jwt_token
            payload = verify_jwt_token(token)
            if payload is None:
                return jsonify({"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired token"}}), 401

            # Log in the user for this request
            from app.models import User
            user = User.query.get(payload.get("user_id"))
            if user and user.is_active:
                login_user(user)
            else:
                return jsonify({"error": {"code": "INVALID_TOKEN", "message": "User not found or inactive"}}), 401

        except ValueError:
            return jsonify({"error": {"code": "INVALID_AUTH_HEADER", "message": "Invalid Authorization header format"}}), 401

        return f(*args, **kwargs)

    return decorated_function


def account_active_required(f):
    """
    Require user account to be active

    Usage:
        @account_active_required
        def some_view():
            pass
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)

        if not current_user.is_active:
            if request.path.startswith("/api/"):
                return jsonify({"error": {"code": "ACCOUNT_INACTIVE", "message": "User account is inactive"}}), 403
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def check_account_locked(user):
    """
    Check if user account is locked due to failed login attempts

    Args:
        user: User model instance

    Returns:
        tuple: (is_locked: bool, remaining_time: int or None)
    """
    if user.account_locked_until is None:
        return False, None

    if user.account_locked_until > datetime.now(timezone.utc):
        remaining_seconds = int((user.account_locked_until - datetime.now(timezone.utc)).total_seconds())
        return True, remaining_seconds

    # Lock has expired, reset it
    return False, None


def permission_required(permission):
    """
    Custom permission checker (for future extension)

    Usage:
        @permission_required('backup.create')
        def create_backup():
            pass

    Note: This is a placeholder for future fine-grained permission system
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            # TODO: Implement fine-grained permission checking
            # For now, we'll use role-based checking

            return f(*args, **kwargs)

        return decorated_function

    return decorator
