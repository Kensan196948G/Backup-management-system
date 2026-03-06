"""
Email Notification Service
Provides email notifications for backup events using SMTP
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from flask import current_app

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Emailバックアップ通知クライアント。
    SMTPを使用してバックアップイベント通知を送信する。
    """

    SUBJECT_PREFIXES = {
        "success": "[SUCCESS]",
        "warning": "[WARNING]",
        "critical": "[CRITICAL]",
        "info": "[INFO]",
    }

    STATUS_SUBJECTS = {
        "success": "バックアップ成功",
        "failed": "バックアップ失敗",
        "warning": "バックアップ警告",
    }

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str,
                 from_email: str, use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls

    def send_email(self, to_emails: List[str], subject: str, body_text: str,
                   body_html: Optional[str] = None) -> bool:
        """
        メール送信。

        Args:
            to_emails: 送信先リスト
            subject: 件名
            body_text: テキスト本文
            body_html: HTML本文（任意）

        Returns:
            bool: 送信成功かどうか
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to_emails)

            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_email, to_emails, msg.as_string())

            logger.info(f"Email sent successfully to {to_emails}: {subject}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    def send_backup_alert(self, job_name: str, status: str, message: str,
                          to_emails: List[str], details: Optional[dict] = None) -> bool:
        """
        バックアップ結果のEmail通知。

        Args:
            job_name: バックアップジョブ名
            status: 実行結果 (success/failed/warning)
            message: メッセージ
            to_emails: 送信先リスト
            details: 詳細情報（任意）

        Returns:
            bool: 送信成功かどうか
        """
        level = "success" if status == "success" else "critical" if status == "failed" else "warning"
        prefix = self.SUBJECT_PREFIXES.get(level, "[INFO]")
        status_label = self.STATUS_SUBJECTS.get(status, status)

        subject = f"{prefix} バックアップ{status_label}: {job_name}"

        # テキスト本文
        lines = [
            f"バックアップジョブ: {job_name}",
            f"ステータス: {status_label}",
            f"メッセージ: {message}",
        ]
        if details:
            lines.append("\n詳細情報:")
            for k, v in details.items():
                lines.append(f"  {k}: {v}")
        body_text = "\n".join(lines)

        # HTML本文
        color = "#28a745" if status == "success" else "#dc3545" if status == "failed" else "#ffc107"
        detail_rows = ""
        if details:
            for k, v in details.items():
                detail_rows += f"<tr><td><b>{k}</b></td><td>{v}</td></tr>"
        body_html = f"""
        <html><body>
        <div style="border-left: 4px solid {color}; padding: 10px; margin: 10px 0;">
            <h2 style="color: {color};">{status_label}: {job_name}</h2>
            <p>{message}</p>
            {f'<table border="1" cellpadding="5">{detail_rows}</table>' if detail_rows else ''}
        </div>
        <p style="color: #666; font-size: 12px;">3-2-1-1-0 Backup Management System</p>
        </body></html>
        """

        return self.send_email(to_emails, subject, body_text, body_html)

    def send_system_alert(self, alert_type: str, message: str,
                          to_emails: List[str]) -> bool:
        """
        システムアラートのEmail通知。
        """
        level = "critical" if "error" in alert_type.lower() or "fail" in alert_type.lower() else "warning"
        prefix = self.SUBJECT_PREFIXES.get(level, "[INFO]")
        subject = f"{prefix} システムアラート: {alert_type}"
        body_text = f"アラートタイプ: {alert_type}\nメッセージ: {message}"
        return self.send_email(to_emails, subject, body_text)


def get_email_notifier() -> Optional[EmailNotifier]:
    """
    Flask アプリケーション設定からEmailNotifierインスタンスを生成。
    """
    try:
        smtp_host = current_app.config.get("SMTP_HOST", "")
        if not smtp_host:
            return None
        return EmailNotifier(
            smtp_host=smtp_host,
            smtp_port=int(current_app.config.get("SMTP_PORT", 587)),
            username=current_app.config.get("SMTP_USERNAME", ""),
            password=current_app.config.get("SMTP_PASSWORD", ""),
            from_email=current_app.config.get("SMTP_FROM_EMAIL", "noreply@backup-system.local"),
            use_tls=current_app.config.get("SMTP_USE_TLS", True),
        )
    except Exception as e:
        logger.error(f"Failed to create EmailNotifier: {e}")
        return None
