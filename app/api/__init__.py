"""
REST API Blueprint
Provides RESTful API endpoints for external integrations
API Version: v1
"""

from flask import Blueprint

# Create API blueprint with /api prefix
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Import routes after blueprint creation to avoid circular imports
from app.api import alerts  # noqa: F401, E402
from app.api import auth  # noqa: F401, E402
from app.api import backup  # noqa: F401, E402
from app.api import dashboard  # noqa: F401, E402
from app.api import jobs  # noqa: F401, E402
from app.api import media  # noqa: F401, E402
from app.api import reports  # noqa: F401, E402
from app.api import verification  # noqa: F401, E402

# Register error handlers
from app.api.errors import register_error_handlers  # noqa: E402

# Note: v1 auth blueprint is registered separately in app/__init__.py
# to preserve its full URL prefix (/api/v1/auth)


register_error_handlers(api_bp)
