"""
Unit tests for ComplianceChecker report generation methods
(check_job_compliance, generate_system_report, generate_csv_report, format_email_body)
"""
import pytest
from unittest.mock import MagicMock, patch


class TestCheckJobCompliance:
    """Tests for check_job_compliance() method"""

    def test_check_job_compliance_not_found(self, app):
        """Non-existent job returns error dict"""
        with app.app_context():
            with patch("app.services.compliance_checker.db") as mock_db:
                mock_db.session.get.return_value = None
                from app.services.compliance_checker import ComplianceChecker
                checker = ComplianceChecker()
                result = checker.check_job_compliance(9999)
                assert "error" in result

    def test_check_job_compliance_fully_compliant(self, app):
        """Fully compliant job: 3+ copies, 2+ media types, offsite copy, offline media"""
        with app.app_context():
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.job_name = "Test Job"

            mock_copies = []
            for i, (ctype, mtype) in enumerate([
                ("offsite", "cloud"),
                ("primary", "disk"),
                ("secondary", "tape"),
            ]):
                copy = MagicMock()
                copy.copy_type = ctype
                copy.media_type = mtype
                mock_copies.append(copy)

            with patch("app.services.compliance_checker.db") as mock_db, \
                 patch("app.services.compliance_checker.BackupCopy") as mock_bc, \
                 patch("app.services.compliance_checker.OfflineMedia") as mock_om:

                mock_db.session.get.return_value = mock_job
                mock_bc.query.filter_by.return_value.all.return_value = mock_copies
                mock_om.query.filter_by.return_value.count.return_value = 2

                from app.services.compliance_checker import ComplianceChecker
                checker = ComplianceChecker()
                result = checker.check_job_compliance(1)

                assert result["job_id"] == 1
                assert result["is_compliant"] is True
                assert len(result["violations"]) == 0
                assert "checked_at" in result

    def test_check_job_compliance_insufficient_copies(self, app):
        """Job with fewer than 3 copies is non-compliant"""
        with app.app_context():
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.job_name = "Test Job"

            copy = MagicMock()
            copy.copy_type = "offsite"
            copy.media_type = "cloud"

            with patch("app.services.compliance_checker.db") as mock_db, \
                 patch("app.services.compliance_checker.BackupCopy") as mock_bc, \
                 patch("app.services.compliance_checker.OfflineMedia") as mock_om:

                mock_db.session.get.return_value = mock_job
                mock_bc.query.filter_by.return_value.all.return_value = [copy]
                mock_om.query.filter_by.return_value.count.return_value = 1

                from app.services.compliance_checker import ComplianceChecker
                checker = ComplianceChecker()
                result = checker.check_job_compliance(1)

                assert result["is_compliant"] is False
                assert any("コピー数不足" in v for v in result["violations"])

    def test_check_job_compliance_no_offsite(self, app):
        """Job with no offsite copy is non-compliant"""
        with app.app_context():
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.job_name = "Test Job"

            copies = []
            for ctype, mtype in [("primary", "disk"), ("secondary", "tape"), ("primary", "external_hdd")]:
                c = MagicMock()
                c.copy_type = ctype
                c.media_type = mtype
                copies.append(c)

            with patch("app.services.compliance_checker.db") as mock_db, \
                 patch("app.services.compliance_checker.BackupCopy") as mock_bc, \
                 patch("app.services.compliance_checker.OfflineMedia") as mock_om:

                mock_db.session.get.return_value = mock_job
                mock_bc.query.filter_by.return_value.all.return_value = copies
                mock_om.query.filter_by.return_value.count.return_value = 1

                from app.services.compliance_checker import ComplianceChecker
                checker = ComplianceChecker()
                result = checker.check_job_compliance(1)

                assert result["is_compliant"] is False
                assert any("オフサイト" in v for v in result["violations"])

    def test_check_job_compliance_no_offline_media(self, app):
        """Job with no available offline media is non-compliant"""
        with app.app_context():
            mock_job = MagicMock()
            mock_job.id = 2
            mock_job.job_name = "Job Without Offline"

            copies = []
            for ctype, mtype in [("offsite", "cloud"), ("primary", "disk"), ("secondary", "tape")]:
                c = MagicMock()
                c.copy_type = ctype
                c.media_type = mtype
                copies.append(c)

            with patch("app.services.compliance_checker.db") as mock_db, \
                 patch("app.services.compliance_checker.BackupCopy") as mock_bc, \
                 patch("app.services.compliance_checker.OfflineMedia") as mock_om:

                mock_db.session.get.return_value = mock_job
                mock_bc.query.filter_by.return_value.all.return_value = copies
                mock_om.query.filter_by.return_value.count.return_value = 0  # no offline media

                from app.services.compliance_checker import ComplianceChecker
                checker = ComplianceChecker()
                result = checker.check_job_compliance(2)

                assert result["is_compliant"] is False
                assert any("オフライン" in v for v in result["violations"])


