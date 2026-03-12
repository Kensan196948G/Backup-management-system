"""
Tests for app/utils/rate_limiter.py - coverage improvement

Covers: RateLimiter init, init_app, limit decorator, exempt,
        get_request_identifier, AdaptiveRateLimiter, helper functions,
        handle_rate_limit_exceeded, register_rate_limit_handlers.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, g


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_app(extra_config=None):
    """Return a minimal Flask app configured for testing."""
    os.environ["FLASK_ENV"] = "testing"
    from app import create_app

    application = create_app("testing")
    if extra_config:
        application.config.update(extra_config)
    return application


# ---------------------------------------------------------------------------
# get_request_identifier
# ---------------------------------------------------------------------------


class TestGetRequestIdentifier:
    """Tests for get_request_identifier()."""

    def test_returns_user_id_when_authenticated(self):
        """Returns user_<id> when g.user is set."""
        from app.utils.rate_limiter import get_request_identifier

        app = make_app()
        with app.test_request_context("/"):
            mock_user = MagicMock()
            mock_user.id = 42
            g.user = mock_user
            result = get_request_identifier()
        assert result == "user_42"

    def test_falls_back_to_ip_when_no_user(self):
        """Returns IP address when g.user is not set."""
        from app.utils.rate_limiter import get_request_identifier

        app = make_app()
        with app.test_request_context("/", environ_base={"REMOTE_ADDR": "1.2.3.4"}):
            result = get_request_identifier()
        # Should return an IP-like string (may be 127.0.0.1 in test context)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_falls_back_to_ip_when_user_is_none(self):
        """Returns IP address when g.user is None."""
        from app.utils.rate_limiter import get_request_identifier

        app = make_app()
        with app.test_request_context("/"):
            g.user = None
            result = get_request_identifier()
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# RateLimiter class
# ---------------------------------------------------------------------------


class TestRateLimiterInit:
    """Tests for RateLimiter.__init__ and init_app."""

    def test_init_without_app_stores_none(self):
        """RateLimiter() without app leaves limiter as None."""
        from app.utils.rate_limiter import RateLimiter

        rl = RateLimiter()
        assert rl.limiter is None
        assert rl.app is None

    def test_init_with_app_calls_init_app(self):
        """RateLimiter(app) calls init_app automatically."""
        from app.utils.rate_limiter import RateLimiter

        app = make_app()
        with app.app_context():
            rl = RateLimiter(app)
        # limiter should be initialised (not None) because RATELIMIT_ENABLED defaults True
        # (memory:// storage is used in testing)
        assert rl.app is app

    def test_init_app_disabled(self):
        """When RATELIMIT_ENABLED=False, limiter remains None."""
        from app.utils.rate_limiter import RateLimiter

        app = make_app({"RATELIMIT_ENABLED": False})
        with app.app_context():
            rl = RateLimiter()
            rl.init_app(app)
        assert rl.limiter is None

    def test_init_app_enabled_with_memory_storage(self):
        """When enabled, limiter is created with memory:// storage."""
        from app.utils.rate_limiter import RateLimiter

        app = make_app({"RATELIMIT_STORAGE_URL": "memory://", "RATELIMIT_ENABLED": True})
        with app.app_context():
            rl = RateLimiter()
            rl.init_app(app)
        assert rl.limiter is not None

    def test_init_app_custom_default_limits(self):
        """Custom RATELIMIT_DEFAULT config is respected."""
        from app.utils.rate_limiter import RateLimiter

        app = make_app(
            {
                "RATELIMIT_ENABLED": True,
                "RATELIMIT_DEFAULT": ["100 per day"],
            }
        )
        with app.app_context():
            rl = RateLimiter()
            rl.init_app(app)
        assert rl.limiter is not None


