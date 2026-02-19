"""
Slack Notification Channel
Sends notifications via Slack Incoming Webhooks
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Config
from app.models import Alert, NotificationLog, db

logger = logging.getLogger(__name__)


class SlackChannel:
    """
    Slack notification channel using Incoming Webhooks
    Supports rich formatting with attachments and blocks
    """

    def __init__(self, webhook_url: Optional[str] = None, config: Optional[Config] = None):
        """
        Initialize Slack channel with webhook URL

        Args:
            webhook_url: Slack webhook URL (overrides config)
            config: Configuration object
        """
        self.config = config or Config()
        self.webhook_url = webhook_url or self.config.TEAMS_WEBHOOK_URL  # Using TEAMS_WEBHOOK_URL as fallback

    def send_alert(self, alert: Alert, webhook_url: Optional[str] = None) -> bool:
        """
        Send alert notification to Slack

        Args:
            alert: Alert object to send
            webhook_url: Optional webhook URL to override default

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            url = webhook_url or self.webhook_url
            if not url:
                logger.error("No Slack webhook URL configured")
                return False

            # Generate Slack message
            message = self._generate_alert_message(alert)

            # Send to Slack
            success = self._send_webhook(url, message)

            # Log notification
            self._log_notification(
                alert=alert,
                webhook_url=url,
                success=success,
            )

            return success

        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}", exc_info=True)
            self._log_notification(
                alert=alert,
                webhook_url=webhook_url or self.webhook_url,
                success=False,
                error_message=str(e),
            )
            return False

    def send_batch_alerts(self, alerts: List[Alert], webhook_url: Optional[str] = None) -> bool:
        """
        Send multiple alerts in a single Slack message

        Args:
            alerts: List of Alert objects
            webhook_url: Optional webhook URL to override default

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not alerts:
                logger.warning("No alerts to send in batch")
                return False

            url = webhook_url or self.webhook_url
            if not url:
                logger.error("No Slack webhook URL configured")
                return False

            # Generate digest message
            message = self._generate_digest_message(alerts)

            # Send to Slack
            success = self._send_webhook(url, message)

            # Log notifications for all alerts
            for alert in alerts:
                self._log_notification(
                    alert=alert,
                    webhook_url=url,
                    success=success,
                )

            return success

        except Exception as e:
            logger.error(f"Error sending batch Slack alerts: {e}", exc_info=True)
            return False

    def send_report(
        self,
        report_title: str,
        report_content: str,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send report notification to Slack

        Args:
            report_title: Title of the report
            report_content: Report summary/content
            webhook_url: Optional webhook URL to override default

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            url = webhook_url or self.webhook_url
            if not url:
                logger.error("No Slack webhook URL configured")
                return False

            # Generate report message
            message = self._generate_report_message(report_title, report_content)

            # Send to Slack
            success = self._send_webhook(url, message)

            return success

        except Exception as e:
            logger.error(f"Error sending Slack report: {e}", exc_info=True)
            return False

    def _send_webhook(self, webhook_url: str, message: Dict) -> bool:
        """
        Send message to Slack webhook

        Args:
            webhook_url: Slack webhook URL
            message: Message payload as dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Convert message to JSON
            data = json.dumps(message).encode("utf-8")

            # Create request
            request = Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )

            # Send request
            start_time = time.time()
            with urlopen(request, timeout=10) as response:
                response_data = response.read()
                delivery_time = int((time.time() - start_time) * 1000)

            if response.status == 200:
                logger.info(f"Slack webhook sent successfully (delivery time: {delivery_time}ms)")
                return True
            else:
                logger.warning(f"Slack webhook returned status {response.status}: {response_data}")
                return False

        except HTTPError as e:
            logger.error(f"HTTP error sending Slack webhook: {e.code} {e.reason}")
            return False
        except URLError as e:
            logger.error(f"URL error sending Slack webhook: {e.reason}")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack webhook: {e}", exc_info=True)
            return False

    def _generate_alert_message(self, alert: Alert) -> Dict:
        """
        Generate Slack message for an alert using Block Kit

        Args:
            alert: Alert object

        Returns:
            Slack message payload
        """
        # Color coding by severity
        color_map = {
            "info": "#36a64f",  # Green
            "warning": "#ff9900",  # Orange
            "error": "#dc3545",  # Red
            "critical": "#721c24",  # Dark red
        }
        color = color_map.get(alert.severity, "#808080")

        # Emoji by severity
        emoji_map = {
            "info": ":information_source:",
            "warning": ":warning:",
            "error": ":x:",
            "critical": ":rotating_light:",
        }
        emoji = emoji_map.get(alert.severity, ":bell:")

        # Build message using attachments (for better compatibility)
        message = {
            "text": f"{emoji} Backup System Alert: {alert.title}",
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} {alert.title}",
                                "emoji": True,
                            },
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Severity:*\n{alert.severity.upper()}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Type:*\n{alert.alert_type}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Time:*\n{alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Job ID:*\n{alert.job_id or 'N/A'}",
                                },
                            ],
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Message:*\n{alert.message}",
                            },
                        },
                    ],
                }
            ],
        }

        return message

    def _generate_digest_message(self, alerts: List[Alert]) -> Dict:
        """
        Generate Slack message for multiple alerts

        Args:
            alerts: List of Alert objects

        Returns:
            Slack message payload
        """
        # Count by severity
        critical_count = sum(1 for a in alerts if a.severity == "critical")
        error_count = sum(1 for a in alerts if a.severity == "error")
        warning_count = sum(1 for a in alerts if a.severity == "warning")
        info_count = sum(1 for a in alerts if a.severity == "info")

        # Build alert list
        alert_fields = []
        for alert in alerts[:10]:  # Limit to 10 alerts to avoid message size issues
            emoji_map = {
                "info": ":information_source:",
                "warning": ":warning:",
                "error": ":x:",
                "critical": ":rotating_light:",
            }
            emoji = emoji_map.get(alert.severity, ":bell:")

            alert_fields.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{alert.title}*\n{alert.message[:100]}...",
                    },
                }
            )

        # Build message
        message = {
            "text": f"Backup Alert Digest: {len(alerts)} alerts",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Backup Alert Digest ({len(alerts)} alerts)",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Critical:* {critical_count}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Error:* {error_count}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Warning:* {warning_count}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Info:* {info_count}",
                        },
                    ],
                },
                {"type": "divider"},
                *alert_fields,
            ],
        }

        if len(alerts) > 10:
            message["blocks"].append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_Showing 10 of {len(alerts)} alerts_",
                        }
                    ],
                }
            )

        return message

    def _generate_report_message(self, title: str, content: str) -> Dict:
        """
        Generate Slack message for a report

        Args:
            title: Report title
            content: Report content

        Returns:
            Slack message payload
        """
        message = {
            "text": f"Backup Report: {title}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":chart_with_upwards_trend: {title}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": content,
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                        }
                    ],
                },
            ],
        }

        return message

    def _log_notification(
        self,
        alert: Alert,
        webhook_url: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Log notification attempt to database"""
        try:
            log = NotificationLog(
                notification_type="slack",
                channel="webhook",
                recipient=webhook_url,
                subject=alert.title,
                message=alert.message,
                severity=alert.severity,
                status="sent" if success else "failed",
                error_message=error_message,
                alert_id=alert.id,
                job_id=alert.job_id,
            )
            db.session.add(log)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error logging Slack notification: {e}", exc_info=True)
            db.session.rollback()

    def test_connection(self, webhook_url: Optional[str] = None) -> bool:
        """
        Test Slack webhook connection

        Args:
            webhook_url: Optional webhook URL to test

        Returns:
            True if connection successful, False otherwise
        """
        try:
            url = webhook_url or self.webhook_url
            if not url:
                logger.error("No Slack webhook URL configured")
                return False

            test_message = {
                "text": "Test notification from Backup Management System",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":white_check_mark: *Test notification from Backup Management System*\n"
                            f"Connection successful at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                        },
                    }
                ],
            }

            success = self._send_webhook(url, test_message)

            if success:
                logger.info("Slack webhook test successful")
            else:
                logger.error("Slack webhook test failed")

            return success

        except Exception as e:
            logger.error(f"Slack webhook test failed: {e}", exc_info=True)
            return False
