"""
Unit tests for app/services/report_generator.py
ReportGenerator: CSV generation, data gathering, cleanup, and utility methods.

Strategy:
- CSV/HTML generation methods: test without DB (pure dict input)
- Data gathering methods: mock DB models in app context
- cleanup_old_reports: mock Report.query in app context
- _save_report_file: use tempfile
"""

import csv
import tempfile
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_generator(tmpdir=None):
    """Create a ReportGenerator with a temporary report directory."""
    from app.services.report_generator import ReportGenerator
    from app.config import Config

    if tmpdir is None:
        tmpdir = tempfile.mkdtemp()

    with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
        gen = ReportGenerator()
    return gen, Path(tmpdir)


def _col_mock():
    """Create a MagicMock column that supports comparison operators.

    In Python 3.14+, MagicMock comparison with datetime can fail because
    datetime's reflected operation raises TypeError. Explicitly setting
    __ge__, __le__, __lt__, __gt__ ensures comparisons work in filter() calls.
    """
    col = MagicMock()
    result = MagicMock()
    col.__ge__ = MagicMock(return_value=result)
    col.__le__ = MagicMock(return_value=result)
    col.__lt__ = MagicMock(return_value=result)
    col.__gt__ = MagicMock(return_value=result)
    return col


# ---------------------------------------------------------------------------
# TestReportGeneratorInit
# ---------------------------------------------------------------------------

class TestReportGeneratorInit:
    """Tests for ReportGenerator initialization"""

    def test_init_creates_report_dir(self):
        import tempfile, os
        from app.services.report_generator import ReportGenerator
        from app.config import Config

        with tempfile.TemporaryDirectory() as base:
            new_dir = Path(base) / "reports" / "new"
            with patch.object(Config, "REPORT_OUTPUT_DIR", new_dir):
                gen = ReportGenerator()
            assert new_dir.exists()

    def test_init_stores_report_dir(self):
        import tempfile
        from app.services.report_generator import ReportGenerator
        from app.config import Config

        with tempfile.TemporaryDirectory() as base:
            d = Path(base) / "rep"
            with patch.object(Config, "REPORT_OUTPUT_DIR", d):
                gen = ReportGenerator()
            assert gen.report_dir == d


# ---------------------------------------------------------------------------
# TestSaveReportFile
# ---------------------------------------------------------------------------

class TestSaveReportFile:
    """Tests for _save_report_file()"""

    def test_save_text_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, report_dir = _make_generator(tmpdir)
            file_path = report_dir / "test_report.html"
            gen._save_report_file(file_path, "<html>test</html>")
            assert file_path.exists()
            assert file_path.read_text(encoding="utf-8") == "<html>test</html>"

    def test_save_bytes_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, report_dir = _make_generator(tmpdir)
            file_path = report_dir / "test_report.pdf"
            content = b"\x25\x50\x44\x46"  # PDF magic bytes
            gen._save_report_file(file_path, content)
            assert file_path.exists()
            assert file_path.read_bytes() == content

    def test_save_raises_on_invalid_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, report_dir = _make_generator(tmpdir)
            invalid_path = report_dir / "nonexistent_subdir" / "file.html"
            with pytest.raises(Exception):
                gen._save_report_file(invalid_path, "content")


# ---------------------------------------------------------------------------
# TestGenerateDailyCsv
# ---------------------------------------------------------------------------

