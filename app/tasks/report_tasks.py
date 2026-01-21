"""
Celery Report Tasks for Backup Management System
Phase 11: Asynchronous Report Generation

This module provides asynchronous PDF report generation
and scheduled report delivery.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.report_tasks.generate_pdf_report",
    max_retries=2,
    default_retry_delay=120,
    time_limit=600,  # 10 minutes max
    soft_time_limit=540,  # 9 minutes soft limit
)
def generate_pdf_report(
    self,
    report_type: str,
    params: Optional[Dict[str, Any]] = None,
    notify_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate PDF report asynchronously.

    This task generates PDF reports in the background,
    allowing complex reports to be created without blocking
    the user interface.

    Args:
        self: Celery task instance (bound)
        report_type: Type of report (compliance, daily, monthly, audit)
        params: Report parameters (date range, filters, etc.)
        notify_email: Email to send report to upon completion

    Returns:
        Dict with report generation status and file path
    """
    from app.services.pdf_generator import PDFGenerator

    task_id = self.request.id

    logger.info(f"[Task {task_id}] Generating {report_type} PDF report")

    result = {
        "task_id": task_id,
        "report_type": report_type,
        "status": "processing",
        "started_at": datetime.utcnow().isoformat(),
    }

    try:
        pdf_generator = PDFGenerator()
        params = params or {}

        # Generate report based on type
        if report_type == "compliance":
            report_path = pdf_generator.generate_compliance_report(**params)
        elif report_type == "daily":
            report_path = pdf_generator.generate_daily_report(**params)
        elif report_type == "monthly":
            report_path = pdf_generator.generate_monthly_report(**params)
        elif report_type == "audit":
            report_path = pdf_generator.generate_audit_report(**params)
        elif report_type == "backup_summary":
            report_path = pdf_generator.generate_backup_summary_report(**params)
        else:
            logger.error(f"[Task {task_id}] Unknown report type: {report_type}")
            result["status"] = "failed"
            result["error"] = f"Unknown report type: {report_type}"
            return result

        if report_path and Path(report_path).exists():
            result["status"] = "completed"
            result["file_path"] = str(report_path)
            result["file_size"] = Path(report_path).stat().st_size
            result["completed_at"] = datetime.utcnow().isoformat()

            logger.info(f"[Task {task_id}] Report generated: {report_path}")

            # Record report in database
            _record_report(
                report_type=report_type,
                file_path=str(report_path),
                task_id=task_id,
                status="completed",
            )

            # Send notification if email provided
            if notify_email:
                _send_report_notification(
                    recipient=notify_email,
                    report_type=report_type,
                    file_path=str(report_path),
                )

        else:
            result["status"] = "failed"
            result["error"] = "Report generation returned no file"

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error generating report: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        result["completed_at"] = datetime.utcnow().isoformat()

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120)

        return result


@celery_app.task(
    bind=True,
    name="app.tasks.report_tasks.generate_daily_report",
    max_retries=2,
)
def generate_daily_report(self) -> Dict[str, Any]:
    """
    Generate and distribute daily backup report.

    This scheduled task generates a daily summary report
    and sends it to configured recipients.

    Returns:
        Dict with daily report status
    """
    task_id = self.request.id
    today = datetime.utcnow().date()

    logger.info(f"[Task {task_id}] Generating daily report for {today}")

    result = {
        "task_id": task_id,
        "report_date": str(today),
        "status": "processing",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        from app.models import Alert, BackupJob, db
        from app.services.compliance_checker import ComplianceChecker

        # Get yesterday's date range
        start_date = datetime.combine(today - timedelta(days=1), datetime.min.time())
        end_date = datetime.combine(today, datetime.min.time())

        # Collect statistics
        stats = {
            "total_jobs": BackupJob.query.filter(
                BackupJob.created_at >= start_date,
                BackupJob.created_at < end_date,
            ).count(),
            "successful_jobs": BackupJob.query.filter(
                BackupJob.created_at >= start_date,
                BackupJob.created_at < end_date,
                BackupJob.status == "success",
            ).count(),
            "failed_jobs": BackupJob.query.filter(
                BackupJob.created_at >= start_date,
                BackupJob.created_at < end_date,
                BackupJob.status == "failed",
            ).count(),
            "alerts_count": Alert.query.filter(
                Alert.created_at >= start_date,
                Alert.created_at < end_date,
            ).count(),
        }

        # Calculate success rate
        if stats["total_jobs"] > 0:
            stats["success_rate"] = round(stats["successful_jobs"] / stats["total_jobs"] * 100, 1)
        else:
            stats["success_rate"] = 100.0

        # Check compliance
        try:
            checker = ComplianceChecker()
            compliance_status = checker.check_all_rules()
            stats["compliance_status"] = compliance_status.get("overall_status", "unknown")
            stats["compliance_score"] = compliance_status.get("score", 0)
        except Exception as e:
            logger.warning(f"Failed to get compliance status: {e}")
            stats["compliance_status"] = "unknown"
            stats["compliance_score"] = 0

        # Generate PDF report
        report_task = generate_pdf_report.apply_async(
            kwargs={
                "report_type": "daily",
                "params": {
                    "date": str(today - timedelta(days=1)),
                    "stats": stats,
                },
            }
        )

        result["stats"] = stats
        result["report_task_id"] = report_task.id
        result["status"] = "completed"

        logger.info(f"[Task {task_id}] Daily report stats: {stats}")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error generating daily report: {e}")
        result["status"] = "error"
        result["error"] = str(e)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)

        return result


