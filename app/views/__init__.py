"""
Web Views Module
Provides web interface for Backup Management System

Blueprints:
- dashboard: Dashboard and overview
- jobs: Backup job management
- media: Offline media management
- verification: Verification test management
- reports: Report viewing and generation
- settings: System settings and configuration
"""

from flask import Blueprint

# Create blueprints
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")
jobs_bp = Blueprint("jobs", __name__, url_prefix="/jobs")
media_bp = Blueprint("media", __name__, url_prefix="/media")
verification_bp = Blueprint("verification", __name__, url_prefix="/verification")
reports_bp = Blueprint("reports", __name__, url_prefix="/reports")
settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

# Import routes after blueprint creation to avoid circular imports


def register_blueprints(app):
    """
    Register all view blueprints with the Flask app

    Args:
        app: Flask application instance
    """
    from app.auth import auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
