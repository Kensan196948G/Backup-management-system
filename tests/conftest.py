"""
Pytest configuration and fixtures for backup management system tests.

This module provides shared fixtures for unit and integration tests,
including database setup, test client, and common test data.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import (
    Alert,
    AuditLog,
    BackupCopy,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    MediaLending,
    MediaRotationSchedule,
    OfflineMedia,
    Report,
    SystemSetting,
    User,
    VerificationSchedule,
    VerificationTest,
    db,
)


@pytest.fixture(scope="function")
def app():
    """
    Create and configure a Flask app instance for testing.

    Uses TestingConfig with SQLite in-memory database for fast test execution.
    Each test gets a fresh database with all tables created.

    Yields:
        Flask: Configured Flask application instance
    """
    # Create app with testing configuration
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("testing")

    # Create application context
    with app.app_context():
        # Create all database tables
        db.create_all()

        yield app

        # Cleanup: remove session and drop all tables
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    Create a test client for the Flask application.

    Args:
        app: Flask application fixture

    Returns:
        FlaskClient: Test client for making HTTP requests
    """
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """
    Create a test CLI runner for the Flask application.

    Args:
        app: Flask application fixture

    Returns:
        FlaskCliRunner: Test runner for CLI commands
    """
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def db_session(app):
    """
    Provide a database session for tests with automatic rollback.

    After each test, all changes are rolled back to maintain test isolation.

    Args:
        app: Flask application fixture

    Yields:
        SQLAlchemy Session: Database session
    """
    with app.app_context():
        # Begin a nested transaction
        connection = db.engine.connect()
        transaction = connection.begin()

        # Use connection in session
        session = db.session

        yield session

        # Rollback transaction after test
        session.close()
        transaction.rollback()
        connection.close()


# User Fixtures
@pytest.fixture(scope="function")
def admin_user(app):
    """
    Create an admin user for testing.

    Returns:
        User: Admin user with full permissions
    """
    with app.app_context():
        user = User(username="admin", email="admin@example.com", full_name="Admin User", role="admin", is_active=True)
        user.set_password("Admin123!@#")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


@pytest.fixture(scope="function")
def operator_user(app):
    """
    Create an operator user for testing.

    Returns:
        User: Operator user with edit permissions
    """
    with app.app_context():
        user = User(
            username="operator", email="operator@example.com", full_name="Operator User", role="operator", is_active=True
        )
        user.set_password("Operator123!@#")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


@pytest.fixture(scope="function")
def auditor_user(app):
    """
    Create an auditor user for testing.

    Returns:
        User: Auditor user with read-only permissions
    """
    with app.app_context():
        user = User(username="auditor", email="auditor@example.com", full_name="Auditor User", role="auditor", is_active=True)
        user.set_password("Auditor123!@#")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


@pytest.fixture(scope="function")
def viewer_user(app):
    """
    Create a viewer user for testing.

    Returns:
        User: Viewer user with read-only permissions
    """
    with app.app_context():
        user = User(username="viewer", email="viewer@example.com", full_name="Viewer User", role="viewer", is_active=True)
        user.set_password("Viewer123!@#")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


# Backup Job Fixtures
@pytest.fixture(scope="function")
def backup_job(app, admin_user):
    """
    Create a sample backup job for testing.

    Returns:
        BackupJob: Basic backup job with daily schedule
    """
    with app.app_context():
        # Get fresh user instance
        user = db.session.get(User, admin_user.id)

        job = BackupJob(
            job_name="Test Backup Job",
            job_type="file",
            backup_tool="custom",
            description="Test backup job description",
            target_path="/data/source",
            schedule_type="daily",
            retention_days=30,
            owner_id=user.id,
            is_active=True,
        )
        db.session.add(job)
        db.session.commit()
        db.session.refresh(job)
        yield job


@pytest.fixture(scope="function")
def multiple_backup_jobs(app, admin_user):
    """
    Create multiple backup jobs for testing.

    Returns:
        list: List of BackupJob instances
    """
    with app.app_context():
        # Get fresh user instance
        user = db.session.get(User, admin_user.id)

        jobs = [
            BackupJob(
                job_name=f"Test Job {i}",
                job_type=["file", "system_image", "database"][i % 3],
                backup_tool="custom",
                description=f"Test job {i} description",
                target_path=f"/data/source{i}",
                schedule_type=["daily", "weekly", "monthly"][i % 3],
                retention_days=30 * (i + 1),
                owner_id=user.id,
                is_active=i % 2 == 0,
            )
            for i in range(5)
        ]
        db.session.add_all(jobs)
        db.session.commit()
        for job in jobs:
            db.session.refresh(job)
        yield jobs


