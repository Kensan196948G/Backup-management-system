"""
Tests for app/utils/security_headers.py - coverage improvement

Covers: SecurityHeaders init/init_app, _get_security_headers,
        _build_csp (default + custom), init_security_headers,
        init_talisman (production / non-production / ImportError paths),
        configure_cors (success / ImportError paths),
        validate_content_type decorator, sanitize_input, validate_file_upload.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_app(extra_config=None):
    os.environ["FLASK_ENV"] = "testing"
    from app import create_app

    application = create_app("testing")
    if extra_config:
        application.config.update(extra_config)
    return application


# ---------------------------------------------------------------------------
# SecurityHeaders class
# ---------------------------------------------------------------------------


class TestSecurityHeadersInit:
    def test_init_without_app(self):
        """SecurityHeaders() without app stores None."""
        from app.utils.security_headers import SecurityHeaders

        sh = SecurityHeaders()
        assert sh.app is None

    def test_init_with_app_registers_after_request(self):
        """SecurityHeaders(app) registers after_request handler."""
        from app.utils.security_headers import SecurityHeaders

        app = make_app()
        with app.app_context():
            sh = SecurityHeaders(app)
        assert sh.app is app

    def test_init_app_via_method(self):
        """init_app() can be called separately from __init__."""
        from app.utils.security_headers import SecurityHeaders

        app = make_app()
        sh = SecurityHeaders()
        with app.app_context():
            sh.init_app(app)
        assert sh.app is app


class TestSecurityHeadersInResponses:
    """Verify headers are injected into actual HTTP responses."""

    @pytest.fixture()
    def client(self):
        app = make_app()
        return app.test_client()

    def test_x_content_type_options(self, client):
        resp = client.get("/auth/login")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/auth/login")
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_x_xss_protection(self, client):
        resp = client.get("/auth/login")
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client):
        resp = client.get("/auth/login")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy_present(self, client):
        resp = client.get("/auth/login")
        pp = resp.headers.get("Permissions-Policy", "")
        assert "geolocation" in pp

    def test_csp_present_when_enabled(self, client):
        resp = client.get("/auth/login")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp

    def test_hsts_present_when_enabled(self):
        # Testing config disables HSTS; enable it explicitly
        app = make_app({"ENABLE_HSTS": True})
        client = app.test_client()
        resp = client.get("/auth/login")
        hsts = resp.headers.get("Strict-Transport-Security", "")
        assert "max-age=" in hsts

    def test_hsts_absent_when_disabled(self):
        app = make_app({"ENABLE_HSTS": False})
        client = app.test_client()
        resp = client.get("/auth/login")
        assert "Strict-Transport-Security" not in resp.headers

    def test_csp_absent_when_disabled(self):
        app = make_app({"ENABLE_CSP": False})
        client = app.test_client()
        resp = client.get("/auth/login")
        assert "Content-Security-Policy" not in resp.headers


class TestBuildCsp:
    """Tests for SecurityHeaders._build_csp()."""

    def test_default_csp_contains_required_directives(self):
        from app.utils.security_headers import SecurityHeaders

        app = make_app()
        with app.app_context():
            sh = SecurityHeaders(app)
            csp = sh._build_csp()
        required = ["default-src", "script-src", "style-src", "img-src", "object-src"]
        for directive in required:
            assert directive in csp, f"Missing CSP directive: {directive}"

    def test_custom_csp_directives_override_defaults(self):
        from app.utils.security_headers import SecurityHeaders

        custom = {"object-src": ["'self'"]}
        app = make_app({"CSP_DIRECTIVES": custom})
        with app.app_context():
            sh = SecurityHeaders(app)
            csp = sh._build_csp()
        # Custom override should be present
        assert "object-src 'self'" in csp

    def test_csp_is_semicolon_separated(self):
        from app.utils.security_headers import SecurityHeaders

        app = make_app()
        with app.app_context():
            sh = SecurityHeaders(app)
            csp = sh._build_csp()
        parts = csp.split("; ")
        assert len(parts) > 1


class TestGetSecurityHeaders:
    """Tests for SecurityHeaders._get_security_headers()."""

    def test_returns_dict(self):
        from app.utils.security_headers import SecurityHeaders

        app = make_app()
        with app.app_context():
            sh = SecurityHeaders(app)
            headers = sh._get_security_headers()
        assert isinstance(headers, dict)

    def test_custom_hsts_max_age(self):
        # Enable HSTS explicitly (disabled by default in testing config)
        from app.utils.security_headers import SecurityHeaders

        app = make_app({"HSTS_MAX_AGE": 7200, "ENABLE_HSTS": True})
        with app.app_context():
            sh = SecurityHeaders(app)
            headers = sh._get_security_headers()
        assert "max-age=7200" in headers.get("Strict-Transport-Security", "")


# ---------------------------------------------------------------------------
# init_security_headers
# ---------------------------------------------------------------------------


class TestInitSecurityHeaders:
    def test_returns_security_headers_instance(self):
        from app.utils.security_headers import SecurityHeaders, init_security_headers

        app = make_app()
        with app.app_context():
            result = init_security_headers(app)
        assert isinstance(result, SecurityHeaders)


# ---------------------------------------------------------------------------
# init_talisman
# ---------------------------------------------------------------------------


class TestInitTalisman:
    def test_non_production_uses_basic_headers(self):
        """In non-production env, init_talisman falls back to basic headers."""
        from app.utils.security_headers import init_talisman

        app = make_app({"FLASK_ENV": "development"})
        with app.app_context():
            init_talisman(app)  # should not raise

    def test_import_error_falls_back_gracefully(self):
        """If flask_talisman is not installed, falls back without error."""
        from app.utils.security_headers import init_talisman

        app = make_app()
        with app.app_context():
            with patch.dict("sys.modules", {"flask_talisman": None}):
                # ImportError path
                init_talisman(app)  # should not raise

    def test_production_with_talisman_mock(self):
        """In production mode, Talisman is initialised."""
        from app.utils.security_headers import init_talisman

        mock_talisman_cls = MagicMock()
        mock_talisman_module = MagicMock()
        mock_talisman_module.Talisman = mock_talisman_cls

        app = make_app({"FLASK_ENV": "production"})
        with app.app_context():
            with patch.dict("sys.modules", {"flask_talisman": mock_talisman_module}):
                init_talisman(app)
        mock_talisman_cls.assert_called_once()


# ---------------------------------------------------------------------------
# configure_cors
# ---------------------------------------------------------------------------


class TestConfigureCors:
    def test_configure_cors_with_flask_cors_available(self):
        """configure_cors runs without error when flask_cors is installed."""
        from app.utils.security_headers import configure_cors

        mock_cors_cls = MagicMock()
        mock_cors_module = MagicMock()
        mock_cors_module.CORS = mock_cors_cls

        app = make_app()
        with app.app_context():
            with patch.dict("sys.modules", {"flask_cors": mock_cors_module}):
                configure_cors(app)
        mock_cors_cls.assert_called_once()

    def test_configure_cors_import_error(self):
        """configure_cors handles missing flask_cors gracefully."""
        from app.utils.security_headers import configure_cors

        app = make_app()
        with app.app_context():
            with patch.dict("sys.modules", {"flask_cors": None}):
                configure_cors(app)  # should not raise

    def test_configure_cors_custom_origins(self):
        """configure_cors uses CORS_ORIGINS from config."""
        from app.utils.security_headers import configure_cors

        mock_cors_cls = MagicMock()
        mock_cors_module = MagicMock()
        mock_cors_module.CORS = mock_cors_cls

        app = make_app({"CORS_ORIGINS": ["https://example.com"]})
        with app.app_context():
            with patch.dict("sys.modules", {"flask_cors": mock_cors_module}):
                configure_cors(app)
        call_kwargs = mock_cors_cls.call_args[1]
        assert "https://example.com" in call_kwargs["origins"]


# ---------------------------------------------------------------------------
# validate_content_type decorator
# ---------------------------------------------------------------------------


class TestValidateContentType:
    def _make_test_app(self):
        from app.utils.security_headers import validate_content_type

        app = make_app()

        @app.route("/json-only", methods=["POST"])
        @validate_content_type(["application/json"])
        def json_endpoint():
            return "ok", 200

        @app.route("/default-ct", methods=["POST"])
        @validate_content_type()
        def default_ct_endpoint():
            return "ok", 200

        return app

    def test_valid_content_type_passes(self):
        app = self._make_test_app()
        client = app.test_client()
        resp = client.post("/json-only", content_type="application/json", data="{}")
        assert resp.status_code == 200

    def test_invalid_content_type_returns_415(self):
        app = self._make_test_app()
        client = app.test_client()
        resp = client.post("/json-only", content_type="text/html", data="<html></html>")
        assert resp.status_code == 415

    def test_415_response_contains_error_info(self):
        app = self._make_test_app()
        client = app.test_client()
        resp = client.post("/json-only", content_type="text/plain", data="hello")
        data = resp.get_json()
        assert "error" in data
        assert "allowed" in data

    def test_default_content_type_is_json(self):
        app = self._make_test_app()
        client = app.test_client()
        resp = client.post("/default-ct", content_type="application/json", data="{}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# sanitize_input
# ---------------------------------------------------------------------------


class TestSanitizeInput:
    def test_returns_empty_string_for_none(self):
        from app.utils.security_headers import sanitize_input

        assert sanitize_input(None) == ""

    def test_returns_empty_string_for_empty(self):
        from app.utils.security_headers import sanitize_input

        assert sanitize_input("") == ""

    def test_truncates_to_max_length(self):
        from app.utils.security_headers import sanitize_input

        assert len(sanitize_input("a" * 2000, max_length=100)) == 100

    def test_removes_null_bytes(self):
        from app.utils.security_headers import sanitize_input

        assert "\x00" not in sanitize_input("hello\x00world")

    def test_strips_whitespace(self):
        from app.utils.security_headers import sanitize_input

        assert sanitize_input("  hello  ") == "hello"

    def test_normal_string_unchanged(self):
        from app.utils.security_headers import sanitize_input

        assert sanitize_input("normal string") == "normal string"

    def test_default_max_length_1000(self):
        from app.utils.security_headers import sanitize_input

        result = sanitize_input("x" * 1500)
        assert len(result) == 1000


# ---------------------------------------------------------------------------
# validate_file_upload
# ---------------------------------------------------------------------------


class TestValidateFileUpload:
    def test_valid_extension_returns_true(self):
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("report.pdf") is True

    def test_invalid_extension_returns_false(self):
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("script.exe") is False

    def test_empty_filename_returns_false(self):
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("") is False

    def test_none_filename_returns_false(self):
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload(None) is False

    def test_no_extension_returns_false(self):
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("noextension") is False

    def test_custom_allowed_extensions(self):
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("image.png", {"png", "jpg"}) is True
        assert validate_file_upload("image.gif", {"png", "jpg"}) is False

    @pytest.mark.parametrize("fname", ["data.csv", "report.txt", "backup.json", "sheet.xlsx"])
    def test_default_allowed_extensions(self, fname):
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload(fname) is True

    def test_case_insensitive_extension(self):
        from app.utils.security_headers import validate_file_upload

        assert validate_file_upload("report.PDF") is True
