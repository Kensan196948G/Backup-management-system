"""
Celery Configuration for Backup Management System
Phase 11: Asynchronous Task Processing

This module configures Celery for background task processing,
using Redis as both message broker and result backend.
"""
import os
from datetime import timedelta

from kombu import Exchange, Queue


class CeleryConfig:
    """Celery configuration class"""

    # Broker settings (Redis)
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    # Task settings
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = os.environ.get("TZ", "Asia/Tokyo")
    enable_utc = True

    # Task result expiration (24 hours)
    result_expires = timedelta(hours=24)

    # Task acknowledgement settings
    task_acks_late = True  # Acknowledge tasks after execution
    task_reject_on_worker_lost = True  # Requeue tasks if worker dies

    # Worker settings
    worker_prefetch_multiplier = 4  # Number of tasks to prefetch
    worker_max_tasks_per_child = 1000  # Restart worker after N tasks

    # Rate limiting
    task_annotations = {
        "app.tasks.email_tasks.send_email": {"rate_limit": "10/m"},  # 10 emails per minute
        "app.tasks.notification_tasks.send_teams_notification": {"rate_limit": "30/m"},
    }

    # Task routes - different queues for different task types
    task_routes = {
        "app.tasks.email_tasks.*": {"queue": "email"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
        "app.tasks.verification_tasks.*": {"queue": "verification"},
        "app.tasks.cleanup_tasks.*": {"queue": "maintenance"},
    }

    # Queue definitions
    task_queues = (
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("email", Exchange("email"), routing_key="email"),
        Queue("notifications", Exchange("notifications"), routing_key="notifications"),
        Queue("reports", Exchange("reports"), routing_key="reports"),
        Queue("verification", Exchange("verification"), routing_key="verification"),
        Queue("maintenance", Exchange("maintenance"), routing_key="maintenance"),
    )

    # Default queue
    task_default_queue = "default"
    task_default_exchange = "default"
    task_default_routing_key = "default"

    # Task time limits
    task_soft_time_limit = 300  # 5 minutes soft limit
    task_time_limit = 600  # 10 minutes hard limit

    # Beat scheduler settings (periodic tasks)
    beat_schedule = {
        # Compliance check every hour
        "check-compliance-hourly": {
            "task": "app.tasks.maintenance_tasks.check_compliance",
            "schedule": timedelta(hours=1),
        },
        # Daily report generation at 8:00 AM
        "generate-daily-report": {
            "task": "app.tasks.report_tasks.generate_daily_report",
            "schedule": timedelta(days=1),
            "options": {"expires": 3600},  # Expire after 1 hour
        },
        # Cleanup old logs at 3:00 AM daily
        "cleanup-old-logs": {
            "task": "app.tasks.cleanup_tasks.cleanup_old_logs",
            "schedule": timedelta(days=1),
        },
        # Check offline media status daily at 9:00 AM
        "check-offline-media": {
            "task": "app.tasks.maintenance_tasks.check_offline_media",
            "schedule": timedelta(days=1),
        },
    }

    # Result backend settings
    result_extended = True  # Store additional task metadata

    # Security settings
    broker_use_ssl = os.environ.get("CELERY_BROKER_USE_SSL", "false").lower() == "true"
    redis_backend_use_ssl = os.environ.get("CELERY_REDIS_USE_SSL", "false").lower() == "true"

    # Retry settings
    broker_connection_retry_on_startup = True
    broker_connection_max_retries = 10

    # Monitoring (Flower)
    worker_send_task_events = True
    task_send_sent_event = True


# Development configuration
class DevelopmentCeleryConfig(CeleryConfig):
    """Development-specific Celery configuration"""

    broker_url = "redis://localhost:6379/0"
    result_backend = "redis://localhost:6379/1"

    # More verbose logging in development
    worker_hijack_root_logger = False


# Production configuration
class ProductionCeleryConfig(CeleryConfig):
    """Production-specific Celery configuration"""

    # Use environment variables for production
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    # Stricter settings for production
    task_always_eager = False
    worker_max_memory_per_child = 200000  # 200MB memory limit


# Testing configuration
class TestingCeleryConfig(CeleryConfig):
    """Testing-specific Celery configuration"""

    # Run tasks synchronously in tests
    task_always_eager = True
    task_eager_propagates = True

    # Use memory backend for tests
    broker_url = "memory://"
    result_backend = "cache+memory://"


def get_celery_config(env=None):
    """Get Celery configuration based on environment"""
    if env is None:
        env = os.environ.get("FLASK_ENV", "development")

    configs = {
        "development": DevelopmentCeleryConfig,
        "production": ProductionCeleryConfig,
        "testing": TestingCeleryConfig,
    }

    return configs.get(env, DevelopmentCeleryConfig)
