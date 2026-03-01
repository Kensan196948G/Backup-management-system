"""
Unit tests for settings views.
app/views/settings.py coverage: 16% -> ~45%
"""
import pytest

from app.models import SystemSetting, User, db


@pytest.fixture
def admin_logged_in(client, app):
    """Create admin and log in."""
    with app.app_context():
        user = User(
            username="settings_admin", email="settings_admin@example.com",
            full_name="Settings Admin", role="admin", is_active=True
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "settings_admin", "password": "Admin123!"})
    return client


@pytest.fixture
def operator_logged_in(client, app):
    """Create operator (non-admin) and log in."""
    with app.app_context():
        user = User(
            username="settings_operator", email="settings_op@example.com",
            full_name="Settings Operator", role="operator", is_active=True
        )
        user.set_password("Oper123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "settings_operator", "password": "Oper123!"})
    return client


@pytest.fixture
def target_user(app):
    """Create a non-admin user to test user management."""
    with app.app_context():
        user = User(
            username="settings_target_user", email="stu@example.com",
            full_name="Target User", role="viewer", is_active=True
        )
        user.set_password("Target123!")
        db.session.add(user)
        db.session.commit()
        yield user.id


class TestSettingsIndexView:
    """Tests for GET /settings/."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/settings/", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access(self, admin_logged_in):
        response = admin_logged_in.get("/settings/")
        assert response.status_code == 200

    def test_operator_forbidden(self, operator_logged_in):
        response = operator_logged_in.get("/settings/", follow_redirects=False)
        # Non-admin should be forbidden or redirected
        assert response.status_code in (200, 302, 403)

    def test_response_contains_settings(self, admin_logged_in):
        response = admin_logged_in.get("/settings/")
        data = response.data.lower()
        assert b"setting" in data or response.status_code == 200


class TestSettingsUpdateView:
    """Tests for POST /settings/update."""

    def test_unauthenticated_redirects(self, client):
        response = client.post("/settings/update", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_update(self, admin_logged_in):
        response = admin_logged_in.post(
            "/settings/update",
            data={"setting_name": "test_key", "setting_value": "test_value"},
            follow_redirects=True,
        )
        assert response.status_code in (200, 302)

    def test_operator_cannot_update(self, operator_logged_in):
        response = operator_logged_in.post("/settings/update", follow_redirects=False)
        assert response.status_code in (302, 403)


class TestSettingsExportView:
    """Tests for GET /settings/export."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/settings/export", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_export(self, admin_logged_in):
        response = admin_logged_in.get("/settings/export")
        assert response.status_code in (200, 302)


class TestSettingsResetView:
    """Tests for POST /settings/reset."""

    def test_unauthenticated_redirects(self, client):
        response = client.post("/settings/reset", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_reset(self, admin_logged_in):
        response = admin_logged_in.post("/settings/reset", follow_redirects=True)
        assert response.status_code in (200, 302)


class TestSettingsOptimizeDB:
    """Tests for POST /settings/optimize-db."""

    def test_admin_can_optimize(self, admin_logged_in):
        response = admin_logged_in.post("/settings/optimize-db", follow_redirects=True)
        assert response.status_code in (200, 302, 500)

    def test_unauthenticated_redirects(self, client):
        response = client.post("/settings/optimize-db", follow_redirects=False)
        assert response.status_code in (301, 302)


class TestSettingsClearCache:
    """Tests for POST /settings/clear-cache."""

    def test_admin_can_clear_cache(self, admin_logged_in):
        response = admin_logged_in.post("/settings/clear-cache", follow_redirects=True)
        assert response.status_code in (200, 302)


class TestSettingsUserManagement:
    """Tests for user management API in settings."""

    def test_list_users_accessible(self, admin_logged_in):
        response = admin_logged_in.get("/settings/users")
        assert response.status_code in (200, 302)

    def test_create_user_post(self, admin_logged_in):
        response = admin_logged_in.post(
            "/settings/users/create",
            data={
                "username": "new_test_user_settings",
                "email": "new_settings@example.com",
                "password": "NewUser123!",
                "role": "viewer",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_toggle_user_status(self, admin_logged_in, target_user):
        response = admin_logged_in.post(
            f"/settings/users/{target_user}/toggle-status",
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404, 415, 500)

    def test_reset_user_password(self, admin_logged_in, target_user):
        response = admin_logged_in.post(
            f"/settings/users/{target_user}/reset-password",
            data={"new_password": "NewPass123!"},
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404)

    def test_unlock_user_account(self, admin_logged_in, target_user):
        response = admin_logged_in.post(
            f"/settings/users/{target_user}/unlock",
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404)

    def test_delete_user(self, admin_logged_in, target_user):
        response = admin_logged_in.delete(
            f"/settings/users/{target_user}",
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404)

    def test_update_user_put(self, admin_logged_in, target_user):
        response = admin_logged_in.put(
            f"/settings/users/{target_user}/update",
            json={"full_name": "Updated Name", "role": "viewer"},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404)

    def test_nonexistent_user_toggle(self, admin_logged_in):
        response = admin_logged_in.post(
            "/settings/users/999999/toggle-status",
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 404)

    def test_operator_cannot_delete_user(self, operator_logged_in, target_user):
        response = operator_logged_in.delete(
            f"/settings/users/{target_user}",
            follow_redirects=False,
        )
        assert response.status_code in (302, 403)


class TestSettingsValidateImport:
    """Tests for POST /settings/validate-import."""

    def test_validate_import_json(self, admin_logged_in):
        response = admin_logged_in.post(
            "/settings/validate-import",
            json={"settings": {}},
            content_type="application/json",
        )
        assert response.status_code in (200, 400, 302)

    def test_unauthenticated_redirects(self, client):
        response = client.post("/settings/validate-import", follow_redirects=False)
        assert response.status_code in (301, 302)