class TestGenerateSystemReport:
    """Tests for generate_system_report() method"""

    def test_generate_system_report_empty(self, app):
        """System report with no active jobs returns zero totals"""
        with app.app_context():
            with patch("app.services.compliance_checker.BackupJob") as mock_bj:
                mock_bj.query.filter_by.return_value.all.return_value = []

                from app.services.compliance_checker import ComplianceChecker
                checker = ComplianceChecker()
                report = checker.generate_system_report()

                assert report["total_jobs"] == 0
                assert report["compliance_rate"] == 0
                assert report["compliant_jobs"] == 0
                assert report["non_compliant_jobs"] == 0
                assert "generated_at" in report
                assert "job_results" in report

    def test_generate_system_report_structure(self, app):
        """System report has required keys"""
        with app.app_context():
            with patch("app.services.compliance_checker.BackupJob") as mock_bj:
                mock_bj.query.filter_by.return_value.all.return_value = []

                from app.services.compliance_checker import ComplianceChecker
                checker = ComplianceChecker()
                report = checker.generate_system_report()

                for key in ("generated_at", "total_jobs", "compliant_jobs",
                            "non_compliant_jobs", "compliance_rate", "job_results", "summary"):
                    assert key in report


class TestGenerateCsvReport:
    """Tests for generate_csv_report() method"""

    def test_generate_csv_report(self, app):
        """CSV report contains job names and status labels"""
        with app.app_context():
            from app.services.compliance_checker import ComplianceChecker
            checker = ComplianceChecker()
            report_data = {
                "generated_at": "2026-03-06T00:00:00+00:00",
                "compliance_rate": 75.0,
                "compliant_jobs": 3,
                "non_compliant_jobs": 1,
                "total_jobs": 4,
                "summary": "NON-COMPLIANT",
                "job_results": [
                    {"job_id": 1, "job_name": "Job1", "is_compliant": True, "violations": []},
                    {"job_id": 2, "job_name": "Job2", "is_compliant": False,
                     "violations": ["コピー数不足: 2/3"]},
                ],
            }

            csv_output = checker.generate_csv_report(report_data)
            assert "Job1" in csv_output
            assert "Job2" in csv_output
            assert "準拠" in csv_output
            assert "非準拠" in csv_output
            assert "75.0%" in csv_output


class TestFormatEmailBody:
    """Tests for format_email_body() method"""

    def test_format_email_body_compliant(self, app):
        """100% compliant report produces text and HTML bodies"""
        with app.app_context():
            from app.services.compliance_checker import ComplianceChecker
            checker = ComplianceChecker()
            report_data = {
                "generated_at": "2026-03-06T00:00:00+00:00",
                "compliance_rate": 100.0,
                "compliant_jobs": 2,
                "total_jobs": 2,
                "summary": "COMPLIANT",
                "job_results": [],
            }

            text_body, html_body = checker.format_email_body(report_data)
            assert "COMPLIANT" in text_body
            assert "100" in text_body
            assert "<html>" in html_body
            assert "COMPLIANT" in html_body

    def test_format_email_body_non_compliant(self, app):
        """Non-compliant report reflects status correctly"""
        with app.app_context():
            from app.services.compliance_checker import ComplianceChecker
            checker = ComplianceChecker()
            report_data = {
                "generated_at": "2026-03-06T00:00:00+00:00",
                "compliance_rate": 50.0,
                "compliant_jobs": 1,
                "total_jobs": 2,
                "summary": "NON-COMPLIANT",
                "job_results": [
                    {"job_name": "Job A", "is_compliant": False,
                     "violations": ["コピー数不足: 1/3"]},
                ],
            }

            text_body, html_body = checker.format_email_body(report_data)
            assert "NON-COMPLIANT" in text_body
            assert "50" in text_body
            assert "コピー数不足" in text_body
            assert "コピー数不足" in html_body
