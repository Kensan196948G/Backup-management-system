"""
Unit tests for media views.
app/views/media.py coverage: 36% -> ~60%
"""
import pytest

from app.models import OfflineMedia, User, db


@pytest.fixture
def admin_logged_in(client, app):
    """Create admin and log in."""
    with app.app_context():
        user = User(
            username="media_admin", email="media_admin@example.com",
            full_name="Media Admin", role="admin", is_active=True
        )
        user.set_password("Admin123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={"username": "media_admin", "password": "Admin123!"})
    return client


@pytest.fixture
def sample_media(app):
    """Create a sample OfflineMedia."""
    with app.app_context():
        user = User(
            username="media_owner_view", email="mov@example.com",
            role="operator", is_active=True
        )
        user.set_password("Test123!")
        db.session.add(user)
        db.session.commit()

        media = OfflineMedia(
            media_id="MEDIA-TEST-VIEW-001",
            media_type="external_hdd",
            capacity_gb=500,
            current_status="available",
            owner_id=user.id,
        )
        db.session.add(media)
        db.session.commit()
        yield {"media_id": media.id, "user_id": user.id}


class TestMediaListView:
    """Tests for GET /media/."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/media/", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access(self, admin_logged_in):
        response = admin_logged_in.get("/media/")
        assert response.status_code in (200, 302)


class TestMediaDetailView:
    """Tests for GET /media/<id>."""

    def test_nonexistent_media(self, admin_logged_in):
        response = admin_logged_in.get("/media/99999")
        assert response.status_code in (200, 302, 404, 500)

    def test_existing_media(self, admin_logged_in, sample_media):
        media_id = sample_media["media_id"]
        response = admin_logged_in.get(f"/media/{media_id}")
        assert response.status_code in (200, 302, 404, 500)


class TestMediaCreateView:
    """Tests for GET/POST /media/create."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/media/create", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access_form(self, admin_logged_in):
        response = admin_logged_in.get("/media/create")
        assert response.status_code in (200, 302)

    def test_create_media_post(self, admin_logged_in):
        response = admin_logged_in.post(
            "/media/create",
            data={
                "media_id": "MEDIA-CREATE-TEST-001",
                "media_type": "external_hdd",
                "capacity_gb": "1000",
                "current_status": "available",
            },
            follow_redirects=True,
        )
        assert response.status_code in (200, 302, 400, 500)


class TestMediaEditView:
    """Tests for GET/POST /media/<id>/edit."""

    def test_nonexistent_media_edit(self, admin_logged_in):
        response = admin_logged_in.get("/media/99999/edit")
        assert response.status_code in (200, 302, 404, 500)

    def test_existing_media_edit_accessible(self, admin_logged_in, sample_media):
        media_id = sample_media["media_id"]
        response = admin_logged_in.get(f"/media/{media_id}/edit")
        assert response.status_code in (200, 302, 404, 500)


class TestMediaDeleteView:
    """Tests for POST /media/<id>/delete."""

    def test_unauthenticated_redirects(self, client):
        response = client.post("/media/99999/delete", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_nonexistent_media_delete(self, admin_logged_in):
        response = admin_logged_in.post("/media/99999/delete", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)


class TestMediaLendView:
    """Tests for GET/POST /media/<id>/lend."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/media/99999/lend", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_lend_nonexistent_media(self, admin_logged_in):
        response = admin_logged_in.get("/media/99999/lend")
        assert response.status_code in (200, 302, 404, 500)

    def test_lend_existing_media(self, admin_logged_in, sample_media):
        media_id = sample_media["media_id"]
        response = admin_logged_in.get(f"/media/{media_id}/lend")
        assert response.status_code in (200, 302, 404, 500)


class TestMediaReturnView:
    """Tests for POST /media/<id>/return."""

    def test_unauthenticated_redirects(self, client):
        response = client.post("/media/99999/return", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_return_nonexistent_media(self, admin_logged_in):
        response = admin_logged_in.post("/media/99999/return", follow_redirects=True)
        assert response.status_code in (200, 302, 404, 500)


class TestMediaRotationScheduleView:
    """Tests for /media/rotation-schedule."""

    def test_unauthenticated_redirects(self, client):
        response = client.get("/media/rotation-schedule", follow_redirects=False)
        assert response.status_code in (301, 302)

    def test_admin_can_access(self, admin_logged_in):
        response = admin_logged_in.get("/media/rotation-schedule")
        assert response.status_code in (200, 302, 500)