# Backup Copy Fixtures
@pytest.fixture(scope="function")
def backup_copies(app, backup_job):
    """
    Create backup copies for a job, demonstrating 3-2-1-1-0 rule.

    Returns:
        list: List of BackupCopy instances
    """
    with app.app_context():
        # Get fresh job instance
        job = db.session.get(BackupJob, backup_job.id)

        copies = [
            # Copy 1: Primary storage, onsite
            BackupCopy(
                job_id=job.id,
                copy_type="primary",
                storage_path="Primary NAS",
                media_type="disk",
                is_encrypted=True,
                is_compressed=True,
                last_backup_size=1024 * 1024 * 1024,  # 1GB
                last_backup_date=datetime.now(timezone.utc),
                status="success",
            ),
            # Copy 2: Secondary storage, onsite
            BackupCopy(
                job_id=job.id,
                copy_type="secondary",
                storage_path="Secondary NAS",
                media_type="disk",
                is_encrypted=True,
                is_compressed=True,
                last_backup_size=1024 * 1024 * 1024,  # 1GB
                last_backup_date=datetime.now(timezone.utc),
                status="success",
            ),
            # Copy 3: Cloud storage, offsite
            BackupCopy(
                job_id=job.id,
                copy_type="offsite",
                storage_path="AWS S3",
                media_type="cloud",
                is_encrypted=True,
                is_compressed=True,
                last_backup_size=1024 * 1024 * 1024,  # 1GB
                last_backup_date=datetime.now(timezone.utc),
                status="success",
            ),
            # Copy 4: Tape storage, offline
            BackupCopy(
                job_id=job.id,
                copy_type="offline",
                storage_path="Tape Library",
                media_type="tape",
                is_encrypted=True,
                is_compressed=True,
                last_backup_size=1024 * 1024 * 1024,  # 1GB
                last_backup_date=datetime.now(timezone.utc),
                status="success",
            ),
        ]
        db.session.add_all(copies)
        db.session.commit()
        for copy in copies:
            db.session.refresh(copy)
        yield copies


# Offline Media Fixtures
@pytest.fixture(scope="function")
def offline_media(app):
    """
    Create offline media for testing.

    Returns:
        list: List of OfflineMedia instances
    """
    with app.app_context():
        media_list = [
            OfflineMedia(
                media_type="tape",
                media_id=f"TAPE-{i:03d}",
                capacity_gb=2000,  # 2TB
                storage_location="Vault A",
                current_status=["available", "in_use", "stored"][i % 3],
                purchase_date=(datetime.now(timezone.utc) - timedelta(days=365)).date(),
            )
            for i in range(5)
        ]
        db.session.add_all(media_list)
        db.session.commit()
        for media in media_list:
            db.session.refresh(media)
        yield media_list


# Verification Test Fixtures
@pytest.fixture(scope="function")
def verification_tests(app, backup_job, admin_user):
    """
    Create verification tests for backup jobs.

    Returns:
        list: List of VerificationTest instances
    """
    with app.app_context():
        # Get fresh instances
        job = db.session.get(BackupJob, backup_job.id)
        user = db.session.get(User, admin_user.id)

        tests = [
            VerificationTest(
                job_id=job.id,
                test_type=["full_restore", "partial", "integrity"][i % 3],
                test_date=datetime.now(timezone.utc),
                tester_id=user.id,
                test_result=["success", "failed"][i % 2],
                duration_seconds=300 + i * 60,
                issues_found=None if i % 2 == 0 else "Test error details",
            )
            for i in range(3)
        ]
        db.session.add_all(tests)
        db.session.commit()
        for test in tests:
            db.session.refresh(test)
        yield tests


