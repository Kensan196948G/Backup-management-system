"""
Unit Tests for Microsoft Teams Notification Service

Tests Teams webhook integration, Adaptive Card generation, and error handling.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from app.services.teams_notification_service import (
    CardType,
    NotificationPriority,
    TeamsNotificationService,
)


class TestTeamsNotificationService:
    """Test suite for TeamsNotificationService"""

    @pytest.fixture
    def service(self):
        """Create service instance with test webhook URL"""
        return TeamsNotificationService(webhook_url="https://test.webhook.office.com/webhookb2/test")

    @pytest.fixture
    def mock_response_success(self):
        """Mock successful response"""
        response = Mock()
        response.status_code = 200
        response.text = "1"
        return response

    @pytest.fixture
    def mock_response_error(self):
        """Mock error response"""
        response = Mock()
        response.status_code = 400
        response.text = "Bad Request"
        return response

    def test_init(self, service):
        """Test service initialization"""
        assert service.webhook_url == "https://test.webhook.office.com/webhookb2/test"
        assert service.timeout == 10
        assert service.max_retries == 3
        assert service.session is not None
        assert isinstance(service._history, list)

    def test_init_with_config(self):
        """Test initialization with Config.TEAMS_WEBHOOK_URL"""
        with patch("app.services.teams_notification_service.Config") as mock_config:
            mock_config.TEAMS_WEBHOOK_URL = "https://config.webhook.com/test"
            service = TeamsNotificationService()
            assert service.webhook_url == "https://config.webhook.com/test"

    def test_validate_webhook_url_valid(self, service):
        """Test webhook URL validation - valid URLs"""
        valid_urls = [
            "https://outlook.office.com/webhook/test",
            "https://test.webhook.office.com/webhookb2/test",
            "http://localhost/webhook/test",
        ]

        for url in valid_urls:
            assert service.validate_webhook_url(url) is True

    def test_validate_webhook_url_invalid(self, service):
        """Test webhook URL validation - invalid URLs"""
        invalid_urls = [
            "not-a-url",
            "https://example.com/no-webhook",
            "ftp://test.com/webhook",
        ]

        for url in invalid_urls:
            assert service.validate_webhook_url(url) is False

        # Empty string should be invalid (explicitly pass it)
        assert service.validate_webhook_url("") is False

        # None returns False only if instance URL is also not set
        service_no_url = TeamsNotificationService(webhook_url=None)
        assert service_no_url.validate_webhook_url(None) is False

    def test_build_card_basic(self, service):
        """Test basic Adaptive Card generation"""
        card = service._build_card(
            card_type=CardType.ALERT, title="Test Alert", message="Test message", severity="info", facts=None, actions=None
        )

        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.5"
        assert "body" in card
        assert len(card["body"]) >= 2  # Header and message
        assert card["msteams"]["width"] == "Full"

    def test_build_card_with_facts(self, service):
        """Test Adaptive Card with facts"""
        facts = [{"title": "Job Name", "value": "TestJob"}, {"title": "Status", "value": "Success"}]

        card = service._build_card(
            card_type=CardType.BACKUP_STATUS,
            title="Backup Complete",
            message="Backup successful",
            severity="success",
            facts=facts,
            actions=None,
        )

        # Check facts are included
        fact_set = None
        for item in card["body"]:
            if item.get("type") == "FactSet":
                fact_set = item
                break

        assert fact_set is not None
        assert fact_set["facts"] == facts

    def test_build_card_with_actions(self, service):
        """Test Adaptive Card with action buttons"""
        actions = [{"type": "Action.OpenUrl", "title": "View Dashboard", "url": "https://example.com/dashboard"}]

        card = service._build_card(
            card_type=CardType.ALERT, title="Test", message="Test", severity="info", facts=None, actions=actions
        )

        assert "actions" in card
        assert card["actions"] == actions

    def test_build_card_severity_colors(self, service):
        """Test different severity colors"""
        severities = ["success", "info", "warning", "error", "critical"]

        for severity in severities:
            card = service._build_card(
                card_type=CardType.ALERT, title="Test", message="Test", severity=severity, facts=None, actions=None
            )

            # Check that color is applied to header
            header = card["body"][0]  # First item is header
            assert "columns" in header
            title_block = header["columns"][1]["items"][0]
            assert "color" in title_block

    @patch("app.services.teams_notification_service.requests.Session.post")
    def test_send_card_success(self, mock_post, service, mock_response_success):
        """Test successful card send"""
        mock_post.return_value = mock_response_success

        card = {"type": "AdaptiveCard", "version": "1.5", "body": []}
        result = service._send_card(card, service.webhook_url)

        assert result is True
        mock_post.assert_called_once()

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["type"] == "message"
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"

    @patch("app.services.teams_notification_service.requests.Session.post")
    def test_send_card_error_response(self, mock_post, service, mock_response_error):
        """Test card send with error response"""
        mock_post.return_value = mock_response_error

        card = {"type": "AdaptiveCard", "version": "1.5", "body": []}
        result = service._send_card(card, service.webhook_url)

        assert result is False

    @patch("app.services.teams_notification_service.requests.Session.post")
    def test_send_card_timeout(self, mock_post, service):
        """Test card send with timeout"""
        mock_post.side_effect = requests.exceptions.Timeout()

        card = {"type": "AdaptiveCard", "version": "1.5", "body": []}
        result = service._send_card(card, service.webhook_url)

        assert result is False

    @patch("app.services.teams_notification_service.requests.Session.post")
    def test_send_card_invalid_url(self, mock_post, service):
        """Test card send with invalid webhook URL"""
        result = service._send_card({}, "invalid-url")
        assert result is False
        mock_post.assert_not_called()

    @patch.object(TeamsNotificationService, "_send_card")
    def test_send_notification_success(self, mock_send_card, service):
        """Test send_notification method"""
        mock_send_card.return_value = True

        result = service.send_notification(
            card_type=CardType.ALERT, title="Test Alert", message="Test message", severity="error"
        )

        assert result is True
        mock_send_card.assert_called_once()

        # Check history
        assert len(service._history) == 1
        assert service._history[0]["success"] is True
        assert service._history[0]["card_type"] == "alert"

    @patch.object(TeamsNotificationService, "_send_card")
    def test_send_notification_failure(self, mock_send_card, service):
        """Test send_notification failure handling"""
        mock_send_card.return_value = False

        result = service.send_notification(
            card_type=CardType.ALERT, title="Test Alert", message="Test message", severity="error"
        )

        assert result is False

        # Check history
        assert len(service._history) == 1
        assert service._history[0]["success"] is False

    @patch.object(TeamsNotificationService, "_send_card")
    def test_send_alert_card(self, mock_send_card, service):
        """Test send_alert_card method"""
        mock_send_card.return_value = True

        result = service.send_alert_card(
            title="Backup Failed",
            message="Job XYZ failed",
            severity="critical",
            alert_type="backup_failed",
            alert_id=123,
            job_name="TestJob",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
        )

        assert result is True
        mock_send_card.assert_called_once()

        # Verify card contains expected facts
        call_args = mock_send_card.call_args
        card = call_args[0][0]
        facts = None
        for item in card["body"]:
            if item.get("type") == "FactSet":
                facts = item["facts"]
                break

        assert facts is not None
        fact_titles = [f["title"] for f in facts]
        assert "Type" in fact_titles
        assert "Severity" in fact_titles
        assert "Job" in fact_titles
        assert "Alert ID" in fact_titles

    @patch.object(TeamsNotificationService, "_send_card")
    def test_send_backup_status_card_success(self, mock_send_card, service):
        """Test send_backup_status_card for successful backup"""
        mock_send_card.return_value = True

        result = service.send_backup_status_card(
            job_name="DailyBackup",
            status="success",
            start_time=datetime(2025, 1, 1, 10, 0, 0),
            end_time=datetime(2025, 1, 1, 11, 0, 0),
            data_size_gb=50.5,
            duration_minutes=60,
        )

        assert result is True

        # Verify severity is success
        call_args = mock_send_card.call_args
        card = call_args[0][0]
        header = card["body"][0]
        title_block = header["columns"][1]["items"][0]
        assert title_block["color"] == "Good"  # Success color

    @patch.object(TeamsNotificationService, "_send_card")
    def test_send_backup_status_card_failed(self, mock_send_card, service):
        """Test send_backup_status_card for failed backup"""
        mock_send_card.return_value = True

        result = service.send_backup_status_card(
            job_name="DailyBackup",
            status="failed",
            start_time=datetime(2025, 1, 1, 10, 0, 0),
            error_message="Disk full",
        )

        assert result is True

        # Verify message contains error
        call_args = mock_send_card.call_args
        card = call_args[0][0]
        message_block = card["body"][1]
        assert "Disk full" in message_block["text"]

    @patch.object(TeamsNotificationService, "_send_card")
    def test_send_daily_summary_card(self, mock_send_card, service):
        """Test send_daily_summary_card"""
        mock_send_card.return_value = True

        result = service.send_daily_summary_card(
            date=datetime(2025, 1, 1),
            total_jobs=10,
            successful_jobs=9,
            failed_jobs=1,
            total_data_gb=500.0,
            alerts_count=3,
        )

        assert result is True

        # Verify facts
        call_args = mock_send_card.call_args
        card = call_args[0][0]
        facts = None
        for item in card["body"]:
            if item.get("type") == "FactSet":
                facts = item["facts"]
                break

        assert facts is not None
        fact_dict = {f["title"]: f["value"] for f in facts}
        assert fact_dict["Total Jobs"] == "10"
        assert "90.0%" in fact_dict["Successful"]  # 9/10 = 90%

    @patch.object(TeamsNotificationService, "_send_card")
    def test_send_weekly_report_card(self, mock_send_card, service):
        """Test send_weekly_report_card"""
        mock_send_card.return_value = True

        result = service.send_weekly_report_card(
            week_start=datetime(2025, 1, 1),
            week_end=datetime(2025, 1, 7),
            total_jobs=70,
            success_rate=96.5,
            total_data_tb=3.5,
            top_issues=["Issue 1", "Issue 2"],
        )

        assert result is True

        # Verify success rate color (>95% = success)
        call_args = mock_send_card.call_args
        card = call_args[0][0]
        header = card["body"][0]
        title_block = header["columns"][1]["items"][0]
        assert title_block["color"] == "Good"

    def test_get_send_history(self, service):
        """Test get_send_history method"""
        # Add some history
        service._record_history(card_type="alert", title="Test 1", severity="info", success=True)
        service._record_history(card_type="alert", title="Test 2", severity="error", success=False)

        history = service.get_send_history(limit=10)
        assert len(history) == 2
        assert history[0]["title"] == "Test 1"
        assert history[1]["title"] == "Test 2"

    def test_get_send_history_limit(self, service):
        """Test history limit"""
        # Add more than 100 records
        for i in range(150):
            service._record_history(card_type="alert", title=f"Test {i}", severity="info", success=True)

        # Should keep only last 100
        assert len(service._history) == 100

        # Get limited results
        history = service.get_send_history(limit=10)
        assert len(history) == 10

    def test_get_statistics_empty(self, service):
        """Test statistics with no history"""
        stats = service.get_statistics()
        assert stats["total_sent"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_statistics_with_data(self, service):
        """Test statistics calculation"""
        # Add history
        service._record_history(card_type="alert", title="Test 1", severity="critical", success=True)
        service._record_history(card_type="alert", title="Test 2", severity="error", success=True)
        service._record_history(card_type="alert", title="Test 3", severity="warning", success=False)
        service._record_history(card_type="backup_status", title="Test 4", severity="info", success=True)

        stats = service.get_statistics()
        assert stats["total_sent"] == 4
        assert stats["successful"] == 3
        assert stats["failed"] == 1
        assert stats["success_rate"] == 75.0

        # Check by severity
        assert stats["by_severity"]["critical"] == 1
        assert stats["by_severity"]["error"] == 1
        assert stats["by_severity"]["warning"] == 1

        # Check by card type
        assert stats["by_card_type"]["alert"] == 3
        assert stats["by_card_type"]["backup_status"] == 1

    @patch.object(TeamsNotificationService, "send_notification")
    def test_test_connection(self, mock_send_notification, service):
        """Test connection test"""
        mock_send_notification.return_value = True

        result = service.test_connection()
        assert result is True

        # Verify correct parameters
        mock_send_notification.assert_called_once()
        call_args = mock_send_notification.call_args
        kwargs = call_args[1]
        assert kwargs["card_type"] == CardType.ALERT
        assert "Connection Test" in kwargs["title"]
        assert kwargs["severity"] == "info"

    def test_record_history(self, service):
        """Test history recording"""
        service._record_history(card_type="alert", title="Test", severity="info", success=True, priority="high")

        assert len(service._history) == 1
        record = service._history[0]
        assert record["card_type"] == "alert"
        assert record["title"] == "Test"
        assert record["severity"] == "info"
        assert record["success"] is True
        assert record["priority"] == "high"
        assert "timestamp" in record

    def test_record_history_with_error(self, service):
        """Test history recording with error"""
        service._record_history(card_type="alert", title="Test", severity="error", success=False, error="Connection timeout")

        record = service._history[0]
        assert record["success"] is False
        assert record["error"] == "Connection timeout"

    @patch("app.services.teams_notification_service.requests.Session.post")
    def test_retry_logic(self, mock_post, service):
        """Test retry logic on failure"""
        # Simulate retryable error (500)
        error_response = Mock()
        error_response.status_code = 500
        mock_post.return_value = error_response

        card = {"type": "AdaptiveCard", "version": "1.5", "body": []}
        result = service._send_card(card, service.webhook_url)

        # Should fail (non-200 response)
        assert result is False
        # Note: The retry is handled by urllib3.Retry in the session, not in our code
        # So we don't test the exact retry count here

    def test_notification_priority(self, service):
        """Test notification priority handling"""
        with patch.object(service, "_send_card", return_value=True):
            # High priority notification
            service.send_notification(
                card_type=CardType.ALERT,
                title="Critical Alert",
                message="Test",
                severity="critical",
                priority=NotificationPriority.URGENT,
            )

            # Check recorded priority
            assert service._history[0]["priority"] == "urgent"