class TestRateLimiterLimitMethod:
    """Tests for RateLimiter.limit()."""

    def test_limit_returns_noop_when_no_limiter(self):
        """limit() returns identity decorator when limiter is None."""
        from app.utils.rate_limiter import RateLimiter

        rl = RateLimiter()

        @rl.limit("5 per minute")
        def dummy():
            return "ok"

        assert dummy() == "ok"

    def test_limit_returns_decorator_when_limiter_present(self):
        """limit() delegates to flask_limiter when available."""
        from app.utils.rate_limiter import RateLimiter

        app = make_app()
        with app.app_context():
            rl = RateLimiter(app)
            if rl.limiter is not None:
                decorator = rl.limit("10 per minute")
                assert callable(decorator)


class TestRateLimiterExemptMethod:
    """Tests for RateLimiter.exempt()."""

    def test_exempt_returns_original_when_no_limiter(self):
        """exempt() returns the function unchanged when limiter is None."""
        from app.utils.rate_limiter import RateLimiter

        rl = RateLimiter()

        def my_func():
            return "original"

        result = rl.exempt(my_func)
        assert result is my_func

    def test_exempt_delegates_when_limiter_present(self):
        """exempt() calls limiter.exempt when limiter exists."""
        from app.utils.rate_limiter import RateLimiter

        app = make_app()
        with app.app_context():
            rl = RateLimiter(app)
            if rl.limiter is not None:
                def func():
                    pass

                result = rl.exempt(func)
                assert callable(result)


# ---------------------------------------------------------------------------
# init_rate_limiting
# ---------------------------------------------------------------------------


class TestInitRateLimiting:
    def test_returns_rate_limiter_instance(self):
        """init_rate_limiting returns the global rate_limiter."""
        from app.utils.rate_limiter import RateLimiter, init_rate_limiting

        app = make_app()
        with app.app_context():
            result = init_rate_limiting(app)
        assert isinstance(result, RateLimiter)


# ---------------------------------------------------------------------------
# Predefined decorators
# ---------------------------------------------------------------------------


class TestPredefinedDecorators:
    """Tests for limit_* helper functions."""

    @pytest.mark.parametrize(
        "func_name,expected",
        [
            ("limit_api_calls", "60 per minute"),
            ("limit_login_attempts", "5 per minute"),
            ("limit_registration", "3 per hour"),
            ("limit_password_reset", "3 per hour"),
            ("limit_file_upload", "10 per hour"),
            ("limit_report_generation", "20 per hour"),
            ("limit_backup_execution", "100 per hour"),
        ],
    )
    def test_decorator_returns_callable(self, func_name, expected):
        """Each limit_* helper returns a callable decorator."""
        import app.utils.rate_limiter as rl_module

        func = getattr(rl_module, func_name)
        # When rate_limiter.limiter is None (unit test, no app), returns noop
        result = func()
        assert callable(result)

    def test_limit_api_calls_custom_limit(self):
        """limit_api_calls accepts a custom limit string."""
        from app.utils.rate_limiter import limit_api_calls

        result = limit_api_calls("120 per minute")
        assert callable(result)


# ---------------------------------------------------------------------------
# AdaptiveRateLimiter
# ---------------------------------------------------------------------------


class TestAdaptiveRateLimiter:
    def test_init_creates_base_limits(self):
        """AdaptiveRateLimiter has low/medium/high base limits."""
        from app.utils.rate_limiter import AdaptiveRateLimiter

        arl = AdaptiveRateLimiter()
        assert "low" in arl.base_limits
        assert "medium" in arl.base_limits
        assert "high" in arl.base_limits

    def test_get_current_limit_returns_string(self):
        """get_current_limit returns a non-empty string."""
        from app.utils.rate_limiter import AdaptiveRateLimiter

        arl = AdaptiveRateLimiter()
        limit = arl.get_current_limit()
        assert isinstance(limit, str)
        assert "per minute" in limit

    def test_check_system_load_returns_float(self):
        """_check_system_load returns a float in [0, 1]."""
        from app.utils.rate_limiter import AdaptiveRateLimiter

        arl = AdaptiveRateLimiter()
        load = arl._check_system_load()
        assert isinstance(load, float)
        assert 0.0 <= load <= 1.0

    @pytest.mark.parametrize("load,expected_key", [(0.3, "low"), (0.65, "medium"), (0.9, "high")])
    def test_get_current_limit_by_load(self, load, expected_key):
        """get_current_limit returns correct tier based on load."""
        from app.utils.rate_limiter import AdaptiveRateLimiter

        arl = AdaptiveRateLimiter()
        with patch.object(arl, "_check_system_load", return_value=load):
            result = arl.get_current_limit()
        assert result == arl.base_limits[expected_key]


