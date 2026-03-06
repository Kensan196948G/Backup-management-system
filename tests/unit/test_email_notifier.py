"""
EmailNotifier ユニットテスト
"""
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_notifier import EmailNotifier, get_email_notifier


class TestEmailNotifier:
    """EmailNotifier の基本動作テスト"""

    @pytest.fixture
    def notifier(self):
        return EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="password",
            from_email="noreply@example.com",
            use_tls=True,
        )

    def test_send_email_success(self, notifier):
        """メール送信成功"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_email(
                ["user@test.com"], "Test Subject", "Test body"
            )
            assert result is True
            mock_server.sendmail.assert_called_once()

    def test_send_email_auth_failure(self, notifier):
        """認証エラー時はFalseを返す"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPAuthenticationError(535, "Auth failed")
            result = notifier.send_email(["user@test.com"], "Subject", "Body")
            assert result is False

    def test_send_email_connect_failure(self, notifier):
        """接続エラー時はFalseを返す"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPConnectError(421, "Connect failed")
            result = notifier.send_email(["user@test.com"], "Subject", "Body")
            assert result is False

    def test_send_email_with_html(self, notifier):
        """HTML本文付きメール送信"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_email(
                ["user@test.com"], "Subject", "Text body",
                body_html="<h1>HTML body</h1>"
            )
            assert result is True

    def test_send_backup_alert_success(self, notifier):
        """バックアップ成功アラート"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_backup_alert(
                "Test Job", "success", "Backup completed",
                ["admin@test.com"]
            )
            assert result is True
            # sendmail が呼ばれたことを確認
            mock_server.sendmail.assert_called_once()
            # 送信元アドレスが正しいことを確認
            call_args = mock_server.sendmail.call_args[0]
            assert call_args[0] == "noreply@example.com"
            assert "admin@test.com" in call_args[1]

    def test_send_backup_alert_failed(self, notifier):
        """バックアップ失敗アラート"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_backup_alert(
                "Test Job", "failed", "Backup failed",
                ["admin@test.com"],
                details={"duration": "5 minutes", "size": "100 MB"}
            )
            assert result is True

    def test_send_backup_alert_with_details(self, notifier):
        """詳細情報付きアラート"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_backup_alert(
                "Job X", "warning", "Slow backup",
                ["admin@test.com"],
                details={"elapsed": "2h", "files": 1000}
            )
            assert result is True

    def test_send_system_alert(self, notifier):
        """システムアラート"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_system_alert(
                "disk_full_error", "Disk is 95% full",
                ["admin@test.com"]
            )
            assert result is True

    def test_send_multiple_recipients(self, notifier):
        """複数宛先への送信"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_email(
                ["user1@test.com", "user2@test.com", "user3@test.com"],
                "Subject", "Body"
            )
            assert result is True

    def test_subject_prefixes(self, notifier):
        """件名プレフィックスの確認"""
        assert notifier.SUBJECT_PREFIXES["success"] == "[SUCCESS]"
        assert notifier.SUBJECT_PREFIXES["critical"] == "[CRITICAL]"
        assert notifier.SUBJECT_PREFIXES["warning"] == "[WARNING]"

    def test_no_tls(self):
        """TLS無効の場合のメール送信"""
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=25,
            username="user",
            password="pass",
            from_email="noreply@example.com",
            use_tls=False,
        )
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_email(["user@test.com"], "Subject", "Body")
            assert result is True
            # starttls は呼ばれない
            mock_server.starttls.assert_not_called()

    def test_no_credentials(self):
        """認証情報なしの場合"""
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=25,
            username="",
            password="",
            from_email="noreply@example.com",
            use_tls=False,
        )
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_email(["user@test.com"], "Subject", "Body")
            assert result is True
            # login は呼ばれない
            mock_server.login.assert_not_called()

    def test_send_email_generic_exception(self, notifier):
        """一般例外時はFalseを返す"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.side_effect = Exception("Unknown error")
            result = notifier.send_email(["user@test.com"], "Subject", "Body")
            assert result is False

    def test_send_backup_alert_warning_status(self, notifier):
        """warningステータスのアラート"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_backup_alert(
                "Test Job", "warning", "Backup slow",
                ["admin@test.com"]
            )
            assert result is True

    def test_send_backup_alert_unknown_status(self, notifier):
        """未知ステータスのアラート"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_backup_alert(
                "Test Job", "unknown", "Something happened",
                ["admin@test.com"]
            )
            assert result is True

    def test_send_system_alert_warning_type(self, notifier):
        """warningタイプのシステムアラート"""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = notifier.send_system_alert(
                "disk_space_warning", "Disk 80% full",
                ["admin@test.com"]
            )
            assert result is True

    def test_status_subjects(self, notifier):
        """STATUS_SUBJECTSの確認"""
        assert notifier.STATUS_SUBJECTS["success"] == "バックアップ成功"
        assert notifier.STATUS_SUBJECTS["failed"] == "バックアップ失敗"
        assert notifier.STATUS_SUBJECTS["warning"] == "バックアップ警告"


class TestGetEmailNotifier:
    """get_email_notifier ファクトリ関数テスト"""

    def test_returns_none_when_no_smtp_host(self, app):
        """SMTP_HOST未設定時はNoneを返す"""
        with app.app_context():
            app.config["SMTP_HOST"] = ""
            result = get_email_notifier()
            assert result is None

    def test_returns_notifier_when_configured(self, app):
        """SMTP設定済み時はEmailNotifierを返す"""
        with app.app_context():
            app.config["SMTP_HOST"] = "smtp.example.com"
            app.config["SMTP_PORT"] = 587
            app.config["SMTP_USERNAME"] = "user"
            app.config["SMTP_PASSWORD"] = "pass"
            app.config["SMTP_FROM_EMAIL"] = "noreply@test.com"
            app.config["SMTP_USE_TLS"] = True
            result = get_email_notifier()
            assert result is not None
            assert isinstance(result, EmailNotifier)

    def test_notifier_attributes(self, app):
        """生成されたEmailNotifierの属性確認"""
        with app.app_context():
            app.config["SMTP_HOST"] = "smtp.example.com"
            app.config["SMTP_PORT"] = 465
            app.config["SMTP_USERNAME"] = "myuser"
            app.config["SMTP_PASSWORD"] = "mypass"
            app.config["SMTP_FROM_EMAIL"] = "backup@test.com"
            app.config["SMTP_USE_TLS"] = False
            result = get_email_notifier()
            assert result is not None
            assert result.smtp_host == "smtp.example.com"
            assert result.smtp_port == 465
            assert result.username == "myuser"
            assert result.from_email == "backup@test.com"
            assert result.use_tls is False

    def test_returns_none_on_exception(self, app):
        """例外発生時はNoneを返す"""
        with app.app_context():
            app.config["SMTP_HOST"] = "smtp.example.com"
            app.config["SMTP_PORT"] = "invalid_port"  # int変換で失敗
            result = get_email_notifier()
            assert result is None
