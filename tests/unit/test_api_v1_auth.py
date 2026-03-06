"""
Unit tests for API v1 Authentication endpoints.

Tests:
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET  /api/v1/auth/verify
- GET  /api/v1/auth/api-keys
- POST /api/v1/auth/api-keys
- POST /api/v1/auth/api-keys/<id>/rotate  (new endpoint)
- DELETE /api/v1/auth/api-keys/<id>
- POST /api/v1/auth/change-password
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models import User, db
from app.models_api_key import ApiKey, RefreshToken


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login"""

    def test_login_success(self, api_client, admin_user, app):
        """Valid credentials return access and refresh tokens."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "Admin123!@#"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "Bearer"
            assert data["expires_in"] == 3600
            assert data["user"]["username"] == "admin"

    def test_login_invalid_password(self, api_client, admin_user, app):
        """Wrong password returns 401."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrongpassword"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401
            data = response.get_json()
            assert data["success"] is False
            assert data["error"] == "AUTHENTICATION_FAILED"

    def test_login_nonexistent_user(self, api_client, app):
        """Non-existent username returns 401."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "nobody", "password": "pass"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401

    def test_login_missing_username(self, api_client, app):
        """Missing username returns 400."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"password": "Admin123!@#"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "MISSING_CREDENTIALS"

    def test_login_missing_password(self, api_client, app):
        """Missing password returns 400."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400

    def test_login_no_body(self, api_client, app):
        """No request body returns 400."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "INVALID_REQUEST"

    def test_login_inactive_user(self, api_client, app):
        """Inactive user cannot login."""
        with app.app_context():
            user = User(
                username="inactive_test",
                email="inactive_test@example.com",
                full_name="Inactive",
                role="operator",
                is_active=False,
            )
            user.set_password("Test123!@#")
            db.session.add(user)
            db.session.commit()

            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "inactive_test", "password": "Test123!@#"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401


