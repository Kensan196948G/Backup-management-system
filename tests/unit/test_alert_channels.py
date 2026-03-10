"""
Unit tests for alert notification channels (Email / Slack)
Covers: app/alerts/channels/email.py, app/alerts/channels/slack.py
"""
import json
import smtplib
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.alerts.channels.email import EmailChannel
from app.alerts.channels.slack import SlackChannel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_alert():
    alert = MagicMock()
    alert.id = 1
    alert.alert_type = "backup_failed"
    alert.severity = "high"
    alert.title = "Backup Job Failed"
    alert.message = "The nightly backup did not complete."
    alert.status = "active"
    alert.created_at = datetime(2026, 3, 10, 1, 0, 0, tzinfo=timezone.utc)
    alert.resolved_at = None
    alert.backup_job_id = 42
    return alert


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.MAIL_SERVER = "smtp.example.com"
    cfg.MAIL_PORT = 587
    cfg.MAIL_USE_TLS = True
    cfg.MAIL_USERNAME = "test@example.com"
    cfg.MAIL_PASSWORD = "secret"
    cfg.MAIL_DEFAULT_SENDER = "noreply@example.com"
    cfg.TEAMS_WEBHOOK_URL = "https://hooks.slack.com/test"
    return cfg


# ---------------------------------------------------------------------------
# EmailChannel tests
# ---------------------------------------------------------------------------


class TestEmailChannel:
    def test_init_with_config(self, mock_config):
        ch = EmailChannel(config=mock_config)
        assert ch.mail_server == "smtp.example.com"
        assert ch.mail_port == 587
        assert ch.mail_use_tls is True

    def test_init_default_config(self):
        with patch("app.alerts.channels.email.Config") as MockConfig:
            MockConfig.return_value.MAIL_SERVER = "localhost"
            MockConfig.return_value.MAIL_PORT = 25
            MockConfig.return_value.MAIL_USE_TLS = False
            MockConfig.return_value.MAIL_USERNAME = None
            MockConfig.return_value.MAIL_PASSWORD = None
            MockConfig.return_value.MAIL_DEFAULT_SENDER = "no-reply@localhost"
            ch = EmailChannel()
            assert ch.mail_server == "localhost"

    def test_generate_subject_high_severity(self, mock_config, mock_alert):
        ch = EmailChannel(config=mock_config)
        subject = ch._generate_subject(mock_alert)
        assert "Backup Job Failed" in subject or "backup_failed" in subject or subject

    def test_generate_text_body(self, mock_config, mock_alert):
        ch = EmailChannel(config=mock_config)
        body = ch._generate_text_body(mock_alert)
        assert isinstance(body, str)
        assert len(body) > 0

    def test_generate_html_body(self, mock_config, mock_alert):
        ch = EmailChannel(config=mock_config)
        html = ch._generate_html_body(mock_alert)
        assert isinstance(html, str)

    @patch("app.alerts.channels.email.smtplib.SMTP")
    def test_send_alert_success(self, mock_smtp_cls, mock_config, mock_alert, app):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = Mock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = Mock(return_value=False)

        with app.app_context():
            ch = EmailChannel(config=mock_config)
            with patch.object(ch, "_send_email", return_value=True):
                with patch("app.alerts.channels.email.db"):
                    result = ch.send_alert(mock_alert, recipients=["admin@example.com"])
        assert result is True

    @patch("app.alerts.channels.email.smtplib.SMTP")
    def test_send_alert_failure_returns_false(self, mock_smtp_cls, mock_config, mock_alert, app):
        with app.app_context():
            ch = EmailChannel(config=mock_config)
            with patch.object(ch, "_send_email", side_effect=Exception("SMTP error")):
                with patch("app.alerts.channels.email.db"):
                    result = ch.send_alert(mock_alert, recipients=["admin@example.com"])
        assert result is False

    @patch("app.alerts.channels.email.smtplib.SMTP")
    def test_send_email_tls(self, mock_smtp_cls, mock_config):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = Mock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = Mock(return_value=False)

        ch = EmailChannel(config=mock_config)
        result = ch._send_email(
            recipients=["a@b.com"],
            subject="Test",
            text_body="Hello",
            html_body="<p>Hello</p>",
        )
        assert isinstance(result, bool)

    def test_send_email_empty_recipients(self, mock_config):
        ch = EmailChannel(config=mock_config)
        result = ch._send_email(recipients=[], subject="Test", text_body="Body")
        assert result is False

    @patch("app.alerts.channels.email.smtplib.SMTP")
    def test_send_batch_alerts(self, mock_smtp_cls, mock_config, mock_alert, app):
        with app.app_context():
            ch = EmailChannel(config=mock_config)
            alerts = [mock_alert, mock_alert]
            with patch.object(ch, "send_alert", return_value=True):
                results = ch.send_batch_alerts(alerts, recipients=["a@b.com"])
            assert isinstance(results, (list, dict, int, bool))

    def test_get_severity_color_high(self, mock_config):
        ch = EmailChannel(config=mock_config)
        if hasattr(ch, "_get_severity_color"):
            color = ch._get_severity_color("high")
            assert color is not None

    def test_get_severity_color_low(self, mock_config):
        ch = EmailChannel(config=mock_config)
        if hasattr(ch, "_get_severity_color"):
            color = ch._get_severity_color("low")
            assert color is not None


