"""
E2E Test Configuration and Fixtures

Playwright + Flask live server integration for browser-based E2E testing.
The live server runs in a background thread with a dynamically assigned port,
allowing Playwright to drive a real browser against the application.

NOTE: The Flask app fixture is named `e2e_app` (not `app`) to avoid conflicts
with pytest-flask, which auto-pushes a request context when it detects an
`app` fixture.  E2E tests use a real browser via Playwright and do not need
the Flask test client or request context machinery.
"""

import socket
import threading
import time

import pytest

from app import create_app
from app.models import User, db


@pytest.fixture(scope="session")
def e2e_app():
    """Create a Flask app instance configured for E2E testing."""
    application = create_app("testing")
    return application


@pytest.fixture(scope="session")
def live_server(e2e_app):
    """Start a live Flask server in a background thread.

    Uses a dynamically assigned free port to avoid conflicts.
    Yields the base URL (e.g. http://127.0.0.1:PORT).
    """
    # Find an available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]

    server_thread = threading.Thread(
        target=lambda: e2e_app.run(
            host="127.0.0.1", port=port, use_reloader=False, threaded=True
        ),
        daemon=True,
    )
    server_thread.start()

    # Wait for the server to become ready
    for _ in range(30):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("127.0.0.1", port))
                break
        except ConnectionRefusedError:
            time.sleep(0.1)
    else:
        raise RuntimeError(f"Live server did not start on port {port}")

    yield f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def _seed_test_user(e2e_app):
    """Seed an admin user into the database for E2E login tests.

    This runs once per session so all E2E tests share the same user.
    """
    with e2e_app.app_context():
        db.create_all()

        existing = User.query.filter_by(username="e2e_admin").first()
        if not existing:
            user = User(
                username="e2e_admin",
                email="e2e_admin@example.com",
                full_name="E2E Admin",
                role="admin",
                is_active=True,
            )
            user.set_password("E2eTest123!")
            db.session.add(user)
            db.session.commit()


@pytest.fixture(scope="session")
def browser_context_args():
    """Playwright browser context arguments."""
    return {"ignore_https_errors": True}