class TestRefreshEndpoint:
    """Tests for POST /api/v1/auth/refresh"""

    def test_refresh_success(self, api_client, admin_user, app):
        """Valid refresh token returns new access token."""
        with app.app_context():
            # First login to get tokens
            login_response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "Admin123!@#"},
                headers={"Content-Type": "application/json"},
            )
            tokens = login_response.get_json()
            refresh_token = tokens["refresh_token"]

            # Now refresh
            response = api_client.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "access_token" in data
            assert data["expires_in"] == 3600

    def test_refresh_invalid_token(self, api_client, app):
        """Invalid refresh token returns 401."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "invalid.token.here"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401
            data = response.get_json()
            assert data["error"] == "INVALID_TOKEN"

    def test_refresh_missing_token(self, api_client, app):
        """Body without refresh_token field returns 400 MISSING_TOKEN."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/refresh",
                json={"other_field": "value"},  # non-empty but missing refresh_token
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "MISSING_TOKEN"

    def test_refresh_no_body(self, api_client, app):
        """No body returns 400 INVALID_REQUEST."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/refresh",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "INVALID_REQUEST"


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout"""

    def test_logout_with_specific_token(self, admin_api_client, app):
        """Logout with specific refresh token revokes that token."""
        with app.app_context():
            # Get a refresh token first
            login_resp = admin_api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "Admin123!@#"},
                headers={"Content-Type": "application/json"},
            )
            refresh_token = login_resp.get_json()["refresh_token"]

            response = admin_api_client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": refresh_token},
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_logout_all_tokens(self, admin_api_client, app):
        """Logout without token revokes all tokens."""
        with app.app_context():
            response = admin_api_client.post("/api/v1/auth/logout", json={})
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_logout_requires_auth(self, api_client, app):
        """Logout without JWT returns 401."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/logout",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401


class TestVerifyEndpoint:
    """Tests for GET /api/v1/auth/verify"""

    def test_verify_valid_token(self, admin_api_client, app):
        """Valid JWT returns user info."""
        with app.app_context():
            response = admin_api_client.get("/api/v1/auth/verify")
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["valid"] is True
            assert "user" in data
            assert data["user"]["username"] == "admin"

    def test_verify_no_token(self, api_client, app):
        """No JWT returns 401."""
        with app.app_context():
            response = api_client.client.get(
                "/api/v1/auth/verify",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401

    def test_verify_invalid_token(self, api_client, app):
        """Invalid JWT returns 401."""
        with app.app_context():
            response = api_client.client.get(
                "/api/v1/auth/verify",
                headers={"Authorization": "Bearer invalid.token.here"},
            )
            assert response.status_code == 401


class TestApiKeyListEndpoint:
    """Tests for GET /api/v1/auth/api-keys"""

    def test_list_api_keys_empty(self, admin_api_client, app):
        """Returns empty list when no keys exist."""
        with app.app_context():
            response = admin_api_client.get("/api/v1/auth/api-keys")
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert isinstance(data["api_keys"], list)

    def test_list_api_keys_with_keys(self, admin_api_client, api_key_fixture, app):
        """Returns list of keys for authenticated user."""
        with app.app_context():
            response = admin_api_client.get("/api/v1/auth/api-keys")
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert len(data["api_keys"]) >= 1

    def test_list_api_keys_requires_auth(self, api_client, app):
        """Unauthenticated request returns 401."""
        with app.app_context():
            response = api_client.client.get(
                "/api/v1/auth/api-keys",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401


class TestApiKeyCreateEndpoint:
    """Tests for POST /api/v1/auth/api-keys"""

    def test_create_api_key_success(self, admin_api_client, app):
        """Successfully create API key returns key."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/api-keys",
                json={"name": "Test Key", "expires_in_days": 365},
            )
            assert response.status_code == 201
            data = response.get_json()
            assert data["success"] is True
            assert "api_key" in data
            assert data["api_key"].startswith("bms_")
            assert "key_info" in data

    def test_create_api_key_no_expiration(self, admin_api_client, app):
        """Create API key without expiration."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/api-keys",
                json={"name": "Permanent Key"},
            )
            assert response.status_code == 201
            data = response.get_json()
            assert data["success"] is True
            assert data["key_info"]["expires_at"] is None

    def test_create_api_key_missing_name(self, admin_api_client, app):
        """Missing name returns 400."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/api-keys",
                json={"expires_in_days": 30},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "MISSING_NAME"

    def test_create_api_key_invalid_expiration(self, admin_api_client, app):
        """Invalid expiration value returns 400."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/api-keys",
                json={"name": "Bad Exp Key", "expires_in_days": 99999},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "INVALID_EXPIRATION"

    def test_create_api_key_zero_expiration(self, admin_api_client, app):
        """Zero expiration days returns 400."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/api-keys",
                json={"name": "Zero Exp", "expires_in_days": 0},
            )
            assert response.status_code == 400

    def test_create_api_key_no_body(self, admin_api_client, app):
        """No request body returns 400."""
        with app.app_context():
            response = admin_api_client.client.post(
                "/api/v1/auth/api-keys",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_api_client.access_token}"},
            )
            assert response.status_code == 400

    def test_create_api_key_requires_auth(self, api_client, app):
        """Unauthenticated request returns 401."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/api-keys",
                json={"name": "Unauthorized Key"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401


class TestApiKeyRotateEndpoint:
    """Tests for POST /api/v1/auth/api-keys/<id>/rotate (new endpoint)"""

    def test_rotate_api_key_success(self, admin_api_client, api_key_fixture, app):
        """Successfully rotate API key returns new key and revokes old one."""
        with app.app_context():
            plaintext_key, api_key_obj = api_key_fixture
            key_id = api_key_obj.id
            old_prefix = api_key_obj.key_prefix

            response = admin_api_client.post(f"/api/v1/auth/api-keys/{key_id}/rotate")
            assert response.status_code == 201
            data = response.get_json()

            assert data["success"] is True
            assert "api_key" in data
            assert data["api_key"].startswith("bms_")
            assert "key_info" in data
            assert data["revoked_key_id"] == key_id
            # New key should have different prefix
            assert data["key_info"]["id"] != key_id

            # Verify old key is deactivated
            old_key = db.session.get(ApiKey, key_id)
            assert old_key.is_active is False

    def test_rotate_api_key_not_found(self, admin_api_client, app):
        """Non-existent key ID returns 404."""
        with app.app_context():
            response = admin_api_client.post("/api/v1/auth/api-keys/99999/rotate")
            assert response.status_code == 404
            data = response.get_json()
            assert data["error"] == "NOT_FOUND"

    def test_rotate_api_key_already_inactive(self, admin_api_client, api_key_fixture, app):
        """Rotating an inactive key returns 400."""
        with app.app_context():
            plaintext_key, api_key_obj = api_key_fixture
            key_id = api_key_obj.id

            # Deactivate the key first
            key = db.session.get(ApiKey, key_id)
            key.is_active = False
            db.session.commit()

            response = admin_api_client.post(f"/api/v1/auth/api-keys/{key_id}/rotate")
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "KEY_INACTIVE"

    def test_rotate_other_users_key(self, admin_api_client, app, operator_user):
        """Cannot rotate another user's API key."""
        with app.app_context():
            # Create key for operator user
            op_user = db.session.get(User, operator_user.id)
            _, op_key = ApiKey.create_api_key(user_id=op_user.id, name="Operator Key")

            response = admin_api_client.post(f"/api/v1/auth/api-keys/{op_key.id}/rotate")
            # Admin cannot rotate other users' keys (filtered by user_id)
            assert response.status_code == 404

    def test_rotate_api_key_requires_auth(self, api_client, api_key_fixture, app):
        """Unauthenticated request returns 401."""
        with app.app_context():
            _, api_key_obj = api_key_fixture
            response = api_client.client.post(
                f"/api/v1/auth/api-keys/{api_key_obj.id}/rotate",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401

    def test_rotate_preserves_key_name(self, admin_api_client, app):
        """Rotated key inherits original key's name."""
        with app.app_context():
            # Create a key with a specific name
            create_resp = admin_api_client.post(
                "/api/v1/auth/api-keys",
                json={"name": "Production Service Key"},
            )
            key_id = create_resp.get_json()["key_info"]["id"]

            rotate_resp = admin_api_client.post(f"/api/v1/auth/api-keys/{key_id}/rotate")
            assert rotate_resp.status_code == 201
            data = rotate_resp.get_json()
            assert data["key_info"]["name"] == "Production Service Key"

    def test_rotate_preserves_expiration(self, admin_api_client, app):
        """Rotated key preserves expiration (remaining days)."""
        with app.app_context():
            # Create key with 30-day expiration
            create_resp = admin_api_client.post(
                "/api/v1/auth/api-keys",
                json={"name": "Expiring Key", "expires_in_days": 30},
            )
            key_id = create_resp.get_json()["key_info"]["id"]

            rotate_resp = admin_api_client.post(f"/api/v1/auth/api-keys/{key_id}/rotate")
            assert rotate_resp.status_code == 201
            data = rotate_resp.get_json()
            # New key should have expiration set
            assert data["key_info"]["expires_at"] is not None


class TestApiKeyRevokeEndpoint:
    """Tests for DELETE /api/v1/auth/api-keys/<id>"""

    def test_revoke_api_key_success(self, admin_api_client, api_key_fixture, app):
        """Successfully revoke an API key."""
        with app.app_context():
            _, api_key_obj = api_key_fixture
            key_id = api_key_obj.id

            response = admin_api_client.delete(f"/api/v1/auth/api-keys/{key_id}")
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

            # Verify key is revoked
            key = db.session.get(ApiKey, key_id)
            assert key.is_active is False

    def test_revoke_api_key_not_found(self, admin_api_client, app):
        """Non-existent key returns 404."""
        with app.app_context():
            response = admin_api_client.delete("/api/v1/auth/api-keys/99999")
            assert response.status_code == 404

    def test_revoke_other_users_key(self, admin_api_client, app, operator_user):
        """Cannot revoke another user's API key."""
        with app.app_context():
            op_user = db.session.get(User, operator_user.id)
            _, op_key = ApiKey.create_api_key(user_id=op_user.id, name="Op Key")

            response = admin_api_client.delete(f"/api/v1/auth/api-keys/{op_key.id}")
            assert response.status_code == 404

    def test_revoke_api_key_requires_auth(self, api_client, api_key_fixture, app):
        """Unauthenticated request returns 401."""
        with app.app_context():
            _, api_key_obj = api_key_fixture
            response = api_client.client.delete(
                f"/api/v1/auth/api-keys/{api_key_obj.id}",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401


class TestChangePasswordEndpoint:
    """Tests for POST /api/v1/auth/change-password"""

    def test_change_password_success(self, admin_api_client, app):
        """Successfully change password."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/change-password",
                json={"current_password": "Admin123!@#", "new_password": "NewAdmin456!@#"},
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_change_password_wrong_current(self, admin_api_client, app):
        """Wrong current password returns 401."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/change-password",
                json={"current_password": "wrongpassword", "new_password": "NewPass456!@#"},
            )
            assert response.status_code == 401
            data = response.get_json()
            assert data["error"] == "INVALID_PASSWORD"

    def test_change_password_weak_new_password(self, admin_api_client, app):
        """New password too short returns 400."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/change-password",
                json={"current_password": "Admin123!@#", "new_password": "short"},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "WEAK_PASSWORD"

    def test_change_password_missing_fields(self, admin_api_client, app):
        """Missing password fields returns 400."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/change-password",
                json={"current_password": "Admin123!@#"},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "MISSING_PASSWORDS"

    def test_change_password_no_body(self, admin_api_client, app):
        """No request body returns 400."""
        with app.app_context():
            response = admin_api_client.client.post(
                "/api/v1/auth/change-password",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {admin_api_client.access_token}",
                },
            )
            assert response.status_code == 400

    def test_change_password_requires_auth(self, api_client, app):
        """Unauthenticated request returns 401."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/change-password",
                json={"current_password": "old", "new_password": "new12345"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 401

    def test_change_password_revokes_refresh_tokens(self, admin_api_client, app):
        """Password change revokes all existing refresh tokens."""
        with app.app_context():
            # Get user ID
            verify_resp = admin_api_client.get("/api/v1/auth/verify")
            user_id = verify_resp.get_json()["user"]["id"]

            # Change password
            response = admin_api_client.post(
                "/api/v1/auth/change-password",
                json={"current_password": "Admin123!@#", "new_password": "NewAdmin789!@#"},
            )
            assert response.status_code == 200

            # All refresh tokens should be revoked
            active_tokens = RefreshToken.query.filter_by(user_id=user_id, is_revoked=False).count()
            assert active_tokens == 0