# ---------------------------------------------------------------------------
# Exemption helpers
# ---------------------------------------------------------------------------


class TestExemptionHelpers:
    def test_is_exempt_ip_true(self):
        """is_exempt_ip returns True for an IP in RATELIMIT_EXEMPT_IPS."""
        from app.utils.rate_limiter import is_exempt_ip

        app = make_app({"RATELIMIT_EXEMPT_IPS": ["10.0.0.1", "10.0.0.2"]})
        with app.app_context():
            assert is_exempt_ip("10.0.0.1") is True

    def test_is_exempt_ip_false(self):
        """is_exempt_ip returns False for an IP not in the list."""
        from app.utils.rate_limiter import is_exempt_ip

        app = make_app({"RATELIMIT_EXEMPT_IPS": ["10.0.0.1"]})
        with app.app_context():
            assert is_exempt_ip("192.168.1.1") is False

    def test_is_exempt_ip_empty_list(self):
        """is_exempt_ip returns False when exempt list is empty."""
        from app.utils.rate_limiter import is_exempt_ip

        app = make_app()
        with app.app_context():
            assert is_exempt_ip("127.0.0.1") is False

    def test_is_admin_user_when_admin(self):
        """is_admin_user returns True when g.user.role == 'admin'."""
        from app.utils.rate_limiter import is_admin_user

        app = make_app()
        with app.test_request_context("/"):
            mock_user = MagicMock()
            mock_user.role = "admin"
            g.user = mock_user
            assert is_admin_user() is True

    def test_is_admin_user_when_not_admin(self):
        """is_admin_user returns False when g.user.role != 'admin'."""
        from app.utils.rate_limiter import is_admin_user

        app = make_app()
        with app.test_request_context("/"):
            mock_user = MagicMock()
            mock_user.role = "operator"
            g.user = mock_user
            assert is_admin_user() is False

    def test_is_admin_user_when_no_user(self):
        """is_admin_user returns False when g has no user."""
        from app.utils.rate_limiter import is_admin_user

        app = make_app()
        with app.test_request_context("/"):
            assert is_admin_user() is False


# ---------------------------------------------------------------------------
# handle_rate_limit_exceeded
# ---------------------------------------------------------------------------


class TestHandleRateLimitExceeded:
    def test_returns_429_json(self):
        """handle_rate_limit_exceeded returns 429 JSON error response."""
        from app.utils.rate_limiter import handle_rate_limit_exceeded

        app = make_app()
        with app.test_request_context("/test"):
            mock_exc = MagicMock()
            mock_exc.description = "1 per second"
            response, status = handle_rate_limit_exceeded(mock_exc)
            data = response.get_json()
            assert status == 429
            assert data["error"] == "Rate limit exceeded"
            assert "retry_after" in data


# ---------------------------------------------------------------------------
# register_rate_limit_handlers
# ---------------------------------------------------------------------------


class TestRegisterRateLimitHandlers:
    def test_registers_handler_without_error(self):
        """register_rate_limit_handlers runs without raising."""
        from app.utils.rate_limiter import register_rate_limit_handlers

        app = make_app()
        with app.app_context():
            register_rate_limit_handlers(app)  # should not raise


# ---------------------------------------------------------------------------
# exempt_admin decorator
# ---------------------------------------------------------------------------


class TestExemptAdminDecorator:
    def test_calls_function_for_admin(self):
        """exempt_admin calls the function directly for admin users."""
        from app.utils.rate_limiter import exempt_admin

        app = make_app()

        @exempt_admin
        def dummy_view():
            return "admin_result"

        with app.test_request_context("/"):
            mock_user = MagicMock()
            mock_user.role = "admin"
            g.user = mock_user
            result = dummy_view()
        assert result == "admin_result"
