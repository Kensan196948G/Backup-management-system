"""
Configuration module for Backup Management System
Supports cross-platform (Linux development / Windows production)
"""

import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.absolute()


class Config:
    """Base configuration"""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f'sqlite:///{BASE_DIR / "data" / "backup_mgmt.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Security
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload

    # Password Policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_EXPIRY_DAYS = 90
    PASSWORD_HISTORY_COUNT = 3

    # Login Protection
    LOGIN_ATTEMPT_LIMIT = 5
    LOGIN_ATTEMPT_WINDOW = 600  # 10 minutes
    ACCOUNT_LOCKOUT_DURATION = 600  # 10 minutes

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # Email (SMTP)
    MAIL_SERVER = os.environ.get("MAIL_SERVER") or "localhost"
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or "Backup Management System <backup-system@example.com>"

    # Microsoft Teams
    TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL")

    # Logging
    LOG_DIR = BASE_DIR / "logs"
    LOG_LEVEL = os.environ.get("LOG_LEVEL") or "INFO"
    LOG_ROTATION_DAYS = 90

    # Scheduler
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "Asia/Tokyo"

    # 3-2-1-1-0 Rule Thresholds
    MIN_COPIES = 3
    MIN_MEDIA_TYPES = 2
    OFFLINE_MEDIA_UPDATE_WARNING_DAYS = 7

    # Verification Test Schedule
    VERIFICATION_REMINDER_DAYS = 7

    # Reports
    REPORT_OUTPUT_DIR = BASE_DIR / "reports"
    REPORT_RETENTION_DAYS = 90

    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100

    # API Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "1000 per hour"
    RATELIMIT_STORAGE_URL = "memory://"

    # Celery Configuration (Phase 11)
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND") or "redis://localhost:6379/1"

    # Cross-platform compatibility
    PLATFORM = os.name  # 'nt' for Windows, 'posix' for Linux/Unix


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = "DEBUG"
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False  # Disable CSRF for development API testing


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    TESTING = False

    # Security (Production)
    SESSION_COOKIE_SECURE = True  # HTTPS only
    PREFERRED_URL_SCHEME = "https"

    # Override SECRET_KEY from parent class
    SECRET_KEY = os.environ.get("SECRET_KEY") or Config.SECRET_KEY

    # Database (Production - PostgreSQL recommended)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f'sqlite:///{BASE_DIR / "data" / "backup_mgmt.db"}'

    def __init__(self):
        """Validate production configuration on instantiation"""
        if os.environ.get("FLASK_ENV") == "production" and not os.environ.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY環境変数が設定されていません。本番環境では必ず設定してください。")


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    DEBUG = True

    # Use in-memory SQLite for tests
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Fast password hashing for tests
    BCRYPT_LOG_ROUNDS = 4

    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False

    # Security headers enabled in tests for header tests
    ENABLE_HSTS = False  # HSTS disabled in test (not HTTPS)
    ENABLE_CSP = True


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name=None):
    """Get configuration by name or from environment"""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    return config.get(config_name, DevelopmentConfig)
