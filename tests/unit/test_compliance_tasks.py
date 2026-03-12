"""
Unit tests for app/scheduler/compliance_tasks.py
Covers: generate_and_send_weekly_report, generate_and_send_monthly_report
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestGenerateAndSendWeeklyReport:

    def test_sends_report_when_notifier_configured(self, app):
        with app.app_context():
            from app.scheduler.compliance_tasks import generate_and_send_weekly_report

            mock_report_data = {
                "compliance_rate": 95.0,
                "total_jobs": 10,
                "compliant_jobs": 9,
                "non_compliant_jobs": 1,
            }

            with patch("app.services.compliance_checker.ComplianceChecker") as MockChecker, \
                 patch("app.services.email_notifier.get_email_notifier") as MockNotif:

                mock_checker = MagicMock()
                mock_checker.generate_system_report.return_value = mock_report_data
                mock_checker.format_email_body.return_value = ("text body", "<html>html body</html>")
                mock_checker.generate_csv_report.return_value = "csv content"
                MockChecker.return_value = mock_checker

                mock_notifier = MagicMock()
                mock_notifier.send_email.return_value = True
                MockNotif.return_value = mock_notifier

                app.config["ALERT_EMAIL_RECIPIENTS"] = ["admin@example.com"]

                result = generate_and_send_weekly_report()

            assert result["status"] == "success"
            assert result["compliance_rate"] == 95.0

    def test_skips_email_when_notifier_not_configured(self, app):
        with app.app_context():
            from app.scheduler.compliance_tasks import generate_and_send_weekly_report

            mock_report_data = {"compliance_rate": 80.0}

            with patch("app.services.compliance_checker.ComplianceChecker") as MockChecker, \
                 patch("app.services.email_notifier.get_email_notifier") as MockNotif:

                mock_checker = MagicMock()
                mock_checker.generate_system_report.return_value = mock_report_data
                mock_checker.format_email_body.return_value = ("text", "<html>")
                mock_checker.generate_csv_report.return_value = ""
                MockChecker.return_value = mock_checker

                MockNotif.return_value = None

                result = generate_and_send_weekly_report()

            assert result["status"] == "success"

    def test_returns_error_on_exception(self, app):
        with app.app_context():
            from app.scheduler.compliance_tasks import generate_and_send_weekly_report

            with patch("app.services.compliance_checker.ComplianceChecker") as MockChecker:
                MockChecker.side_effect = Exception("Checker failed")

                result = generate_and_send_weekly_report()

            assert result["status"] == "error"
            assert "Checker failed" in result["message"]


class TestGenerateAndSendMonthlyReport:

    def test_sends_monthly_report(self, app):
        with app.app_context():
            from app.scheduler.compliance_tasks import generate_and_send_monthly_report

            mock_report_data = {"compliance_rate": 88.5}

            with patch("app.services.compliance_checker.ComplianceChecker") as MockChecker, \
                 patch("app.services.email_notifier.get_email_notifier") as MockNotif:

                mock_checker = MagicMock()
                mock_checker.generate_system_report.return_value = mock_report_data
                mock_checker.format_email_body.return_value = ("text", "<html>")
                MockChecker.return_value = mock_checker

                mock_notifier = MagicMock()
                MockNotif.return_value = mock_notifier

                app.config["ALERT_EMAIL_RECIPIENTS"] = ["admin@example.com"]

                result = generate_and_send_monthly_report()

            assert result["status"] == "success"
            assert "compliance_rate" in result
            assert "period" in result

    def test_skips_email_when_notifier_not_configured(self, app):
        with app.app_context():
            from app.scheduler.compliance_tasks import generate_and_send_monthly_report

            mock_report_data = {"compliance_rate": 70.0}

            with patch("app.services.compliance_checker.ComplianceChecker") as MockChecker, \
                 patch("app.services.email_notifier.get_email_notifier") as MockNotif:

                mock_checker = MagicMock()
                mock_checker.generate_system_report.return_value = mock_report_data
                mock_checker.format_email_body.return_value = ("text", "<html>")
                MockChecker.return_value = mock_checker

                MockNotif.return_value = None

                result = generate_and_send_monthly_report()

            assert result["status"] == "success"

    def test_returns_error_on_exception(self, app):
        with app.app_context():
            from app.scheduler.compliance_tasks import generate_and_send_monthly_report

            with patch("app.services.compliance_checker.ComplianceChecker") as MockChecker:
                MockChecker.side_effect = Exception("Monthly report failed")

                result = generate_and_send_monthly_report()

            assert result["status"] == "error"
            assert "Monthly report failed" in result["message"]
