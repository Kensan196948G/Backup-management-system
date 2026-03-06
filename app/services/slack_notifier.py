"""
Slack通知サービス
Slack Incoming Webhookを使用したアラート・通知送信
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Slack Incoming Webhook通知クラス"""

    # アラートレベルに対応する色
    COLORS = {
        "critical": "#FF0000",  # 赤
        "warning": "#FFA500",   # オレンジ
        "info": "#36A64F",      # 緑
        "success": "#36A64F",   # 緑
    }

    EMOJIS = {
        "critical": ":rotating_light:",
        "warning": ":warning:",
        "info": ":information_source:",
        "success": ":white_check_mark:",
    }

    def __init__(self, webhook_url: str, channel: Optional[str] = None, timeout: int = 10):
        """
        Args:
            webhook_url: Slack Incoming Webhook URL
            channel: 送信チャンネル（省略時はWebhookデフォルト）
            timeout: HTTPタイムアウト秒数
        """
        self.webhook_url = webhook_url
        self.channel = channel
        self.timeout = timeout

    def send_message(self, text: str, level: str = "info") -> bool:
        """
        シンプルなメッセージ送信

        Args:
            text: 送信テキスト
            level: アラートレベル（critical/warning/info/success）

        Returns:
            bool: 送信成功かどうか
        """
        emoji = self.EMOJIS.get(level, ":information_source:")
        payload = {"text": f"{emoji} {text}"}
        if self.channel:
            payload["channel"] = self.channel
        return self._send(payload)

    def send_backup_alert(
        self,
        job_name: str,
        status: str,
        message: str,
        details: Optional[dict] = None,
    ) -> bool:
        """
        バックアップアラート送信（リッチフォーマット）

        Args:
            job_name: バックアップジョブ名
            status: ステータス（success/failed/warning）
            message: メッセージ
            details: 追加情報のdict（任意）

        Returns:
            bool: 送信成功かどうか
        """
        level = "success" if status == "success" else "critical" if status == "failed" else "warning"
        color = self.COLORS.get(level, "#808080")
        emoji = self.EMOJIS.get(level, ":information_source:")

        fields = [
            {"title": "Job Name", "value": job_name, "short": True},
            {"title": "Status", "value": f"{emoji} {status.upper()}", "short": True},
            {
                "title": "Timestamp",
                "value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "short": True,
            },
        ]

        if details:
            for key, value in details.items():
                fields.append({"title": key, "value": str(value), "short": True})

        attachment = {
            "color": color,
            "title": f":lock: Backup {self._status_label(status)}",
            "text": message,
            "fields": fields,
            "footer": "Backup Management System",
            "ts": int(datetime.now(timezone.utc).timestamp()),
        }

        payload = {"attachments": [attachment]}
        if self.channel:
            payload["channel"] = self.channel

        return self._send(payload)

    def send_system_alert(self, title: str, message: str, level: str = "warning") -> bool:
        """
        システムアラート送信

        Args:
            title: アラートタイトル
            message: アラートメッセージ
            level: アラートレベル

        Returns:
            bool: 送信成功かどうか
        """
        color = self.COLORS.get(level, "#808080")
        emoji = self.EMOJIS.get(level, ":information_source:")

        attachment = {
            "color": color,
            "title": f"{emoji} {title}",
            "text": message,
            "footer": "Backup Management System",
            "ts": int(datetime.now(timezone.utc).timestamp()),
        }

        payload = {"attachments": [attachment]}
        if self.channel:
            payload["channel"] = self.channel

        return self._send(payload)

    def _send(self, payload: dict) -> bool:
        """
        Webhookへ送信

        Args:
            payload: 送信データ

        Returns:
            bool: 成功かどうか
        """
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(f"Slack notification sent successfully: status={response.status_code}")
            return True
        except requests.exceptions.Timeout:
            logger.error(f"Slack notification timeout: url={self.webhook_url}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Slack notification send error: {e}")
            return False

    @staticmethod
    def _status_label(status: str) -> str:
        labels = {
            "success": "Success",
            "failed": "Failed",
            "warning": "Warning",
            "running": "Running",
        }
        return labels.get(status, status)


def get_slack_notifier() -> Optional[SlackNotifier]:
    """
    設定からSlackNotifierインスタンスを取得

    Returns:
        SlackNotifier または None（未設定時）
    """
    from flask import current_app
    webhook_url = current_app.config.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return None
    channel = current_app.config.get("SLACK_CHANNEL")
    return SlackNotifier(webhook_url=webhook_url, channel=channel)
