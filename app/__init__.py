"""
Backup Management System - Application Factory
Implements 3-2-1-1-0 backup rule compliance management

Features:
- Flask application factory pattern
- Cross-platform support (Linux development / Windows production)
- Role-based access control (RBAC)
- Scheduled backup monitoring
- Compliance checking and alerting
"""

import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import HTTPException

from app.config import get_config

# Import extensions (initialized here, configured in create_app)
from app.models import db

# Import security utilities
from app.utils.security_headers import init_security_headers
from app.utils.rate_limiter import init_rate_limiting, register_rate_limit_handlers

# Initialize Flask extensions
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()
csrf = CSRFProtect()
# Scheduler will be initialized in _init_scheduler() function


def create_app(config_name=None):
    """
    Application factory function

    Args:
        config_name: Configuration name ('development', 'production', 'testing')
                    If None, reads from FLASK_ENV environment variable

    Returns:
        Flask application instance
    """
    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config = get_config(config_name)
    app.config.from_object(config)

    # Ensure required directories exist
    _ensure_directories(app)

    # Initialize logging
    _init_logging(app)

    app.logger.info(f"Starting Backup Management System in {config_name} mode")
    app.logger.info(f'Platform: {app.config["PLATFORM"]}')

    # Initialize extensions
    _init_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    _register_error_handlers(app)

    # Initialize scheduler (skip in testing mode)
    if not app.config.get("TESTING"):
        try:
            _init_scheduler(app)
        except Exception as e:
            app.logger.warning(f"Scheduler initialization skipped: {str(e)}")

    # Register template context processors
    _register_context_processors(app)

    # Register CLI commands
    _register_cli_commands(app)

    return app


