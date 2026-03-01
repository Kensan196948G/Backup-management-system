"""
API Error Handlers
Standardized error response format for REST API
"""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def error_response(status_code, message, error_code=None, details=None):
    """
    Create standardized error response

    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Application-specific error code
        details: Additional error details (optional)

    Returns:
        JSON response with error information
    """
    payload = {"error": {"code": error_code or f"HTTP_{status_code}", "message": message}}

    if details:
        payload["error"]["details"] = details

    return jsonify(payload), status_code


def validation_error_response(errors):
    """
    Create validation error response

    Args:
        errors: Dictionary of field validation errors

    Returns:
        JSON response with validation errors
    """
    return error_response(400, "Validation failed", "VALIDATION_ERROR", {"fields": errors})


def register_error_handlers(blueprint):
    """
    Register error handlers for API blueprint

    Args:
        blueprint: Flask blueprint instance
    """

    @blueprint.errorhandler(400)
    def bad_request(e):
        """Handle 400 Bad Request"""
        return error_response(400, str(e), "BAD_REQUEST")

    @blueprint.errorhandler(401)
    def unauthorized(e):
        """Handle 401 Unauthorized"""
        return error_response(401, "Authentication required", "AUTHENTICATION_REQUIRED")

    @blueprint.errorhandler(403)
    def forbidden(e):
        """Handle 403 Forbidden"""
        return error_response(403, "Insufficient permissions", "AUTHORIZATION_FAILED")

    @blueprint.errorhandler(404)
    def not_found(e):
        """Handle 404 Not Found"""
        return error_response(404, "Resource not found", "RESOURCE_NOT_FOUND")

    @blueprint.errorhandler(405)
    def method_not_allowed(e):
        """Handle 405 Method Not Allowed"""
        return error_response(405, "Method not allowed", "METHOD_NOT_ALLOWED")

    @blueprint.errorhandler(409)
    def conflict(e):
        """Handle 409 Conflict"""
        return error_response(409, str(e), "RESOURCE_CONFLICT")

    @blueprint.errorhandler(500)
    def internal_server_error(e):
        """Handle 500 Internal Server Error"""
        logger.error(f"Internal server error: {str(e)}", exc_info=True)
        return error_response(500, "Internal server error", "INTERNAL_ERROR")

    @blueprint.errorhandler(Exception)
    def handle_unexpected_error(e):
        """Handle unexpected errors"""
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)

        # Return different response for HTTP exceptions
        if isinstance(e, HTTPException):
            return error_response(e.code, e.description, f"HTTP_{e.code}")

        return error_response(500, "An unexpected error occurred", "UNEXPECTED_ERROR")