@celery_app.task(
    bind=True,
    name="app.tasks.report_tasks.generate_monthly_report",
    max_retries=2,
    time_limit=900,  # 15 minutes max
)
def generate_monthly_report(
    self,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate monthly backup report.

    Args:
        self: Celery task instance (bound)
        year: Report year (defaults to current year)
        month: Report month (defaults to previous month)

    Returns:
        Dict with monthly report status
    """
    task_id = self.request.id

    # Default to previous month
    now = datetime.utcnow()
    if year is None or month is None:
        if now.month == 1:
            year = now.year - 1
            month = 12
        else:
            year = now.year
            month = now.month - 1

    logger.info(f"[Task {task_id}] Generating monthly report for {year}-{month:02d}")

    result = {
        "task_id": task_id,
        "year": year,
        "month": month,
        "status": "processing",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Generate PDF report
        report_task = generate_pdf_report.apply_async(
            kwargs={
                "report_type": "monthly",
                "params": {
                    "year": year,
                    "month": month,
                },
            }
        )

        result["report_task_id"] = report_task.id
        result["status"] = "queued"

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error generating monthly report: {e}")
        result["status"] = "error"
        result["error"] = str(e)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)

        return result


@celery_app.task(
    bind=True,
    name="app.tasks.report_tasks.schedule_report",
    max_retries=1,
)
def schedule_report(
    self,
    report_type: str,
    schedule_type: str,  # daily, weekly, monthly
    recipients: List[str],
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Schedule recurring report generation.

    Args:
        self: Celery task instance (bound)
        report_type: Type of report
        schedule_type: Frequency (daily, weekly, monthly)
        recipients: List of email recipients
        params: Report parameters

    Returns:
        Dict with scheduling status
    """
    task_id = self.request.id

    logger.info(f"[Task {task_id}] Scheduling {schedule_type} {report_type} report")

    result = {
        "task_id": task_id,
        "report_type": report_type,
        "schedule_type": schedule_type,
        "recipients": recipients,
        "status": "processing",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        from app.models import ScheduledReport, db

        # Create or update scheduled report
        scheduled = ScheduledReport(
            report_type=report_type,
            schedule_type=schedule_type,
            recipients=",".join(recipients),
            parameters=str(params or {}),
            is_active=True,
            created_at=datetime.utcnow(),
        )

        db.session.add(scheduled)
        db.session.commit()

        result["scheduled_report_id"] = scheduled.id
        result["status"] = "scheduled"

        logger.info(f"[Task {task_id}] Report scheduled: {scheduled.id}")

        return result

    except Exception as e:
        logger.exception(f"[Task {task_id}] Error scheduling report: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


def _record_report(
    report_type: str,
    file_path: str,
    task_id: str,
    status: str,
):
    """Record generated report in database."""
    try:
        from app.models import Report, db

        report = Report(
            report_type=report_type,
            file_path=file_path,
            task_id=task_id,
            status=status,
            generated_at=datetime.utcnow(),
        )

        db.session.add(report)
        db.session.commit()

        logger.debug(f"Recorded report: {report.id}")

    except Exception as e:
        logger.warning(f"Failed to record report: {e}")
        db.session.rollback()


def _send_report_notification(
    recipient: str,
    report_type: str,
    file_path: str,
):
    """Send notification about generated report."""
    from app.tasks.email_tasks import send_email

    subject = f"📊 レポート生成完了: {report_type}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <h2>レポート生成完了</h2>
        <p>リクエストされた<strong>{report_type}</strong>レポートが生成されました。</p>
        <p><strong>ファイル:</strong> {Path(file_path).name}</p>
        <p><strong>生成日時:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        <hr>
        <p>3-2-1-1-0 Backup Management System</p>
    </body>
    </html>
    """

    send_email.apply_async(
        kwargs={
            "to": recipient,
            "subject": subject,
            "html_body": html_body,
        }
    )