def _ensure_directories(app):
    """Ensure required directories exist"""
    directories = [
        Path(app.root_path).parent / "data",
        Path(app.root_path).parent / "logs",
        Path(app.root_path).parent / "reports",
        Path(app.root_path) / "static" / "uploads",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        app.logger.debug(f"Ensured directory exists: {directory}") if hasattr(app, "logger") else None


def _init_logging(app):
    """Initialize application logging"""
    # Create logs directory
    log_dir = Path(app.root_path).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Set log level
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"))
    app.logger.setLevel(log_level)

    # Remove default handlers
    app.logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    app.logger.addHandler(console_handler)

    # File handler (rotating by size)
    if not app.config.get("TESTING"):
        file_handler = RotatingFileHandler(log_dir / "backup_system.log", maxBytes=10 * 1024 * 1024, backupCount=10)  # 10MB
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s")
        file_handler.setFormatter(file_formatter)
        app.logger.addHandler(file_handler)

        # Error log handler (rotating by date)
        error_handler = TimedRotatingFileHandler(
            log_dir / "errors.log", when="midnight", interval=1, backupCount=app.config.get("LOG_ROTATION_DAYS", 90)
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        app.logger.addHandler(error_handler)

    # Log SQL queries in debug mode
    if app.config.get("SQLALCHEMY_ECHO"):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def _init_extensions(app):
    """Initialize Flask extensions"""
    # Database
    db.init_app(app)

    # Migration
    migrate.init_app(app, db)

    # Login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "このページにアクセスするにはログインが必要です。"
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID"""
        from app.models import User, db

        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        """Handle unauthorized access"""
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required", "message": "Please login to access this resource"}), 401
        # WebUIの場合はログインページにリダイレクト
        return redirect(url_for("auth.login"))

    # Mail
    mail.init_app(app)

    # CSRF Protection
    csrf.init_app(app)

    # Exempt API endpoints from CSRF (they use JWT)
    csrf.exempt("api")

    # Security Headers
    init_security_headers(app)
    app.logger.info("Security headers initialized")

    # Rate Limiting
    rate_limiter = init_rate_limiting(app)
    app.extensions["rate_limiter"] = rate_limiter
    register_rate_limit_handlers(app)
    app.logger.info("Rate limiting initialized")

    app.logger.info("Extensions initialized successfully")


def _register_blueprints(app):
    """Register Flask blueprints"""
    # Authentication blueprint
    from app.auth import auth_bp

    app.register_blueprint(auth_bp)
    app.logger.info("Auth blueprint registered")

    # Views blueprints (web UI)
    try:
        from app.views import (
            dashboard_bp,
            jobs_bp,
            media_bp,
            reports_bp,
            settings_bp,
            verification_bp,
        )

        app.register_blueprint(dashboard_bp)
        app.register_blueprint(jobs_bp)
        app.register_blueprint(media_bp)
        app.register_blueprint(verification_bp)
        app.register_blueprint(reports_bp)
        app.register_blueprint(settings_bp)
        app.logger.info("Views blueprints registered")
    except ImportError as e:
        app.logger.warning(f"Views blueprints not found: {e}")

    # Admin blueprints (Phase 13)
    try:
        from app.views.admin.postgres_monitor import bp as postgres_monitor_bp

        app.register_blueprint(postgres_monitor_bp)
        app.logger.info("Admin blueprints registered")
    except ImportError as e:
        app.logger.warning(f"Admin blueprints not found: {e}")

    # API blueprint (REST API)
    try:
        from app.api import api_bp

        app.register_blueprint(api_bp)
        app.logger.info("API blueprint registered")
    except ImportError as e:
        app.logger.warning(f"API blueprint not found: {e}")

    # API v1 Authentication blueprint
    try:
        from app.api.v1.auth import auth_bp

        app.register_blueprint(auth_bp)
        app.logger.info("API v1 Auth blueprint registered")
    except ImportError as e:
        app.logger.warning(f"API v1 Auth blueprint not found: {e}")

    app.logger.info("All blueprints registered successfully")

    # Register root route
    @app.route("/")
    def index():
        """Redirect root URL to login page if not authenticated, otherwise to dashboard"""
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))


def _register_error_handlers(app):
    """Register error handlers"""

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request"""
        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": "Bad Request",
                        "message": str(error.description) if hasattr(error, "description") else "Invalid request",
                    }
                ),
                400,
            )
        return render_template("errors/400.html", error=error), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized"""
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
        return render_template("errors/401.html", error=error), 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden"""
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Forbidden", "message": "You do not have permission to access this resource"}), 403
        return render_template("errors/403.html", error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found"""
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Not Found", "message": "The requested resource was not found"}), 404
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        app.logger.error(f"Internal Server Error: {error}", exc_info=True)
        db.session.rollback()
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500
        return render_template("errors/500.html", error=error), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable"""
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Service Unavailable", "message": "The service is temporarily unavailable"}), 503
        return render_template("errors/503.html", error=error), 503

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions"""
        # Pass through HTTP exceptions
        if isinstance(error, HTTPException):
            return error

        # Log the error
        app.logger.error(f"Unhandled exception: {error}", exc_info=True)
        db.session.rollback()

        # Return 500 error
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500
        return render_template("errors/500.html", error=error), 500

    app.logger.info("Error handlers registered successfully")


def _init_scheduler(app):
    """Initialize APScheduler for background tasks"""
    if app.config.get("TESTING"):
        app.logger.info("Scheduler disabled in testing mode")
        return

    # Configure scheduler
    jobstores = {"default": SQLAlchemyJobStore(url=app.config["SQLALCHEMY_DATABASE_URI"])}

    executors = {"default": ThreadPoolExecutor(max_workers=10)}

    job_defaults = {
        "coalesce": True,  # Combine multiple pending executions of job into one
        "max_instances": 1,  # Maximum number of concurrently running instances
        "misfire_grace_time": 300,  # 5 minutes grace time for misfired jobs
    }

    # Create scheduler instance
    scheduler = BackgroundScheduler()
    scheduler.configure(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=app.config.get("SCHEDULER_TIMEZONE", "Asia/Tokyo"),
    )

    # Store scheduler in app context
    app.scheduler = scheduler

    # Register scheduled tasks
    _register_scheduled_tasks(app)

    # Start scheduler
    if not scheduler.running:
        scheduler.start()
        app.logger.info("Scheduler started successfully")

    # Shutdown scheduler on app teardown
    import atexit

    atexit.register(lambda: scheduler.shutdown(wait=False))


def _register_scheduled_tasks(app):
    """Register scheduled tasks"""
    try:
        from app.scheduler.tasks import (
            check_compliance_status,
            check_offline_media_updates,
            check_verification_reminders,
            cleanup_old_logs,
            generate_daily_report,
        )

        # Get scheduler from app
        scheduler = app.scheduler

        # Check compliance status every hour
        scheduler.add_job(
            id="check_compliance_status",
            func=check_compliance_status,
            trigger="interval",
            hours=1,
            replace_existing=True,
            args=[app],
        )

        # Check offline media updates every day at 9:00 AM
        scheduler.add_job(
            id="check_offline_media_updates",
            func=check_offline_media_updates,
            trigger="cron",
            hour=9,
            minute=0,
            replace_existing=True,
            args=[app],
        )

        # Check verification reminders every day at 10:00 AM
        scheduler.add_job(
            id="check_verification_reminders",
            func=check_verification_reminders,
            trigger="cron",
            hour=10,
            minute=0,
            replace_existing=True,
            args=[app],
        )

        # Cleanup old logs every day at 3:00 AM
        scheduler.add_job(
            id="cleanup_old_logs", func=cleanup_old_logs, trigger="cron", hour=3, minute=0, replace_existing=True, args=[app]
        )

        # Generate daily report at 8:00 AM
        scheduler.add_job(
            id="generate_daily_report",
            func=generate_daily_report,
            trigger="cron",
            hour=8,
            minute=0,
            replace_existing=True,
            args=[app],
        )

        app.logger.info("Scheduled tasks registered successfully")

    except ImportError as e:
        app.logger.warning(f"Failed to import scheduled tasks: {e}")


def _register_context_processors(app):
    """Register template context processors"""

    @app.context_processor
    def inject_config():
        """Inject configuration into templates"""
        return {
            "app_name": "3-2-1-1-0 Backup Management System",
            "app_version": "1.0.0",
            "platform": app.config.get("PLATFORM"),
            "environment": os.environ.get("FLASK_ENV", "development"),
        }

    @app.context_processor
    def utility_processor():
        """Inject utility functions into templates"""

        def format_datetime(dt, format="%Y-%m-%d %H:%M:%S"):
            """Format datetime object"""
            if dt is None:
                return ""
            return dt.strftime(format)

        def format_filesize(size_bytes):
            """Format file size in human-readable format"""
            if size_bytes is None:
                return ""
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} PB"

        def compliance_badge_class(is_compliant):
            """Get CSS class for compliance badge"""
            return "badge-success" if is_compliant else "badge-danger"

        return {
            "format_datetime": format_datetime,
            "format_filesize": format_filesize,
            "compliance_badge_class": compliance_badge_class,
        }


def _register_cli_commands(app):
    """Register Flask CLI commands"""

    @app.cli.command("init-db")
    def init_db():
        """Initialize the database"""
        db.create_all()
        print("Database initialized successfully")

    @app.cli.command("create-admin")
    def create_admin():
        """Create admin user"""
        from app.models import User

        username = input("Username: ")
        email = input("Email: ")
        password = input("Password: ")
        full_name = input("Full Name: ")

        if User.query.filter_by(username=username).first():
            print(f"User {username} already exists")
            return

        admin = User(username=username, email=email, full_name=full_name, role="admin", is_active=True)
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        print(f"Admin user {username} created successfully")

    @app.cli.command("list-routes")
    def list_routes():
        """List all application routes"""
        import urllib

        from flask import current_app

        output = []
        for rule in current_app.url_map.iter_rules():
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            line = urllib.parse.unquote(f"{rule.endpoint:50s} {methods:20s} {rule.rule}")
            output.append(line)

        for line in sorted(output):
            print(line)

    @app.cli.command("test-email")
    def test_email():
        """Test email configuration"""
        from flask_mail import Message

        recipient = input("Recipient email: ")

        msg = Message(
            subject="Test Email from Backup Management System",
            recipients=[recipient],
            body="This is a test email to verify email configuration.",
        )

        try:
            mail.send(msg)
            print(f"Test email sent to {recipient}")
        except Exception as e:
            print(f"Failed to send email: {e}")


# Import models to ensure they are registered
from app import models