class TestGenerateDailyCsv:
    """Tests for _generate_daily_csv()"""

    def _make_execution(self, job_id=1, result="success", size=1024, duration=10.0):
        e = MagicMock()
        e.job_id = job_id
        e.execution_date = datetime(2026, 3, 6, 0, 0, 0)
        e.execution_result = result
        e.backup_size_bytes = size
        e.duration_seconds = duration
        return e

    def test_csv_contains_date_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            d = date(2026, 3, 6)
            data = {"date": d, "total_jobs": 5, "success_count": 3, "failed_count": 1, "warning_count": 1, "executions": []}
            _, content = gen._generate_daily_csv(data, d)
            assert "2026-03-06" in content

    def test_csv_contains_summary_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            d = date(2026, 3, 6)
            data = {"date": d, "total_jobs": 10, "success_count": 8, "failed_count": 2, "warning_count": 0, "executions": []}
            _, content = gen._generate_daily_csv(data, d)
            assert "10" in content  # total_jobs
            assert "8" in content   # success_count
            assert "2" in content   # failed_count

    def test_csv_contains_execution_row(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            d = date(2026, 3, 6)
            execution = self._make_execution(job_id=42, result="success")
            data = {"date": d, "total_jobs": 1, "success_count": 1, "failed_count": 0, "warning_count": 0, "executions": [execution]}
            _, content = gen._generate_daily_csv(data, d)
            assert "42" in content

    def test_csv_file_path_contains_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, report_dir = _make_generator(tmpdir)
            d = date(2026, 3, 6)
            data = {"date": d, "total_jobs": 0, "success_count": 0, "failed_count": 0, "warning_count": 0, "executions": []}
            file_path, _ = gen._generate_daily_csv(data, d)
            assert "2026-03-06" in str(file_path)
            assert str(file_path).endswith(".csv")

    def test_csv_no_executions_is_valid_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            d = date(2026, 3, 6)
            data = {"date": d, "total_jobs": 0, "success_count": 0, "failed_count": 0, "warning_count": 0, "executions": []}
            _, content = gen._generate_daily_csv(data, d)
            reader = csv.reader(StringIO(content))
            rows = list(reader)
            assert len(rows) >= 1


# ---------------------------------------------------------------------------
# TestGenerateWeeklyCsv
# ---------------------------------------------------------------------------

class TestGenerateWeeklyCsv:
    """Tests for _generate_weekly_csv()"""

    def test_csv_contains_date_range(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 7)
            data = {"start_date": start, "end_date": end, "total_jobs": 5, "success_count": 4, "failed_count": 1, "executions": [], "daily_data": {}}
            _, content = gen._generate_weekly_csv(data, start, end)
            assert "2026-03-01" in content
            assert "2026-03-07" in content

    def test_csv_file_path_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 7)
            data = {"total_jobs": 0, "success_count": 0, "failed_count": 0, "executions": [], "daily_data": {}}
            file_path, _ = gen._generate_weekly_csv(data, start, end)
            assert "weekly_report" in str(file_path)
            assert str(file_path).endswith(".csv")


# ---------------------------------------------------------------------------
# TestGenerateMonthlyCsv
# ---------------------------------------------------------------------------

class TestGenerateMonthlyCsv:
    """Tests for _generate_monthly_csv()"""

    def test_csv_contains_verification_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 31)
            data = {
                "total_jobs": 3, "success_count": 10, "failed_count": 2,
                "test_success_count": 5, "test_failed_count": 1,
                "executions": [], "compliance_statuses": [], "verification_tests": []
            }
            _, content = gen._generate_monthly_csv(data, start, end)
            assert "5" in content   # test_success_count
            assert "1" in content   # test_failed_count

    def test_csv_file_path_contains_year_month(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 31)
            data = {
                "total_jobs": 0, "success_count": 0, "failed_count": 0,
                "test_success_count": 0, "test_failed_count": 0,
                "executions": [], "compliance_statuses": [], "verification_tests": []
            }
            file_path, _ = gen._generate_monthly_csv(data, start, end)
            assert "2026-03" in str(file_path)


# ---------------------------------------------------------------------------
# TestGenerateComplianceCsv
# ---------------------------------------------------------------------------

class TestGenerateComplianceCsv:
    """Tests for _generate_compliance_csv()"""

    def test_csv_contains_compliance_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 31)
            data = {
                "total_jobs": 10, "compliant_jobs": 7,
                "non_compliant_jobs": 2, "warning_jobs": 1, "compliance_rate": 70.0,
                "compliance_statuses": []
            }
            _, content = gen._generate_compliance_csv(data, start, end)
            assert "70.0" in content
            assert "7" in content

    def test_csv_contains_321_rule_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 31)
            data = {
                "total_jobs": 0, "compliant_jobs": 0,
                "non_compliant_jobs": 0, "warning_jobs": 0, "compliance_rate": 0,
                "compliance_statuses": []
            }
            _, content = gen._generate_compliance_csv(data, start, end)
            assert "3-2-1-1-0" in content or "Compliance" in content


# ---------------------------------------------------------------------------
# TestGenerateAuditCsv
# ---------------------------------------------------------------------------

