"""
Authentication and Authorization Module
Implements Flask-Login and role-based access control (RBAC)
"""

from flask import Blueprint

# Create authentication blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Import routes after blueprint creation to avoid circular imports
from app.auth import routes