# Alert Fixtures
@pytest.fixture(scope="function")
def alerts(app, backup_job):
    """
    Create alerts for testing.

    Returns:
        list: List of Alert instances
    """
    with app.app_context():
        # Get fresh job instance
        job = db.session.get(BackupJob, backup_job.id)

        alerts_list = [
            Alert(
                job_id=job.id,
                alert_type=["compliance_check", "backup_failure", "media_warning"][i % 3],
                severity=["critical", "warning", "info"][i % 3],
                title=f"Test Alert {i}",
                message=f"Test alert message {i}",
                is_acknowledged=i % 2 == 0,
            )
            for i in range(5)
        ]
        db.session.add_all(alerts_list)
        db.session.commit()
        for alert in alerts_list:
            db.session.refresh(alert)
        yield alerts_list


# Report Fixtures
@pytest.fixture(scope="function")
def reports(app, admin_user):
    """
    Create reports for testing.

    Returns:
        list: List of Report instances
    """
    with app.app_context():
        # Get fresh user instance
        user = db.session.get(User, admin_user.id)

        reports_list = [
            Report(
                report_type=["daily", "weekly", "monthly"][i % 3],
                report_title=f"Test Report {i}",
                date_from=(datetime.now(timezone.utc) - timedelta(days=i + 1)).date(),
                date_to=(datetime.now(timezone.utc) - timedelta(days=i)).date(),
                file_format="pdf",
                file_path=f"/reports/test_report_{i}.pdf",
                generated_by=user.id,
            )
            for i in range(5)
        ]
        db.session.add_all(reports_list)
        db.session.commit()
        for report in reports_list:
            db.session.refresh(report)
        yield reports_list


# System Setting Fixtures
@pytest.fixture(scope="function")
def system_settings(app):
    """
    Create system settings for testing.

    Returns:
        list: List of SystemSetting instances
    """
    with app.app_context():
        settings = [
            SystemSetting(
                setting_key="min_copies", setting_value="3", value_type="int", description="Minimum backup copies required"
            ),
            SystemSetting(
                setting_key="retention_days",
                setting_value="30",
                value_type="int",
                description="Default retention period in days",
            ),
            SystemSetting(
                setting_key="email_enabled", setting_value="true", value_type="bool", description="Enable email notifications"
            ),
        ]
        db.session.add_all(settings)
        db.session.commit()
        for setting in settings:
            db.session.refresh(setting)
        yield settings


# Authentication Fixtures
@pytest.fixture(scope="function")
def authenticated_client(client, app):
    """
    Create an authenticated test client with admin user logged in.

    Args:
        client: Flask test client
        app: Flask application fixture

    Returns:
        FlaskClient: Authenticated test client
    """
    # Create admin user
    user = User(
        username="admin_test", email="admin_test@example.com", full_name="Admin Test User", role="admin", is_active=True
    )
    user.set_password("Admin123!@#")
    db.session.add(user)
    db.session.commit()

    # Login
    client.post("/auth/login", data={"username": "admin_test", "password": "Admin123!@#"}, follow_redirects=True)
    yield client


@pytest.fixture(scope="function")
def operator_authenticated_client(client, app):
    """
    Create an authenticated test client with operator user logged in.

    Args:
        client: Flask test client
        app: Flask application fixture

    Returns:
        FlaskClient: Authenticated test client with operator role
    """
    user = User(
        username="operator_test",
        email="operator_test@example.com",
        full_name="Operator Test User",
        role="operator",
        is_active=True,
    )
    user.set_password("Operator123!@#")
    db.session.add(user)
    db.session.commit()

    # Login
    client.post("/auth/login", data={"username": "operator_test", "password": "Operator123!@#"}, follow_redirects=True)
    yield client


@pytest.fixture(scope="function")
def auditor_authenticated_client(client, app):
    """
    Create an authenticated test client with auditor user logged in.

    Args:
        client: Flask test client
        app: Flask application fixture

    Returns:
        FlaskClient: Authenticated test client with auditor role
    """
    user = User(
        username="auditor_test",
        email="auditor_test@example.com",
        full_name="Auditor Test User",
        role="auditor",
        is_active=True,
    )
    user.set_password("Auditor123!@#")
    db.session.add(user)
    db.session.commit()

    # Login
    client.post("/auth/login", data={"username": "auditor_test", "password": "Auditor123!@#"}, follow_redirects=True)
    yield client


# API Token Fixtures
@pytest.fixture(scope="function")
def api_headers(admin_user, app):
    """
    Create API authentication headers.

    Args:
        admin_user: Admin user fixture
        app: Flask application fixture

    Returns:
        dict: Headers with authentication token
    """
    with app.app_context():
        # In a real app, generate a JWT token here
        # For testing, we'll use basic auth or session-based auth
        return {"Content-Type": "application/json", "Accept": "application/json"}


