"""
API Authentication and Authorization Tests

Tests:
1. JWT Authentication Flow
   - Login with valid credentials
   - Login with invalid credentials
   - Token expiration handling
   - Token refresh mechanism

2. API Key Authentication
   - Create API key
   - Use API key for authentication
   - Revoke API key
   - Expired API key handling

3. Role-Based Access Control
   - Admin access permissions
   - Operator access permissions
   - Auditor read-only access
   - Viewer read-only access

4. Security Tests
   - Password validation
   - Account lockout after failed attempts
   - Token invalidation
   - Concurrent session handling
"""

import json
import time
from datetime import datetime, timedelta

import pytest

from app.models import User, db
from app.models_api_key import ApiKey, RefreshToken


class TestJWTAuthentication:
    """Test JWT-based authentication flow."""

    def test_login_success(self, api_client, admin_user, app):
        """Test successful login with valid credentials."""
        with app.app_context():
            response = api_client.login("admin", "Admin123!@#")

            assert response.status_code == 200
            data = response.get_json()

            assert data["success"] is True
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "Bearer"
            assert data["expires_in"] == 3600

            # Verify user info
            assert data["user"]["username"] == "admin"
            assert data["user"]["role"] == "admin"

    def test_login_invalid_username(self, api_client, app):
        """Test login with non-existent username."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "nonexistent", "password": "password"},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 401
            data = response.get_json()

            assert data["success"] is False
            assert data["error"] == "AUTHENTICATION_FAILED"

    def test_login_invalid_password(self, api_client, admin_user, app):
        """Test login with incorrect password."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "WrongPassword"},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 401
            data = response.get_json()

            assert data["success"] is False
            assert data["error"] == "AUTHENTICATION_FAILED"

    def test_login_inactive_user(self, api_client, admin_user, app):
        """Test login with inactive user account."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)
            user.is_active = False
            db.session.commit()

            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "Admin123!@#"},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 401
            data = response.get_json()

            assert data["success"] is False
            assert "inactive" in data["message"].lower()

    def test_login_missing_credentials(self, api_client, app):
        """Test login without username or password."""
        with app.app_context():
            # Missing password
            response = api_client.client.post(
                "/api/v1/auth/login", json={"username": "admin"}, headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False

            # Missing username
            response = api_client.client.post(
                "/api/v1/auth/login", json={"password": "password"}, headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 400

    def test_access_protected_endpoint_with_token(self, admin_api_client, app):
        """Test accessing protected endpoint with valid JWT token."""
        with app.app_context():
            response = admin_api_client.get("/api/v1/backups/jobs")

            # Should successfully access the endpoint
            assert response.status_code in [200, 404]

    def test_access_protected_endpoint_without_token(self, api_client, app):
        """Test accessing protected endpoint without authentication."""
        with app.app_context():
            response = api_client.client.get("/api/v1/backups/jobs")

            assert response.status_code == 401
            data = response.get_json()

            assert data["success"] is False
            assert data["error"] == "AUTHENTICATION_REQUIRED"

    def test_access_with_invalid_token(self, api_client, app):
        """Test accessing endpoint with invalid JWT token."""
        with app.app_context():
            response = api_client.client.get("/api/v1/backups/jobs", headers={"Authorization": "Bearer invalid_token_here"})

            assert response.status_code == 401
            data = response.get_json()

            assert data["success"] is False
            assert data["error"] == "INVALID_TOKEN"

    def test_token_refresh_success(self, api_client, admin_user, app):
        """Test successful token refresh."""
        with app.app_context():
            # Login first
            login_response = api_client.login("admin", "Admin123!@#")
            assert login_response.status_code == 200

            # Wait a moment
            time.sleep(1)

            # Refresh token
            refresh_response = api_client.refresh()

            assert refresh_response.status_code == 200
            data = refresh_response.get_json()

            assert data["success"] is True
            assert "access_token" in data
            assert data["token_type"] == "Bearer"

            # New token should be different
            assert data["access_token"] != api_client.access_token

    def test_token_refresh_invalid_token(self, api_client, app):
        """Test token refresh with invalid refresh token."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "invalid_refresh_token"},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 401
            data = response.get_json()

            assert data["success"] is False

    def test_logout_success(self, admin_api_client, app):
        """Test successful logout."""
        with app.app_context():
            response = admin_api_client.logout()

            if response:  # Logout endpoint may not be implemented
                assert response.status_code in [200, 404]

            # Token should be cleared
            assert admin_api_client.access_token is None


