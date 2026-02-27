"""
Security Enhancement Tests for Phase 15D

Tests covering:
- Security headers added to HTTP responses
- Rate limiting integration (disabled in testing, module structure tested)
- Input sanitization functions
- Input validation functions
"""

import pytest

from app import create_app
from app.models import db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def app():
    """Create test Flask application."""
    import os

    os.environ["FLASK_ENV"] = "testing"
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Create test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Security Header Tests
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    """Tests that security headers are present in HTTP responses."""

    def test_x_content_type_options_header(self, client):
        """X-Content-Type-Options: nosniff must be present."""
        response = client.get("/auth/login")
        assert "X-Content-Type-Options" in response.headers, (
            "X-Content-Type-Options header is missing"
        )
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_header(self, client):
        """X-Frame-Options must be set to prevent clickjacking."""
        response = client.get("/auth/login")
        assert "X-Frame-Options" in response.headers, (
            "X-Frame-Options header is missing"
        )
        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_x_xss_protection_header(self, client):
        """X-XSS-Protection must be enabled."""
        response = client.get("/auth/login")
        assert "X-XSS-Protection" in response.headers, (
            "X-XSS-Protection header is missing"
        )
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy_header(self, client):
        """Referrer-Policy must restrict referrer information."""
        response = client.get("/auth/login")
        assert "Referrer-Policy" in response.headers, (
            "Referrer-Policy header is missing"
        )
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self, client):
        """Permissions-Policy must restrict browser features."""
        response = client.get("/auth/login")
        assert "Permissions-Policy" in response.headers, (
            "Permissions-Policy header is missing"
        )
        policy = response.headers["Permissions-Policy"]
        # Check that dangerous capabilities are restricted
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy

    def test_content_security_policy_header(self, client):
        """Content-Security-Policy must be present when CSP is enabled."""
        response = client.get("/auth/login")
        # CSP is enabled in TestingConfig (ENABLE_CSP = True)
        assert "Content-Security-Policy" in response.headers, (
            "Content-Security-Policy header is missing"
        )
        csp = response.headers["Content-Security-Policy"]
        assert "default-src" in csp

    def test_security_headers_on_api_response(self, client):
        """Security headers must also appear on API responses."""
        response = client.get("/api/v1/auth/login", content_type="application/json")
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    def test_security_headers_on_404(self, client):
        """Security headers must appear even on 404 error responses."""
        response = client.get("/nonexistent-path-xyz")
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


# ---------------------------------------------------------------------------
# Rate Limiter Module Tests
# ---------------------------------------------------------------------------


class TestRateLimiterModule:
    """Tests for the rate limiter module structure and helpers."""

    def test_rate_limiter_module_imports(self):
        """Rate limiter module must be importable."""
        from app.utils.rate_limiter import (
            RateLimiter,
            init_rate_limiting,
            limit_login_attempts,
            limit_api_calls,
            limit_registration,
            limit_password_reset,
            limit_file_upload,
            limit_report_generation,
        )
        assert RateLimiter is not None
        assert init_rate_limiting is not None
        assert limit_login_attempts is not None
        assert limit_api_calls is not None

    def test_rate_limiter_disabled_in_testing(self, app):
        """Rate limiter should be disabled in testing mode."""
        assert app.config.get("RATELIMIT_ENABLED") is False

    def test_rate_limiter_no_op_when_disabled(self):
        """When rate limiting is disabled, the limiter returns no-op decorators."""
        from app.utils.rate_limiter import RateLimiter

        limiter = RateLimiter()  # No app means limiter is None
        decorator = limiter.limit("5 per minute")

        # Should return a no-op decorator (function is unchanged)
        def my_func():
            return "ok"

        decorated = decorator(my_func)
        assert decorated() == "ok"

    def test_handle_rate_limit_exceeded_returns_429(self, app):
        """Rate limit exceeded handler should return 429 with JSON body."""
        from app.utils.rate_limiter import handle_rate_limit_exceeded

        class FakeException:
            description = "5 per 1 minute"

        with app.test_request_context("/api/v1/auth/login"):
            response, status_code = handle_rate_limit_exceeded(FakeException())
            assert status_code == 429
            data = response.get_json()
            assert data["error"] == "Rate limit exceeded"
            assert "message" in data

    def test_get_request_identifier_fallback(self, app):
        """get_request_identifier should fall back to remote address."""
        from app.utils.rate_limiter import get_request_identifier
        from flask import g

        with app.test_request_context("/"):
            # g.user is not set; should fall back to IP
            result = get_request_identifier()
            assert result is not None


