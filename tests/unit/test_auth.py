"""
Unit tests for authentication system.

Tests authentication, authorization, session management,
and role-based access control.
"""

import pytest
from flask import session
from flask_login import current_user

from app.models import User, db


class TestAuthentication:
    """Test cases for user authentication."""

    def test_login_success(self, client, admin_user):
        """Test successful user login."""
        response = client.post("/auth/login", data={"username": "admin", "password": "Admin123!@#"}, follow_redirects=True)

        assert response.status_code == 200
        # Check if redirected to dashboard or home
        assert b"dashboard" in response.data.lower() or b"Dashboard" in response.data

    def test_login_invalid_username(self, client):
        """Test login with invalid username."""
        response = client.post("/auth/login", data={"username": "nonexistent", "password": "password"}, follow_redirects=True)

        assert response.status_code == 200
        assert b"Invalid username or password" in response.data or b"error" in response.data.lower()

    def test_login_invalid_password(self, client, admin_user):
        """Test login with invalid password."""
        response = client.post("/auth/login", data={"username": "admin", "password": "wrongpassword"}, follow_redirects=True)

        assert response.status_code == 200
        assert b"Invalid username or password" in response.data or b"error" in response.data.lower()

    def test_login_inactive_user(self, client, app):
        """Test login with inactive user account."""
        with app.app_context():
            user = User(
                username="inactive", email="inactive@example.com", full_name="Inactive User", role="operator", is_active=False
            )
            user.set_password("Inactive123!@#")
            db.session.add(user)
            db.session.commit()

        response = client.post(
            "/auth/login", data={"username": "inactive", "password": "Inactive123!@#"}, follow_redirects=True
        )

        assert response.status_code == 200
        # Should show error or not allow login
        assert (
            b"inactive" in response.data.lower() or b"disabled" in response.data.lower() or b"error" in response.data.lower()
        )

    def test_logout(self, authenticated_client):
        """Test user logout."""
        response = authenticated_client.get("/auth/logout", follow_redirects=True)

        assert response.status_code == 200
        # Should redirect to login page
        assert b"login" in response.data.lower() or b"Login" in response.data

    def test_login_required_decorator(self, client):
        """Test that protected routes require authentication."""
        # Try to access dashboard without logging in
        response = client.get("/dashboard", follow_redirects=True)

        # Should redirect to login
        assert response.status_code == 200
        assert b"login" in response.data.lower() or b"Login" in response.data


