"""
Rate Limiting

Implements rate limiting to prevent abuse:
- Flask-Limiter integration
- IP-based rate limiting
- Endpoint-specific limits
- Custom rate limit strategies
- Rate limit exemptions
"""
import logging
from functools import wraps
from typing import Callable

from flask import Flask, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)


def get_request_identifier():
    """
    Get identifier for rate limiting.

    Returns:
        Identifier string (IP address or user ID)
    """
    # Prefer user ID if authenticated
    if hasattr(g, "user") and g.user:
        return f"user_{g.user.id}"

    # Fall back to IP address
    return get_remote_address()


class RateLimiter:
    """
    Rate limiting manager.

    Provides configurable rate limiting for API endpoints.
    """

    def __init__(self, app: Flask = None):
        """
        Initialize rate limiter.

        Args:
            app: Flask application instance
        """
        self.limiter = None
        self.app = app

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """
        Initialize rate limiter with Flask app.

        Args:
            app: Flask application instance
        """
        self.app = app

        # Get configuration
        enabled = app.config.get("RATELIMIT_ENABLED", True)

        if not enabled:
            logger.info("Rate limiting disabled")
            return

        # Configure limiter
        storage_uri = app.config.get("RATELIMIT_STORAGE_URL", "memory://")

        self.limiter = Limiter(
            app=app,
            key_func=get_request_identifier,
            storage_uri=storage_uri,
            default_limits=app.config.get("RATELIMIT_DEFAULT", ["200 per day", "50 per hour"]),
            strategy="fixed-window",
            headers_enabled=True,
            swallow_errors=True,  # Don't break app if rate limiting fails
        )

        # Add exemption for health checks
        @self.limiter.request_filter
        def exempt_health_check():
            """Exempt health check endpoint from rate limiting"""
            return request.endpoint == "health_check"

        # Add custom headers to responses
        @app.after_request
        def add_rate_limit_headers(response):
            """Add rate limit info to response headers"""
            return response

        logger.info(f"Rate limiting initialized with storage: {storage_uri}")

    def limit(self, limit_string: str):
        """
        Rate limit decorator.

        Args:
            limit_string: Rate limit specification (e.g., "10 per minute")

        Example:
            @rate_limiter.limit("5 per minute")
            def my_endpoint():
                pass
        """
        if self.limiter:
            return self.limiter.limit(limit_string)
        else:
            # No-op decorator if rate limiting disabled
            def decorator(f):
                return f

            return decorator

    def exempt(self, f: Callable) -> Callable:
        """
        Exempt endpoint from rate limiting.

        Args:
            f: Function to exempt

        Returns:
            Decorated function
        """
        if self.limiter:
            return self.limiter.exempt(f)
        else:
            return f


# Global rate limiter instance
rate_limiter = RateLimiter()


def init_rate_limiting(app: Flask):
    """
    Initialize rate limiting for Flask app.

    Args:
        app: Flask application instance
    """
    rate_limiter.init_app(app)
    return rate_limiter


# Predefined rate limit decorators


def limit_api_calls(limit: str = "60 per minute"):
    """
    Decorator for standard API endpoints.

    Args:
        limit: Rate limit string
    """
    return rate_limiter.limit(limit)


def limit_login_attempts(limit: str = "5 per minute"):
    """
    Decorator for login endpoint.

    Args:
        limit: Rate limit string
    """
    return rate_limiter.limit(limit)


def limit_registration(limit: str = "3 per hour"):
    """
    Decorator for registration endpoint.

    Args:
        limit: Rate limit string
    """
    return rate_limiter.limit(limit)


def limit_password_reset(limit: str = "3 per hour"):
    """
    Decorator for password reset endpoint.

    Args:
        limit: Rate limit string
    """
    return rate_limiter.limit(limit)


def limit_file_upload(limit: str = "10 per hour"):
    """
    Decorator for file upload endpoint.

    Args:
        limit: Rate limit string
    """
    return rate_limiter.limit(limit)


def limit_report_generation(limit: str = "20 per hour"):
    """
    Decorator for report generation endpoint.

    Args:
        limit: Rate limit string
    """
    return rate_limiter.limit(limit)


def limit_backup_execution(limit: str = "100 per hour"):
    """
    Decorator for backup execution endpoint.

    Args:
        limit: Rate limit string
    """
    return rate_limiter.limit(limit)


# Advanced rate limiting


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on system load.

    Implements more sophisticated rate limiting strategies.
    """

    def __init__(self):
        """Initialize adaptive rate limiter"""
        self.base_limits = {
            "low": "100 per minute",
            "medium": "50 per minute",
            "high": "20 per minute",
        }

    def get_current_limit(self) -> str:
        """
        Get current rate limit based on system load.

        Returns:
            Rate limit string
        """
        # This is a placeholder - actual implementation would check system metrics
        load = self._check_system_load()

        if load < 0.5:
            return self.base_limits["low"]
        elif load < 0.8:
            return self.base_limits["medium"]
        else:
            return self.base_limits["high"]

    def _check_system_load(self) -> float:
        """
        Check current system load.

        Returns:
            Load factor (0-1)
        """
        # Placeholder - would integrate with actual monitoring
        return 0.3


# Exemption helpers


def is_exempt_ip(ip: str) -> bool:
    """
    Check if IP is exempt from rate limiting.

    Args:
        ip: IP address

    Returns:
        True if exempt
    """
    # Get exempt IPs from config
    from flask import current_app

    exempt_ips = current_app.config.get("RATELIMIT_EXEMPT_IPS", [])
    return ip in exempt_ips


def is_admin_user() -> bool:
    """
    Check if current user is admin.

    Returns:
        True if admin
    """
    if hasattr(g, "user") and g.user:
        return g.user.role == "admin"
    return False


def exempt_admin(f: Callable) -> Callable:
    """
    Decorator to exempt admin users from rate limiting.

    Args:
        f: Function to decorate

    Returns:
        Decorated function
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        if is_admin_user():
            # Bypass rate limiting for admin
            return f(*args, **kwargs)
        else:
            # Apply rate limiting
            return rate_limiter.limit("60 per minute")(f)(*args, **kwargs)

    return wrapper


# Error handlers


def handle_rate_limit_exceeded(e):
    """
    Handle rate limit exceeded error.

    Args:
        e: RateLimitExceeded exception

    Returns:
        JSON response with error
    """
    from flask import jsonify

    logger.warning(f"Rate limit exceeded: {request.remote_addr} on {request.endpoint}")

    return (
        jsonify(
            {
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": e.description,
            }
        ),
        429,
    )


def register_rate_limit_handlers(app: Flask):
    """
    Register rate limit error handlers.

    Args:
        app: Flask application instance
    """
    from flask_limiter.errors import RateLimitExceeded

    app.register_error_handler(RateLimitExceeded, handle_rate_limit_exceeded)
    logger.info("Rate limit error handlers registered")