# ---------------------------------------------------------------------------
# Input Sanitization Tests
# ---------------------------------------------------------------------------


class TestSanitizeString:
    """Tests for the sanitize_string function."""

    def test_removes_null_bytes(self):
        """Null bytes must be stripped from strings."""
        from app.utils.sanitize import sanitize_string

        result = sanitize_string("hello\x00world")
        assert "\x00" not in result
        assert result == "helloworld"

    def test_truncates_to_max_length(self):
        """Strings exceeding max_length must be truncated."""
        from app.utils.sanitize import sanitize_string

        result = sanitize_string("a" * 300, max_length=255)
        assert len(result) == 255

    def test_default_max_length_is_255(self):
        """Default max_length should be 255."""
        from app.utils.sanitize import sanitize_string

        long_string = "x" * 300
        result = sanitize_string(long_string)
        assert len(result) == 255

    def test_non_string_returns_empty(self):
        """Non-string input must return empty string."""
        from app.utils.sanitize import sanitize_string

        assert sanitize_string(None) == ""
        assert sanitize_string(123) == ""
        assert sanitize_string([]) == ""

    def test_normal_string_unchanged(self):
        """Normal strings without null bytes must pass through unchanged."""
        from app.utils.sanitize import sanitize_string

        result = sanitize_string("Hello, World!")
        assert result == "Hello, World!"

    def test_multiple_null_bytes_removed(self):
        """Multiple null bytes across the string must all be removed."""
        from app.utils.sanitize import sanitize_string

        result = sanitize_string("\x00start\x00middle\x00end\x00")
        assert result == "startmiddleend"

    def test_empty_string_input(self):
        """Empty string should return empty string."""
        from app.utils.sanitize import sanitize_string

        result = sanitize_string("")
        assert result == ""


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------


class TestValidateJobName:
    """Tests for the validate_job_name function."""

    def test_valid_alphanumeric_name(self):
        """Alphanumeric job names must be accepted."""
        from app.utils.sanitize import validate_job_name

        result = validate_job_name("BackupJob123")
        assert result == "BackupJob123"

    def test_valid_name_with_hyphens_and_underscores(self):
        """Names with hyphens and underscores must be accepted."""
        from app.utils.sanitize import validate_job_name

        result = validate_job_name("valid-name_123")
        assert result == "valid-name_123"

    def test_valid_name_with_spaces(self):
        """Names with spaces must be accepted."""
        from app.utils.sanitize import validate_job_name

        result = validate_job_name("My Backup Job")
        assert result == "My Backup Job"

    def test_empty_string_returns_none(self):
        """Empty string must return None."""
        from app.utils.sanitize import validate_job_name

        assert validate_job_name("") is None

    def test_none_returns_none(self):
        """None input must return None."""
        from app.utils.sanitize import validate_job_name

        assert validate_job_name(None) is None

    def test_non_string_returns_none(self):
        """Non-string input must return None."""
        from app.utils.sanitize import validate_job_name

        assert validate_job_name(123) is None

    def test_name_with_sql_injection_attempt_rejected(self):
        """Names containing SQL injection characters must be rejected."""
        from app.utils.sanitize import validate_job_name

        assert validate_job_name("'; DROP TABLE users; --") is None

    def test_name_with_angle_brackets_rejected(self):
        """Names containing HTML/script injection characters must be rejected."""
        from app.utils.sanitize import validate_job_name

        assert validate_job_name("<script>alert('xss')</script>") is None

    def test_name_too_long_is_truncated_or_accepted(self):
        """Names exceeding 100 characters are truncated to 100."""
        from app.utils.sanitize import validate_job_name

        long_name = "a" * 150
        result = validate_job_name(long_name)
        # Result should be truncated to 100 characters
        assert result is not None
        assert len(result) == 100

    def test_japanese_characters_accepted(self):
        """Japanese characters (Kanji, Hiragana, Katakana) must be accepted."""
        from app.utils.sanitize import validate_job_name

        result = validate_job_name("バックアップジョブ1")
        assert result is not None

    def test_whitespace_only_returns_none(self):
        """Whitespace-only names must return None after stripping."""
        from app.utils.sanitize import validate_job_name

        assert validate_job_name("   ") is None