class TestGenerateAuditCsv:
    """Tests for _generate_audit_csv()"""

    def _make_log(self, action_type="CREATE", result="success", resource_type="BackupJob"):
        log = MagicMock()
        log.action_type = action_type
        log.action_result = result
        log.resource_type = resource_type
        log.created_at = datetime(2026, 3, 6, 10, 0, 0)
        log.user = MagicMock()
        log.user.username = "admin"
        return log

    def test_csv_contains_total_actions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 31)
            data = {"total_actions": 42, "success_count": 40, "failed_count": 2, "audit_logs": []}
            _, content = gen._generate_audit_csv(data, start, end)
            assert "42" in content

    def test_csv_contains_log_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 31)
            log = self._make_log(action_type="DELETE", result="success")
            data = {"total_actions": 1, "success_count": 1, "failed_count": 0, "audit_logs": [log]}
            _, content = gen._generate_audit_csv(data, start, end)
            assert "DELETE" in content
            assert "admin" in content

    def test_csv_no_logs_is_valid_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            start = date(2026, 3, 1)
            end = date(2026, 3, 31)
            data = {"total_actions": 0, "success_count": 0, "failed_count": 0, "audit_logs": []}
            _, content = gen._generate_audit_csv(data, start, end)
            rows = list(csv.reader(StringIO(content)))
            assert len(rows) >= 1


# ---------------------------------------------------------------------------
# TestGenerateDailyHtml
# ---------------------------------------------------------------------------

