"""
Comprehensive unit tests for app/api/alerts.py
Tests all alert management API endpoints.
"""

import pytest

from app.models import Alert, BackupJob, User, db


class TestListAlerts:
    """Tests for GET /api/alerts"""

    def test_list_alerts_authenticated(self, authenticated_client, alerts):
        """GET /api/alerts returns 200 with list and pagination for authenticated user."""
        response = authenticated_client.get("/api/alerts")
        assert response.status_code == 200
        data = response.get_json()
        assert "alerts" in data
        assert "pagination" in data
        assert isinstance(data["alerts"], list)
        assert len(data["alerts"]) == 5
        pagination = data["pagination"]
        assert "page" in pagination
        assert "per_page" in pagination
        assert "total" in pagination
        assert "pages" in pagination

    def test_list_alerts_unauthenticated(self, client):
        """GET /api/alerts returns 401 for unauthenticated user."""
        response = client.get("/api/alerts")
        assert response.status_code == 401

    def test_list_alerts_filter_severity(self, authenticated_client, alerts):
        """GET /api/alerts?severity=critical returns only critical alerts."""
        response = authenticated_client.get("/api/alerts?severity=critical")
        assert response.status_code == 200
        data = response.get_json()
        for alert in data["alerts"]:
            assert alert["severity"] == "critical"

    def test_list_alerts_filter_acknowledged(self, authenticated_client, alerts):
        """GET /api/alerts?is_acknowledged=false returns only unacknowledged alerts."""
        response = authenticated_client.get("/api/alerts?is_acknowledged=false")
        assert response.status_code == 200
        data = response.get_json()
        for alert in data["alerts"]:
            assert alert["is_acknowledged"] is False

    def test_list_alerts_filter_acknowledged_true(self, authenticated_client, alerts):
        """GET /api/alerts?is_acknowledged=true returns only acknowledged alerts."""
        response = authenticated_client.get("/api/alerts?is_acknowledged=true")
        assert response.status_code == 200
        data = response.get_json()
        for alert in data["alerts"]:
            assert alert["is_acknowledged"] is True

    def test_list_alerts_filter_job_id(self, authenticated_client, alerts, backup_job):
        """GET /api/alerts?job_id=X returns only alerts for that job."""
        response = authenticated_client.get(f"/api/alerts?job_id={backup_job.id}")
        assert response.status_code == 200
        data = response.get_json()
        for alert in data["alerts"]:
            assert alert["job_id"] == backup_job.id

    def test_list_alerts_pagination(self, authenticated_client, alerts):
        """GET /api/alerts?page=1&per_page=2 returns limited results."""
        response = authenticated_client.get("/api/alerts?page=1&per_page=2")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["alerts"]) == 2
        assert data["pagination"]["per_page"] == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["has_next"] is True

    def test_list_alerts_no_data(self, authenticated_client):
        """GET /api/alerts with no alerts returns empty list."""
        response = authenticated_client.get("/api/alerts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["alerts"] == []
        assert data["pagination"]["total"] == 0

    def test_list_alerts_filter_alert_type(self, authenticated_client, alerts):
        """GET /api/alerts?alert_type=backup_failure filters by alert type."""
        response = authenticated_client.get("/api/alerts?alert_type=backup_failure")
        assert response.status_code == 200
        data = response.get_json()
        for alert in data["alerts"]:
            assert alert["alert_type"] == "backup_failure"


class TestGetAlert:
    """Tests for GET /api/alerts/<id>"""

    def test_get_alert_authenticated(self, authenticated_client, alerts):
        """GET /api/alerts/<id> returns 200 with alert details."""
        alert_id = alerts[0].id
        response = authenticated_client.get(f"/api/alerts/{alert_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == alert_id
        assert "alert_type" in data
        assert "severity" in data
        assert "title" in data
        assert "message" in data
        assert "is_acknowledged" in data
        assert "created_at" in data

    def test_get_alert_with_job_info(self, authenticated_client, alerts, backup_job):
        """GET /api/alerts/<id> includes job information when job exists."""
        alert_id = alerts[0].id
        response = authenticated_client.get(f"/api/alerts/{alert_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["job"] is not None
        assert data["job"]["id"] == backup_job.id

    def test_get_alert_not_found(self, authenticated_client):
        """GET /api/alerts/99999 returns 404."""
        response = authenticated_client.get("/api/alerts/99999")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "ALERT_NOT_FOUND"

    def test_get_alert_unauthenticated(self, client, alerts):
        """GET /api/alerts/<id> returns 401 for unauthenticated user."""
        alert_id = alerts[0].id
        response = client.get(f"/api/alerts/{alert_id}")
        assert response.status_code == 401


class TestAcknowledgeAlert:
    """Tests for POST /api/alerts/<id>/acknowledge"""

    def test_acknowledge_alert(self, authenticated_client, alerts):
        """POST /api/alerts/<id>/acknowledge returns 200 for unacknowledged alert."""
        # Find an unacknowledged alert (is_acknowledged=False for odd indices)
        unack_alert = next(a for a in alerts if not a.is_acknowledged)
        response = authenticated_client.post(f"/api/alerts/{unack_alert.id}/acknowledge")
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert data["alert_id"] == unack_alert.id
        assert "acknowledged_at" in data

    def test_acknowledge_alert_already_acknowledged(self, authenticated_client, alerts):
        """POST /api/alerts/<id>/acknowledge returns 409 for already acknowledged alert."""
        # Find an already acknowledged alert (is_acknowledged=True for even indices)
        ack_alert = next(a for a in alerts if a.is_acknowledged)
        response = authenticated_client.post(f"/api/alerts/{ack_alert.id}/acknowledge")
        assert response.status_code == 409
        data = response.get_json()
        assert data["error"]["code"] == "ALREADY_ACKNOWLEDGED"

    def test_acknowledge_alert_not_found(self, authenticated_client):
        """POST /api/alerts/99999/acknowledge returns 404."""
        response = authenticated_client.post("/api/alerts/99999/acknowledge")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "ALERT_NOT_FOUND"

    def test_acknowledge_alert_unauthenticated(self, client, alerts):
        """POST /api/alerts/<id>/acknowledge returns 401 for unauthenticated user."""
        unack_alert = next(a for a in alerts if not a.is_acknowledged)
        response = client.post(f"/api/alerts/{unack_alert.id}/acknowledge")
        assert response.status_code == 401

    def test_acknowledge_alert_persists(self, authenticated_client, alerts, app):
        """Acknowledge persists the change in the database."""
        unack_alert = next(a for a in alerts if not a.is_acknowledged)
        alert_id = unack_alert.id
        authenticated_client.post(f"/api/alerts/{alert_id}/acknowledge")
        with app.app_context():
            updated = db.session.get(Alert, alert_id)
            assert updated.is_acknowledged is True
            assert updated.acknowledged_at is not None


class TestUnacknowledgeAlert:
    """Tests for POST /api/alerts/<id>/unacknowledge"""

    def test_unacknowledge_alert(self, authenticated_client, alerts):
        """POST /api/alerts/<id>/unacknowledge returns 200."""
        ack_alert = next(a for a in alerts if a.is_acknowledged)
        response = authenticated_client.post(f"/api/alerts/{ack_alert.id}/unacknowledge")
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert data["alert_id"] == ack_alert.id

    def test_unacknowledge_alert_not_found(self, authenticated_client):
        """POST /api/alerts/99999/unacknowledge returns 404."""
        response = authenticated_client.post("/api/alerts/99999/unacknowledge")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "ALERT_NOT_FOUND"

    def test_unacknowledge_alert_unauthenticated(self, client, alerts):
        """POST /api/alerts/<id>/unacknowledge returns 401."""
        ack_alert = next(a for a in alerts if a.is_acknowledged)
        response = client.post(f"/api/alerts/{ack_alert.id}/unacknowledge")
        assert response.status_code == 401

    def test_unacknowledge_alert_persists(self, authenticated_client, alerts, app):
        """Unacknowledge persists the change in the database."""
        ack_alert = next(a for a in alerts if a.is_acknowledged)
        alert_id = ack_alert.id
        authenticated_client.post(f"/api/alerts/{alert_id}/unacknowledge")
        with app.app_context():
            updated = db.session.get(Alert, alert_id)
            assert updated.is_acknowledged is False
            assert updated.acknowledged_by is None
            assert updated.acknowledged_at is None


class TestAlertsSummary:
    """Tests for GET /api/alerts/summary"""

    def test_alerts_summary(self, authenticated_client, alerts):
        """GET /api/alerts/summary returns 200 with counts."""
        response = authenticated_client.get("/api/alerts/summary")
        assert response.status_code == 200
        data = response.get_json()
        assert "unacknowledged" in data
        assert "acknowledged" in data
        assert "grand_total" in data
        unack = data["unacknowledged"]
        assert "total" in unack
        assert "by_severity" in unack
        assert "by_type" in unack
        severity_counts = unack["by_severity"]
        assert "critical" in severity_counts
        assert "error" in severity_counts
        assert "warning" in severity_counts
        assert "info" in severity_counts

    def test_alerts_summary_unauthenticated(self, client):
        """GET /api/alerts/summary returns 401 for unauthenticated user."""
        response = client.get("/api/alerts/summary")
        assert response.status_code == 401

    def test_alerts_summary_empty(self, authenticated_client):
        """GET /api/alerts/summary with no data returns zeros."""
        response = authenticated_client.get("/api/alerts/summary")
        assert response.status_code == 200
        data = response.get_json()
        assert data["grand_total"] == 0
        assert data["unacknowledged"]["total"] == 0
        assert data["acknowledged"]["total"] == 0

    def test_alerts_summary_grand_total_correct(self, authenticated_client, alerts):
        """GET /api/alerts/summary grand_total equals total alert count."""
        response = authenticated_client.get("/api/alerts/summary")
        assert response.status_code == 200
        data = response.get_json()
        assert data["grand_total"] == len(alerts)


class TestBulkAcknowledge:
    """Tests for POST /api/alerts/bulk-acknowledge"""

    def test_bulk_acknowledge(self, authenticated_client, alerts):
        """POST /api/alerts/bulk-acknowledge with valid alert_ids returns 200."""
        unack_ids = [a.id for a in alerts if not a.is_acknowledged]
        assert len(unack_ids) > 0
        response = authenticated_client.post(
            "/api/alerts/bulk-acknowledge",
            json={"alert_ids": unack_ids},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "acknowledged_count" in data
        assert data["acknowledged_count"] == len(unack_ids)
        assert "acknowledged_at" in data

    def test_bulk_acknowledge_empty_list(self, authenticated_client):
        """POST /api/alerts/bulk-acknowledge with empty list returns 400."""
        response = authenticated_client.post(
            "/api/alerts/bulk-acknowledge",
            json={"alert_ids": []},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_bulk_acknowledge_invalid_format(self, authenticated_client):
        """POST /api/alerts/bulk-acknowledge without alert_ids key returns 400."""
        response = authenticated_client.post(
            "/api/alerts/bulk-acknowledge",
            json={"ids": [1, 2, 3]},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_bulk_acknowledge_unauthenticated(self, client, alerts):
        """POST /api/alerts/bulk-acknowledge returns 401 for unauthenticated user."""
        alert_ids = [a.id for a in alerts]
        response = client.post(
            "/api/alerts/bulk-acknowledge",
            json={"alert_ids": alert_ids},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_bulk_acknowledge_nonexistent_ids(self, authenticated_client):
        """POST /api/alerts/bulk-acknowledge with non-existent IDs returns 200 with 0 count."""
        response = authenticated_client.post(
            "/api/alerts/bulk-acknowledge",
            json={"alert_ids": [99990, 99991, 99992]},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["acknowledged_count"] == 0

    def test_bulk_acknowledge_already_acknowledged(self, authenticated_client, alerts):
        """POST /api/alerts/bulk-acknowledge with already acknowledged alerts returns 200 with 0 count."""
        ack_ids = [a.id for a in alerts if a.is_acknowledged]
        response = authenticated_client.post(
            "/api/alerts/bulk-acknowledge",
            json={"alert_ids": ack_ids},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        # Already acknowledged alerts are not counted again
        assert data["acknowledged_count"] == 0

    def test_bulk_acknowledge_alert_ids_not_list(self, authenticated_client):
        """POST /api/alerts/bulk-acknowledge with non-list alert_ids returns 400."""
        response = authenticated_client.post(
            "/api/alerts/bulk-acknowledge",
            json={"alert_ids": "not-a-list"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