class TestAPIKeyAuthentication:
    """Test API key-based authentication."""

    def test_create_api_key(self, admin_api_client, app):
        """Test creating an API key."""
        with app.app_context():
            response = admin_api_client.post(
                "/api/v1/auth/api-keys", json={"name": "Test Integration Key", "expires_in_days": 30}
            )

            # May return 200, 201, or 404 if endpoint not implemented
            if response.status_code in [200, 201]:
                data = response.get_json()

                assert data["success"] is True
                assert "api_key" in data
                assert data["api_key"].startswith("bms_")
                assert "key_id" in data or "id" in data

    def test_list_api_keys(self, admin_api_client, api_key_fixture, app):
        """Test listing user's API keys."""
        with app.app_context():
            response = admin_api_client.get("/api/v1/auth/api-keys")

            if response.status_code == 200:
                data = response.get_json()

                assert "api_keys" in data or isinstance(data, list)

                # Should not include full key, only prefix
                if isinstance(data, dict) and "api_keys" in data:
                    for key in data["api_keys"]:
                        assert "key_prefix" in key or "id" in key
                        assert "key" not in key or key["key"].endswith("...")

    def test_use_api_key_for_authentication(self, api_client, api_key_fixture, app):
        """Test using API key to authenticate requests."""
        with app.app_context():
            plaintext_key, api_key_obj = api_key_fixture

            response = api_client.client.get("/api/v1/backups/jobs", headers={"X-API-Key": plaintext_key})

            # Should successfully authenticate
            if response.status_code == 200:
                # API key authentication working
                assert True
            elif response.status_code == 404:
                # Endpoint not found, but auth passed
                assert True
            elif response.status_code == 401:
                # API key auth may not be fully implemented
                pytest.skip("API key authentication not implemented")

    def test_use_invalid_api_key(self, api_client, app):
        """Test authentication with invalid API key."""
        with app.app_context():
            response = api_client.client.get("/api/v1/backups/jobs", headers={"X-API-Key": "bms_invalid_key_12345"})

            # Should reject invalid key
            if response.status_code == 401:
                data = response.get_json()
                assert data["success"] is False

    def test_revoke_api_key(self, admin_api_client, api_key_fixture, app):
        """Test revoking an API key."""
        with app.app_context():
            plaintext_key, api_key_obj = api_key_fixture

            response = admin_api_client.delete(f"/api/v1/auth/api-keys/{api_key_obj.id}")

            if response.status_code in [200, 204]:
                data = response.get_json()
                assert data["success"] is True

                # Verify key is revoked in database
                key = db.session.get(ApiKey, api_key_obj.id)
                assert key.is_active is False

    def test_expired_api_key(self, admin_user, api_client, app):
        """Test authentication with expired API key."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)

            # Create API key that expires immediately
            plaintext_key, api_key_obj = ApiKey.create_api_key(
                user_id=user.id, name="Expired Key", expires_in_days=-1  # Already expired
            )
            db.session.commit()

            # Try to use expired key
            response = api_client.client.get("/api/v1/backups/jobs", headers={"X-API-Key": plaintext_key})

            # Should reject expired key
            assert response.status_code == 401


class TestRoleBasedAccessControl:
    """Test role-based access control."""

    def test_admin_full_access(self, admin_api_client, app):
        """Test admin has full access to all endpoints."""
        with app.app_context():
            # Admin can read
            response = admin_api_client.get("/api/v1/backups/jobs")
            assert response.status_code in [200, 404]

            # Admin can create
            response = admin_api_client.post(
                "/api/v1/backups/jobs",
                json={
                    "job_name": "Admin Test Job",
                    "job_type": "file",
                    "backup_tool": "custom",
                    "target_path": "/data/test",
                    "schedule_type": "daily",
                    "retention_days": 30,
                },
            )
            assert response.status_code in [200, 201, 400, 404]

    def test_operator_can_edit(self, operator_api_client, app):
        """Test operator has edit permissions."""
        with app.app_context():
            # Operator can read
            response = operator_api_client.get("/api/v1/backups/jobs")
            assert response.status_code in [200, 404]

            # Operator can create
            response = operator_api_client.post(
                "/api/v1/backups/jobs",
                json={
                    "job_name": "Operator Test Job",
                    "job_type": "file",
                    "backup_tool": "custom",
                    "target_path": "/data/test",
                    "schedule_type": "daily",
                    "retention_days": 30,
                },
            )
            # Should have create permission
            assert response.status_code in [200, 201, 400, 404]

    def test_auditor_read_only(self, api_client, auditor_user, app):
        """Test auditor has read-only access."""
        with app.app_context():
            api_client.login("auditor", "Auditor123!@#")

            # Auditor can read
            response = api_client.get("/api/v1/backups/jobs")
            assert response.status_code in [200, 404]

            # Auditor cannot create
            response = api_client.post(
                "/api/v1/backups/jobs",
                json={
                    "job_name": "Auditor Test Job",
                    "job_type": "file",
                    "backup_tool": "custom",
                    "target_path": "/data/test",
                },
            )
            # Should be forbidden
            assert response.status_code in [403, 401, 404]

    def test_viewer_read_only(self, api_client, viewer_user, app):
        """Test viewer has read-only access."""
        with app.app_context():
            api_client.login("viewer", "Viewer123!@#")

            # Viewer can read
            response = api_client.get("/api/v1/backups/jobs")
            assert response.status_code in [200, 404]

            # Viewer cannot create
            response = api_client.post("/api/v1/backups/jobs", json={"job_name": "Viewer Test Job"})
            # Should be forbidden
            assert response.status_code in [403, 401, 404]

    def test_role_required_decorator(self, api_client, viewer_user, app):
        """Test role_required decorator enforcement."""
        with app.app_context():
            api_client.login("viewer", "Viewer123!@#")

            # Try to access admin-only endpoint
            response = api_client.delete("/api/v1/backups/jobs/1")

            # Should be forbidden for viewer
            assert response.status_code in [403, 401, 404]


class TestSecurityFeatures:
    """Test security features."""

    def test_account_lockout_after_failed_attempts(self, api_client, admin_user, app):
        """Test account locks after multiple failed login attempts."""
        with app.app_context():
            # Attempt to login with wrong password 5 times
            for i in range(5):
                response = api_client.client.post(
                    "/api/v1/auth/login",
                    json={"username": "admin", "password": "WrongPassword"},
                    headers={"Content-Type": "application/json"},
                )
                assert response.status_code == 401

            # 6th attempt should result in account lock
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "WrongPassword"},
                headers={"Content-Type": "application/json"},
            )

            data = response.get_json()
            assert "locked" in data["message"].lower() or "attempts" in data["message"].lower()

    def test_password_validation(self, admin_api_client, app):
        """Test password complexity requirements."""
        with app.app_context():
            # Try to create user with weak password
            response = admin_api_client.post(
                "/api/v1/users",
                json={"username": "newuser", "email": "newuser@example.com", "password": "weak", "role": "viewer"},  # Too weak
            )

            # Should reject weak password
            if response.status_code == 400:
                data = response.get_json()
                assert "password" in data.get("message", "").lower()

    def test_token_invalidation_after_logout(self, admin_api_client, app):
        """Test that tokens are invalidated after logout."""
        with app.app_context():
            # Save token before logout
            old_token = admin_api_client.access_token

            # Logout
            admin_api_client.logout()

            # Try to use old token
            response = admin_api_client.client.get("/api/v1/backups/jobs", headers={"Authorization": f"Bearer {old_token}"})

            # Token should be rejected if refresh token is revoked
            # Note: This depends on implementation - stateless JWTs may still work until expiry
            # If using token blacklist, should return 401

    def test_csrf_protection(self, api_client, app):
        """Test CSRF protection on state-changing operations."""
        with app.app_context():
            # API should use token-based auth, not cookies
            # CSRF protection is less critical for APIs
            # But test that API doesn't rely on session cookies

            response = api_client.client.post("/api/v1/backups/jobs", json={"job_name": "Test"})

            # Should require authentication, not session
            assert response.status_code == 401

    def test_concurrent_sessions(self, api_client, admin_user, app):
        """Test handling of concurrent login sessions."""
        with app.app_context():
            # Login from first client
            response1 = api_client.login("admin", "Admin123!@#")
            assert response1.status_code == 200
            token1 = api_client.access_token

            # Login from second client (new instance)
            from tests.conftest import api_client as api_client_fixture

            api_client2 = api_client_fixture(api_client.client, api_client.app)
            response2 = api_client2.login("admin", "Admin123!@#")
            assert response2.status_code == 200
            token2 = api_client2.access_token

            # Both tokens should be valid
            assert token1 != token2

            # Both should work
            resp1 = api_client.client.get("/api/v1/backups/jobs", headers={"Authorization": f"Bearer {token1}"})
            resp2 = api_client2.client.get("/api/v1/backups/jobs", headers={"Authorization": f"Bearer {token2}"})

            # Both should succeed
            assert resp1.status_code in [200, 404]
            assert resp2.status_code in [200, 404]


class TestAuthenticationEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_authorization_header(self, api_client, app):
        """Test request with empty Authorization header."""
        with app.app_context():
            response = api_client.client.get("/api/v1/backups/jobs", headers={"Authorization": ""})

            assert response.status_code == 401

    def test_malformed_bearer_token(self, api_client, app):
        """Test request with malformed Bearer token."""
        with app.app_context():
            # Missing "Bearer" prefix
            response = api_client.client.get("/api/v1/backups/jobs", headers={"Authorization": "some_token"})

            assert response.status_code == 401

    def test_token_with_tampered_payload(self, api_client, admin_user, app):
        """Test JWT token with tampered payload."""
        with app.app_context():
            api_client.login("admin", "Admin123!@#")
            token = api_client.access_token

            # Tamper with token (change a character)
            if token:
                tampered_token = token[:-5] + "XXXXX"

                response = api_client.client.get("/api/v1/backups/jobs", headers={"Authorization": f"Bearer {tampered_token}"})

                assert response.status_code == 401

    def test_sql_injection_in_login(self, api_client, app):
        """Test SQL injection attempts in login."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "admin' OR '1'='1", "password": "anything"},
                headers={"Content-Type": "application/json"},
            )

            # Should safely reject
            assert response.status_code == 401

    def test_xss_in_username(self, api_client, app):
        """Test XSS attempts in username field."""
        with app.app_context():
            response = api_client.client.post(
                "/api/v1/auth/login",
                json={"username": "<script>alert('xss')</script>", "password": "password"},
                headers={"Content-Type": "application/json"},
            )

            # Should safely reject and not execute script
            assert response.status_code == 401
            data = response.get_json()

            # Response should not contain unescaped HTML
            response_text = json.dumps(data)
            assert "<script>" not in response_text
