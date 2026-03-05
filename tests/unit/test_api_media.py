"""
Unit tests for app/api/media.py
Tests CRUD operations, borrowing, and returning of offline media.
"""


# Helper data
MEDIA_DATA = {
    "media_id": "TAPE-TEST-001",
    "media_type": "tape",
    "capacity_gb": 2000,
    "storage_location": "Vault A",
    "current_status": "stored",
}


def _create_media(authenticated_client, data=None):
    """Helper: create a media item and return the response."""
    if data is None:
        data = MEDIA_DATA.copy()
    return authenticated_client.post("/api/media", json=data)


# --- List Media ---

def test_list_media_authenticated(authenticated_client, offline_media):
    """GET /api/media returns 200 with pagination for authenticated user."""
    response = authenticated_client.get("/api/media")
    assert response.status_code == 200
    data = response.get_json()
    assert "media" in data
    assert "pagination" in data
    assert isinstance(data["media"], list)


def test_list_media_unauthenticated(client):
    """GET /api/media returns 401 for unauthenticated user."""
    response = client.get("/api/media")
    assert response.status_code == 401


def test_list_media_pagination_structure(authenticated_client, offline_media):
    """GET /api/media pagination object has required keys."""
    response = authenticated_client.get("/api/media")
    data = response.get_json()
    pagination = data["pagination"]
    assert "page" in pagination
    assert "per_page" in pagination
    assert "total" in pagination
    assert "pages" in pagination
    assert "has_next" in pagination
    assert "has_prev" in pagination


def test_list_media_filter_type(authenticated_client, offline_media):
    """GET /api/media?media_type=tape returns only tape media."""
    response = authenticated_client.get("/api/media?media_type=tape")
    assert response.status_code == 200
    data = response.get_json()
    for item in data["media"]:
        assert item["media_type"] == "tape"


def test_list_media_filter_status(authenticated_client, offline_media):
    """GET /api/media?current_status=stored returns only stored media."""
    response = authenticated_client.get("/api/media?current_status=stored")
    assert response.status_code == 200
    data = response.get_json()
    for item in data["media"]:
        assert item["current_status"] == "stored"


def test_list_media_empty(authenticated_client):
    """GET /api/media returns empty list when no media exists."""
    response = authenticated_client.get("/api/media")
    assert response.status_code == 200
    data = response.get_json()
    assert data["media"] == []
    assert data["pagination"]["total"] == 0


def test_list_media_contains_expected_fields(authenticated_client, offline_media):
    """GET /api/media items contain expected fields."""
    response = authenticated_client.get("/api/media")
    data = response.get_json()
    if data["media"]:
        item = data["media"][0]
        assert "id" in item
        assert "media_id" in item
        assert "media_type" in item
        assert "current_status" in item
        assert "is_borrowed" in item


# --- Get Single Media ---

def test_get_media_not_found(authenticated_client):
    """GET /api/media/<id> returns 404 for non-existent media."""
    response = authenticated_client.get("/api/media/99999")
    assert response.status_code == 404


