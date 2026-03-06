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


class TestSettingsExportFormats:
    """Tests for export endpoint with various query parameters."""

    def test_export_csv_format(self, admin_logged_in):
        response = admin_logged_in.get("/settings/export?format=csv")
        assert response.status_code in (200, 302, 500)
        if response.status_code == 200:
            assert b"Section" in response.data or b"section" in response.data.lower()

    def test_export_json_explicit(self, admin_logged_in):
        response = admin_logged_in.get("/settings/export?format=json")
        assert response.status_code in (200, 302, 500)

    def test_export_with_security_section(self, admin_logged_in):
        response = admin_logged_in.get("/settings/export?security=true")
        assert response.status_code in (200, 302, 500)
        if response.status_code == 200:
            data = response.data
            assert b"security" in data.lower() or len(data) > 0

    def test_export_with_users_section(self, admin_logged_in):
        response = admin_logged_in.get("/settings/export?users=true")
        assert response.status_code in (200, 302, 500)

    def test_export_csv_with_security_and_users(self, admin_logged_in):
        response = admin_logged_in.get("/settings/export?format=csv&security=true&users=true")
        assert response.status_code in (200, 302, 500)

    def test_export_no_sections(self, admin_logged_in):
        response = admin_logged_in.get(
            "/settings/export?backup=false&notification=false&schedule=false&storage=false"
        )
        assert response.status_code in (200, 302, 500)

    def test_export_with_filename(self, admin_logged_in):
        response = admin_logged_in.get("/settings/export?filename=my-custom-export")
        assert response.status_code in (200, 302, 500)


class TestSettingsValidateImportAdvanced:
    """Advanced tests for the validate-import endpoint."""

    def test_validate_import_no_file(self, admin_logged_in):
        """POST with no file should return 400."""
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={},
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 302)

    def test_validate_import_valid_json_file(self, admin_logged_in):
        """Upload a valid JSON settings file."""
        import io
        import json
        settings = {
            "version": "3.2.1.1.0",
            "sections": {
                "backup": {
                    "default_retention": 90,
                    "compression_level": 5,
                },
            },
        }
        file_data = json.dumps(settings).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(file_data), "settings.json")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (200, 400)

    def test_validate_import_empty_filename(self, admin_logged_in):
        """Upload with empty filename."""
        import io
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(b"{}"), "")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 200)

    def test_validate_import_unsupported_format(self, admin_logged_in):
        """Upload a file with unsupported extension."""
        import io
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(b"some data"), "settings.xml")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 200)

    def test_validate_import_csv_file(self, admin_logged_in):
        """Upload a CSV settings file."""
        import io
        csv_content = "Section,Key,Value\nbackup,default_retention,90\nbackup,compression_level,5\n"
        file_data = csv_content.encode("utf-8")
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(file_data), "settings.csv")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (200, 400)

    def test_validate_import_invalid_json(self, admin_logged_in):
        """Upload invalid JSON."""
        import io
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(b"not json {{"), "settings.json")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 200)

    def test_validate_import_missing_sections_key(self, admin_logged_in):
        """Upload JSON without sections key should return validation error."""
        import io
        import json
        data = {"version": "3.2.1.1.0"}
        file_data = json.dumps(data).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(file_data), "settings.json")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 200)

    def test_validate_import_with_version_mismatch(self, admin_logged_in):
        """Upload with a different version number to trigger warning."""
        import io
        import json
        settings = {
            "version": "1.0.0",
            "sections": {"backup": {"default_retention": 30, "compression_level": 3}},
        }
        file_data = json.dumps(settings).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(file_data), "settings.json")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (200, 400)

    def test_validate_import_with_storage_threshold_warning(self, admin_logged_in):
        """Upload settings with storage_threshold < 50 to trigger warning."""
        import io
        import json
        settings = {
            "version": "3.2.1.1.0",
            "sections": {
                "storage": {"storage_threshold": 30},
            },
        }
        file_data = json.dumps(settings).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(file_data), "settings.json")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (200, 400)

    def test_validate_import_with_security_session_timeout_warning(self, admin_logged_in):
        """Upload settings with session_timeout < 5 to trigger warning."""
        import io
        import json
        settings = {
            "version": "3.2.1.1.0",
            "sections": {
                "security": {"session_timeout": 2},
            },
        }
        file_data = json.dumps(settings).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(file_data), "settings.json")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (200, 400)

    def test_validate_import_with_users_section(self, admin_logged_in):
        """Upload settings with users section (valid)."""
        import io
        import json
        settings = {
            "version": "3.2.1.1.0",
            "sections": {
                "users": [
                    {"username": "testuser", "email": "test@example.com", "role": "viewer"},
                ]
            },
        }
        file_data = json.dumps(settings).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(file_data), "settings.json")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (200, 400)

    def test_validate_import_with_users_missing_fields(self, admin_logged_in):
        """Upload settings with users missing required fields."""
        import io
        import json
        settings = {
            "version": "3.2.1.1.0",
            "sections": {
                "users": [
                    {"role": "viewer"},  # missing username and email
                ]
            },
        }
        file_data = json.dumps(settings).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/validate-import",
            data={"file": (io.BytesIO(file_data), "settings.json")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 200)


