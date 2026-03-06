"""
Microsoft Teams Notification Service

Manages Microsoft Teams Webhook integrations with Adaptive Card support.
Supports async delivery, error handling, and notification history tracking.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import Config

logger = logging.getLogger(__name__)


class CardType(Enum):
    """Adaptive Card template types"""

    ALERT = "alert"
    BACKUP_STATUS = "backup_status"
    REPORT_SUMMARY = "report_summary"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_REPORT = "weekly_report"


class NotificationPriority(Enum):
    """Notification priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TeamsNotificationService:
    """
    Microsoft Teams notification service with Adaptive Card support.

    Features:
    - Adaptive Card generation (v1.5)
    - Multi-webhook support (channel-based)
    - Async/sync sending
    - Retry logic with exponential backoff
    - Rate limiting
    - Send history tracking
    """

    # Adaptive Card schema version
    CARD_VERSION = "1.5"

    # Color scheme for different severities
    COLORS = {
        "success": "Good",  # Green
        "info": "Accent",  # Blue
        "warning": "Warning",  # Yellow
        "error": "Attention",  # Red
        "critical": "Attention",  # Red
    }

    # Severity icons (Unicode emoji)
    ICONS = {
        "success": "✅",
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "critical": "🚨",
    }

    def __init__(self, webhook_url: Optional[str] = None, timeout: int = 10, max_retries: int = 3):
        """
        Initialize Teams notification service.

        Args:
            webhook_url: Teams webhook URL (defaults to Config.TEAMS_WEBHOOK_URL)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.webhook_url = webhook_url or Config.TEAMS_WEBHOOK_URL
        self.timeout = timeout
        self.max_retries = max_retries

        # Setup HTTP session with retry logic
        self.session = self._create_session()

        # Notification history (in-memory for now)
        self._history: List[Dict] = []

    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry logic.

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        # Retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
            backoff_factor=1,  # 1, 2, 4, 8... seconds
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def validate_webhook_url(self, url: Optional[str] = None) -> bool:
        """
        Validate Teams webhook URL format.

        Teams webhook URLs should match patterns like:
        - https://outlook.office.com/webhook/...
        - https://*.webhook.office.com/...

        Args:
            url: Webhook URL to validate (defaults to instance URL)

        Returns:
            True if valid
        """
        # Handle None and empty string explicitly
        if url is None:
            target_url = self.webhook_url
        else:
            target_url = url

        if not target_url or not target_url.strip():
            return False

        try:
            parsed = urlparse(target_url)

            # Check basic structure
            if parsed.scheme not in ["https", "http"]:
                return False

            if not parsed.netloc or not parsed.path:
                return False

            # Check for Teams webhook patterns
            # Accept office.com domains with webhook in domain or path
            netloc_lower = parsed.netloc.lower()
            path_lower = parsed.path.lower()

            # Valid patterns:
            # - outlook.office.com/webhook/...
            # - *.webhook.office.com/...
            # - localhost for testing
            if "localhost" in netloc_lower:
                return "/webhook" in path_lower

            is_office_domain = "office.com" in netloc_lower or "office365.com" in netloc_lower
            has_webhook = "webhook" in netloc_lower or "/webhook" in path_lower

            return is_office_domain and has_webhook

        except Exception:
            return False

    def send_notification(
        self,
        card_type: CardType,
        title: str,
        message: str,
        severity: str = "info",
        facts: Optional[List[Dict[str, str]]] = None,
        actions: Optional[List[Dict]] = None,
        webhook_url: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> bool:
        """
        Send Teams notification with Adaptive Card.

        Args:
            card_type: Type of card template to use
            title: Card title
            message: Main message
            severity: Severity level (info/warning/error/critical)
            facts: List of fact dictionaries (title, value)
            actions: List of action button configurations
            webhook_url: Override webhook URL
            priority: Notification priority

        Returns:
            True if successful
        """
        try:
            # Build Adaptive Card
            card = self._build_card(
                card_type=card_type, title=title, message=message, severity=severity, facts=facts, actions=actions
            )

            # Send to Teams
            result = self._send_card(card, webhook_url or self.webhook_url)

            # Record history
            self._record_history(
                card_type=card_type.value,
                title=title,
                severity=severity,
                success=result,
                priority=priority.value,
            )

            return result

        except Exception as e:
            logger.error(f"Failed to send Teams notification: {str(e)}", exc_info=True)
            self._record_history(card_type=card_type.value, title=title, severity=severity, success=False, error=str(e))
            return False

    def send_alert_card(
        self,
        title: str,
        message: str,
        severity: str,
        alert_type: str,
        alert_id: Optional[int] = None,
        job_name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send alert notification card.

        Args:
            title: Alert title
            message: Alert message
            severity: Severity level (info/warning/error/critical)
            alert_type: Type of alert
            alert_id: Alert ID
            job_name: Related backup job name
            created_at: Alert creation time
            webhook_url: Override webhook URL

        Returns:
            True if successful
        """
        facts = [
            {"title": "Type", "value": alert_type},
            {"title": "Severity", "value": severity.upper()},
        ]

        if job_name:
            facts.insert(1, {"title": "Job", "value": job_name})

        if created_at:
            facts.append({"title": "Time", "value": created_at.strftime("%Y-%m-%d %H:%M:%S")})

        if alert_id:
            facts.append({"title": "Alert ID", "value": str(alert_id)})

        # Add action button if system URL is available
        actions = []
        # In production, add dashboard link:
        # actions = [{"type": "Action.OpenUrl", "title": "View Dashboard", "url": f"{dashboard_url}/alerts/{alert_id}"}]

        priority = NotificationPriority.URGENT if severity in ["critical", "error"] else NotificationPriority.NORMAL

        return self.send_notification(
            card_type=CardType.ALERT,
            title=title,
            message=message,
            severity=severity,
            facts=facts,
            actions=actions,
            webhook_url=webhook_url,
            priority=priority,
        )

    def send_backup_status_card(
        self,
        job_name: str,
        status: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        data_size_gb: Optional[float] = None,
        duration_minutes: Optional[int] = None,
        error_message: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send backup job status card.

        Args:
            job_name: Backup job name
            status: Job status (success/failed/running)
            start_time: Job start time
            end_time: Job end time
            data_size_gb: Data size in GB
            duration_minutes: Duration in minutes
            error_message: Error message if failed
            webhook_url: Override webhook URL

        Returns:
            True if successful
        """
        severity = "success" if status == "success" else "error" if status == "failed" else "info"

        message = error_message if error_message else f"Backup job completed with status: {status}"

        facts = [
            {"title": "Job Name", "value": job_name},
            {"title": "Status", "value": status.upper()},
            {"title": "Start Time", "value": start_time.strftime("%Y-%m-%d %H:%M:%S")},
        ]

        if end_time:
            facts.append({"title": "End Time", "value": end_time.strftime("%Y-%m-%d %H:%M:%S")})

        if duration_minutes is not None:
            facts.append({"title": "Duration", "value": f"{duration_minutes} minutes"})

        if data_size_gb is not None:
            facts.append({"title": "Data Size", "value": f"{data_size_gb:.2f} GB"})

        return self.send_notification(
            card_type=CardType.BACKUP_STATUS,
            title=f"Backup Job: {job_name}",
            message=message,
            severity=severity,
            facts=facts,
            webhook_url=webhook_url,
        )

    def send_daily_summary_card(
        self,
        date: datetime,
        total_jobs: int,
        successful_jobs: int,
        failed_jobs: int,
        total_data_gb: float,
        alerts_count: int,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send daily summary card.

        Args:
            date: Summary date
            total_jobs: Total number of jobs
            successful_jobs: Number of successful jobs
            failed_jobs: Number of failed jobs
            total_data_gb: Total data backed up (GB)
            alerts_count: Number of alerts
            webhook_url: Override webhook URL

        Returns:
            True if successful
        """
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
        severity = "success" if failed_jobs == 0 else "warning" if failed_jobs < 3 else "error"

        message = f"Daily backup summary for {date.strftime('%Y-%m-%d')}"

        facts = [
            {"title": "Total Jobs", "value": str(total_jobs)},
            {"title": "Successful", "value": f"{successful_jobs} ({success_rate:.1f}%)"},
            {"title": "Failed", "value": str(failed_jobs)},
            {"title": "Total Data", "value": f"{total_data_gb:.2f} GB"},
            {"title": "Alerts", "value": str(alerts_count)},
        ]

        return self.send_notification(
            card_type=CardType.DAILY_SUMMARY,
            title="📊 Daily Backup Summary",
            message=message,
            severity=severity,
            facts=facts,
            webhook_url=webhook_url,
        )

    def send_weekly_report_card(
        self,
        week_start: datetime,
        week_end: datetime,
        total_jobs: int,
        success_rate: float,
        total_data_tb: float,
        top_issues: List[str],
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send weekly report card.

        Args:
            week_start: Week start date
            week_end: Week end date
            total_jobs: Total jobs executed
            success_rate: Success rate percentage
            total_data_tb: Total data backed up (TB)
            top_issues: List of top issues
            webhook_url: Override webhook URL

        Returns:
            True if successful
        """
        severity = "success" if success_rate >= 95 else "warning" if success_rate >= 90 else "error"

        message = f"Weekly backup report: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"

        facts = [
            {"title": "Total Jobs", "value": str(total_jobs)},
            {"title": "Success Rate", "value": f"{success_rate:.1f}%"},
            {"title": "Total Data", "value": f"{total_data_tb:.2f} TB"},
            {"title": "Reporting Period", "value": f"{(week_end - week_start).days} days"},
        ]

        # Add top issues as separate text block
        issues_text = ""
        if top_issues:
            issues_text = "\n\n**Top Issues:**\n" + "\n".join([f"• {issue}" for issue in top_issues[:5]])

        return self.send_notification(
            card_type=CardType.WEEKLY_REPORT,
            title="📈 Weekly Backup Report",
            message=message + issues_text,
            severity=severity,
            facts=facts,
            webhook_url=webhook_url,
        )

    def _build_card(
        self,
        card_type: CardType,
        title: str,
        message: str,
        severity: str,
        facts: Optional[List[Dict[str, str]]] = None,
        actions: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Build Adaptive Card JSON.

        Args:
            card_type: Type of card
            title: Card title
            message: Main message
            severity: Severity level
            facts: List of facts
            actions: List of actions

        Returns:
            Adaptive Card JSON dictionary
        """
        # Get color and icon
        color = self.COLORS.get(severity, "Default")
        icon = self.ICONS.get(severity, "")

        # Build card body
        body = []

        # Header with icon and title
        header = {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [{"type": "TextBlock", "text": icon, "size": "ExtraLarge"}],
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": title,
                            "weight": "Bolder",
                            "size": "Large",
                            "color": color,
                            "wrap": True,
                        }
                    ],
                },
            ],
        }
        body.append(header)

        # Message
        if message:
            body.append({"type": "TextBlock", "text": message, "wrap": True, "spacing": "Medium"})

        # Facts
        if facts:
            body.append({"type": "FactSet", "facts": facts, "spacing": "Medium"})

        # Build card
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": self.CARD_VERSION,
            "body": body,
        }

        # Add actions if provided
        if actions:
            card["actions"] = actions

        # Add metadata
        card["msteams"] = {"width": "Full"}

        return card

    def _send_card(self, card: Dict, webhook_url: str) -> bool:
        """
        Send Adaptive Card to Teams webhook.

        Args:
            card: Adaptive Card JSON
            webhook_url: Teams webhook URL

        Returns:
            True if successful
        """
        if not self.validate_webhook_url(webhook_url):
            logger.error(f"Invalid webhook URL: {webhook_url}")
            return False

        try:
            # Build payload
            payload = {
                "type": "message",
                "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": card}],
            }

            # Send request
            response = self.session.post(webhook_url, json=payload, timeout=self.timeout)

            # Check response
            if response.status_code == 200:
                logger.info(f"Teams notification sent successfully")
                return True
            else:
                logger.error(f"Teams webhook returned status {response.status_code}: {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error(f"Teams webhook request timed out after {self.timeout}s")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Teams webhook request failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Teams notification: {str(e)}", exc_info=True)
            return False

    def _record_history(
        self,
        card_type: str,
        title: str,
        severity: str,
        success: bool,
        priority: str = "normal",
        error: Optional[str] = None,
    ):
        """
        Record notification send history.

        Args:
            card_type: Type of card
            title: Card title
            severity: Severity level
            success: Whether send was successful
            priority: Notification priority
            error: Error message if failed
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "card_type": card_type,
            "title": title,
            "severity": severity,
            "priority": priority,
            "success": success,
            "error": error,
        }

        self._history.append(record)

        # Keep only last 100 records
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def get_send_history(self, limit: int = 50) -> List[Dict]:
        """
        Get notification send history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of history records
        """
        return self._history[-limit:]

    def get_statistics(self) -> Dict:
        """
        Get notification statistics.

        Returns:
            Statistics dictionary
        """
        if not self._history:
            return {
                "total_sent": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "by_severity": {},
                "by_card_type": {},
            }

        total = len(self._history)
        successful = sum(1 for r in self._history if r["success"])
        failed = total - successful

        # Count by severity
        by_severity = {}
        for record in self._history:
            severity = record["severity"]
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # Count by card type
        by_card_type = {}
        for record in self._history:
            card_type = record["card_type"]
            by_card_type[card_type] = by_card_type.get(card_type, 0) + 1

        return {
            "total_sent": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "by_severity": by_severity,
            "by_card_type": by_card_type,
        }

    def test_connection(self, webhook_url: Optional[str] = None) -> bool:
        """
        Test Teams webhook connection.

        Args:
            webhook_url: Override webhook URL

        Returns:
            True if connection successful
        """
        return self.send_notification(
            card_type=CardType.ALERT,
            title="🔔 Connection Test",
            message="This is a test notification from Backup Management System.",
            severity="info",
            facts=[{"title": "Test Time", "value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}],
            webhook_url=webhook_url,
        )
