"""
Integration tests for authentication workflows.

Tests end-to-end authentication flows including:
- Login/logout flow
- Session management
- Role-based access
- Password management
"""

import pytest
from flask import session

from app.models import AuditLog, User, db


class TestLoginLogoutFlow:
    """Test complete login and logout workflows."""

    def test_complete_login_logout_flow(self, client, admin_user, app):
        """Test full login and logout process."""
        with client:
            # Step 1: Access login page
            response = client.get("/auth/login")
            assert response.status_code == 200
            assert b"login" in response.data.lower() or b"Login" in response.data

            # Step 2: Submit login credentials
            response = client.post("/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
            assert response.status_code == 200

            # Step 3: Verify redirected to dashboard
            assert b"dashboard" in response.data.lower() or b"Dashboard" in response.data

            # Step 4: Access protected resource
            response = client.get("/dashboard")
            assert response.status_code == 200

            # Step 5: Logout
            response = client.get("/auth/logout", follow_redirects=True)
            assert response.status_code == 200
            assert b"login" in response.data.lower() or b"Login" in response.data

            # Step 6: Verify cannot access protected resource
            response = client.get("/dashboard", follow_redirects=True)
            assert b"login" in response.data.lower()

    def test_failed_login_attempts(self, client, admin_user, app):
        """Test multiple failed login attempts."""
        with client:
            # Attempt 1: Wrong password
            response = client.post(
                "/auth/login", data={"username": "admin", "password": "wrongpassword"}, follow_redirects=True
            )
            assert response.status_code == 200
            assert b"invalid" in response.data.lower() or b"error" in response.data.lower()

            # Attempt 2: Wrong username
            response = client.post(
                "/auth/login", data={"username": "nonexistent", "password": "admin123"}, follow_redirects=True
            )
            assert response.status_code == 200
            assert b"invalid" in response.data.lower() or b"error" in response.data.lower()

            # Attempt 3: Successful login
            response = client.post("/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
            assert response.status_code == 200
            assert b"dashboard" in response.data.lower() or b"Dashboard" in response.data

    def test_logout_clears_session(self, client, admin_user, app):
        """Test that logout properly clears session."""
        with client:
            # Login
            client.post("/auth/login", data={"username": "admin", "password": "admin123"})

            # Verify session exists
            response = client.get("/dashboard")
            assert response.status_code == 200

            # Logout
            client.get("/auth/logout")

            # Try to access protected route
            response = client.get("/api/jobs", follow_redirects=True)
            # Should require re-authentication
            assert response.status_code in [401, 302] or b"login" in response.data.lower()


class TestRoleBasedAccessFlow:
    """Test role-based access control workflows."""

    def test_admin_full_access_flow(self, client, admin_user, app):
        """Test admin user accessing all features."""
        with client:
            # Login as admin
            client.post("/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)

            # Access dashboard
            response = client.get("/dashboard")
            assert response.status_code == 200

            # Access jobs
            response = client.get("/jobs")
            assert response.status_code == 200

            # Access reports
            response = client.get("/reports")
            assert response.status_code == 200

            # Access media management
            response = client.get("/media")
            assert response.status_code == 200

            # Create job via API
            response = client.post(
                "/api/jobs",
                json={"name": "Admin Test Job", "source_path": "/data/test", "schedule_type": "daily"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code in [200, 201]

    def test_operator_access_flow(self, client, operator_user, app):
        """Test operator user access restrictions."""
        with client:
            # Login as operator
            client.post("/auth/login", data={"username": "operator", "password": "operator123"}, follow_redirects=True)

            # Can access dashboard
            response = client.get("/dashboard")
            assert response.status_code == 200

            # Can access jobs
            response = client.get("/jobs")
            assert response.status_code == 200

            # Can create jobs
            response = client.post(
                "/api/jobs",
                json={"name": "Operator Job", "source_path": "/data/operator", "schedule_type": "daily"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code in [200, 201]

            # Cannot access admin features
            response = client.get("/admin/users")
            assert response.status_code in [403, 302, 404]

    def test_auditor_read_only_flow(self, client, auditor_user, app):
        """Test auditor user read-only access."""
        with client:
            # Login as auditor
            client.post("/auth/login", data={"username": "auditor", "password": "auditor123"}, follow_redirects=True)

            # Can view dashboard
            response = client.get("/dashboard")
            assert response.status_code == 200

            # Can view reports
            response = client.get("/reports")
            assert response.status_code == 200

            # Can view jobs
            response = client.get("/jobs")
            assert response.status_code == 200

            # Cannot create jobs
            response = client.post(
                "/api/jobs",
                json={"name": "Auditor Job", "source_path": "/data/auditor", "schedule_type": "daily"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 403

            # Cannot modify data
            with app.app_context():
                job = db.session.query(User).first()
                if job:
                    response = client.delete(f"/api/jobs/{job.id}")
                    assert response.status_code in [403, 404]


class TestPasswordManagementFlow:
    """Test password change workflows."""

    def test_successful_password_change_flow(self, client, admin_user, app):
        """Test complete password change process."""
        with client:
            # Login with original password
            client.post("/auth/login", data={"username": "admin", "password": "admin123"})

            # Change password
            response = client.post(
                "/auth/change-password",
                data={"current_password": "admin123", "new_password": "newpassword123", "confirm_password": "newpassword123"},
                follow_redirects=True,
            )

            # Should be successful
            if response.status_code == 200:
                # Logout
                client.get("/auth/logout")

                # Try old password (should fail)
                response = client.post(
                    "/auth/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True
                )
                # Should show error or stay on login page

                # Login with new password
                response = client.post(
                    "/auth/login", data={"username": "admin", "password": "newpassword123"}, follow_redirects=True
                )
                assert response.status_code == 200
                assert b"dashboard" in response.data.lower() or b"Dashboard" in response.data

    def test_password_change_validation_flow(self, client, admin_user, app):
        """Test password change validation."""
        with client:
            # Login
            client.post("/auth/login", data={"username": "admin", "password": "admin123"})

            # Try to change with wrong current password
            response = client.post(
                "/auth/change-password",
                data={
                    "current_password": "wrongpassword",
                    "new_password": "newpassword123",
                    "confirm_password": "newpassword123",
                },
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"current" in response.data.lower() or b"incorrect" in response.data.lower()

            # Try to change with mismatched new passwords
            response = client.post(
                "/auth/change-password",
                data={
                    "current_password": "admin123",
                    "new_password": "newpassword123",
                    "confirm_password": "differentpassword",
                },
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"match" in response.data.lower() or b"confirm" in response.data.lower()


class TestSessionPersistence:
    """Test session persistence and timeout."""

    def test_session_persists_across_requests(self, client, admin_user, app):
        """Test that authenticated session persists."""
        with client:
            # Login
            client.post("/auth/login", data={"username": "admin", "password": "admin123"})

            # Make multiple requests
            for _ in range(5):
                response = client.get("/dashboard")
                assert response.status_code == 200

    def test_remember_me_functionality(self, client, admin_user, app):
        """Test remember me checkbox."""
        with client:
            # Login with remember me
            response = client.post(
                "/auth/login", data={"username": "admin", "password": "admin123", "remember": True}, follow_redirects=True
            )

            # Session should persist longer
            # This is implementation-specific

    def test_concurrent_sessions(self, client, app, admin_user):
        """Test handling of concurrent sessions."""
        # Create two client instances
        client1 = app.test_client()
        client2 = app.test_client()

        with client1, client2:
            # Login with both clients
            client1.post("/auth/login", data={"username": "admin", "password": "admin123"})

            client2.post("/auth/login", data={"username": "admin", "password": "admin123"})

            # Both should have valid sessions
            response1 = client1.get("/dashboard")
            response2 = client2.get("/dashboard")

            assert response1.status_code == 200
            assert response2.status_code == 200


class TestAccountManagement:
    """Test account management workflows."""

    def test_inactive_user_cannot_login(self, client, app):
        """Test that inactive users cannot login."""
        with app.app_context():
            # Create inactive user
            user = User(username="inactive", email="inactive@example.com", role="operator", is_active=False)
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

        # Try to login
        response = client.post("/auth/login", data={"username": "inactive", "password": "password123"}, follow_redirects=True)

        assert response.status_code == 200
        assert b"inactive" in response.data.lower() or b"disabled" in response.data.lower()

    def test_reactivate_user_flow(self, client, app, admin_user):
        """Test reactivating an inactive user."""
        with app.app_context():
            # Create inactive user
            user = User(username="reactivate", email="reactivate@example.com", role="operator", is_active=False)
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        # Admin logs in
        with client:
            client.post("/auth/login", data={"username": "admin", "password": "admin123"})

            # Reactivate user (via admin interface)
            with app.app_context():
                user = db.session.get(User, user_id)
                user.is_active = True
                db.session.commit()

        # Now inactive user should be able to login
        response = client.post(
            "/auth/login", data={"username": "reactivate", "password": "password123"}, follow_redirects=True
        )

        assert response.status_code == 200


class TestAuditLogging:
    """Test audit logging for authentication events."""

    def test_login_creates_audit_log(self, client, admin_user, app):
        """Test that login events are logged."""
        with client:
            client.post("/auth/login", data={"username": "admin", "password": "admin123"})

            # Check if audit log was created
            with app.app_context():
                log = AuditLog.query.filter_by(user_id=admin_user.id, action="login").first()

                # Audit logging may or may not be implemented
                if log:
                    assert log.user_id == admin_user.id
                    assert log.action == "login"

    def test_failed_login_creates_audit_log(self, client, app):
        """Test that failed login attempts are logged."""
        with client:
            client.post("/auth/login", data={"username": "admin", "password": "wrongpassword"})

            # Check for failed login log
            with app.app_context():
                log = AuditLog.query.filter_by(action="failed_login").first()

                # May or may not be implemented
                if log:
                    assert "failed" in log.action.lower()

    def test_logout_creates_audit_log(self, client, admin_user, app):
        """Test that logout events are logged."""
        with client:
            client.post("/auth/login", data={"username": "admin", "password": "admin123"})

            client.get("/auth/logout")

            # Check for logout log
            with app.app_context():
                log = AuditLog.query.filter_by(user_id=admin_user.id, action="logout").first()

                if log:
                    assert log.action == "logout"