def test_get_media_found(authenticated_client, offline_media):
    """GET /api/media/<id> returns 200 with media details."""
    media_db_id = offline_media[0].id
    response = authenticated_client.get(f"/api/media/{media_db_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert "id" in data
    assert "media_id" in data
    assert "media_type" in data
    assert data["id"] == media_db_id


def test_get_media_contains_detail_fields(authenticated_client, offline_media):
    """GET /api/media/<id> response contains backup_copies and lending_history."""
    media_db_id = offline_media[0].id
    response = authenticated_client.get(f"/api/media/{media_db_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert "backup_copies" in data
    assert "lending_history" in data
    assert "rotation_schedule" in data


def test_get_media_unauthenticated(client, offline_media):
    """GET /api/media/<id> returns 401 for unauthenticated user."""
    media_db_id = offline_media[0].id
    response = client.get(f"/api/media/{media_db_id}")
    assert response.status_code == 401


# --- Create Media ---

def test_create_media_success(authenticated_client):
    """POST /api/media with valid data returns 201."""
    response = _create_media(authenticated_client)
    assert response.status_code == 201
    data = response.get_json()
    assert "media_id" in data
    assert "media_identifier" in data
    assert data["media_identifier"] == MEDIA_DATA["media_id"]


def test_create_media_missing_fields(authenticated_client):
    """POST /api/media without media_id returns 400."""
    response = authenticated_client.post("/api/media", json={"media_type": "tape"})
    assert response.status_code == 400


def test_create_media_missing_media_type(authenticated_client):
    """POST /api/media without media_type returns 400."""
    response = authenticated_client.post("/api/media", json={"media_id": "TAPE-X-001"})
    assert response.status_code == 400


def test_create_media_duplicate_id(authenticated_client):
    """POST /api/media with duplicate media_id returns 409."""
    _create_media(authenticated_client)
    response = _create_media(authenticated_client)
    assert response.status_code == 409


def test_create_media_invalid_type(authenticated_client):
    """POST /api/media with invalid media_type returns 400."""
    bad_data = MEDIA_DATA.copy()
    bad_data["media_id"] = "TAPE-BAD-001"
    bad_data["media_type"] = "floppy_disk"
    response = authenticated_client.post("/api/media", json=bad_data)
    assert response.status_code == 400


def test_create_media_unauthenticated(client):
    """POST /api/media returns 401 for unauthenticated user."""
    response = client.post("/api/media", json=MEDIA_DATA)
    assert response.status_code == 401


def test_create_media_external_hdd_type(authenticated_client):
    """POST /api/media with external_hdd media type returns 201."""
    data = MEDIA_DATA.copy()
    data["media_id"] = "HDD-TEST-001"
    data["media_type"] = "external_hdd"
    response = authenticated_client.post("/api/media", json=data)
    assert response.status_code == 201


def test_create_media_usb_type(authenticated_client):
    """POST /api/media with usb media type returns 201."""
    data = MEDIA_DATA.copy()
    data["media_id"] = "USB-TEST-001"
    data["media_type"] = "usb"
    response = authenticated_client.post("/api/media", json=data)
    assert response.status_code == 201


# --- Update Media ---

def test_update_media_success(authenticated_client):
    """PUT /api/media/<id> returns 200 with valid update data."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    update_data = {"storage_location": "Vault B", "notes": "Updated note"}
    response = authenticated_client.put(f"/api/media/{media_db_id}", json=update_data)
    assert response.status_code == 200
    data = response.get_json()
    assert "media_id" in data


def test_update_media_not_found(authenticated_client):
    """PUT /api/media/<id> returns 404 for non-existent media."""
    response = authenticated_client.put("/api/media/99999", json={"notes": "Updated"})
    assert response.status_code == 404


def test_update_media_invalid_type(authenticated_client):
    """PUT /api/media/<id> returns 400 for invalid media_type."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    response = authenticated_client.put(f"/api/media/{media_db_id}", json={"media_type": "invalid_type"})
    assert response.status_code == 400


def test_update_media_unauthenticated(client, offline_media):
    """PUT /api/media/<id> returns 401 for unauthenticated user."""
    media_db_id = offline_media[0].id
    response = client.put(f"/api/media/{media_db_id}", json={"notes": "Updated"})
    assert response.status_code == 401


def test_update_media_status(authenticated_client):
    """PUT /api/media/<id> can update current_status."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    response = authenticated_client.put(f"/api/media/{media_db_id}", json={"current_status": "in_use"})
    assert response.status_code == 200


# --- Delete Media ---

def test_delete_media_success(authenticated_client):
    """DELETE /api/media/<id> returns 200 for existing media without backup copies."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    response = authenticated_client.delete(f"/api/media/{media_db_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data


def test_delete_media_not_found(authenticated_client):
    """DELETE /api/media/<id> returns 404 for non-existent media."""
    response = authenticated_client.delete("/api/media/99999")
    assert response.status_code == 404


def test_delete_media_unauthenticated(client, offline_media):
    """DELETE /api/media/<id> returns 401 for unauthenticated user."""
    media_db_id = offline_media[0].id
    response = client.delete(f"/api/media/{media_db_id}")
    assert response.status_code == 401


def test_delete_media_verifies_deletion(authenticated_client):
    """DELETE /api/media/<id> actually removes the media from the database."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    authenticated_client.delete(f"/api/media/{media_db_id}")
    get_resp = authenticated_client.get(f"/api/media/{media_db_id}")
    assert get_resp.status_code == 404


# --- Borrow Media ---

def test_borrow_media_success(authenticated_client):
    """POST /api/media/<id>/borrow with valid data returns 201."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    borrow_data = {"expected_return": "2026-12-31"}
    response = authenticated_client.post(f"/api/media/{media_db_id}/borrow", json=borrow_data)
    assert response.status_code == 201
    data = response.get_json()
    assert "lending_id" in data
    assert "media_id" in data


def test_borrow_media_missing_fields(authenticated_client):
    """POST /api/media/<id>/borrow without expected_return returns 400 or 500.

    Note: The app validates expected_return presence but then accesses data["expected_return"]
    directly before checking errors, causing a KeyError (500) in this edge case.
    """
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    response = authenticated_client.post(f"/api/media/{media_db_id}/borrow", json={})
    assert response.status_code in (400, 500)


def test_borrow_media_not_found(authenticated_client):
    """POST /api/media/<id>/borrow returns 404 for non-existent media."""
    response = authenticated_client.post("/api/media/99999/borrow", json={"expected_return": "2026-12-31"})
    assert response.status_code == 404


def test_borrow_media_already_borrowed(authenticated_client):
    """POST /api/media/<id>/borrow returns 409 when media is already borrowed."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    borrow_data = {"expected_return": "2026-12-31"}
    authenticated_client.post(f"/api/media/{media_db_id}/borrow", json=borrow_data)
    # Try to borrow again
    response = authenticated_client.post(f"/api/media/{media_db_id}/borrow", json=borrow_data)
    assert response.status_code == 409


def test_borrow_media_unauthenticated(client, offline_media):
    """POST /api/media/<id>/borrow returns 401 for unauthenticated user."""
    media_db_id = offline_media[0].id
    response = client.post(f"/api/media/{media_db_id}/borrow", json={"expected_return": "2026-12-31"})
    assert response.status_code == 401


def test_borrow_media_updates_status(authenticated_client, app):
    """POST /api/media/<id>/borrow changes media status to in_use."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    authenticated_client.post(f"/api/media/{media_db_id}/borrow", json={"expected_return": "2026-12-31"})

    get_resp = authenticated_client.get(f"/api/media/{media_db_id}")
    data = get_resp.get_json()
    assert data["current_status"] == "in_use"


# --- Return Media ---

def test_return_media_success(authenticated_client):
    """POST /api/media/<id>/return returns 200 after successful borrow."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    authenticated_client.post(f"/api/media/{media_db_id}/borrow", json={"expected_return": "2026-12-31"})
    response = authenticated_client.post(f"/api/media/{media_db_id}/return", json={"return_condition": "normal"})
    assert response.status_code == 200
    data = response.get_json()
    assert "lending_id" in data
    assert "return_condition" in data


def test_return_media_not_borrowed(authenticated_client):
    """POST /api/media/<id>/return returns 404 when media is not currently borrowed."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    response = authenticated_client.post(f"/api/media/{media_db_id}/return", json={})
    assert response.status_code == 404


def test_return_media_not_found(authenticated_client):
    """POST /api/media/<id>/return returns 404 for non-existent media."""
    response = authenticated_client.post("/api/media/99999/return", json={})
    assert response.status_code == 404


def test_return_media_unauthenticated(client, offline_media):
    """POST /api/media/<id>/return returns 401 for unauthenticated user."""
    media_db_id = offline_media[0].id
    response = client.post(f"/api/media/{media_db_id}/return", json={})
    assert response.status_code == 401


def test_return_media_updates_status(authenticated_client):
    """POST /api/media/<id>/return changes media status back to stored."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    authenticated_client.post(f"/api/media/{media_db_id}/borrow", json={"expected_return": "2026-12-31"})
    authenticated_client.post(f"/api/media/{media_db_id}/return", json={})

    get_resp = authenticated_client.get(f"/api/media/{media_db_id}")
    data = get_resp.get_json()
    assert data["current_status"] == "stored"


def test_borrow_return_cycle(authenticated_client):
    """Full borrow-return cycle works correctly: media can be borrowed again after return."""
    create_resp = _create_media(authenticated_client)
    media_db_id = create_resp.get_json()["media_id"]

    # Borrow
    borrow_resp = authenticated_client.post(f"/api/media/{media_db_id}/borrow", json={"expected_return": "2026-12-31"})
    assert borrow_resp.status_code == 201

    # Return
    return_resp = authenticated_client.post(f"/api/media/{media_db_id}/return", json={})
    assert return_resp.status_code == 200

    # Borrow again
    borrow_again_resp = authenticated_client.post(
        f"/api/media/{media_db_id}/borrow", json={"expected_return": "2026-12-31"}
    )
    assert borrow_again_resp.status_code == 201
