"""
Unit tests for reports API endpoints.
app/api/reports.py coverage target: 60%+
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models import Report, User, db


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client(client, app):
    """Create admin user and return authenticated client."""
    with app.app_context():
        user = User(
            username="reports_api_admin",
            email="reports_api_admin@example.com",
            full_name="Reports API Admin",
            role="admin",
            is_active=True,
        )
        user.set_password("Admin123!@#")
        db.session.add(user)
        db.session.commit()

    client.post(
        "/auth/login",
        data={"username": "reports_api_admin", "password": "Admin123!@#"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def sample_report(app, auth_client):
    """Create a single Report record for tests."""
    from datetime import date, timedelta

    with app.app_context():
        user = User.query.filter_by(username="reports_api_admin").first()
        report = Report(
            report_type="compliance",
            report_title="Test Compliance Report",
            date_from=(date.today() - timedelta(days=7)),
            date_to=date.today(),
            file_format="html",
            file_path=None,
            generated_by=user.id,
        )
        db.session.add(report)
        db.session.commit()
        db.session.refresh(report)
        yield report


# ---------------------------------------------------------------------------
# Tests: GET /api/reports
# ---------------------------------------------------------------------------

class TestListReports:
    def test_list_reports_authenticated(self, auth_client, sample_report):
        """Authenticated request returns 200 with list and pagination."""
        response = auth_client.get("/api/reports")
        assert response.status_code == 200
        data = response.get_json()
        assert "reports" in data
        assert "pagination" in data
        assert isinstance(data["reports"], list)

    def test_list_reports_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/reports")
        assert response.status_code == 401

    def test_list_reports_empty(self, auth_client):
        """Returns empty list when no reports exist."""
        response = auth_client.get("/api/reports")
        assert response.status_code == 200
        data = response.get_json()
        assert data["reports"] == []

    def test_list_reports_filter_by_type(self, auth_client, sample_report):
        """Filter by report_type returns matching reports."""
        response = auth_client.get("/api/reports?report_type=compliance")
        assert response.status_code == 200
        data = response.get_json()
        for r in data["reports"]:
            assert r["report_type"] == "compliance"

    def test_list_reports_pagination_structure(self, auth_client, sample_report):
        """Pagination structure contains required keys."""
        response = auth_client.get("/api/reports?page=1&per_page=10")
        assert response.status_code == 200
        data = response.get_json()
        pagination = data["pagination"]
        assert "page" in pagination
        assert "per_page" in pagination
        assert "total" in pagination
        assert "pages" in pagination

    def test_list_reports_has_file_field(self, auth_client, sample_report):
        """Each report entry includes the has_file field."""
        response = auth_client.get("/api/reports")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["reports"]) >= 1
        assert "has_file" in data["reports"][0]


# ---------------------------------------------------------------------------
# Tests: GET /api/reports/<id>
# ---------------------------------------------------------------------------

class TestGetReport:
    def test_get_report_found(self, auth_client, sample_report):
        """Returns 200 with report details for a valid ID."""
        response = auth_client.get(f"/api/reports/{sample_report.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == sample_report.id
        assert data["report_type"] == "compliance"

    def test_get_report_not_found(self, auth_client):
        """Returns 404 for non-existent report ID."""
        response = auth_client.get("/api/reports/999999")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "REPORT_NOT_FOUND"

    def test_get_report_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/reports/1")
        assert response.status_code == 401

    def test_get_report_contains_dates(self, auth_client, sample_report):
        """Report details include date_from and date_to fields."""
        response = auth_client.get(f"/api/reports/{sample_report.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "date_from" in data
        assert "date_to" in data
        assert "has_file" in data


# ---------------------------------------------------------------------------
# Tests: POST /api/reports/generate
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def _make_mock_generator(self, report_id=1):
        """Create a mock ReportGenerator that returns success."""
        mock_instance = MagicMock()
        mock_instance.generate_compliance_report.return_value = {
            "success": True,
            "report_id": report_id,
            "file_path": "/tmp/test_report.html",
        }
        mock_instance.generate_operational_report.return_value = {
            "success": True,
            "report_id": report_id,
            "file_path": "/tmp/test_report.html",
        }
        mock_instance.generate_audit_report.return_value = {
            "success": True,
            "report_id": report_id,
            "file_path": "/tmp/test_report.html",
        }
        return mock_instance

    def test_generate_compliance_report_success(self, auth_client):
        """Valid POST generates compliance report and returns 201."""
        mock_instance = self._make_mock_generator()
        with patch("app.api.reports.ReportGenerator") as mock_rg:
            mock_rg.return_value = mock_instance
            response = auth_client.post(
                "/api/reports/generate",
                json={
                    "report_type": "compliance",
                    "date_from": "2026-01-01",
                    "date_to": "2026-01-31",
                    "file_format": "html",
                },
            )
        assert response.status_code == 201
        data = response.get_json()
        assert "report_id" in data
        assert data["report_type"] == "compliance"

    def test_generate_operational_report_success(self, auth_client):
        """Valid POST generates operational report and returns 201."""
        mock_instance = self._make_mock_generator(report_id=2)
        with patch("app.api.reports.ReportGenerator") as mock_rg:
            mock_rg.return_value = mock_instance
            response = auth_client.post(
                "/api/reports/generate",
                json={
                    "report_type": "operational",
                    "date_from": "2026-01-01",
                    "date_to": "2026-01-31",
                    "file_format": "html",
                },
            )
        assert response.status_code == 201

    def test_generate_audit_report_success(self, auth_client):
        """Valid POST generates audit report and returns 201."""
        mock_instance = self._make_mock_generator(report_id=3)
        with patch("app.api.reports.ReportGenerator") as mock_rg:
            mock_rg.return_value = mock_instance
            response = auth_client.post(
                "/api/reports/generate",
                json={
                    "report_type": "audit",
                    "date_from": "2026-01-01",
                    "date_to": "2026-01-31",
                    "file_format": "pdf",
                },
            )
        assert response.status_code == 201

    def test_generate_daily_report_success(self, auth_client):
        """Daily report type uses operational generator."""
        mock_instance = self._make_mock_generator()
        with patch("app.api.reports.ReportGenerator") as mock_rg:
            mock_rg.return_value = mock_instance
            response = auth_client.post(
                "/api/reports/generate",
                json={
                    "report_type": "daily",
                    "date_from": "2026-01-01",
                    "date_to": "2026-01-01",
                    "file_format": "csv",
                },
            )
        assert response.status_code == 201

    def test_generate_report_missing_fields(self, auth_client):
        """Missing required fields returns 400."""
        response = auth_client.post("/api/reports/generate", json={})
        assert response.status_code == 400
        data = response.get_json()
        assert "errors" in data or "error" in data

    def test_generate_report_missing_report_type(self, auth_client):
        """Missing report_type field returns 400."""
        response = auth_client.post(
            "/api/reports/generate",
            json={
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "file_format": "html",
            },
        )
        assert response.status_code == 400

    def test_generate_report_invalid_type(self, auth_client):
        """Invalid report_type returns 400."""
        response = auth_client.post(
            "/api/reports/generate",
            json={
                "report_type": "invalid_type",
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "file_format": "html",
            },
        )
        assert response.status_code == 400

    def test_generate_report_invalid_format(self, auth_client):
        """Invalid file_format returns 400."""
        response = auth_client.post(
            "/api/reports/generate",
            json={
                "report_type": "compliance",
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "file_format": "xlsx",
            },
        )
        assert response.status_code == 400

    def test_generate_report_invalid_dates(self, auth_client):
        """Invalid date format returns 400."""
        response = auth_client.post(
            "/api/reports/generate",
            json={
                "report_type": "compliance",
                "date_from": "01/01/2026",
                "date_to": "31/01/2026",
                "file_format": "html",
            },
        )
        assert response.status_code == 400

    def test_generate_report_date_range_reversed(self, auth_client):
        """date_from after date_to returns 400."""
        response = auth_client.post(
            "/api/reports/generate",
            json={
                "report_type": "compliance",
                "date_from": "2026-01-31",
                "date_to": "2026-01-01",
                "file_format": "html",
            },
        )
        assert response.status_code == 400

    def test_generate_report_generator_failure(self, auth_client):
        """Generator returning success=False results in 500."""
        mock_instance = MagicMock()
        mock_instance.generate_compliance_report.return_value = {
            "success": False,
            "error": "Database error during generation",
        }
        with patch("app.api.reports.ReportGenerator") as mock_rg:
            mock_rg.return_value = mock_instance
            response = auth_client.post(
                "/api/reports/generate",
                json={
                    "report_type": "compliance",
                    "date_from": "2026-01-01",
                    "date_to": "2026-01-31",
                    "file_format": "html",
                },
            )
        assert response.status_code == 500

    def test_generate_report_unauthenticated(self, client):
        """Unauthenticated POST returns 401."""
        response = client.post(
            "/api/reports/generate",
            json={
                "report_type": "compliance",
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "file_format": "html",
            },
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /api/reports/<id>/download
# ---------------------------------------------------------------------------

class TestDownloadReport:
    def test_download_report_not_found(self, auth_client):
        """Returns 404 for non-existent report ID."""
        response = auth_client.get("/api/reports/999999/download")
        assert response.status_code == 404

    def test_download_report_no_file_path(self, auth_client, sample_report):
        """Report with no file_path returns 404 FILE_NOT_FOUND."""
        # sample_report has file_path=None
        response = auth_client.get(f"/api/reports/{sample_report.id}/download")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "FILE_NOT_FOUND"

    def test_download_report_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/reports/1/download")
        assert response.status_code == 401

    def test_download_report_nonexistent_file(self, auth_client, app):
        """Report with non-existent file_path returns 404 FILE_NOT_FOUND."""
        from datetime import date, timedelta

        with app.app_context():
            user = User.query.filter_by(username="reports_api_admin").first()
            report = Report(
                report_type="operational",
                report_title="Ghost Report",
                date_from=(date.today() - timedelta(days=3)),
                date_to=date.today(),
                file_format="pdf",
                file_path="/nonexistent/path/report.pdf",
                generated_by=user.id,
            )
            db.session.add(report)
            db.session.commit()
            report_id = report.id

        response = auth_client.get(f"/api/reports/{report_id}/download")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "FILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# Tests: GET /api/reports/types
# ---------------------------------------------------------------------------

class TestGetReportTypes:
    def test_get_report_types_authenticated(self, auth_client):
        """Returns 200 with list of report types."""
        response = auth_client.get("/api/reports/types")
        assert response.status_code == 200
        data = response.get_json()
        assert "report_types" in data
        assert "supported_formats" in data
        assert len(data["report_types"]) >= 1

    def test_get_report_types_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/reports/types")
        assert response.status_code == 401
