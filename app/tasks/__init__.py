"""
Celery Tasks Module for Backup Management System
Phase 11: Asynchronous Task Processing

This module initializes the Celery application and provides
a factory function for Flask-Celery integration.
"""

import os

from celery import Celery

from app.celery_config import get_celery_config

# Create Celery instance
celery_app = Celery("backup_management")


def init_celery(app=None):
    """
    Initialize Celery with Flask application context.

    This function configures Celery to work with Flask's application
    context, ensuring database and other Flask extensions are available
    within Celery tasks.

    Args:
        app: Flask application instance

    Returns:
        Configured Celery application instance
    """
    # Get configuration based on environment
    env = os.environ.get("FLASK_ENV", "development")
    config_class = get_celery_config(env)

    # Update Celery configuration
    celery_app.config_from_object(config_class)

    if app is not None:
        # Update Celery config from Flask config
        celery_app.conf.update(
            broker_url=app.config.get("CELERY_BROKER_URL", config_class.broker_url),
            result_backend=app.config.get("CELERY_RESULT_BACKEND", config_class.result_backend),
        )

        class ContextTask(celery_app.Task):
            """Task class that wraps task execution in Flask application context."""

            abstract = True

            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery_app.Task = ContextTask

        # Store Flask app reference
        celery_app.flask_app = app

    return celery_app


def get_celery_app():
    """Get the Celery application instance."""
    return celery_app


# Import tasks to register them with Celery
# These imports must be at the bottom to avoid circular imports
def register_tasks():
    """Register all Celery tasks."""
    from app.tasks import (
        cleanup_tasks,
        email_tasks,
        notification_tasks,
        report_tasks,
        verification_tasks,
    )

    return {
        "email_tasks": email_tasks,
        "notification_tasks": notification_tasks,
        "report_tasks": report_tasks,
        "verification_tasks": verification_tasks,
        "cleanup_tasks": cleanup_tasks,
    }