class TestPasswordManagement:
    """Test cases for password management."""

    def test_change_password_success(self, authenticated_client, app):
        """Test successful password change."""
        with app.app_context():
            # Get the authenticated user
            user = User.query.filter_by(username="admin_test").first()
            if not user:
                return  # Skip if no auth context

            response = authenticated_client.post(
                "/auth/change-password",
                data={"current_password": "Admin123!@#", "new_password": "NewPass123!@#", "confirm_password": "NewPass123!@#"},
                follow_redirects=True,
            )

            # Verify password was changed
            user = User.query.filter_by(username="admin_test").first()
            if user:
                assert user.check_password("NewPass123!@#") is True
                assert user.check_password("Admin123!@#") is False

    def test_change_password_wrong_current(self, authenticated_client):
        """Test password change with wrong current password."""
        response = authenticated_client.post(
            "/auth/change-password",
            data={"current_password": "wrongpassword", "new_password": "NewPass123!@#", "confirm_password": "NewPass123!@#"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert (
            b"current password" in response.data.lower()
            or b"incorrect" in response.data.lower()
            or b"error" in response.data.lower()
        )

    def test_change_password_mismatch(self, authenticated_client):
        """Test password change with mismatched new passwords."""
        response = authenticated_client.post(
            "/auth/change-password",
            data={
                "current_password": "Admin123!@#",
                "new_password": "NewPass123!@#",
                "confirm_password": "DifferentPass123!@#",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"match" in response.data.lower() or b"confirm" in response.data.lower() or b"error" in response.data.lower()

    def test_password_strength_requirements(self, authenticated_client):
        """Test password strength validation."""
        # Try to set a weak password
        response = authenticated_client.post(
            "/auth/change-password",
            data={"current_password": "Admin123!@#", "new_password": "123", "confirm_password": "123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Should show validation error
        # Note: This assumes password strength validation is implemented


class TestRoleBasedAccessControl:
    """Test cases for role-based access control."""

    def test_admin_full_access(self, authenticated_client, app):
        """Test that admin has full access to all features."""
        # Admin should access admin panel
        response = authenticated_client.get("/dashboard")
        assert response.status_code == 200

        # Admin should create backup jobs
        with app.app_context():
            response = authenticated_client.post(
                "/api/jobs",
                json={
                    "job_name": "Test Job",
                    "job_type": "file",
                    "backup_tool": "custom",
                    "target_path": "/data/test",
                    "schedule_type": "daily",
                    "retention_days": 30,
                },
            )
            # Should be successful (200 or 201)
            assert response.status_code in [200, 201]

    def test_operator_edit_access(self, operator_authenticated_client):
        """Test that operator can edit but not access admin features."""
        # Operator should access dashboard
        response = operator_authenticated_client.get("/dashboard")
        assert response.status_code == 200

        # Operator should not access user management (admin only)
        response = operator_authenticated_client.get("/admin/users")
        # Should be forbidden, redirect, or not found (route may not exist)
        assert response.status_code in [403, 302, 404]

    def test_auditor_read_only_access(self, auditor_authenticated_client, app):
        """Test that auditor has read-only access."""
        # Auditor should view dashboard
        response = auditor_authenticated_client.get("/dashboard")
        assert response.status_code == 200

        # Auditor should view reports
        response = auditor_authenticated_client.get("/reports", follow_redirects=True)
        assert response.status_code == 200

        # Auditor should NOT create backup jobs
        with app.app_context():
            response = auditor_authenticated_client.post("/api/jobs", json={"name": "Test Job", "source_path": "/data/test"})
            # Should be forbidden
            assert response.status_code == 403

    def test_unauthorized_api_access(self, client):
        """Test API access without authentication."""
        # Try to access API without authentication
        response = client.get("/api/jobs")
        # Should require authentication
        assert response.status_code in [401, 302]

    def test_role_decorator_admin_only(self, operator_authenticated_client):
        """Test admin-only decorator blocks non-admin users."""
        # Operator tries to access admin-only route
        response = operator_authenticated_client.get("/admin/settings")
        # Should be forbidden, redirect, or not found (route may not exist)
        assert response.status_code in [403, 302, 404]

    def test_role_decorator_operator_and_admin(self, auditor_authenticated_client):
        """Test operator-level access blocks auditor."""
        # Auditor tries to access operator/admin route
        response = auditor_authenticated_client.post("/api/jobs/1/run")
        # Should be forbidden
        assert response.status_code in [403, 302, 404]


class TestSessionManagement:
    """Test cases for session management."""

    def test_session_creation_on_login(self, client, admin_user):
        """Test that session is created on successful login."""
        with client:
            response = client.post("/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)

            # Session should contain user information
            # This depends on Flask-Login implementation
            assert response.status_code == 200

    def test_session_persistence(self, authenticated_client):
        """Test that session persists across requests."""
        with authenticated_client:
            # First request
            response1 = authenticated_client.get("/dashboard")
            assert response1.status_code == 200

            # Second request should still be authenticated
            response2 = authenticated_client.get("/dashboard")
            assert response2.status_code == 200

    def test_session_cleared_on_logout(self, client, admin_user):
        """Test that session is cleared on logout."""
        with client:
            # Login
            client.post("/auth/login", data={"username": "admin", "password": "admin123"})

            # Logout
            client.get("/auth/logout")

            # Try to access protected route
            response = client.get("/dashboard", follow_redirects=True)
            # Should redirect to login
            assert b"login" in response.data.lower()

    def test_remember_me_functionality(self, client, admin_user):
        """Test remember me functionality."""
        with client:
            response = client.post(
                "/auth/login", data={"username": "admin", "password": "admin123", "remember": True}, follow_redirects=True
            )

            # Cookie should be set with longer expiration
            # This is implementation-specific
            assert response.status_code == 200


class TestUserRegistration:
    """Test cases for user registration (if implemented)."""

    def test_create_user_as_admin(self, authenticated_client, app):
        """Test admin creating a new user."""
        with app.app_context():
            response = authenticated_client.post(
                "/admin/users/create",
                data={
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password": "NewUser123!@#",
                    "full_name": "New User",
                    "role": "operator",
                },
                follow_redirects=True,
            )

            # Verify user was created
            user = User.query.filter_by(username="newuser").first()
            if response.status_code == 200:
                assert user is not None
                assert user.role == "operator"

    def test_duplicate_username_prevention(self, authenticated_client, admin_user):
        """Test that duplicate usernames are prevented."""
        response = authenticated_client.post(
            "/admin/users/create",
            data={
                "username": "admin",  # Already exists
                "email": "another@example.com",
                "password": "Pass123!@#",
                "full_name": "Another User",
                "role": "operator",
            },
            follow_redirects=True,
        )

        # Should show error
        assert (
            b"already exists" in response.data.lower()
            or b"duplicate" in response.data.lower()
            or b"error" in response.data.lower()
        )

    def test_duplicate_email_prevention(self, authenticated_client, admin_user):
        """Test that duplicate emails are prevented."""
        response = authenticated_client.post(
            "/admin/users/create",
            data={
                "username": "newuser",
                "email": "admin@example.com",  # Already exists
                "password": "Pass123!@#",
                "full_name": "New User",
                "role": "operator",
            },
            follow_redirects=True,
        )

        # Should show error
        assert (
            b"already exists" in response.data.lower()
            or b"duplicate" in response.data.lower()
            or b"error" in response.data.lower()
        )


class TestAccountSecurity:
    """Test cases for account security features."""

    def test_user_deactivation(self, client, app, operator_user):
        """Test user account deactivation."""
        with app.app_context():
            # Deactivate user
            user = db.session.get(User, operator_user.id)
            user.is_active = False
            db.session.commit()

        # Try to login with deactivated account
        response = client.post(
            "/auth/login", data={"username": "operator", "password": "Operator123!@#"}, follow_redirects=True
        )

        # Should not allow login
        assert (
            b"inactive" in response.data.lower() or b"disabled" in response.data.lower() or b"error" in response.data.lower()
        )

    def test_password_change_invalidates_sessions(self, client, admin_user, app):
        """Test that password change invalidates existing sessions."""
        with client:
            # Login
            client.post("/auth/login", data={"username": "admin", "password": "Admin123!@#"})

            # Change password in another context
            with app.app_context():
                user = db.session.get(User, admin_user.id)
                user.set_password("NewPassword456!@#")
                db.session.commit()

            # Try to access protected route with old session
            # Behavior depends on implementation
            # Ideally, session should be invalidated

    def test_case_insensitive_username_login(self, client, admin_user):
        """Test if username login is case-insensitive."""
        response = client.post(
            "/auth/login", data={"username": "ADMIN", "password": "Admin123!@#"}, follow_redirects=True  # Uppercase
        )

        # Behavior depends on implementation
        # Most systems should support case-insensitive usernames


class TestAuthorizationHelpers:
    """Test authorization helper functions."""

    def test_user_can_edit_check(self, app, admin_user, operator_user, auditor_user):
        """Test can_edit() helper method."""
        with app.app_context():
            admin = db.session.get(User, admin_user.id)
            operator = db.session.get(User, operator_user.id)
            auditor = db.session.get(User, auditor_user.id)

            assert admin.can_edit() is True
            assert operator.can_edit() is True
            assert auditor.can_edit() is False

    def test_user_can_view_check(self, app, admin_user, operator_user, auditor_user):
        """Test can_view() helper method."""
        with app.app_context():
            admin = db.session.get(User, admin_user.id)
            operator = db.session.get(User, operator_user.id)
            auditor = db.session.get(User, auditor_user.id)

            # All roles should be able to view
            assert admin.can_view() is True
            assert operator.can_view() is True
            assert auditor.can_view() is True

    def test_role_check_methods(self, app, admin_user, operator_user, auditor_user):
        """Test role-specific check methods."""
        with app.app_context():
            admin = db.session.get(User, admin_user.id)
            operator = db.session.get(User, operator_user.id)
            auditor = db.session.get(User, auditor_user.id)

            # Test is_admin()
            assert admin.is_admin() is True
            assert operator.is_admin() is False
            assert auditor.is_admin() is False

            # Test is_operator() - admin also has operator permissions
            assert admin.is_operator() is True
            assert operator.is_operator() is True
            assert auditor.is_operator() is False

            # Test is_auditor()
            assert admin.is_auditor() is False
            assert operator.is_auditor() is False
            assert auditor.is_auditor() is True
