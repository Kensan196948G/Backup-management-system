"""
API Authentication Module
Provides JWT-based authentication and API key validation for REST API endpoints

Supports:
- JWT token-based authentication (short-lived access tokens)
- API key authentication (long-lived tokens for service accounts)
- Role-based access control (RBAC) integration
- Token refresh mechanism
"""

import logging
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Tuple

import jwt
from flask import current_app, jsonify, request
from werkzeug.security import check_password_hash

from app.models import User, db

logger = logging.getLogger(__name__)


# ============================================================================
# JWT Token Management
# ============================================================================


def generate_jwt_token(user: User, expires_in: int = 3600) -> str:
    """
    Generate JWT access token for authenticated user

    Args:
        user: User object
        expires_in: Token expiration time in seconds (default: 1 hour)

    Returns:
        JWT token string
    """
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        "iat": datetime.utcnow(),
        "type": "access",
    }

    token = jwt.encode(payload, current_app.config.get("SECRET_KEY", "dev-secret-key"), algorithm="HS256")

    return token


def generate_refresh_token(user: User, expires_in: int = 2592000) -> str:
    """
    Generate JWT refresh token for token renewal

    Args:
        user: User object
        expires_in: Token expiration time in seconds (default: 30 days)

    Returns:
        JWT refresh token string
    """
    payload = {
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    token = jwt.encode(payload, current_app.config.get("SECRET_KEY", "dev-secret-key"), algorithm="HS256")

    return token


def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verify and decode JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, current_app.config.get("SECRET_KEY", "dev-secret-key"), algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


# ============================================================================
# API Key Management
# ============================================================================


def generate_api_key() -> str:
    """
    Generate secure random API key

    Returns:
        API key string (64 characters)
    """
    return secrets.token_urlsafe(48)  # Generates ~64 character string


def verify_api_key(api_key: str) -> Optional[User]:
    """
    Verify API key and return associated user

    Note: In production, API keys should be stored in a separate table
    with hashing. This is a simplified implementation.

    Args:
        api_key: API key string

    Returns:
        User object if valid, None otherwise
    """
    from app.models_api_key import ApiKey

    api_key_obj = ApiKey.verify_key(api_key)
    if api_key_obj is not None:
        return api_key_obj.user
    return None


# ============================================================================
# Authentication Decorators
# ============================================================================


def jwt_required(f):
    """
    Decorator to require JWT authentication for API endpoints

    Usage:
        @api_bp.route('/protected')
        @jwt_required
        def protected_endpoint(current_user):
            return jsonify({'message': f'Hello {current_user.username}'})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return (
                jsonify({"success": False, "error": "AUTHENTICATION_REQUIRED", "message": "Authentication token is missing"}),
                401,
            )

        # Verify token
        payload = verify_jwt_token(token)
        if not payload:
            return (
                jsonify({"success": False, "error": "INVALID_TOKEN", "message": "Invalid or expired authentication token"}),
                401,
            )

        # Check token type
        if payload.get("type") != "access":
            return jsonify({"success": False, "error": "INVALID_TOKEN_TYPE", "message": "Invalid token type"}), 401

        # Get user from database
        user = User.query.get(payload["user_id"])
        if not user or not user.is_active:
            return (
                jsonify({"success": False, "error": "USER_INACTIVE", "message": "User account is inactive or not found"}),
                401,
            )

        # Pass user to the decorated function
        return f(current_user=user, *args, **kwargs)

    return decorated_function


def api_key_required(f):
    """
    Decorator to require API key authentication for API endpoints

    Usage:
        @api_bp.route('/webhook')
        @api_key_required
        def webhook_endpoint(current_user):
            return jsonify({'message': 'Webhook received'})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = None

        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return jsonify({"success": False, "error": "API_KEY_REQUIRED", "message": "API key is missing"}), 401

        # Verify API key
        user = verify_api_key(api_key)
        if not user:
            return jsonify({"success": False, "error": "INVALID_API_KEY", "message": "Invalid API key"}), 401

        # Pass user to the decorated function
        return f(current_user=user, *args, **kwargs)

    return decorated_function


def auth_required(f):
    """
    Decorator to require either JWT or API key authentication

    Tries JWT first, then API key

    Usage:
        @api_bp.route('/flexible')
        @auth_required
        def flexible_endpoint(current_user):
            return jsonify({'message': f'Hello {current_user.username}'})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = None

        # Try JWT authentication first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = verify_jwt_token(token)
            if payload and payload.get("type") == "access":
                user = User.query.get(payload["user_id"])

        # Try API key authentication if JWT failed
        if not user:
            api_key = request.headers.get("X-API-Key")
            if api_key:
                user = verify_api_key(api_key)

        if not user or not user.is_active:
            return (
                jsonify({"success": False, "error": "AUTHENTICATION_REQUIRED", "message": "Valid authentication is required"}),
                401,
            )

        # Pass user to the decorated function
        return f(current_user=user, *args, **kwargs)

    return decorated_function


def role_required(*allowed_roles):
    """
    Decorator to require specific role(s) for API endpoints

    Must be used after @auth_required, @jwt_required, or @api_key_required

    Usage:
        @api_bp.route('/admin')
        @jwt_required
        @role_required('admin')
        def admin_endpoint(current_user):
            return jsonify({'message': 'Admin access granted'})
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(current_user=None, *args, **kwargs):
            if not current_user:
                return (
                    jsonify({"success": False, "error": "AUTHENTICATION_REQUIRED", "message": "Authentication is required"}),
                    401,
                )

            if current_user.role not in allowed_roles:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "INSUFFICIENT_PERMISSIONS",
                            "message": f'This action requires one of the following roles: {", ".join(allowed_roles)}',
                        }
                    ),
                    403,
                )

            return f(current_user=current_user, *args, **kwargs)

        return decorated_function

    return decorator


# ============================================================================
# Authentication Endpoints Helper Functions
# ============================================================================


def authenticate_user(username: str, password: str) -> Tuple[Optional[User], Optional[str]]:
    """
    Authenticate user with username and password

    Args:
        username: Username
        password: Password

    Returns:
        Tuple of (User object, error message)
    """
    user = User.query.filter_by(username=username).first()

    if not user:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return None, "Invalid username or password"

    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {username}")
        return None, "User account is inactive"

    if not user.check_password(password):
        logger.warning(f"Failed login attempt for user: {username}")
        # Increment failed login attempts
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.utcnow()

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.session.commit()
            logger.warning(f"User account locked due to failed login attempts: {username}")
            return None, "Account locked due to multiple failed login attempts"

        db.session.commit()
        return None, "Invalid username or password"

    # Check if account is locked
    if user.account_locked_until and user.account_locked_until > datetime.utcnow():
        remaining = (user.account_locked_until - datetime.utcnow()).total_seconds() / 60
        return None, f"Account is locked. Try again in {int(remaining)} minutes"

    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    user.account_locked_until = None
    db.session.commit()

    logger.info(f"Successful login for user: {username}")
    return user, None


def refresh_access_token(refresh_token: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate new access token from refresh token

    Args:
        refresh_token: JWT refresh token

    Returns:
        Tuple of (new access token, error message)
    """
    payload = verify_jwt_token(refresh_token)

    if not payload:
        return None, "Invalid or expired refresh token"

    if payload.get("type") != "refresh":
        return None, "Invalid token type"

    user = User.query.get(payload["user_id"])
    if not user or not user.is_active:
        return None, "User account is inactive or not found"

    # Generate new access token
    access_token = generate_jwt_token(user)

    return access_token, None
