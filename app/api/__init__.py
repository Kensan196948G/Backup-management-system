"""
REST API Blueprint
Provides RESTful API endpoints for external integrations
API Version: v1
"""

from flask import Blueprint

# Create API blueprint with /api prefix
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Import routes after blueprint creation to avoid circular imports
# Import v1 API routes
from app.api import alerts, backup, dashboard, jobs, media, reports, verification

# Register error handlers
from app.api.errors import register_error_handlers

# Note: v1 auth blueprint is registered separately in app/__init__.py
# to preserve its full URL prefix (/api/v1/auth)


register_error_handlers(api_bp)