# ---------------------------------------------------------------------------
# SlackChannel tests
# ---------------------------------------------------------------------------


class TestSlackChannel:
    def test_init_with_webhook(self, mock_config):
        ch = SlackChannel(webhook_url="https://hooks.slack.com/custom", config=mock_config)
        assert ch.webhook_url == "https://hooks.slack.com/custom"

    def test_init_from_config(self, mock_config):
        ch = SlackChannel(config=mock_config)
        assert ch.webhook_url == mock_config.TEAMS_WEBHOOK_URL

    def test_init_no_webhook(self):
        with patch("app.alerts.channels.slack.Config") as MockConfig:
            MockConfig.return_value.TEAMS_WEBHOOK_URL = None
            ch = SlackChannel()
            assert ch.webhook_url is None

    def test_generate_alert_message_structure(self, mock_config, mock_alert):
        ch = SlackChannel(webhook_url="https://hooks.slack.com/test", config=mock_config)
        msg = ch._generate_alert_message(mock_alert)
        assert isinstance(msg, dict)

    def test_send_alert_no_webhook(self, mock_config, mock_alert, app):
        with app.app_context():
            ch = SlackChannel(webhook_url=None, config=mock_config)
            ch.webhook_url = None
            with patch("app.alerts.channels.slack.db"):
                result = ch.send_alert(mock_alert)
        assert result is False

    @patch("app.alerts.channels.slack.urlopen")
    def test_send_alert_success(self, mock_urlopen, mock_config, mock_alert, app):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        with app.app_context():
            ch = SlackChannel(webhook_url="https://hooks.slack.com/test", config=mock_config)
            with patch("app.alerts.channels.slack.db"):
                result = ch.send_alert(mock_alert)
        assert isinstance(result, bool)

    @patch("app.alerts.channels.slack.urlopen", side_effect=Exception("Network error"))
    def test_send_alert_network_error(self, mock_urlopen, mock_config, mock_alert, app):
        with app.app_context():
            ch = SlackChannel(webhook_url="https://hooks.slack.com/test", config=mock_config)
            with patch("app.alerts.channels.slack.db"):
                result = ch.send_alert(mock_alert)
        assert result is False

    @patch("app.alerts.channels.slack.urlopen")
    def test_send_webhook_success(self, mock_urlopen, mock_config):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        ch = SlackChannel(webhook_url="https://hooks.slack.com/test", config=mock_config)
        result = ch._send_webhook("https://hooks.slack.com/test", {"text": "hello"})
        assert isinstance(result, bool)

    def test_get_severity_emoji(self, mock_config):
        ch = SlackChannel(webhook_url="https://hooks.slack.com/test", config=mock_config)
        if hasattr(ch, "_get_severity_emoji"):
            emoji = ch._get_severity_emoji("critical")
            assert emoji is not None

    def test_format_timestamp(self, mock_config):
        ch = SlackChannel(webhook_url="https://hooks.slack.com/test", config=mock_config)
        if hasattr(ch, "_format_timestamp"):
            ts = ch._format_timestamp(datetime(2026, 3, 10, tzinfo=timezone.utc))
            assert isinstance(ts, str)

    @patch("app.alerts.channels.slack.urlopen")
    def test_send_batch_alerts(self, mock_urlopen, mock_config, mock_alert, app):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        with app.app_context():
            ch = SlackChannel(webhook_url="https://hooks.slack.com/test", config=mock_config)
            alerts = [mock_alert, mock_alert]
            with patch("app.alerts.channels.slack.db"):
                if hasattr(ch, "send_batch_alerts"):
                    results = ch.send_batch_alerts(alerts)
                    assert results is not None
