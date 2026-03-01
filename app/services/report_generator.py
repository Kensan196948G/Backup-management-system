"""
Report Generator Service

Generates backup management reports in multiple formats:
- HTML (interactive web format)
- PDF (portable format)
- CSV (data export format)

Report types:
- Daily: Daily backup status and compliance
- Weekly: Weekly summary with trends
- Monthly: Monthly performance and compliance metrics
- Compliance: 3-2-1-1-0 rule compliance analysis
- Audit: Audit log report for compliance
"""

import csv
import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import Config
from app.models import (
    AuditLog,
    BackupCopy,
    BackupExecution,
    BackupJob,
    ComplianceStatus,
    Report,
    User,
    VerificationTest,
    db,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates reports in various formats (HTML, PDF, CSV).

    Responsibilities:
    - Generate daily/weekly/monthly reports
    - Generate compliance reports
    - Generate audit reports
    - Export data in multiple formats
    - Store report files
    """

    def __init__(self):
        """Initialize report generator"""
        self.report_dir = Config.REPORT_OUTPUT_DIR
        self.ensure_report_directory()

    def ensure_report_directory(self) -> None:
        """Ensure report output directory exists"""
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Report directory ready: {self.report_dir}")
        except Exception as e:
            logger.error(f"Failed to create report directory: {str(e)}")
            raise

    def generate_daily_report(self, generated_by: int, date: Optional[datetime] = None, format: str = "html") -> Report:
        """
        Generate daily backup status report.

        Args:
            generated_by: User ID generating the report
            date: Date to generate report for (default: today)
            format: Output format (html, pdf, csv)

        Returns:
            Report object with file path
        """
        try:
            if date is None:
                date = datetime.now(timezone.utc).date()
            elif isinstance(date, datetime):
                date = date.date()

            # Gather data for the date
            data = self._gather_daily_data(date)

            # Generate report based on format
            if format == "html":
                file_path, content = self._generate_daily_html(data, date)
            elif format == "pdf":
                file_path, content = self._generate_daily_pdf(data, date)
            elif format == "csv":
                file_path, content = self._generate_daily_csv(data, date)
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to file
            self._save_report_file(file_path, content)

            # Create database record
            report = Report(
                report_type="daily",
                report_title=f'Daily Backup Report - {date.strftime("%Y-%m-%d")}',
                date_from=date,
                date_to=date,
                file_path=str(file_path),
                file_format=format,
                generated_by=generated_by,
            )

            db.session.add(report)
            db.session.commit()

            logger.info(f"Generated daily report: {file_path}")

            return report

        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}", exc_info=True)
            db.session.rollback()
            raise

    def generate_weekly_report(self, generated_by: int, end_date: Optional[datetime] = None, format: str = "html") -> Report:
        """
        Generate weekly summary report.

        Args:
            generated_by: User ID generating the report
            end_date: Last date of the week (default: today)
            format: Output format (html, pdf, csv)

        Returns:
            Report object with file path
        """
        try:
            if end_date is None:
                end_date = datetime.now(timezone.utc).date()
            elif isinstance(end_date, datetime):
                end_date = end_date.date()

            start_date = end_date - timedelta(days=6)

            # Gather data for the week
            data = self._gather_weekly_data(start_date, end_date)

            # Generate report based on format
            if format == "html":
                file_path, content = self._generate_weekly_html(data, start_date, end_date)
            elif format == "pdf":
                file_path, content = self._generate_weekly_pdf(data, start_date, end_date)
            elif format == "csv":
                file_path, content = self._generate_weekly_csv(data, start_date, end_date)
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to file
            self._save_report_file(file_path, content)

            # Create database record
            report = Report(
                report_type="weekly",
                report_title=f"Weekly Report - {start_date} to {end_date}",
                date_from=start_date,
                date_to=end_date,
                file_path=str(file_path),
                file_format=format,
                generated_by=generated_by,
            )

            db.session.add(report)
            db.session.commit()

            logger.info(f"Generated weekly report: {file_path}")

            return report

        except Exception as e:
            logger.error(f"Error generating weekly report: {str(e)}", exc_info=True)
            db.session.rollback()
            raise

    def generate_monthly_report(
        self, generated_by: int, year: Optional[int] = None, month: Optional[int] = None, format: str = "html"
    ) -> Report:
        """
        Generate monthly performance and compliance report.

        Args:
            generated_by: User ID generating the report
            year: Year (default: current)
            month: Month (default: current)
            format: Output format (html, pdf, csv)

        Returns:
            Report object with file path
        """
        try:
            now = datetime.now(timezone.utc)
            if year is None:
                year = now.year
            if month is None:
                month = now.month

            # Calculate date range
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

            # Gather data for the month
            data = self._gather_monthly_data(start_date, end_date)

            # Generate report based on format
            if format == "html":
                file_path, content = self._generate_monthly_html(data, start_date, end_date)
            elif format == "pdf":
                file_path, content = self._generate_monthly_pdf(data, start_date, end_date)
            elif format == "csv":
                file_path, content = self._generate_monthly_csv(data, start_date, end_date)
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to file
            self._save_report_file(file_path, content)

            # Create database record
            report = Report(
                report_type="monthly",
                report_title=f"Monthly Report - {year}-{month:02d}",
                date_from=start_date,
                date_to=end_date,
                file_path=str(file_path),
                file_format=format,
                generated_by=generated_by,
            )

            db.session.add(report)
            db.session.commit()

            logger.info(f"Generated monthly report: {file_path}")

            return report

        except Exception as e:
            logger.error(f"Error generating monthly report: {str(e)}", exc_info=True)
            db.session.rollback()
            raise

    def generate_compliance_report(
        self, generated_by: int, end_date: Optional[datetime] = None, format: str = "html"
    ) -> Report:
        """
        Generate 3-2-1-1-0 compliance analysis report.

        Args:
            generated_by: User ID generating the report
            end_date: Report end date (default: today)
            format: Output format (html, pdf, csv)

        Returns:
            Report object with file path
        """
        try:
            if end_date is None:
                end_date = datetime.now(timezone.utc).date()
            elif isinstance(end_date, datetime):
                end_date = end_date.date()

            start_date = end_date - timedelta(days=30)

            # Gather compliance data
            data = self._gather_compliance_data(start_date, end_date)

            # Generate report based on format
            if format == "html":
                file_path, content = self._generate_compliance_html(data, start_date, end_date)
            elif format == "pdf":
                file_path, content = self._generate_compliance_pdf(data, start_date, end_date)
            elif format == "csv":
                file_path, content = self._generate_compliance_csv(data, start_date, end_date)
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to file
            self._save_report_file(file_path, content)

            # Create database record
            report = Report(
                report_type="compliance",
                report_title=f"Compliance Report - {start_date} to {end_date}",
                date_from=start_date,
                date_to=end_date,
                file_path=str(file_path),
                file_format=format,
                generated_by=generated_by,
            )

            db.session.add(report)
            db.session.commit()

            logger.info(f"Generated compliance report: {file_path}")

            return report

        except Exception as e:
            logger.error(f"Error generating compliance report: {str(e)}", exc_info=True)
            db.session.rollback()
            raise

    def generate_audit_report(
        self,
        generated_by: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "html",
    ) -> Report:
        """
        Generate audit log report.

        Args:
            generated_by: User ID generating the report
            start_date: Report start date (default: 30 days ago)
            end_date: Report end date (default: today)
            format: Output format (html, pdf, csv)

        Returns:
            Report object with file path
        """
        try:
            now = datetime.now(timezone.utc).date()
            if end_date is None:
                end_date = now
            elif isinstance(end_date, datetime):
                end_date = end_date.date()

            if start_date is None:
                start_date = end_date - timedelta(days=30)
            elif isinstance(start_date, datetime):
                start_date = start_date.date()

            # Gather audit data
            data = self._gather_audit_data(start_date, end_date)

            # Generate report based on format
            if format == "html":
                file_path, content = self._generate_audit_html(data, start_date, end_date)
            elif format == "pdf":
                file_path, content = self._generate_audit_pdf(data, start_date, end_date)
            elif format == "csv":
                file_path, content = self._generate_audit_csv(data, start_date, end_date)
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to file
            self._save_report_file(file_path, content)

            # Create database record
            report = Report(
                report_type="audit",
                report_title=f"Audit Report - {start_date} to {end_date}",
                date_from=start_date,
                date_to=end_date,
                file_path=str(file_path),
                file_format=format,
                generated_by=generated_by,
            )

            db.session.add(report)
            db.session.commit()

            logger.info(f"Generated audit report: {file_path}")

            return report

        except Exception as e:
            logger.error(f"Error generating audit report: {str(e)}", exc_info=True)
            db.session.rollback()
            raise

    # Data gathering methods

    def _gather_daily_data(self, date) -> Dict:
        """Gather data for daily report"""
        try:
            date_start = datetime.combine(date, datetime.min.time())
            date_end = datetime.combine(date, datetime.max.time())

            jobs = BackupJob.query.filter_by(is_active=True).all()

            executions = BackupExecution.query.filter(
                BackupExecution.execution_date >= date_start, BackupExecution.execution_date <= date_end
            ).all()

            return {
                "date": date,
                "total_jobs": len(jobs),
                "executions": executions,
                "success_count": sum(1 for e in executions if e.execution_result == "success"),
                "failed_count": sum(1 for e in executions if e.execution_result == "failed"),
                "warning_count": sum(1 for e in executions if e.execution_result == "warning"),
            }

        except Exception as e:
            logger.error(f"Error gathering daily data: {str(e)}")
            return {}

    def _gather_weekly_data(self, start_date, end_date) -> Dict:
        """Gather data for weekly report"""
        try:
            date_start = datetime.combine(start_date, datetime.min.time())
            date_end = datetime.combine(end_date, datetime.max.time())

            jobs = BackupJob.query.filter_by(is_active=True).all()

            executions = BackupExecution.query.filter(
                BackupExecution.execution_date >= date_start, BackupExecution.execution_date <= date_end
            ).all()

            daily_data = {}
            for i in range((end_date - start_date).days + 1):
                current_date = start_date + timedelta(days=i)
                daily_data[current_date] = sum(
                    1 for e in executions if e.execution_date.date() == current_date and e.execution_result == "success"
                )

            return {
                "start_date": start_date,
                "end_date": end_date,
                "total_jobs": len(jobs),
                "executions": executions,
                "daily_data": daily_data,
                "success_count": sum(1 for e in executions if e.execution_result == "success"),
                "failed_count": sum(1 for e in executions if e.execution_result == "failed"),
            }

        except Exception as e:
            logger.error(f"Error gathering weekly data: {str(e)}")
            return {}

    def _gather_monthly_data(self, start_date, end_date) -> Dict:
        """Gather data for monthly report"""
        try:
            date_start = datetime.combine(start_date, datetime.min.time())
            date_end = datetime.combine(end_date, datetime.max.time())

            jobs = BackupJob.query.filter_by(is_active=True).all()

            executions = BackupExecution.query.filter(
                BackupExecution.execution_date >= date_start, BackupExecution.execution_date <= date_end
            ).all()

            compliance_statuses = ComplianceStatus.query.filter(
                ComplianceStatus.check_date >= date_start, ComplianceStatus.check_date <= date_end
            ).all()

            verification_tests = VerificationTest.query.filter(
                VerificationTest.test_date >= date_start, VerificationTest.test_date <= date_end
            ).all()

            return {
                "start_date": start_date,
                "end_date": end_date,
                "total_jobs": len(jobs),
                "executions": executions,
                "compliance_statuses": compliance_statuses,
                "verification_tests": verification_tests,
                "success_count": sum(1 for e in executions if e.execution_result == "success"),
                "failed_count": sum(1 for e in executions if e.execution_result == "failed"),
                "test_success_count": sum(1 for t in verification_tests if t.test_result == "success"),
                "test_failed_count": sum(1 for t in verification_tests if t.test_result == "failed"),
            }

        except Exception as e:
            logger.error(f"Error gathering monthly data: {str(e)}")
            return {}

    def _gather_compliance_data(self, start_date, end_date) -> Dict:
        """Gather compliance data"""
        try:
            date_start = datetime.combine(start_date, datetime.min.time())
            date_end = datetime.combine(end_date, datetime.max.time())

            compliance_statuses = ComplianceStatus.query.filter(
                ComplianceStatus.check_date >= date_start, ComplianceStatus.check_date <= date_end
            ).all()

            jobs = BackupJob.query.filter_by(is_active=True).all()

            compliant_jobs = sum(1 for c in compliance_statuses if c.overall_status == "compliant")
            non_compliant_jobs = sum(1 for c in compliance_statuses if c.overall_status == "non_compliant")
            warning_jobs = sum(1 for c in compliance_statuses if c.overall_status == "warning")

            return {
                "start_date": start_date,
                "end_date": end_date,
                "total_jobs": len(jobs),
                "compliance_statuses": compliance_statuses,
                "compliant_jobs": compliant_jobs,
                "non_compliant_jobs": non_compliant_jobs,
                "warning_jobs": warning_jobs,
                "compliance_rate": round((compliant_jobs / len(jobs) * 100), 2) if jobs else 0,
            }

        except Exception as e:
            logger.error(f"Error gathering compliance data: {str(e)}")
            return {}

    def _gather_audit_data(self, start_date, end_date) -> Dict:
        """Gather audit log data"""
        try:
            date_start = datetime.combine(start_date, datetime.min.time())
            date_end = datetime.combine(end_date, datetime.max.time())

            audit_logs = (
                AuditLog.query.filter(AuditLog.created_at >= date_start, AuditLog.created_at <= date_end)
                .order_by(AuditLog.created_at.desc())
                .all()
            )

            success_count = sum(1 for log in audit_logs if log.action_result == "success")
            failed_count = sum(1 for log in audit_logs if log.action_result == "failed")

            return {
                "start_date": start_date,
                "end_date": end_date,
                "audit_logs": audit_logs,
                "total_actions": len(audit_logs),
                "success_count": success_count,
                "failed_count": failed_count,
            }

        except Exception as e:
            logger.error(f"Error gathering audit data: {str(e)}")
            return {}

    # HTML generation methods

    def _generate_daily_html(self, data: Dict, date) -> Tuple[Path, str]:
        """Generate HTML daily report"""
        html = f"""
        <html>
            <head>
                <title>Daily Report - {date}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
                    .section {{ margin: 20px 0; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .success {{ color: green; }}
                    .failed {{ color: red; }}
                    .warning {{ color: orange; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Daily Backup Report</h1>
                    <p>Date: {date}</p>
                </div>

                <div class="section">
                    <h2>Summary</h2>
                    <p>Total Jobs: {data.get('total_jobs', 0)}</p>
                    <p class="success">Successful: {data.get('success_count', 0)}</p>
                    <p class="failed">Failed: {data.get('failed_count', 0)}</p>
                    <p class="warning">Warnings: {data.get('warning_count', 0)}</p>
                </div>

                <div class="section">
                    <h2>Execution Details</h2>
                    <table>
                        <tr>
                            <th>Job ID</th>
                            <th>Execution Time</th>
                            <th>Result</th>
                            <th>Size (bytes)</th>
                            <th>Duration (sec)</th>
                        </tr>
        """

        for execution in data.get("executions", []):
            result_class = "success" if execution.execution_result == "success" else "failed"
            html += f"""
                        <tr>
                            <td>{execution.job_id}</td>
                            <td>{execution.execution_date}</td>
                            <td class="{result_class}">{execution.execution_result}</td>
                            <td>{execution.backup_size_bytes or '-'}</td>
                            <td>{execution.duration_seconds or '-'}</td>
                        </tr>
            """

        html += """
                    </table>
                </div>
            </body>
        </html>
        """

        file_path = self.report_dir / f"daily_report_{date}.html"
        return file_path, html

    def _generate_weekly_html(self, data: Dict, start_date, end_date) -> Tuple[Path, str]:
        """Generate HTML weekly report"""
        html = f"""
        <html>
            <head>
                <title>Weekly Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
                    .section {{ margin: 20px 0; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Weekly Report</h1>
                    <p>Period: {start_date} to {end_date}</p>
                </div>

                <div class="section">
                    <h2>Summary</h2>
                    <p>Total Jobs: {data.get('total_jobs', 0)}</p>
                    <p>Successful Executions: {data.get('success_count', 0)}</p>
                    <p>Failed Executions: {data.get('failed_count', 0)}</p>
                </div>
            </body>
        </html>
        """

        file_path = self.report_dir / f"weekly_report_{start_date}_to_{end_date}.html"
        return file_path, html

    def _generate_monthly_html(self, data: Dict, start_date, end_date) -> Tuple[Path, str]:
        """Generate HTML monthly report"""
        html = f"""
        <html>
            <head>
                <title>Monthly Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
                    .section {{ margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Monthly Report</h1>
                    <p>Period: {start_date} to {end_date}</p>
                </div>

                <div class="section">
                    <h2>Summary</h2>
                    <p>Total Jobs: {data.get('total_jobs', 0)}</p>
                    <p>Successful Executions: {data.get('success_count', 0)}</p>
                    <p>Failed Executions: {data.get('failed_count', 0)}</p>
                    <p>Verification Tests Passed: {data.get('test_success_count', 0)}</p>
                    <p>Verification Tests Failed: {data.get('test_failed_count', 0)}</p>
                </div>
            </body>
        </html>
        """

        file_path = self.report_dir / f"monthly_report_{start_date.strftime('%Y-%m')}.html"
        return file_path, html

    def _generate_compliance_html(self, data: Dict, start_date, end_date) -> Tuple[Path, str]:
        """Generate HTML compliance report"""
        html = f"""
        <html>
            <head>
                <title>Compliance Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
                    .section {{ margin: 20px 0; }}
                    .compliant {{ color: green; }}
                    .non-compliant {{ color: red; }}
                    .warning {{ color: orange; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>3-2-1-1-0 Compliance Report</h1>
                    <p>Period: {start_date} to {end_date}</p>
                </div>

                <div class="section">
                    <h2>Compliance Summary</h2>
                    <p>Total Jobs: {data.get('total_jobs', 0)}</p>
                    <p class="compliant">Compliant: {data.get('compliant_jobs', 0)}</p>
                    <p class="warning">Warning: {data.get('warning_jobs', 0)}</p>
                    <p class="non-compliant">Non-Compliant: {data.get('non_compliant_jobs', 0)}</p>
                    <p><strong>Compliance Rate: {data.get('compliance_rate', 0)}%</strong></p>
                </div>
            </body>
        </html>
        """

        file_path = self.report_dir / f"compliance_report_{start_date}_to_{end_date}.html"
        return file_path, html

    def _generate_audit_html(self, data: Dict, start_date, end_date) -> Tuple[Path, str]:
        """Generate HTML audit report"""
        html = f"""
        <html>
            <head>
                <title>Audit Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
                    .section {{ margin: 20px 0; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Audit Log Report</h1>
                    <p>Period: {start_date} to {end_date}</p>
                </div>

                <div class="section">
                    <h2>Summary</h2>
                    <p>Total Actions: {data.get('total_actions', 0)}</p>
                    <p>Successful: {data.get('success_count', 0)}</p>
                    <p>Failed: {data.get('failed_count', 0)}</p>
                </div>

                <div class="section">
                    <h2>Audit Details</h2>
                    <table>
                        <tr>
                            <th>User</th>
                            <th>Action</th>
                            <th>Resource</th>
                            <th>Result</th>
                            <th>Time</th>
                        </tr>
        """

        for log in data.get("audit_logs", [])[:100]:  # Limit to first 100
            user_name = log.user.username if log.user else "-"
            html += f"""
                        <tr>
                            <td>{user_name}</td>
                            <td>{log.action_type}</td>
                            <td>{log.resource_type or '-'}</td>
                            <td>{log.action_result}</td>
                            <td>{log.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
                        </tr>
            """

        html += """
                    </table>
                </div>
            </body>
        </html>
        """

        file_path = self.report_dir / f"audit_report_{start_date}_to_{end_date}.html"
        return file_path, html

    # PDF generation methods

    def _generate_daily_pdf(self, data: Dict, date) -> Tuple[Path, bytes]:
        """
        Generate PDF daily report using WeasyPrint.

        Args:
            data: Report data dictionary
            date: Report date

        Returns:
            Tuple of (file_path, pdf_bytes)
        """
        try:
            from app.services.pdf_generator import PDFGenerator

            pdf_gen = PDFGenerator()

            # Prepare context with all necessary data
            context = {
                "report_title": f"Daily Backup Report - {date}",
                "start_date": datetime.combine(date, datetime.min.time()),
                "end_date": datetime.combine(date, datetime.max.time()),
                "generated_date": datetime.now(timezone.utc),
                "data": {
                    **data,
                    "success_rate": (
                        (data.get("success_count", 0) / len(data.get("executions", [])) * 100) if data.get("executions") else 0
                    ),
                    "avg_backup_size": (
                        sum(e.backup_size_bytes or 0 for e in data.get("executions", [])) / len(data.get("executions", []))
                        if data.get("executions")
                        else 0
                    ),
                    "avg_duration": (
                        sum(e.duration_seconds or 0 for e in data.get("executions", [])) / len(data.get("executions", []))
                        if data.get("executions")
                        else 0
                    ),
                },
            }

            # Generate PDF using compliance template (can use for daily too)
            pdf_bytes = pdf_gen.generate_pdf_from_template("compliance_report_template.html", context)

            file_path = self.report_dir / f"daily_report_{date}.pdf"
            logger.info(f"Generated daily PDF report: {file_path}")

            return file_path, pdf_bytes

        except Exception as e:
            logger.error(f"Error generating daily PDF: {str(e)}", exc_info=True)
            raise

    def _generate_weekly_pdf(self, data: Dict, start_date, end_date) -> Tuple[Path, bytes]:
        """
        Generate PDF weekly report using WeasyPrint.

        Args:
            data: Report data dictionary
            start_date: Week start date
            end_date: Week end date

        Returns:
            Tuple of (file_path, pdf_bytes)
        """
        try:
            from app.services.pdf_generator import PDFGenerator

            pdf_gen = PDFGenerator()

            # Calculate statistics
            total_executions = len(data.get("executions", []))

            context = {
                "report_title": f"Weekly Report - {start_date} to {end_date}",
                "start_date": datetime.combine(start_date, datetime.min.time()),
                "end_date": datetime.combine(end_date, datetime.max.time()),
                "generated_date": datetime.now(timezone.utc),
                "data": {
                    **data,
                    "success_rate": ((data.get("success_count", 0) / total_executions * 100) if total_executions > 0 else 0),
                    "compliance_rate": 0,  # Will be calculated if compliance data available
                },
            }

            pdf_bytes = pdf_gen.generate_pdf_from_template("compliance_report_template.html", context)

            file_path = self.report_dir / f"weekly_report_{start_date}_to_{end_date}.pdf"
            logger.info(f"Generated weekly PDF report: {file_path}")

            return file_path, pdf_bytes

        except Exception as e:
            logger.error(f"Error generating weekly PDF: {str(e)}", exc_info=True)
            raise

    def _generate_monthly_pdf(self, data: Dict, start_date, end_date) -> Tuple[Path, bytes]:
        """
        Generate PDF monthly report using ISO 27001 template.

        Args:
            data: Report data dictionary
            start_date: Month start date
            end_date: Month end date

        Returns:
            Tuple of (file_path, pdf_bytes)
        """
        try:
            from app.services.pdf_generator import PDFGenerator

            pdf_gen = PDFGenerator()

            # Calculate metrics
            total_executions = len(data.get("executions", []))
            total_tests = len(data.get("verification_tests", []))

            context = {
                "report_title": f"Monthly Report - {start_date.strftime('%Y-%m')}",
                "start_date": datetime.combine(start_date, datetime.min.time()),
                "end_date": datetime.combine(end_date, datetime.max.time()),
                "generated_date": datetime.now(timezone.utc),
                "data": {
                    **data,
                    "success_rate": ((data.get("success_count", 0) / total_executions * 100) if total_executions > 0 else 0),
                    "verification_rate": ((data.get("test_success_count", 0) / total_tests * 100) if total_tests > 0 else 0),
                    "compliance_rate": 0,  # Will be calculated from compliance_statuses
                    "total_backup_size": sum(e.backup_size_bytes or 0 for e in data.get("executions", [])),
                    "avg_backup_size": (
                        sum(e.backup_size_bytes or 0 for e in data.get("executions", [])) / total_executions
                        if total_executions > 0
                        else 0
                    ),
                    "avg_duration": (
                        sum(e.duration_seconds or 0 for e in data.get("executions", [])) / total_executions
                        if total_executions > 0
                        else 0
                    ),
                },
                "clauses": [],  # Will be populated by pdf_generator
            }

            # Use ISO 27001 template for monthly reports
            pdf_bytes = pdf_gen.generate_iso27001_report(context["data"], context["start_date"], context["end_date"])

            file_path = self.report_dir / f"monthly_report_{start_date.strftime('%Y-%m')}.pdf"
            logger.info(f"Generated monthly PDF report: {file_path}")

            return file_path, pdf_bytes

        except Exception as e:
            logger.error(f"Error generating monthly PDF: {str(e)}", exc_info=True)
            raise

    def _generate_compliance_pdf(self, data: Dict, start_date, end_date) -> Tuple[Path, bytes]:
        """
        Generate PDF compliance report using compliance template.

        Args:
            data: Report data dictionary
            start_date: Report start date
            end_date: Report end date

        Returns:
            Tuple of (file_path, pdf_bytes)
        """
        try:
            from app.services.pdf_generator import PDFGenerator

            pdf_gen = PDFGenerator()

            # Calculate detailed compliance metrics
            compliance_statuses = data.get("compliance_statuses", [])
            total_jobs = data.get("total_jobs", 0)

            # Calculate per-requirement compliance rates
            three_copies_count = sum(1 for c in compliance_statuses if c.three_copies)
            two_media_count = sum(1 for c in compliance_statuses if c.two_media_types)
            one_offsite_count = sum(1 for c in compliance_statuses if c.one_offsite)
            one_offline_count = sum(1 for c in compliance_statuses if c.one_offline)
            zero_errors_count = sum(1 for c in compliance_statuses if c.zero_errors)

            context = {
                "report_title": "3-2-1-1-0 Compliance Report",
                "start_date": datetime.combine(start_date, datetime.min.time()),
                "end_date": datetime.combine(end_date, datetime.max.time()),
                "generated_date": datetime.now(timezone.utc),
                "data": {
                    **data,
                    "three_copies_count": three_copies_count,
                    "three_copies_rate": (three_copies_count / total_jobs * 100) if total_jobs > 0 else 0,
                    "two_media_count": two_media_count,
                    "two_media_rate": (two_media_count / total_jobs * 100) if total_jobs > 0 else 0,
                    "one_offsite_count": one_offsite_count,
                    "one_offsite_rate": (one_offsite_count / total_jobs * 100) if total_jobs > 0 else 0,
                    "one_offline_count": one_offline_count,
                    "one_offline_rate": (one_offline_count / total_jobs * 100) if total_jobs > 0 else 0,
                    "zero_errors_count": zero_errors_count,
                    "zero_errors_rate": (zero_errors_count / total_jobs * 100) if total_jobs > 0 else 0,
                    "non_compliant_list": [],  # Can be populated with detailed list
                    "previous_compliance_rate": 0,  # Can be fetched from previous report
                },
            }

            pdf_bytes = pdf_gen.generate_pdf_from_template("compliance_report_template.html", context)

            file_path = self.report_dir / f"compliance_report_{start_date}_to_{end_date}.pdf"
            logger.info(f"Generated compliance PDF report: {file_path}")

            return file_path, pdf_bytes

        except Exception as e:
            logger.error(f"Error generating compliance PDF: {str(e)}", exc_info=True)
            raise

    def _generate_audit_pdf(self, data: Dict, start_date, end_date) -> Tuple[Path, bytes]:
        """
        Generate PDF audit report using audit template.

        Args:
            data: Report data dictionary
            start_date: Report start date
            end_date: Report end date

        Returns:
            Tuple of (file_path, pdf_bytes)
        """
        try:
            from app.services.pdf_generator import PDFGenerator

            pdf_gen = PDFGenerator()

            # Calculate audit statistics
            audit_logs = data.get("audit_logs", [])

            # Count by action type
            action_type_stats = {}
            for log in audit_logs:
                action_type = log.action_type
                if action_type not in action_type_stats:
                    action_type_stats[action_type] = {"total": 0, "success": 0, "failed": 0}

                action_type_stats[action_type]["total"] += 1
                if log.action_result == "success":
                    action_type_stats[action_type]["success"] += 1
                else:
                    action_type_stats[action_type]["failed"] += 1

            # Calculate success rate for each action type
            for stats in action_type_stats.values():
                stats["success_rate"] = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0

            # Count by resource type
            resource_type_stats = {}
            for log in audit_logs:
                resource_type = log.resource_type or "Other"
                if resource_type not in resource_type_stats:
                    resource_type_stats[resource_type] = {"count": 0, "top_actions": []}

                resource_type_stats[resource_type]["count"] += 1

            # Get unique users
            active_users = set(log.user_id for log in audit_logs if log.user_id)

            # Security event counts
            failed_login_count = sum(1 for log in audit_logs if log.action_type == "LOGIN" and log.action_result == "failed")
            permission_error_count = sum(
                1 for log in audit_logs if "permission" in (log.description or "").lower() and log.action_result == "failed"
            )
            delete_count = sum(1 for log in audit_logs if log.action_type == "DELETE")
            config_change_count = sum(1 for log in audit_logs if log.action_type == "UPDATE")

            login_count = sum(1 for log in audit_logs if log.action_type == "LOGIN")
            logout_count = sum(1 for log in audit_logs if log.action_type == "LOGOUT")
            create_count = sum(1 for log in audit_logs if log.action_type == "CREATE")
            update_count = sum(1 for log in audit_logs if log.action_type == "UPDATE")
            execute_count = sum(1 for log in audit_logs if log.action_type == "EXECUTE")
            verify_count = sum(1 for log in audit_logs if log.action_type == "VERIFY")

            context = {
                "report_title": "Audit Log Report",
                "start_date": datetime.combine(start_date, datetime.min.time()),
                "end_date": datetime.combine(end_date, datetime.max.time()),
                "generated_date": datetime.now(timezone.utc),
                "data": {
                    **data,
                    "action_type_stats": action_type_stats,
                    "resource_type_stats": resource_type_stats,
                    "active_users_count": len(active_users),
                    "failed_login_count": failed_login_count,
                    "permission_error_count": permission_error_count,
                    "delete_count": delete_count,
                    "config_change_count": config_change_count,
                    "login_count": login_count,
                    "logout_count": logout_count,
                    "create_count": create_count,
                    "update_count": update_count,
                    "execute_count": execute_count,
                    "verify_count": verify_count,
                    "user_activity_stats": [],  # Can be populated with detailed user stats
                    "security_events": [],  # Can be populated with security events
                },
            }

            pdf_bytes = pdf_gen.generate_pdf_from_template("audit_report_template.html", context)

            file_path = self.report_dir / f"audit_report_{start_date}_to_{end_date}.pdf"
            logger.info(f"Generated audit PDF report: {file_path}")

            return file_path, pdf_bytes

        except Exception as e:
            logger.error(f"Error generating audit PDF: {str(e)}", exc_info=True)
            raise

    # CSV generation methods

    def _generate_daily_csv(self, data: Dict, date) -> Tuple[Path, str]:
        """Generate CSV daily report"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["Daily Backup Report", date])
        writer.writerow([])
        writer.writerow(["Total Jobs", data.get("total_jobs", 0)])
        writer.writerow(["Successful", data.get("success_count", 0)])
        writer.writerow(["Failed", data.get("failed_count", 0)])
        writer.writerow(["Warnings", data.get("warning_count", 0)])
        writer.writerow([])

        writer.writerow(["Job ID", "Execution Time", "Result", "Size (bytes)", "Duration (sec)"])
        for execution in data.get("executions", []):
            writer.writerow(
                [
                    execution.job_id,
                    execution.execution_date,
                    execution.execution_result,
                    execution.backup_size_bytes or "-",
                    execution.duration_seconds or "-",
                ]
            )

        file_path = self.report_dir / f"daily_report_{date}.csv"
        return file_path, output.getvalue()

    def _generate_weekly_csv(self, data: Dict, start_date, end_date) -> Tuple[Path, str]:
        """Generate CSV weekly report"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["Weekly Report", f"{start_date} to {end_date}"])
        writer.writerow([])
        writer.writerow(["Total Jobs", data.get("total_jobs", 0)])
        writer.writerow(["Successful Executions", data.get("success_count", 0)])
        writer.writerow(["Failed Executions", data.get("failed_count", 0)])

        file_path = self.report_dir / f"weekly_report_{start_date}_to_{end_date}.csv"
        return file_path, output.getvalue()

    def _generate_monthly_csv(self, data: Dict, start_date, end_date) -> Tuple[Path, str]:
        """Generate CSV monthly report"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["Monthly Report", f"{start_date} to {end_date}"])
        writer.writerow([])
        writer.writerow(["Total Jobs", data.get("total_jobs", 0)])
        writer.writerow(["Successful Executions", data.get("success_count", 0)])
        writer.writerow(["Failed Executions", data.get("failed_count", 0)])
        writer.writerow(["Verification Tests Passed", data.get("test_success_count", 0)])
        writer.writerow(["Verification Tests Failed", data.get("test_failed_count", 0)])

        file_path = self.report_dir / f"monthly_report_{start_date.strftime('%Y-%m')}.csv"
        return file_path, output.getvalue()

    def _generate_compliance_csv(self, data: Dict, start_date, end_date) -> Tuple[Path, str]:
        """Generate CSV compliance report"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["3-2-1-1-0 Compliance Report", f"{start_date} to {end_date}"])
        writer.writerow([])
        writer.writerow(["Total Jobs", data.get("total_jobs", 0)])
        writer.writerow(["Compliant", data.get("compliant_jobs", 0)])
        writer.writerow(["Warning", data.get("warning_jobs", 0)])
        writer.writerow(["Non-Compliant", data.get("non_compliant_jobs", 0)])
        writer.writerow(["Compliance Rate (%)", data.get("compliance_rate", 0)])

        file_path = self.report_dir / f"compliance_report_{start_date}_to_{end_date}.csv"
        return file_path, output.getvalue()

    def _generate_audit_csv(self, data: Dict, start_date, end_date) -> Tuple[Path, str]:
        """Generate CSV audit report"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["Audit Log Report", f"{start_date} to {end_date}"])
        writer.writerow([])
        writer.writerow(["Total Actions", data.get("total_actions", 0)])
        writer.writerow(["Successful", data.get("success_count", 0)])
        writer.writerow(["Failed", data.get("failed_count", 0)])
        writer.writerow([])

        writer.writerow(["User", "Action", "Resource", "Result", "Time"])
        for log in data.get("audit_logs", []):
            user_name = log.user.username if log.user else "-"
            writer.writerow(
                [
                    user_name,
                    log.action_type,
                    log.resource_type or "-",
                    log.action_result,
                    log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        file_path = self.report_dir / f"audit_report_{start_date}_to_{end_date}.csv"
        return file_path, output.getvalue()

    # Utility methods

    def _save_report_file(self, file_path: Path, content) -> None:
        """Save report file to disk"""
        try:
            if isinstance(content, str):
                file_path.write_text(content, encoding="utf-8")
            else:
                file_path.write_bytes(content)

            logger.debug(f"Saved report file: {file_path}")

        except Exception as e:
            logger.error(f"Error saving report file {file_path}: {str(e)}")
            raise

    def cleanup_old_reports(self, days: int = 90) -> int:
        """
        Delete old report files and database records.

        Args:
            days: Delete reports older than this many days

        Returns:
            Number of deleted reports
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Delete database records
            count = Report.query.filter(Report.created_at < cutoff_date).delete()

            db.session.commit()

            logger.info(f"Cleaned up {count} old report records")

            return count

        except Exception as e:
            logger.error(f"Error cleaning up old reports: {str(e)}")
            db.session.rollback()
            return 0
