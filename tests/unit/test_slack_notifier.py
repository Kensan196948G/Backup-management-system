"""
SlackNotifier unit tests
"""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.slack_notifier import SlackNotifier


class TestSlackNotifier:
    """SlackNotifierクラスのテスト"""

    def setup_method(self):
        self.webhook_url = "https://hooks.slack.com/services/TEST/TEST/TEST"
        self.notifier = SlackNotifier(webhook_url=self.webhook_url)

    def test_init_default(self):
        """デフォルト設定での初期化テスト"""
        assert self.notifier.webhook_url == self.webhook_url
        assert self.notifier.channel is None
        assert self.notifier.timeout == 10

    def test_init_with_channel(self):
        """チャンネル指定での初期化テスト"""
        notifier = SlackNotifier(webhook_url=self.webhook_url, channel="#alerts")
        assert notifier.channel == "#alerts"

    def test_init_with_custom_timeout(self):
        """カスタムタイムアウトでの初期化テスト"""
        notifier = SlackNotifier(webhook_url=self.webhook_url, timeout=30)
        assert notifier.timeout == 30

    @patch("app.services.slack_notifier.requests.post")
    def test_send_message_success(self, mock_post):
        """メッセージ送信成功テスト"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.notifier.send_message("Test message", level="info")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == self.webhook_url
        # Verify Content-Type header
        assert call_args[1]["headers"]["Content-Type"] == "application/json"

    @patch("app.services.slack_notifier.requests.post")
    def test_send_message_failure(self, mock_post):
        """メッセージ送信失敗テスト（ネットワークエラー）"""
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        result = self.notifier.send_message("Test message")

        assert result is False

    @patch("app.services.slack_notifier.requests.post")
    def test_send_message_timeout(self, mock_post):
        """メッセージ送信タイムアウトテスト"""
        mock_post.side_effect = requests.exceptions.Timeout()

        result = self.notifier.send_message("Test message")

        assert result is False

    @patch("app.services.slack_notifier.requests.post")
    def test_send_message_includes_emoji(self, mock_post):
        """メッセージにレベル対応の絵文字が含まれるテスト"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.notifier.send_message("Critical alert", level="critical")

        payload = json.loads(mock_post.call_args[1]["data"])
        assert ":rotating_light:" in payload["text"]

    @patch("app.services.slack_notifier.requests.post")
    def test_send_backup_alert_success(self, mock_post):
        """バックアップ成功アラート送信テスト"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.notifier.send_backup_alert(
            job_name="daily-backup",
            status="success",
            message="Backup completed successfully",
            details={"size": "1.2GB", "duration": "5m30s"},
        )

        assert result is True
        payload = json.loads(mock_post.call_args[1]["data"])
        assert "attachments" in payload
        assert payload["attachments"][0]["color"] == "#36A64F"

    @patch("app.services.slack_notifier.requests.post")
    def test_send_backup_alert_failed(self, mock_post):
        """バックアップ失敗アラート送信テスト"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.notifier.send_backup_alert(
            job_name="daily-backup",
            status="failed",
            message="Backup failed",
        )

        assert result is True
        payload = json.loads(mock_post.call_args[1]["data"])
        assert payload["attachments"][0]["color"] == "#FF0000"

    @patch("app.services.slack_notifier.requests.post")
    def test_send_backup_alert_warning(self, mock_post):
        """バックアップ警告アラート送信テスト"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.notifier.send_backup_alert(
            job_name="daily-backup",
            status="warning",
            message="Backup completed with warnings",
        )

        assert result is True
        payload = json.loads(mock_post.call_args[1]["data"])
        assert payload["attachments"][0]["color"] == "#FFA500"

    @patch("app.services.slack_notifier.requests.post")
    def test_send_backup_alert_with_details(self, mock_post):
        """追加情報付きバックアップアラートのフィールドテスト"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.notifier.send_backup_alert(
            job_name="weekly-backup",
            status="success",
            message="Done",
            details={"size": "5GB", "files": "10000"},
        )

        payload = json.loads(mock_post.call_args[1]["data"])
        fields = payload["attachments"][0]["fields"]
        field_titles = [f["title"] for f in fields]
        assert "size" in field_titles
        assert "files" in field_titles

    @patch("app.services.slack_notifier.requests.post")
    def test_send_system_alert(self, mock_post):
        """システムアラート送信テスト"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.notifier.send_system_alert(
            title="Disk Space Warning",
            message="Storage usage exceeded 90%",
            level="critical",
        )

        assert result is True
        payload = json.loads(mock_post.call_args[1]["data"])
        assert payload["attachments"][0]["color"] == "#FF0000"

    @patch("app.services.slack_notifier.requests.post")
    def test_send_with_channel(self, mock_post):
        """チャンネル指定送信テスト"""
        notifier = SlackNotifier(webhook_url=self.webhook_url, channel="#backup-alerts")
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier.send_message("Test")

        payload = json.loads(mock_post.call_args[1]["data"])
        assert payload.get("channel") == "#backup-alerts"

    @patch("app.services.slack_notifier.requests.post")
    def test_send_without_channel_omits_channel_key(self, mock_post):
        """チャンネル未指定時はpayloadにchannelキーが含まれないテスト"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.notifier.send_message("Test")

        payload = json.loads(mock_post.call_args[1]["data"])
        assert "channel" not in payload

    def test_status_label(self):
        """ステータスラベル変換テスト"""
        assert SlackNotifier._status_label("success") == "Success"
        assert SlackNotifier._status_label("failed") == "Failed"
        assert SlackNotifier._status_label("warning") == "Warning"
        assert SlackNotifier._status_label("running") == "Running"
        assert SlackNotifier._status_label("unknown") == "unknown"
