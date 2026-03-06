"""
Compliance Checker Service

Implements 3-2-1-1-0 backup rule validation:
- 3 copies of data
- 2 different storage media types
- 1 copy offsite
- 1 copy offline
- 0 (zero) copies on the original source
"""

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from app.config import Config
from app.models import (
    BackupCopy,
    BackupJob,
    ComplianceStatus,
    OfflineMedia,
    db,
)

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """
    Validates backup jobs against 3-2-1-1-0 rule.

    3-2-1-1-0 Rule Requirements:
    - 3: Minimum three copies of backup data
    - 2: Stored on two different media types
    - 1: One copy stored offsite
    - 1: One copy stored offline (disconnected)
    - 0: Zero copies on original production source
    """

    def __init__(self):
        """Initialize the compliance checker"""
        self.min_copies = Config.MIN_COPIES  # 3
        self.min_media_types = Config.MIN_MEDIA_TYPES  # 2
        self.offline_warning_days = Config.OFFLINE_MEDIA_UPDATE_WARNING_DAYS  # 7

    def check_3_2_1_1_0(self, job_id: int) -> Dict[str, any]:
        """
        Check if a backup job complies with 3-2-1-1-0 rule.

        Args:
            job_id: Backup job ID

        Returns:
            Dictionary containing:
            {
                'compliant': bool,
                'status': 'compliant' | 'non_compliant' | 'warning',
                'copies_count': int,
                'media_types': List[str],
                'media_types_count': int,
                'has_offsite': bool,
                'has_offline': bool,
                'has_errors': bool,
                'details': Dict with detailed information,
                'violations': List of violation messages,
                'warnings': List of warning messages
            }
        """
        try:
            job = db.session.get(BackupJob, job_id)
            if not job:
                logger.warning(f"Backup job {job_id} not found")
                return self._create_not_found_result()

            if not job.is_active:
                logger.warning(f"Backup job {job_id} is inactive")
                return self._create_not_found_result()

            # Fetch all copies for this job
            copies = BackupCopy.query.filter_by(job_id=job_id).all()

            # Get unique media types
            media_types = list(set(copy.media_type for copy in copies))

            # Check each requirement
            violations = []
            warnings = []

            # Check 1: At least 3 copies
            copies_count = len(copies)
            if copies_count < self.min_copies:
                violations.append(f"Only {copies_count} copy/copies found. " f"Minimum {self.min_copies} required.")

            # Check 2: At least 2 different media types
            media_types_count = len(media_types)
            if media_types_count < self.min_media_types:
                violations.append(
                    f"Only {media_types_count} media type(s) found. " f"Minimum {self.min_media_types} required."
                )

            # Check 3: At least one offsite copy
            has_offsite = any(copy.copy_type in ["offsite", "cloud"] for copy in copies)
            if not has_offsite:
                violations.append("No offsite copy found.")

            # Check 4: At least one offline copy
            has_offline = any(copy.copy_type == "offline" or copy.media_type == "tape" for copy in copies)
            if not has_offline:
                violations.append("No offline copy found.")

            # Check copy statuses for errors
            has_errors = any(copy.status == "failed" for copy in copies)
            if has_errors:
                violations.append("Some copies have failed status.")

            # Check for stale offline backups
            offline_copies = [copy for copy in copies if copy.copy_type == "offline" or copy.media_type == "tape"]
            for copy in offline_copies:
                if copy.last_backup_date:
                    # Handle both naive (SQLite) and aware (PostgreSQL) datetimes
                    last_date = copy.last_backup_date
                    now = datetime.now(timezone.utc)
                    if last_date.tzinfo is None:
                        last_date = last_date.replace(tzinfo=timezone.utc)
                    age_days = (now - last_date).days
                    if age_days > self.offline_warning_days:
                        warnings.append(
                            f"Offline copy '{copy.storage_path}' "
                            f"is {age_days} days old (warning threshold: {self.offline_warning_days} days)"
                        )

            # Determine overall status
            if violations:
                overall_status = "non_compliant"
                compliant = False
            elif warnings:
                overall_status = "warning"
                compliant = False
            else:
                overall_status = "compliant"
                compliant = True

            # Build result dictionary
            result = {
                "compliant": compliant,
                "status": overall_status,
                "copies_count": copies_count,
                "media_types": media_types,
                "media_types_count": media_types_count,
                "has_offsite": has_offsite,
                "has_offline": has_offline,
                "has_errors": has_errors,
                "violations": violations,
                "warnings": warnings,
                "details": {
                    "job_id": job_id,
                    "job_name": job.job_name,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "copies": [
                        {
                            "id": copy.id,
                            "copy_type": copy.copy_type,
                            "media_type": copy.media_type,
                            "status": copy.status,
                            "last_backup_date": copy.last_backup_date.isoformat() if copy.last_backup_date else None,
                            "storage_path": copy.storage_path,
                        }
                        for copy in copies
                    ],
                },
            }

            # Cache compliance status
            self._cache_compliance_status(job_id, result)

            logger.info(f"Compliance check for job {job_id} ({job.job_name}): {overall_status}")

            return result

        except Exception as e:
            logger.error(f"Error checking compliance for job {job_id}: {str(e)}", exc_info=True)
            return self._create_error_result(str(e))

    def check_all_jobs(self) -> Dict[str, any]:
        """
        Check compliance for all active backup jobs.

        Returns:
            Dictionary containing:
            {
                'total_jobs': int,
                'compliant_jobs': int,
                'non_compliant_jobs': int,
                'warning_jobs': int,
                'compliance_rate': float (percentage),
                'results': List of individual job results,
                'checked_at': ISO timestamp
            }
        """
        try:
            active_jobs = BackupJob.query.filter_by(is_active=True).all()

            results = []
            compliant_count = 0
            warning_count = 0
            non_compliant_count = 0

            for job in active_jobs:
                result = self.check_3_2_1_1_0(job.id)
                results.append({"job_id": job.id, "job_name": job.job_name, **result})

                if result["status"] == "compliant":
                    compliant_count += 1
                elif result["status"] == "warning":
                    warning_count += 1
                else:
                    non_compliant_count += 1

            total_jobs = len(active_jobs)
            compliance_rate = (compliant_count / total_jobs * 100) if total_jobs > 0 else 0

            summary = {
                "total_jobs": total_jobs,
                "compliant_jobs": compliant_count,
                "warning_jobs": warning_count,
                "non_compliant_jobs": non_compliant_count,
                "compliance_rate": round(compliance_rate, 2),
                "results": results,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"System compliance check: {compliant_count}/{total_jobs} jobs compliant " f"({compliance_rate:.1f}%)")

            return summary

        except Exception as e:
            logger.error(f"Error checking all job compliance: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "total_jobs": 0,
                "compliant_jobs": 0,
                "warning_jobs": 0,
                "non_compliant_jobs": 0,
                "results": [],
            }

    def get_compliance_history(self, job_id: int, days: int = 30) -> List[Dict]:
        """
        Get compliance status history for a job.

        Args:
            job_id: Backup job ID
            days: Number of days to look back

        Returns:
            List of historical compliance checks
        """
        try:
            since_date = datetime.now(timezone.utc) - timedelta(days=days)

            history = (
                ComplianceStatus.query.filter(ComplianceStatus.job_id == job_id, ComplianceStatus.check_date >= since_date)
                .order_by(ComplianceStatus.check_date.desc())
                .all()
            )

            return [
                {
                    "check_date": status.check_date.isoformat(),
                    "status": status.overall_status,
                    "copies_count": status.copies_count,
                    "media_types_count": status.media_types_count,
                    "has_offsite": status.has_offsite,
                    "has_offline": status.has_offline,
                    "has_errors": status.has_errors,
                }
                for status in history
            ]

        except Exception as e:
            logger.error(f"Error fetching compliance history for job {job_id}: {str(e)}")
            return []

    def _cache_compliance_status(self, job_id: int, result: Dict) -> None:
        """
        Cache compliance check result in database.

        Args:
            job_id: Backup job ID
            result: Compliance check result
        """
        try:
            # Create new compliance status record
            status = ComplianceStatus(
                job_id=job_id,
                check_date=datetime.now(timezone.utc),
                copies_count=result["copies_count"],
                media_types_count=result["media_types_count"],
                has_offsite=result["has_offsite"],
                has_offline=result["has_offline"],
                has_errors=result["has_errors"],
                overall_status=result["status"],
            )
            db.session.add(status)
            db.session.commit()

            logger.debug(f"Cached compliance status for job {job_id}")

        except Exception as e:
            logger.error(f"Error caching compliance status: {str(e)}")
            db.session.rollback()

    @staticmethod
    def _create_not_found_result() -> Dict[str, any]:
        """Create a result for job not found"""
        return {
            "compliant": False,
            "status": "unknown",
            "copies_count": 0,
            "media_types": [],
            "media_types_count": 0,
            "has_offsite": False,
            "has_offline": False,
            "has_errors": False,
            "violations": ["Job not found or inactive"],
            "warnings": [],
            "details": {},
        }

    @staticmethod
    def _create_error_result(error_message: str) -> Dict[str, any]:
        """Create a result for error condition"""
        return {
            "compliant": False,
            "status": "unknown",
            "copies_count": 0,
            "media_types": [],
            "media_types_count": 0,
            "has_offsite": False,
            "has_offline": False,
            "has_errors": True,
            "violations": [f"Compliance check error: {error_message}"],
            "warnings": [],
            "details": {},
        }

    # -------------------------------------------------------------------------
    # Report generation methods (weekly/monthly schedule support)
    # -------------------------------------------------------------------------

    def check_job_compliance(self, job_id: int) -> Dict:
        """
        Check 3-2-1-1-0 rule compliance for a specific backup job.
        Returns a simplified dict suitable for report generation.

        Returns:
            Dict with compliance details and violations
        """
        job = db.session.get(BackupJob, job_id)
        if not job:
            return {"error": f"Job {job_id} not found"}

        violations = []
        checks = {}

        # Get all copies for this job
        copies = BackupCopy.query.filter_by(job_id=job_id).all()

        # Rule 1: At least 3 copies
        copy_count = len(copies)
        checks["copies"] = {
            "required": 3,
            "actual": copy_count,
            "passed": copy_count >= 3,
        }
        if copy_count < 3:
            violations.append(f"コピー数不足: {copy_count}/3")

        # Rule 2: At least 2 different media types (media_type field)
        media_types = set(c.media_type for c in copies if getattr(c, "media_type", None))
        media_type_count = len(media_types)
        checks["media_types"] = {
            "required": 2,
            "actual": media_type_count,
            "types": list(media_types),
            "passed": media_type_count >= 2,
        }
        if media_type_count < 2:
            violations.append(f"メディアタイプ不足: {media_type_count}/2")

        # Rule 3: At least 1 offsite copy (copy_type: offsite/cloud/offline)
        offsite_copies = [c for c in copies if getattr(c, "copy_type", None) in ("offsite", "cloud", "offline")]
        has_offsite = len(offsite_copies) >= 1
        checks["offsite"] = {
            "required": 1,
            "actual": len(offsite_copies),
            "passed": has_offsite,
        }
        if not has_offsite:
            violations.append("オフサイトコピーなし")

        # Rule 4: At least 1 offline/air-gapped copy (OfflineMedia with available status)
        offline_count = OfflineMedia.query.filter_by(current_status="available").count()
        has_offline = offline_count >= 1
        checks["offline"] = {
            "required": 1,
            "actual": offline_count,
            "passed": has_offline,
        }
        if not has_offline:
            violations.append("オフラインメディアなし")

        return {
            "job_id": job_id,
            "job_name": job.job_name,
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "checks": checks,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_system_report(self) -> Dict:
        """
        Generate full system compliance report for all active jobs.

        Returns:
            Dict with system-wide compliance summary
        """
        jobs = BackupJob.query.filter_by(is_active=True).all()

        job_results = []
        compliant_count = 0

        for job in jobs:
            result = self.check_job_compliance(job.id)
            job_results.append(result)
            if result.get("is_compliant"):
                compliant_count += 1

        total_jobs = len(jobs)
        compliance_rate = (compliant_count / total_jobs * 100) if total_jobs > 0 else 0

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_jobs": total_jobs,
            "compliant_jobs": compliant_count,
            "non_compliant_jobs": total_jobs - compliant_count,
            "compliance_rate": round(compliance_rate, 1),
            "job_results": job_results,
            "summary": "COMPLIANT" if compliance_rate == 100 else "NON-COMPLIANT",
        }

    def generate_csv_report(self, report_data: Dict) -> str:
        """
        Generate CSV format compliance report.

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["生成日時", report_data["generated_at"]])
        writer.writerow(["コンプライアンス率", f"{report_data['compliance_rate']}%"])
        writer.writerow([])
        writer.writerow(["ジョブID", "ジョブ名", "準拠状態", "違反内容"])

        for job in report_data.get("job_results", []):
            violations_str = "; ".join(job.get("violations", []))
            status = "準拠" if job.get("is_compliant") else "非準拠"
            writer.writerow(
                [
                    job.get("job_id"),
                    job.get("job_name"),
                    status,
                    violations_str or "なし",
                ]
            )

        return output.getvalue()

    def format_email_body(self, report_data: Dict) -> Tuple[str, str]:
        """
        Format compliance report for email distribution.

        Returns:
            Tuple of (text_body, html_body)
        """
        rate = report_data["compliance_rate"]
        status_label = "OK" if rate == 100 else "WARNING" if rate >= 80 else "CRITICAL"

        text_body = (
            f"\n3-2-1-1-0 バックアップコンプライアンスレポート\n"
            f"生成日時: {report_data['generated_at']}\n\n"
            f"[総合結果] {status_label} {report_data['summary']}\n"
            f"コンプライアンス率: {rate}%\n"
            f"準拠ジョブ: {report_data['compliant_jobs']}/{report_data['total_jobs']}\n\n"
        )

        for job in report_data.get("job_results", []):
            job_status = "[準拠]" if job.get("is_compliant") else "[非準拠]"
            text_body += f"- {job.get('job_name', 'Unknown')}: {job_status}\n"
            for v in job.get("violations", []):
                text_body += f"  - {v}\n"

        html_rows = ""
        for job in report_data.get("job_results", []):
            status_cell = "準拠" if job.get("is_compliant") else "非準拠"
            violations = "<br>".join(job.get("violations", [])) or "なし"
            html_rows += f"<tr><td>{job.get('job_name')}</td>" f"<td>{status_cell}</td>" f"<td>{violations}</td></tr>\n"

        html_body = (
            "<html><body>"
            "<h2>3-2-1-1-0 バックアップコンプライアンスレポート</h2>"
            f"<p><strong>生成日時:</strong> {report_data['generated_at']}</p>"
            f"<h3>{status_label} {report_data['summary']} - コンプライアンス率: {rate}%</h3>"
            f"<p>準拠ジョブ: {report_data['compliant_jobs']}/{report_data['total_jobs']}</p>"
            '<table border="1" cellpadding="5" cellspacing="0">'
            "<tr><th>ジョブ名</th><th>状態</th><th>違反内容</th></tr>"
            f"{html_rows}"
            "</table></body></html>"
        )

        return text_body, html_body