class TestValidateUsername:
    """Tests for the validate_username function."""

    def test_valid_username(self):
        """Standard alphanumeric usernames must be accepted."""
        from app.utils.sanitize import validate_username

        result = validate_username("john_doe")
        assert result == "john_doe"

    def test_username_with_period(self):
        """Usernames with periods must be accepted."""
        from app.utils.sanitize import validate_username

        result = validate_username("john.doe")
        assert result == "john.doe"

    def test_short_username_rejected(self):
        """Usernames shorter than 3 characters must be rejected."""
        from app.utils.sanitize import validate_username

        assert validate_username("ab") is None

    def test_empty_username_rejected(self):
        """Empty username must be rejected."""
        from app.utils.sanitize import validate_username

        assert validate_username("") is None

    def test_username_with_spaces_rejected(self):
        """Usernames containing spaces must be rejected."""
        from app.utils.sanitize import validate_username

        assert validate_username("john doe") is None

    def test_username_with_special_chars_rejected(self):
        """Usernames containing dangerous special characters must be rejected."""
        from app.utils.sanitize import validate_username

        assert validate_username("admin'; DROP TABLE") is None


class TestValidatePath:
    """Tests for the validate_path function."""

    def test_valid_absolute_path(self):
        """Valid absolute paths must be accepted."""
        from app.utils.sanitize import validate_path

        result = validate_path("/data/backups/job1")
        assert result == "/data/backups/job1"

    def test_path_traversal_rejected(self):
        """Paths containing '..' must be rejected."""
        from app.utils.sanitize import validate_path

        assert validate_path("/data/../etc/passwd") is None
        assert validate_path("../../secret") is None

    def test_none_path_rejected(self):
        """None must be rejected."""
        from app.utils.sanitize import validate_path

        assert validate_path(None) is None

    def test_empty_path_rejected(self):
        """Empty path must be rejected."""
        from app.utils.sanitize import validate_path

        assert validate_path("") is None

    def test_path_with_null_byte_rejected(self):
        """Paths with null bytes must be sanitized (null byte removed)."""
        from app.utils.sanitize import validate_path

        result = validate_path("/data/file\x00.txt")
        assert "\x00" not in result


class TestSanitizeSearchQuery:
    """Tests for the sanitize_search_query function."""

    def test_normal_query_unchanged(self):
        """Normal search queries should pass through unchanged."""
        from app.utils.sanitize import sanitize_search_query

        result = sanitize_search_query("backup job 2024")
        assert result == "backup job 2024"

    def test_control_characters_removed(self):
        """Control characters must be stripped from search queries."""
        from app.utils.sanitize import sanitize_search_query

        result = sanitize_search_query("test\x01\x02query")
        assert "\x01" not in result
        assert "\x02" not in result

    def test_query_truncated(self):
        """Queries exceeding max_length must be truncated."""
        from app.utils.sanitize import sanitize_search_query

        result = sanitize_search_query("a" * 300, max_length=200)
        assert len(result) == 200

    def test_non_string_returns_empty(self):
        """Non-string input must return empty string."""
        from app.utils.sanitize import sanitize_search_query

        assert sanitize_search_query(None) == ""
        assert sanitize_search_query(42) == ""


# ---------------------------------------------------------------------------
# Security Utilities Integration Tests
# ---------------------------------------------------------------------------


class TestSecurityHeadersModule:
    """Tests for the security headers module."""

    def test_security_headers_module_imports(self):
        """Security headers module must be importable."""
        from app.utils.security_headers import (
            SecurityHeaders,
            init_security_headers,
            sanitize_input,
            validate_file_upload,
        )
        assert SecurityHeaders is not None
        assert init_security_headers is not None

    def test_sanitize_input_removes_null_bytes(self):
        """sanitize_input in security_headers must remove null bytes."""
        from app.utils.security_headers import sanitize_input

        result = sanitize_input("test\x00value")
        assert "\x00" not in result

    def test_sanitize_input_truncates(self):
        """sanitize_input must truncate to max_length."""
        from app.utils.security_headers import sanitize_input

        result = sanitize_input("a" * 200, max_length=50)
        assert len(result) == 50

    def test_sanitize_input_strips_whitespace(self):
        """sanitize_input must strip surrounding whitespace."""
        from app.utils.security_headers import sanitize_input

        result = sanitize_input("  hello  ")
        assert result == "hello"

    def test_validate_file_upload_valid_extension(self):
        """Valid file extensions must pass validation."""
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("report.pdf") is True
        assert validate_file_upload("data.csv") is True
        assert validate_file_upload("config.json") is True

    def test_validate_file_upload_invalid_extension(self):
        """Dangerous file extensions must be rejected."""
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("malware.exe") is False
        assert validate_file_upload("script.sh") is False
        assert validate_file_upload("config.php") is False

    def test_validate_file_upload_no_extension(self):
        """Filenames without extension must be rejected."""
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("noextension") is False

    def test_validate_file_upload_empty_filename(self):
        """Empty filename must be rejected."""
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("") is False
        assert validate_file_upload(None) is False
