"""
Unit tests for app/auth/decorators.py
認証・認可デコレーターのカバレッジ向上テスト
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone


@pytest.fixture
def app():
    from app import create_app
    application = create_app("testing")
    return application


@pytest.fixture
def client(app):
    return app.test_client()


class TestDecoratorImport:
    """モジュールインポートと基本構造テスト"""

    def test_module_importable(self):
        from app.auth import decorators
        assert decorators is not None

    def test_login_required_exists(self):
        from app.auth.decorators import login_required
        assert callable(login_required)

    def test_role_required_exists(self):
        from app.auth.decorators import role_required
        assert callable(role_required)

    def test_admin_required_exists(self):
        from app.auth.decorators import admin_required
        assert callable(admin_required)

    def test_operator_required_exists(self):
        from app.auth.decorators import operator_required
        assert callable(operator_required)

    def test_viewer_required_exists(self):
        from app.auth.decorators import viewer_required
        assert callable(viewer_required)

    def test_auditor_required_exists(self):
        from app.auth.decorators import auditor_required
        assert callable(auditor_required)

    def test_api_token_required_exists(self):
        from app.auth.decorators import api_token_required
        assert callable(api_token_required)

    def test_check_account_locked_exists(self):
        from app.auth.decorators import check_account_locked
        assert callable(check_account_locked)


class TestCheckAccountLocked:
    """check_account_locked 関数のテスト"""

    def test_account_not_locked_none(self):
        from app.auth.decorators import check_account_locked
        user = MagicMock()
        user.account_locked_until = None
        is_locked, remaining = check_account_locked(user)
        assert is_locked is False
        assert remaining is None

    def test_account_locked_future(self):
        from app.auth.decorators import check_account_locked
        user = MagicMock()
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        user.account_locked_until = future
        is_locked, remaining = check_account_locked(user)
        assert is_locked is True
        assert remaining > 0
        assert remaining <= 300  # 5分以内

    def test_account_lock_expired(self):
        from app.auth.decorators import check_account_locked
        user = MagicMock()
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        user.account_locked_until = past
        is_locked, remaining = check_account_locked(user)
        assert is_locked is False
        assert remaining is None

    def test_account_locked_remaining_time_type(self):
        from app.auth.decorators import check_account_locked
        user = MagicMock()
        user.account_locked_until = datetime.now(timezone.utc) + timedelta(seconds=60)
        is_locked, remaining = check_account_locked(user)
        assert isinstance(remaining, int)


class TestLoginRequired:
    """login_required デコレーターのテスト"""

    def test_login_required_wraps_function(self):
        from app.auth.decorators import login_required

        @login_required
        def view_func():
            return "ok"

        assert callable(view_func)

    def test_login_required_unauthenticated_api(self, app):
        from app.auth.decorators import login_required
        from flask import jsonify

        @login_required
        def api_view():
            return jsonify({"result": "ok"})

        with app.test_request_context("/api/test"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = False
                resp = api_view()
                # 401 JSON レスポンス
                assert resp[1] == 401

    def test_login_required_authenticated_user(self, app):
        from app.auth.decorators import login_required
        from flask import jsonify

        @login_required
        def view_func():
            return jsonify({"result": "ok"})

        with app.test_request_context("/dashboard"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = True
                resp = view_func()
                assert resp.status_code == 200


class TestRoleRequired:
    """role_required デコレーターのテスト"""

    def test_role_required_returns_decorator(self):
        from app.auth.decorators import role_required
        decorator = role_required("admin")
        assert callable(decorator)

    def test_role_required_wraps_function(self):
        from app.auth.decorators import role_required

        @role_required("admin")
        def admin_view():
            return "admin"

        assert callable(admin_view)

    def test_role_required_unauthenticated_api(self, app):
        from app.auth.decorators import role_required
        from flask import jsonify

        @role_required("admin")
        def view():
            return jsonify({"ok": True})

        with app.test_request_context("/api/admin"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = False
                resp = view()
                assert resp[1] == 401

    def test_role_required_wrong_role_api(self, app):
        from app.auth.decorators import role_required
        from flask import jsonify

        @role_required("admin")
        def view():
            return jsonify({"ok": True})

        with app.test_request_context("/api/admin"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = True
                mock_user.has_any_role = MagicMock(return_value=False)
                resp = view()
                assert resp[1] == 403

    def test_role_required_correct_role(self, app):
        from app.auth.decorators import role_required
        from flask import jsonify

        @role_required("admin")
        def view():
            return jsonify({"ok": True})

        with app.test_request_context("/dashboard"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = True
                mock_user.has_any_role.return_value = True
                resp = view()
                assert resp.status_code == 200


class TestAdminRequired:
    """admin_required デコレーターのテスト"""

    def test_admin_required_wraps_correctly(self, app):
        from app.auth.decorators import admin_required
        from flask import jsonify

        @admin_required
        def admin_view():
            return jsonify({"role": "admin"})

        with app.test_request_context("/api/admin"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = True
                mock_user.has_any_role.return_value = True
                resp = admin_view()
                assert resp.status_code == 200


class TestOperatorRequired:
    """operator_required デコレーターのテスト"""

    def test_operator_required_wraps_correctly(self, app):
        from app.auth.decorators import operator_required
        from flask import jsonify

        @operator_required
        def op_view():
            return jsonify({"role": "operator"})

        with app.test_request_context("/api/op"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = True
                mock_user.has_any_role.return_value = True
                resp = op_view()
                assert resp.status_code == 200


class TestAccountActiveRequired:
    """account_active_required デコレーターのテスト"""

    def test_account_active_required_exists(self):
        from app.auth import decorators
        assert hasattr(decorators, "account_active_required")

    def test_inactive_account_api(self, app):
        from app.auth.decorators import account_active_required
        from flask import jsonify

        @account_active_required
        def view():
            return jsonify({"ok": True})

        with app.test_request_context("/api/test"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = True
                mock_user.is_active = False
                resp = view()
                assert resp[1] == 403

    def test_active_account_allowed(self, app):
        from app.auth.decorators import account_active_required
        from flask import jsonify

        @account_active_required
        def view():
            return jsonify({"ok": True})

        with app.test_request_context("/dashboard"):
            with patch("app.auth.decorators.current_user") as mock_user:
                mock_user.is_authenticated = True
                mock_user.is_active = True
                resp = view()
                assert resp.status_code == 200
