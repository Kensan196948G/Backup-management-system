"""
Security Headers

Implements security headers and Flask-Talisman integration:
- HSTS (HTTP Strict Transport Security)
- CSP (Content Security Policy)
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy
"""
import logging
from typing import Dict

from flask import Flask

logger = logging.getLogger(__name__)


class SecurityHeaders:
    """
    Manages security headers for Flask application.

    Implements OWASP recommended security headers.
    """

    def __init__(self, app: Flask = None):
        """
        Initialize security headers.

        Args:
            app: Flask application instance
        """
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """
        Initialize security headers with Flask app.

        Args:
            app: Flask application instance
        """
        self.app = app

        # Register after_request handler
        @app.after_request
        def add_security_headers(response):
            """Add security headers to response"""
            headers = self._get_security_headers()

            for header, value in headers.items():
                response.headers[header] = value

            return response

        logger.info("Security headers initialized")

    def _get_security_headers(self) -> Dict[str, str]:
        """
        Get security headers configuration.

        Returns:
            Dictionary of header name -> value
        """
        headers = {}

        # HSTS - HTTP Strict Transport Security
        if self.app.config.get("ENABLE_HSTS", True):
            hsts_age = self.app.config.get("HSTS_MAX_AGE", 31536000)  # 1 year
            headers["Strict-Transport-Security"] = f"max-age={hsts_age}; includeSubDomains"

        # CSP - Content Security Policy
        if self.app.config.get("ENABLE_CSP", True):
            csp = self._build_csp()
            headers["Content-Security-Policy"] = csp

        # X-Frame-Options - Clickjacking protection
        headers["X-Frame-Options"] = "SAMEORIGIN"

        # X-Content-Type-Options - MIME sniffing prevention
        headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection - XSS filter (legacy browsers)
        headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy - Control referrer information
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy - Control browser features
        permissions = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
        ]
        headers["Permissions-Policy"] = ", ".join(permissions)

        return headers

    def _build_csp(self) -> str:
        """
        Build Content Security Policy.

        Returns:
            CSP header value
        """
        # Get custom CSP from config or use defaults
        csp_config = self.app.config.get("CSP_DIRECTIVES", {})

        # Default CSP directives
        default_directives = {
            "default-src": ["'self'"],
            "script-src": [
                "'self'",
                "'unsafe-inline'",  # For inline scripts (should be minimized)
                "https://cdn.jsdelivr.net",  # For CDN resources
            ],
            "style-src": [
                "'self'",
                "'unsafe-inline'",  # For inline styles
                "https://cdn.jsdelivr.net",
            ],
            "img-src": [
                "'self'",
                "data:",  # For data URIs
                "https:",
            ],
            "font-src": [
                "'self'",
                "https://cdn.jsdelivr.net",
            ],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'self'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "object-src": ["'none'"],
        }

        # Merge with custom directives
        directives = {**default_directives, **csp_config}

        # Build CSP string
        csp_parts = []
        for directive, sources in directives.items():
            sources_str = " ".join(sources)
            csp_parts.append(f"{directive} {sources_str}")

        return "; ".join(csp_parts)


def init_security_headers(app: Flask):
    """
    Initialize security headers for Flask app.

    Args:
        app: Flask application instance
    """
    security_headers = SecurityHeaders(app)
    return security_headers


def init_talisman(app: Flask):
    """
    Initialize Flask-Talisman for enhanced security.

    Args:
        app: Flask application instance
    """
    try:
        from flask_talisman import Talisman

        # Only enable in production
        if app.config.get("FLASK_ENV") == "production":
            # Configure Talisman
            talisman_config = {
                "force_https": app.config.get("FORCE_HTTPS", True),
                "strict_transport_security": True,
                "strict_transport_security_max_age": 31536000,
                "strict_transport_security_include_subdomains": True,
                "content_security_policy": {
                    "default-src": "'self'",
                    "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
                    "style-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
                    "img-src": ["'self'", "data:", "https:"],
                    "font-src": ["'self'", "https://cdn.jsdelivr.net"],
                },
                "content_security_policy_nonce_in": ["script-src"],
                "feature_policy": {
                    "geolocation": "'none'",
                    "microphone": "'none'",
                    "camera": "'none'",
                },
                "frame_options": "SAMEORIGIN",
                "frame_options_allow_from": None,
                "referrer_policy": "strict-origin-when-cross-origin",
            }

            Talisman(app, **talisman_config)
            logger.info("Flask-Talisman initialized")
        else:
            logger.info("Flask-Talisman disabled in development mode")
            # Use basic security headers instead
            init_security_headers(app)

    except ImportError:
        logger.warning("Flask-Talisman not installed, using basic security headers")
        init_security_headers(app)


# CORS configuration helper
def configure_cors(app: Flask):
    """
    Configure CORS settings.

    Args:
        app: Flask application instance
    """
    try:
        from flask_cors import CORS

        # Get allowed origins from config
        allowed_origins = app.config.get("CORS_ORIGINS", ["http://localhost:3000"])

        CORS(
            app,
            origins=allowed_origins,
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["Content-Type", "Authorization", "X-Correlation-ID"],
            expose_headers=["X-Correlation-ID"],
            supports_credentials=True,
            max_age=3600,
        )

        logger.info(f"CORS configured for origins: {allowed_origins}")

    except ImportError:
        logger.warning("Flask-CORS not installed")


# Request validation helpers
def validate_content_type(allowed_types: list = None):
    """
    Decorator to validate request content type.

    Args:
        allowed_types: List of allowed content types

    Example:
        @validate_content_type(['application/json'])
        def my_endpoint():
            pass
    """
    if allowed_types is None:
        allowed_types = ["application/json"]

    def decorator(f):
        from functools import wraps

        from flask import jsonify, request

        @wraps(f)
        def wrapper(*args, **kwargs):
            content_type = request.content_type

            if content_type not in allowed_types:
                return (
                    jsonify(
                        {
                            "error": "Invalid content type",
                            "allowed": allowed_types,
                            "received": content_type,
                        }
                    ),
                    415,
                )

            return f(*args, **kwargs)

        return wrapper

    return decorator


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input.

    Args:
        value: Input value
        max_length: Maximum allowed length

    Returns:
        Sanitized value
    """
    if not value:
        return ""

    # Truncate to max length
    value = value[:max_length]

    # Remove null bytes
    value = value.replace("\x00", "")

    # Strip whitespace
    value = value.strip()

    return value


def validate_file_upload(filename: str, allowed_extensions: set = None) -> bool:
    """
    Validate uploaded file.

    Args:
        filename: Name of uploaded file
        allowed_extensions: Set of allowed file extensions

    Returns:
        True if file is valid
    """
    if not filename:
        return False

    if allowed_extensions is None:
        allowed_extensions = {"txt", "pdf", "csv", "json", "xlsx"}

    # Check file extension
    if "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_extensions