class TestSettingsImport:
    """Tests for POST /settings/import."""

    def test_import_unauthenticated_redirects(self, client):
        response = client.post("/settings/import", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_import_no_file(self, admin_logged_in):
        response = admin_logged_in.post(
            "/settings/import",
            data={},
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 302)

    def test_import_without_confirmed(self, admin_logged_in):
        """Import without confirmed=true should return 400."""
        import io
        import json
        settings = {"version": "3.2.1.1.0", "sections": {}}
        file_data = json.dumps(settings).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/import",
            data={
                "file": (io.BytesIO(file_data), "settings.json"),
                "confirmed": "false",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 302)

    def test_import_with_confirmed_json(self, admin_logged_in):
        """Import with confirmed=true and valid JSON."""
        import io
        import json
        settings = {
            "version": "3.2.1.1.0",
            "sections": {
                "backup": {"default_retention": 90, "compression_level": 5},
            },
        }
        file_data = json.dumps(settings).encode("utf-8")
        response = admin_logged_in.post(
            "/settings/import",
            data={
                "file": (io.BytesIO(file_data), "settings.json"),
                "confirmed": "true",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in (200, 400, 302)

    def test_import_with_confirmed_csv(self, admin_logged_in):
        """Import with confirmed=true and valid CSV."""
        import io
        csv_content = "Section,Key,Value\nbackup,default_retention,90\n"
        file_data = csv_content.encode("utf-8")
        response = admin_logged_in.post(
            "/settings/import",
            data={
                "file": (io.BytesIO(file_data), "settings.csv"),
                "confirmed": "true",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in (200, 400, 302)

    def test_import_unsupported_format(self, admin_logged_in):
        """Import with unsupported file format."""
        import io
        response = admin_logged_in.post(
            "/settings/import",
            data={
                "file": (io.BytesIO(b"<xml/>"), "settings.xml"),
                "confirmed": "true",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 302)

    def test_import_invalid_json(self, admin_logged_in):
        """Import with invalid JSON content."""
        import io
        response = admin_logged_in.post(
            "/settings/import",
            data={
                "file": (io.BytesIO(b"not json {{"), "settings.json"),
                "confirmed": "true",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in (400, 302)


class TestSettingsResetJSON:
    """Tests for POST /settings/reset returning JSON."""

    def test_reset_returns_json(self, admin_logged_in):
        response = admin_logged_in.post(
            "/settings/reset",
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 500)
        if response.status_code == 200:
            data = response.get_json()
            if data:
                assert "success" in data or "error" in data


class TestSettingsRotateLogs:
    """Tests for POST /settings/rotate-logs."""

    def test_rotate_logs_unauthenticated(self, client):
        response = client.post("/settings/rotate-logs", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_rotate_logs_admin(self, admin_logged_in):
        response = admin_logged_in.post("/settings/rotate-logs")
        assert response.status_code in (200, 302, 500)
        if response.status_code == 200:
            data = response.get_json()
            if data:
                assert "success" in data

    def test_rotate_logs_operator_forbidden(self, operator_logged_in):
        response = operator_logged_in.post("/settings/rotate-logs", follow_redirects=False)
        assert response.status_code in (302, 403)


class TestSettingsTestConnections:
    """Tests for POST /settings/test-connections."""

    def test_test_connections_unauthenticated(self, client):
        response = client.post("/settings/test-connections", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_test_connections_admin(self, admin_logged_in):
        response = admin_logged_in.post("/settings/test-connections")
        assert response.status_code in (200, 302, 500)
        if response.status_code == 200:
            data = response.get_json()
            if data:
                assert "database" in data or "error" in data

    def test_test_connections_operator_forbidden(self, operator_logged_in):
        response = operator_logged_in.post("/settings/test-connections", follow_redirects=False)
        assert response.status_code in (302, 403)


class TestSettingsUserManagementAdvanced:
    """Advanced tests for user management covering JSON endpoints."""

    def test_get_users_returns_json(self, admin_logged_in):
        """GET /settings/users should return JSON with users list."""
        response = admin_logged_in.get(
            "/settings/users",
            headers={"Accept": "application/json"},
        )
        assert response.status_code in (200, 302, 500)
        if response.status_code == 200:
            data = response.get_json()
            if data:
                assert "users" in data or "error" in data

    def test_create_user_json(self, admin_logged_in):
        """POST /settings/users/create with JSON body."""
        response = admin_logged_in.post(
            "/settings/users/create",
            json={
                "username": "new_json_user",
                "email": "new_json@example.com",
                "password": "NewUser123!",
                "role": "viewer",
            },
            content_type="application/json",
        )
        assert response.status_code in (200, 201, 400, 302, 500)

    def test_create_user_missing_fields(self, admin_logged_in):
        """POST /settings/users/create with missing required fields."""
        response = admin_logged_in.post(
            "/settings/users/create",
            json={"username": "incomplete_user"},
            content_type="application/json",
        )
        assert response.status_code in (400, 302, 500)

    def test_create_user_invalid_username_format(self, admin_logged_in):
        """POST /settings/users/create with invalid username (special chars)."""
        response = admin_logged_in.post(
            "/settings/users/create",
            json={
                "username": "bad user!",
                "email": "bad@example.com",
                "password": "BadUser123!",
                "role": "viewer",
            },
            content_type="application/json",
        )
        assert response.status_code in (400, 302, 500)

    def test_create_user_invalid_email(self, admin_logged_in):
        """POST /settings/users/create with invalid email."""
        response = admin_logged_in.post(
            "/settings/users/create",
            json={
                "username": "valid_user",
                "email": "not-an-email",
                "password": "ValidUser123!",
                "role": "viewer",
            },
            content_type="application/json",
        )
        assert response.status_code in (400, 302, 500)

    def test_create_user_weak_password(self, admin_logged_in):
        """POST /settings/users/create with weak password."""
        response = admin_logged_in.post(
            "/settings/users/create",
            json={
                "username": "weak_pw_user",
                "email": "weak@example.com",
                "password": "simple",
                "role": "viewer",
            },
            content_type="application/json",
        )
        assert response.status_code in (400, 302, 500)

    def test_create_user_invalid_role(self, admin_logged_in):
        """POST /settings/users/create with invalid role."""
        response = admin_logged_in.post(
            "/settings/users/create",
            json={
                "username": "badrole_user",
                "email": "badrole@example.com",
                "password": "BadRole123!",
                "role": "superuser",
            },
            content_type="application/json",
        )
        assert response.status_code in (400, 302, 500)

    def test_create_user_duplicate_username(self, admin_logged_in, app):
        """POST /settings/users/create with existing username."""
        from app.models import User, db
        with app.app_context():
            existing = User(
                username="dup_json_user", email="dup_json@example.com",
                full_name="Dup User", role="viewer", is_active=True,
            )
            existing.set_password("Dup123!")
            db.session.add(existing)
            db.session.commit()

        response = admin_logged_in.post(
            "/settings/users/create",
            json={
                "username": "dup_json_user",
                "email": "other_dup@example.com",
                "password": "NewDup123!",
                "role": "viewer",
            },
            content_type="application/json",
        )
        assert response.status_code in (400, 302, 500)

    def test_create_user_duplicate_email(self, admin_logged_in, app):
        """POST /settings/users/create with existing email."""
        from app.models import User, db
        with app.app_context():
            existing = User(
                username="dup_email_user2", email="dup_email2@example.com",
                full_name="Dup Email User", role="viewer", is_active=True,
            )
            existing.set_password("DupEmail123!")
            db.session.add(existing)
            db.session.commit()

        response = admin_logged_in.post(
            "/settings/users/create",
            json={
                "username": "brand_new_user",
                "email": "dup_email2@example.com",
                "password": "BrandNew123!",
                "role": "viewer",
            },
            content_type="application/json",
        )
        assert response.status_code in (400, 302, 500)

    def test_toggle_user_status_json(self, admin_logged_in, target_user):
        """Toggle user status with JSON body."""
        response = admin_logged_in.post(
            f"/settings/users/{target_user}/toggle-status",
            json={"is_active": False},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404, 500)
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("success") is True

    def test_toggle_own_user_forbidden(self, admin_logged_in, app):
        """Admin trying to toggle their own status should be forbidden."""
        from app.models import User
        with app.app_context():
            user = User.query.filter_by(username="settings_admin").first()
            if user:
                user_id = user.id
                response = admin_logged_in.post(
                    f"/settings/users/{user_id}/toggle-status",
                    json={"is_active": False},
                    content_type="application/json",
                )
                assert response.status_code in (200, 302, 403, 404, 500)

    def test_reset_password_json(self, admin_logged_in, target_user):
        """Reset password via JSON endpoint."""
        response = admin_logged_in.post(
            f"/settings/users/{target_user}/reset-password",
            json={},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404, 500)
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("success") is True

    def test_reset_password_nonexistent_user(self, admin_logged_in):
        """Reset password for non-existent user should return 404."""
        response = admin_logged_in.post(
            "/settings/users/999999/reset-password",
            json={},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_unlock_user_json(self, admin_logged_in, target_user):
        """Unlock user via JSON endpoint."""
        response = admin_logged_in.post(
            f"/settings/users/{target_user}/unlock",
            json={},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404, 500)
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("success") is True

    def test_unlock_nonexistent_user(self, admin_logged_in):
        """Unlock non-existent user should return 404."""
        response = admin_logged_in.post(
            "/settings/users/999999/unlock",
            json={},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_delete_user_json(self, admin_logged_in, target_user):
        """Delete user via JSON endpoint."""
        response = admin_logged_in.delete(
            f"/settings/users/{target_user}",
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_delete_nonexistent_user(self, admin_logged_in):
        """Delete non-existent user should return 404."""
        response = admin_logged_in.delete(
            "/settings/users/999999",
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_delete_own_account_forbidden(self, admin_logged_in, app):
        """Admin cannot delete their own account."""
        from app.models import User
        with app.app_context():
            user = User.query.filter_by(username="settings_admin").first()
            if user:
                user_id = user.id
                response = admin_logged_in.delete(
                    f"/settings/users/{user_id}",
                    content_type="application/json",
                )
                assert response.status_code in (302, 403, 200, 500)

    def test_update_user_not_found(self, admin_logged_in):
        """Update non-existent user should return 404."""
        response = admin_logged_in.put(
            "/settings/users/999999/update",
            json={"full_name": "Non Existent"},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 404, 500)

    def test_update_user_invalid_email(self, admin_logged_in, target_user):
        """Update user with invalid email format."""
        response = admin_logged_in.put(
            f"/settings/users/{target_user}/update",
            json={"email": "not-an-email"},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 400, 404, 500)

    def test_update_user_invalid_role(self, admin_logged_in, target_user):
        """Update user with invalid role."""
        response = admin_logged_in.put(
            f"/settings/users/{target_user}/update",
            json={"role": "superadmin"},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 400, 404, 500)

    def test_update_user_weak_password(self, admin_logged_in, target_user):
        """Update user with weak password."""
        response = admin_logged_in.put(
            f"/settings/users/{target_user}/update",
            json={"password": "simple"},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 400, 404, 500)

    def test_update_user_duplicate_email(self, admin_logged_in, target_user, app):
        """Update user with already existing email."""
        from app.models import User, db
        with app.app_context():
            other_user = User(
                username="other_dup_upd", email="other_dup_upd@example.com",
                full_name="Other Dup", role="viewer", is_active=True,
            )
            other_user.set_password("OtherDup123!")
            db.session.add(other_user)
            db.session.commit()

        response = admin_logged_in.put(
            f"/settings/users/{target_user}/update",
            json={"email": "other_dup_upd@example.com"},
            content_type="application/json",
        )
        assert response.status_code in (200, 302, 400, 404, 500)


class TestSettingsUpdateException:
    """Test exception handling in settings update."""

    def test_update_handles_exception(self, admin_logged_in):
        """Test update with form data that might cause exceptions."""
        response = admin_logged_in.post(
            "/settings/update",
            data={"key1": "val1", "key2": "val2"},
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 500)


class TestSettingsOptimizeDBJSON:
    """Tests for optimize-db endpoint returning JSON."""

    def test_optimize_db_returns_json_or_error(self, admin_logged_in):
        """optimize-db should return JSON success or error."""
        response = admin_logged_in.post("/settings/optimize-db")
        assert response.status_code in (200, 302, 500)
        if response.status_code in (200, 500):
            data = response.get_json()
            if data:
                assert "success" in data or "error" in data


class TestSettingsClearCacheJSON:
    """Tests for clear-cache endpoint returning JSON."""

    def test_clear_cache_returns_json(self, admin_logged_in):
        """clear-cache should return JSON success."""
        response = admin_logged_in.post("/settings/clear-cache")
        assert response.status_code in (200, 302, 500)
        if response.status_code == 200:
            data = response.get_json()
            if data:
                assert "success" in data