class TestGenerateDailyHtml:
    """Tests for _generate_daily_html()"""

    def test_html_contains_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            d = date(2026, 3, 6)
            data = {"date": d, "total_jobs": 3, "success_count": 3, "failed_count": 0, "warning_count": 0, "executions": []}
            _, html = gen._generate_daily_html(data, d)
            assert "2026-03-06" in html

    def test_html_contains_summary_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            d = date(2026, 3, 6)
            data = {"total_jobs": 5, "success_count": 4, "failed_count": 1, "warning_count": 0, "executions": []}
            _, html = gen._generate_daily_html(data, d)
            assert "<html" in html
            assert "Total Jobs" in html

    def test_html_file_path_ends_with_html(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = _make_generator(tmpdir)
            d = date(2026, 3, 6)
            data = {"total_jobs": 0, "success_count": 0, "failed_count": 0, "warning_count": 0, "executions": []}
            file_path, _ = gen._generate_daily_html(data, d)
            assert str(file_path).endswith(".html")


# ---------------------------------------------------------------------------
# TestGatherDailyData
# ---------------------------------------------------------------------------

class TestGatherDailyData:
    """Tests for _gather_daily_data() with mocked DB"""

    def test_returns_dict_with_required_keys(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                with patch("app.services.report_generator.BackupJob") as MockJob, \
                     patch("app.services.report_generator.BackupExecution") as MockExec:

                    MockJob.query.filter_by.return_value.all.return_value = []
                    MockExec.execution_date = _col_mock()
                    MockExec.query.filter.return_value.all.return_value = []

                    d = date(2026, 3, 6)
                    result = gen._gather_daily_data(d)

            assert "date" in result
            assert "total_jobs" in result
            assert "success_count" in result
            assert "failed_count" in result
            assert "warning_count" in result
            assert "executions" in result

    def test_counts_successful_executions(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                mock_exec_success = MagicMock()
                mock_exec_success.execution_result = "success"
                mock_exec_success.execution_date = datetime(2026, 3, 6, 12, 0)

                mock_exec_failed = MagicMock()
                mock_exec_failed.execution_result = "failed"
                mock_exec_failed.execution_date = datetime(2026, 3, 6, 13, 0)

                with patch("app.services.report_generator.BackupJob") as MockJob, \
                     patch("app.services.report_generator.BackupExecution") as MockExec:

                    MockJob.query.filter_by.return_value.all.return_value = []
                    MockExec.execution_date = _col_mock()
                    MockExec.query.filter.return_value.all.return_value = [mock_exec_success, mock_exec_failed]

                    d = date(2026, 3, 6)
                    result = gen._gather_daily_data(d)

            assert result["success_count"] == 1
            assert result["failed_count"] == 1

    def test_returns_empty_dict_on_exception(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                with patch("app.services.report_generator.BackupJob") as MockJob:
                    MockJob.query.filter_by.side_effect = Exception("DB error")
                    d = date(2026, 3, 6)
                    result = gen._gather_daily_data(d)

            assert result == {}


# ---------------------------------------------------------------------------
# TestGatherComplianceData
# ---------------------------------------------------------------------------

class TestGatherComplianceData:
    """Tests for _gather_compliance_data()"""

    def test_compliance_rate_zero_when_no_jobs(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                with patch("app.services.report_generator.BackupJob") as MockJob, \
                     patch("app.services.report_generator.ComplianceStatus") as MockCS:

                    MockJob.query.filter_by.return_value.all.return_value = []
                    MockCS.check_date = _col_mock()
                    MockCS.query.filter.return_value.all.return_value = []

                    start = date(2026, 2, 5)
                    end = date(2026, 3, 6)
                    result = gen._gather_compliance_data(start, end)

            assert result["compliance_rate"] == 0

    def test_compliance_rate_calculation(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                mock_job = MagicMock()
                compliant_status = MagicMock()
                compliant_status.overall_status = "compliant"
                non_compliant_status = MagicMock()
                non_compliant_status.overall_status = "non_compliant"

                with patch("app.services.report_generator.BackupJob") as MockJob, \
                     patch("app.services.report_generator.ComplianceStatus") as MockCS:

                    MockJob.query.filter_by.return_value.all.return_value = [mock_job, mock_job]  # 2 jobs
                    MockCS.check_date = _col_mock()
                    MockCS.query.filter.return_value.all.return_value = [compliant_status, non_compliant_status]

                    start = date(2026, 2, 5)
                    end = date(2026, 3, 6)
                    result = gen._gather_compliance_data(start, end)

            assert result["compliant_jobs"] == 1
            assert result["non_compliant_jobs"] == 1
            assert result["compliance_rate"] == 50.0


# ---------------------------------------------------------------------------
# TestGatherAuditData
# ---------------------------------------------------------------------------

class TestGatherAuditData:
    """Tests for _gather_audit_data()"""

    def test_counts_success_and_failed(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                log_success = MagicMock()
                log_success.action_result = "success"
                log_failed = MagicMock()
                log_failed.action_result = "failed"

                with patch("app.services.report_generator.AuditLog") as MockAudit:
                    MockAudit.created_at = _col_mock()
                    MockAudit.query.filter.return_value.order_by.return_value.all.return_value = [
                        log_success, log_success, log_failed
                    ]

                    start = date(2026, 2, 5)
                    end = date(2026, 3, 6)
                    result = gen._gather_audit_data(start, end)

            assert result["total_actions"] == 3
            assert result["success_count"] == 2
            assert result["failed_count"] == 1


# ---------------------------------------------------------------------------
# TestCleanupOldReports
# ---------------------------------------------------------------------------

class TestCleanupOldReports:
    """Tests for cleanup_old_reports()"""

    def test_returns_deleted_count(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                with patch("app.services.report_generator.Report") as MockReport, \
                     patch("app.services.report_generator.db") as mock_db:

                    MockReport.created_at = _col_mock()
                    MockReport.query.filter.return_value.delete.return_value = 5
                    mock_db.session.commit.return_value = None

                    count = gen.cleanup_old_reports(days=90)

            assert count == 5

    def test_returns_zero_on_exception(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                with patch("app.services.report_generator.Report") as MockReport, \
                     patch("app.services.report_generator.db") as mock_db:

                    MockReport.created_at = _col_mock()
                    MockReport.query.filter.side_effect = Exception("DB error")
                    mock_db.session.rollback.return_value = None

                    count = gen.cleanup_old_reports(days=90)

            assert count == 0

    def test_custom_days_parameter(self, app):
        with app.app_context():
            from app.services.report_generator import ReportGenerator
            from app.config import Config

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Config, "REPORT_OUTPUT_DIR", Path(tmpdir)):
                    gen = ReportGenerator()

                with patch("app.services.report_generator.Report") as MockReport, \
                     patch("app.services.report_generator.db") as mock_db:

                    MockReport.created_at = _col_mock()
                    MockReport.query.filter.return_value.delete.return_value = 0
                    mock_db.session.commit.return_value = None

                    count = gen.cleanup_old_reports(days=30)

            assert count == 0
