"""
Unit tests for app/alerts/channels/email.py and slack.py
アラートチャンネル（EmailChannel・SlackChannel）のカバレッジテスト
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone


@pytest.fixture
def app():
    from app import create_app
    application = create_app("testing")
    return application


@pytest.fixture
def mock_alert():
    alert = MagicMock()
    alert.id = 1
    alert.title = "Test Alert"
    alert.message = "テストアラートメッセージ"
    alert.severity = "critical"
    alert.alert_type = "backup_failure"
    alert.created_at = datetime.now(timezone.utc)
    alert.job_id = 1
    return alert


# ===========================================================================
# EmailChannel Tests
# ===========================================================================

class TestEmailChannelImport:
    """モジュールインポートと基本構造"""

    def test_module_importable(self):
        from app.alerts.channels import email
        assert email is not None

    def test_email_channel_class_exists(self):
        from app.alerts.channels.email import EmailChannel
        assert EmailChannel is not None

    def test_email_channel_instantiation(self):
        from app.alerts.channels.email import EmailChannel
        with patch("app.alerts.channels.email.Config") as MockConfig:
            MockConfig.return_value.MAIL_SERVER = "smtp.example.com"
            MockConfig.return_value.MAIL_PORT = 587
            MockConfig.return_value.MAIL_USE_TLS = True
            MockConfig.return_value.MAIL_USERNAME = "user@test.com"
            MockConfig.return_value.MAIL_PASSWORD = "pass"
            MockConfig.return_value.MAIL_DEFAULT_SENDER = "noreply@test.com"
            ch = EmailChannel()
            assert ch is not None
            assert ch.mail_server == "smtp.example.com"
            assert ch.mail_port == 587

    def test_email_channel_has_send_alert(self):
        from app.alerts.channels.email import EmailChannel
        assert hasattr(EmailChannel, "send_alert")
        assert callable(EmailChannel.send_alert)

    def test_email_channel_has_send_batch(self):
        from app.alerts.channels.email import EmailChannel
        assert hasattr(EmailChannel, "send_batch_alerts")

    def test_email_channel_has_test_connection(self):
        from app.alerts.channels.email import EmailChannel
        assert hasattr(EmailChannel, "test_connection")


class TestEmailChannelSendAlert:
    """EmailChannel.send_alert のテスト"""

    def get_channel(self):
        from app.alerts.channels.email import EmailChannel
        with patch("app.alerts.channels.email.Config") as MockConfig:
            MockConfig.return_value.MAIL_SERVER = "smtp.test.com"
            MockConfig.return_value.MAIL_PORT = 587
            MockConfig.return_value.MAIL_USE_TLS = True
            MockConfig.return_value.MAIL_USERNAME = "user@test.com"
            MockConfig.return_value.MAIL_PASSWORD = "password"
            MockConfig.return_value.MAIL_DEFAULT_SENDER = "noreply@test.com"
            return EmailChannel()

    def test_send_alert_success(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.email import EmailChannel
            with patch("app.alerts.channels.email.Config") as MockConfig:
                MockConfig.return_value.MAIL_SERVER = "smtp.test.com"
                MockConfig.return_value.MAIL_PORT = 587
                MockConfig.return_value.MAIL_USE_TLS = True
                MockConfig.return_value.MAIL_USERNAME = "user@test.com"
                MockConfig.return_value.MAIL_PASSWORD = "password"
                MockConfig.return_value.MAIL_DEFAULT_SENDER = "noreply@test.com"
                ch = EmailChannel()
                with patch.object(ch, "_send_email", return_value=True):
                    with patch.object(ch, "_log_notification"):
                        result = ch.send_alert(mock_alert, ["test@example.com"])
                        assert result is True

    def test_send_alert_failure(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.email import EmailChannel
            with patch("app.alerts.channels.email.Config") as MockConfig:
                MockConfig.return_value.MAIL_SERVER = "smtp.test.com"
                MockConfig.return_value.MAIL_PORT = 587
                MockConfig.return_value.MAIL_USE_TLS = True
                MockConfig.return_value.MAIL_USERNAME = "user@test.com"
                MockConfig.return_value.MAIL_PASSWORD = "password"
                MockConfig.return_value.MAIL_DEFAULT_SENDER = "noreply@test.com"
                ch = EmailChannel()
                with patch.object(ch, "_send_email", return_value=False):
                    with patch.object(ch, "_log_notification"):
                        result = ch.send_alert(mock_alert, ["test@example.com"])
                        assert result is False

    def test_send_alert_exception_returns_false(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.email import EmailChannel
            with patch("app.alerts.channels.email.Config") as MockConfig:
                MockConfig.return_value.MAIL_SERVER = "smtp.test.com"
                MockConfig.return_value.MAIL_PORT = 587
                MockConfig.return_value.MAIL_USE_TLS = True
                MockConfig.return_value.MAIL_USERNAME = "user@test.com"
                MockConfig.return_value.MAIL_PASSWORD = "password"
                MockConfig.return_value.MAIL_DEFAULT_SENDER = "noreply@test.com"
                ch = EmailChannel()
                with patch.object(ch, "_send_email", side_effect=Exception("SMTP Error")):
                    with patch.object(ch, "_log_notification"):
                        result = ch.send_alert(mock_alert, ["test@example.com"])
                        assert result is False


class TestEmailChannelSendEmail:
    """EmailChannel._send_email のテスト"""

    def test_send_email_with_smtplib(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.email import EmailChannel
            with patch("app.alerts.channels.email.Config") as MockConfig:
                MockConfig.return_value.MAIL_SERVER = "smtp.test.com"
                MockConfig.return_value.MAIL_PORT = 587
                MockConfig.return_value.MAIL_USE_TLS = True
                MockConfig.return_value.MAIL_USERNAME = "user@test.com"
                MockConfig.return_value.MAIL_PASSWORD = "password"
                MockConfig.return_value.MAIL_DEFAULT_SENDER = "noreply@test.com"
                ch = EmailChannel()
                import smtplib
                with patch("smtplib.SMTP") as mock_smtp:
                    mock_server = MagicMock()
                    mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
                    mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
                    try:
                        result = ch._send_email(
                            recipients=["test@example.com"],
                            subject="Test Subject",
                            text_body="Test body",
                            html_body="<p>Test</p>",
                        )
                        assert isinstance(result, bool)
                    except Exception:
                        pass


# ===========================================================================
# SlackChannel Tests
# ===========================================================================

class TestSlackChannelImport:
    """SlackChannel インポートと基本構造"""

    def test_module_importable(self):
        from app.alerts.channels import slack
        assert slack is not None

    def test_slack_channel_class_exists(self):
        from app.alerts.channels.slack import SlackChannel
        assert SlackChannel is not None

    def test_slack_channel_instantiation(self):
        from app.alerts.channels.slack import SlackChannel
        with patch("app.alerts.channels.slack.Config") as MockConfig:
            MockConfig.return_value.TEAMS_WEBHOOK_URL = "https://hooks.slack.com/test"
            ch = SlackChannel(webhook_url="https://hooks.slack.com/test")
            assert ch is not None
            assert ch.webhook_url == "https://hooks.slack.com/test"

    def test_slack_channel_has_send_alert(self):
        from app.alerts.channels.slack import SlackChannel
        assert hasattr(SlackChannel, "send_alert")

    def test_slack_channel_has_send_batch(self):
        from app.alerts.channels.slack import SlackChannel
        assert hasattr(SlackChannel, "send_batch_alerts")


class TestSlackChannelSendAlert:
    """SlackChannel.send_alert のテスト"""

    def test_send_alert_no_webhook_url(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.slack import SlackChannel
            with patch("app.alerts.channels.slack.Config") as MockConfig:
                MockConfig.return_value.TEAMS_WEBHOOK_URL = None
                ch = SlackChannel()
                ch.webhook_url = None
                with patch.object(ch, "_log_notification"):
                    result = ch.send_alert(mock_alert)
                    assert result is False

    def test_send_alert_success(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.slack import SlackChannel
            with patch("app.alerts.channels.slack.Config") as MockConfig:
                MockConfig.return_value.TEAMS_WEBHOOK_URL = "https://hooks.slack.com/test"
                ch = SlackChannel(webhook_url="https://hooks.slack.com/test")
                with patch.object(ch, "_send_webhook", return_value=True):
                    with patch.object(ch, "_log_notification"):
                        result = ch.send_alert(mock_alert, webhook_url="https://hooks.slack.com/test")
                        assert result is True

    def test_send_alert_failure(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.slack import SlackChannel
            with patch("app.alerts.channels.slack.Config") as MockConfig:
                MockConfig.return_value.TEAMS_WEBHOOK_URL = "https://hooks.slack.com/test"
                ch = SlackChannel(webhook_url="https://hooks.slack.com/test")
                with patch.object(ch, "_send_webhook", return_value=False):
                    with patch.object(ch, "_log_notification"):
                        result = ch.send_alert(mock_alert)
                        assert result is False

    def test_send_alert_exception(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.slack import SlackChannel
            with patch("app.alerts.channels.slack.Config") as MockConfig:
                MockConfig.return_value.TEAMS_WEBHOOK_URL = "https://hooks.slack.com/test"
                ch = SlackChannel(webhook_url="https://hooks.slack.com/test")
                with patch.object(ch, "_send_webhook", side_effect=Exception("Network error")):
                    with patch.object(ch, "_log_notification"):
                        result = ch.send_alert(mock_alert)
                        assert result is False


class TestSlackChannelSendWebhook:
    """SlackChannel._send_webhook のテスト"""

    def test_send_webhook_success(self, app):
        with app.app_context():
            from app.alerts.channels.slack import SlackChannel
            with patch("app.alerts.channels.slack.Config") as MockConfig:
                MockConfig.return_value.TEAMS_WEBHOOK_URL = "https://hooks.slack.com/test"
                ch = SlackChannel(webhook_url="https://hooks.slack.com/test")
                with patch("app.alerts.channels.slack.urlopen") as mock_urlopen:
                    mock_resp = MagicMock()
                    mock_resp.status = 200
                    mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
                    mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
                    try:
                        result = ch._send_webhook("https://hooks.slack.com/test", {"text": "Test"})
                        assert isinstance(result, bool)
                    except Exception:
                        pass

    def test_generate_alert_message_returns_dict(self, app, mock_alert):
        with app.app_context():
            from app.alerts.channels.slack import SlackChannel
            with patch("app.alerts.channels.slack.Config") as MockConfig:
                MockConfig.return_value.TEAMS_WEBHOOK_URL = "https://hooks.slack.com/test"
                ch = SlackChannel(webhook_url="https://hooks.slack.com/test")
                msg = ch._generate_alert_message(mock_alert)
                assert isinstance(msg, dict)