@pytest.fixture(scope="function")
def api_client(client, app):
    """
    Create API test client with helper methods for authentication.

    Args:
        client: Flask test client
        app: Flask application fixture

    Returns:
        APITestClient: Enhanced test client with JWT token management
    """

    class APITestClient:
        def __init__(self, flask_client, flask_app):
            self.client = flask_client
            self.app = flask_app
            self.access_token = None
            self.refresh_token = None
            self.current_user = None

        def login(self, username, password):
            """Login and store tokens."""
            response = self.client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                data = response.get_json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.current_user = data.get("user")
            return response

        def logout(self):
            """Logout and clear tokens."""
            if self.access_token:
                response = self.client.post("/api/v1/auth/logout", headers=self.get_headers())
                self.access_token = None
                self.refresh_token = None
                self.current_user = None
                return response
            return None

        def refresh(self):
            """Refresh access token."""
            if self.refresh_token:
                response = self.client.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": self.refresh_token},
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    data = response.get_json()
                    self.access_token = data.get("access_token")
                return response
            return None

        def get_headers(self, extra_headers=None):
            """Get headers with authentication token."""
            headers = {"Content-Type": "application/json"}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            if extra_headers:
                headers.update(extra_headers)
            return headers

        def get(self, url, **kwargs):
            """GET request with authentication."""
            if "headers" not in kwargs:
                kwargs["headers"] = self.get_headers()
            return self.client.get(url, **kwargs)

        def post(self, url, **kwargs):
            """POST request with authentication."""
            if "headers" not in kwargs:
                kwargs["headers"] = self.get_headers()
            return self.client.post(url, **kwargs)

        def put(self, url, **kwargs):
            """PUT request with authentication."""
            if "headers" not in kwargs:
                kwargs["headers"] = self.get_headers()
            return self.client.put(url, **kwargs)

        def delete(self, url, **kwargs):
            """DELETE request with authentication."""
            if "headers" not in kwargs:
                kwargs["headers"] = self.get_headers()
            return self.client.delete(url, **kwargs)

    return APITestClient(client, app)


@pytest.fixture(scope="function")
def jwt_token(admin_user, app):
    """
    Generate JWT token for admin user.

    Args:
        admin_user: Admin user fixture
        app: Flask application fixture

    Returns:
        str: JWT access token
    """
    from app.api.auth import generate_jwt_token

    with app.app_context():
        user = db.session.get(User, admin_user.id)
        return generate_jwt_token(user)


@pytest.fixture(scope="function")
def api_key_fixture(admin_user, app):
    """
    Create API key for admin user.

    Args:
        admin_user: Admin user fixture
        app: Flask application fixture

    Returns:
        tuple: (plaintext_key, ApiKey object)
    """
    from app.models_api_key import ApiKey

    with app.app_context():
        user = db.session.get(User, admin_user.id)
        plaintext_key, api_key_obj = ApiKey.create_api_key(user_id=user.id, name="Test API Key", expires_in_days=30)
        db.session.commit()
        db.session.refresh(api_key_obj)
        yield plaintext_key, api_key_obj


@pytest.fixture(scope="function")
def operator_api_client(api_client, operator_user, app):
    """
    Create authenticated API client with operator user.

    Args:
        api_client: API test client fixture
        operator_user: Operator user fixture
        app: Flask application fixture

    Returns:
        APITestClient: Authenticated API client
    """
    with app.app_context():
        api_client.login("operator", "Operator123!@#")
        yield api_client


@pytest.fixture(scope="function")
def admin_api_client(api_client, admin_user, app):
    """
    Create authenticated API client with admin user.

    Args:
        api_client: API test client fixture
        admin_user: Admin user fixture
        app: Flask application fixture

    Returns:
        APITestClient: Authenticated API client
    """
    with app.app_context():
        api_client.login("admin", "Admin123!@#")
        yield api_client


# Cleanup Fixtures
@pytest.fixture(autouse=True)
def reset_db(app):
    """
    Automatically reset database before each test.

    This fixture runs before every test to ensure clean state.
    """
    with app.app_context():
        db.session.rollback()
        yield
        db.session.rollback()
