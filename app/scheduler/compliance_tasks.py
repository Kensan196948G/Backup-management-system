"""
Celery tasks for automated compliance report generation and distribution.
Scheduled tasks:
- Weekly report: Every Monday at 09:00 JST
- Monthly report: 1st of each month at 08:00 JST
"""
from datetime import datetime, timezone

from celery import shared_task
from flask import current_app


@shared_task(name="compliance.generate_and_send_weekly_report")
def generate_and_send_weekly_report():
    """
    Celery task: Generate weekly compliance report and send via email.
    Scheduled every Monday at 09:00 JST.
    """
    from app.services.compliance_checker import ComplianceChecker
    from app.services.email_notifier import get_email_notifier

    try:
        checker = ComplianceChecker()
        report_data = checker.generate_system_report()

        text_body, html_body = checker.format_email_body(report_data)
        checker.generate_csv_report(report_data)  # generate for potential future attachment use

        notifier = get_email_notifier()
        if notifier:
            subject = (
                f"【週次レポート】3-2-1-1-0 コンプライアンス率: "
                f"{report_data['compliance_rate']}%"
            )
            recipients = current_app.config.get("ALERT_EMAIL_RECIPIENTS", [])
            notifier.send_email(
                to_emails=recipients,
                subject=subject,
                body_text=text_body,
                body_html=html_body,
            )
            current_app.logger.info(
                f"Weekly compliance report sent: {report_data['compliance_rate']}%"
            )
        else:
            current_app.logger.warning(
                "EmailNotifier not configured, skipping email send"
            )

        return {
            "status": "success",
            "compliance_rate": report_data["compliance_rate"],
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        current_app.logger.error(f"Compliance report task failed: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="compliance.generate_and_send_monthly_report")
def generate_and_send_monthly_report():
    """
    Celery task: Generate monthly compliance report.
    Scheduled on the 1st of each month at 08:00 JST.
    """
    from app.services.compliance_checker import ComplianceChecker
    from app.services.email_notifier import get_email_notifier

    try:
        checker = ComplianceChecker()
        report_data = checker.generate_system_report()

        text_body, html_body = checker.format_email_body(report_data)

        notifier = get_email_notifier()
        if notifier:
            period = datetime.now(timezone.utc).strftime("%Y年%m月")
            subject = f"【月次レポート】3-2-1-1-0 コンプライアンスサマリー {period}"
            recipients = current_app.config.get("ALERT_EMAIL_RECIPIENTS", [])
            notifier.send_email(
                to_emails=recipients,
                subject=subject,
                body_text=text_body,
                body_html=html_body,
            )
            current_app.logger.info(
                f"Monthly compliance report sent: {report_data['compliance_rate']}%"
            )
        else:
            current_app.logger.warning(
                "EmailNotifier not configured, skipping email send"
            )

        return {
            "status": "success",
            "compliance_rate": report_data["compliance_rate"],
            "period": datetime.now(timezone.utc).strftime("%Y-%m"),
        }

    except Exception as e:
        current_app.logger.error(f"Monthly compliance report task failed: {e}")
        return {"status": "error", "message": str(e)}
