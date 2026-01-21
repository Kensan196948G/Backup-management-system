"""
AOMEI Backupper Integration Service
Handles integration with AOMEI Backupper backup tool via PowerShell script communication

Features:
- Job registration and management
- Status updates from PowerShell scripts
- Log parsing results processing
- Backup execution tracking
- Database synchronization
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.models import BackupCopy, BackupExecution, BackupJob, db

logger = logging.getLogger(__name__)


class AOMEIService:
    """
    AOMEI Backupper integration service

    Handles communication between PowerShell AOMEI integration script
    and the Backup Management System database
    """

    # AOMEI backup tool identifier
    BACKUP_TOOL = "aomei"

    # Status mapping from AOMEI to system status
    STATUS_MAPPING = {
        "success": "success",
        "failed": "failed",
        "warning": "warning",
        "unknown": "warning",
    }

    @staticmethod
    def register_job(
        job_id: int,
        task_name: str,
        job_type: str = "system_image",
        target_server: Optional[str] = None,
        target_path: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[BackupJob]]:
        """
        Register or update AOMEI backup job in the system

        Args:
            job_id: Backup job ID (0 for new job)
            task_name: AOMEI task name
            job_type: Backup type (system_image/file/database/vm)
            target_server: Target server name
            target_path: Target path for backup
            description: Job description

        Returns:
            Tuple of (success, message, job)
        """
        try:
            if job_id == 0:
                # Create new job
                job = BackupJob(
                    job_name=task_name,
                    job_type=job_type,
                    target_server=target_server or "localhost",
                    target_path=target_path or "",
                    backup_tool=AOMEIService.BACKUP_TOOL,
                    schedule_type="manual",
                    retention_days=30,
                    description=description or f"AOMEI Task: {task_name}",
                    is_active=True,
                    owner_id=1,  # Default admin user
                )
                db.session.add(job)
                db.session.commit()

                logger.info(f"Registered new AOMEI job: {task_name} (ID: {job.id})")
                return True, f"Job registered successfully with ID {job.id}", job
            else:
                # Update existing job
                job = BackupJob.query.get(job_id)
                if not job:
                    return False, f"Job ID {job_id} not found", None

                if job.backup_tool != AOMEIService.BACKUP_TOOL:
                    return False, f"Job ID {job_id} is not an AOMEI job", None

                # Update job information
                job.job_name = task_name
                job.job_type = job_type
                if target_server:
                    job.target_server = target_server
                if target_path:
                    job.target_path = target_path
                if description:
                    job.description = description
                job.updated_at = datetime.utcnow()

                db.session.commit()

                logger.info(f"Updated AOMEI job: {task_name} (ID: {job.id})")
                return True, f"Job ID {job.id} updated successfully", job

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to register AOMEI job: {e}")
            return False, f"Failed to register job: {str(e)}", None

    @staticmethod
    def receive_status(
        job_id: int,
        status: str,
        backup_size: int = 0,
        duration: int = 0,
        error_message: Optional[str] = None,
        task_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        details: Optional[str] = None,
        copy_type: str = "primary",
        storage_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Receive and process status update from AOMEI PowerShell script

        Args:
            job_id: Backup job ID
            status: Backup status (success/failed/warning/unknown)
            backup_size: Backup size in bytes
            duration: Execution duration in seconds
            error_message: Error message if failed
            task_name: AOMEI task name
            start_time: Backup start time
            end_time: Backup end time
            details: Additional details
            copy_type: Copy type (primary/secondary/offsite/offline)
            storage_path: Storage path for backup

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate job exists
            job = BackupJob.query.get(job_id)
            if not job:
                return False, f"Job ID {job_id} not found"

            if job.backup_tool != AOMEIService.BACKUP_TOOL:
                return False, f"Job ID {job_id} is not an AOMEI job"

            # Map AOMEI status to system status
            mapped_status = AOMEIService.STATUS_MAPPING.get(status.lower(), "warning")

            # Use current time if not provided
            if not start_time:
                start_time = datetime.utcnow()
            if not end_time:
                end_time = datetime.utcnow()

            # Create backup execution record
            execution = BackupExecution(
                job_id=job_id,
                execution_date=end_time,
                execution_result=mapped_status,
                error_message=error_message or "",
                backup_size_bytes=backup_size,
                duration_seconds=duration,
                source_system="aomei_powershell",
            )
            db.session.add(execution)

            # Update or create backup copy record
            copy = BackupCopy.query.filter_by(job_id=job_id, copy_type=copy_type, media_type="disk").first()

            if not copy:
                copy = BackupCopy(
                    job_id=job_id,
                    copy_type=copy_type,
                    media_type="disk",
                    storage_path=storage_path or job.target_path or "",
                    is_encrypted=False,
                    is_compressed=True,
                )
                db.session.add(copy)

            # Update copy information
            copy.last_backup_date = end_time
            copy.last_backup_size = backup_size
            copy.status = mapped_status
            copy.storage_path = storage_path or copy.storage_path
            copy.updated_at = datetime.utcnow()

            # Update job information
            if task_name:
                job.job_name = task_name
            job.updated_at = datetime.utcnow()

            db.session.commit()

            logger.info(
                f"AOMEI status received for job {job_id}: " f"status={mapped_status}, size={backup_size}, duration={duration}s"
            )

            return True, f"Status updated successfully for job {job_id}"

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to receive AOMEI status for job {job_id}: {e}")
            return False, f"Failed to update status: {str(e)}"

    @staticmethod
    def process_log_analysis(
        job_id: int,
        log_file_path: str,
        parsed_data: Dict,
    ) -> Tuple[bool, str]:
        """
        Process AOMEI log analysis results from PowerShell script

        Args:
            job_id: Backup job ID
            log_file_path: Path to the log file
            parsed_data: Parsed log data dictionary with keys:
                - task_name: str
                - status: str (success/failed/warning/unknown)
                - start_time: datetime
                - end_time: datetime
                - duration: int (seconds)
                - backup_size: int (bytes)
                - error_message: str
                - details: str

        Returns:
            Tuple of (success, message)
        """
        try:
            # Extract data from parsed results
            task_name = parsed_data.get("task_name", "")
            status = parsed_data.get("status", "unknown")
            start_time = parsed_data.get("start_time")
            end_time = parsed_data.get("end_time")
            duration = parsed_data.get("duration", 0)
            backup_size = parsed_data.get("backup_size", 0)
            error_message = parsed_data.get("error_message", "")
            details = parsed_data.get("details", "")

            # Call receive_status with parsed data
            success, message = AOMEIService.receive_status(
                job_id=job_id,
                status=status,
                backup_size=backup_size,
                duration=duration,
                error_message=error_message,
                task_name=task_name,
                start_time=start_time,
                end_time=end_time,
                details=f"{details} | Log: {log_file_path}",
            )

            if success:
                logger.info(f"Processed AOMEI log analysis for job {job_id}: {log_file_path}")

            return success, message

        except Exception as e:
            logger.error(f"Failed to process AOMEI log analysis: {e}")
            return False, f"Failed to process log analysis: {str(e)}"

    @staticmethod
    def get_aomei_jobs(
        active_only: bool = True,
        include_executions: bool = False,
    ) -> List[BackupJob]:
        """
        Get all AOMEI backup jobs

        Args:
            active_only: Return only active jobs
            include_executions: Include execution history

        Returns:
            List of BackupJob objects
        """
        try:
            query = BackupJob.query.filter_by(backup_tool=AOMEIService.BACKUP_TOOL)

            if active_only:
                query = query.filter_by(is_active=True)

            jobs = query.all()

            if include_executions:
                for job in jobs:
                    # Force load executions relationship
                    _ = job.executions.count()

            return jobs

        except Exception as e:
            logger.error(f"Failed to get AOMEI jobs: {e}")
            return []

    @staticmethod
    def get_job_status(job_id: int) -> Optional[Dict]:
        """
        Get current status of AOMEI backup job

        Args:
            job_id: Backup job ID

        Returns:
            Dictionary with job status or None if not found
        """
        try:
            job = BackupJob.query.get(job_id)
            if not job or job.backup_tool != AOMEIService.BACKUP_TOOL:
                return None

            # Get latest execution
            latest_execution = (
                BackupExecution.query.filter_by(job_id=job_id).order_by(BackupExecution.execution_date.desc()).first()
            )

            # Get backup copies
            copies = BackupCopy.query.filter_by(job_id=job_id).all()

            return {
                "job_id": job.id,
                "job_name": job.job_name,
                "job_type": job.job_type,
                "is_active": job.is_active,
                "latest_execution": (
                    {
                        "date": latest_execution.execution_date if latest_execution else None,
                        "result": latest_execution.execution_result if latest_execution else None,
                        "size": latest_execution.backup_size_bytes if latest_execution else None,
                        "duration": latest_execution.duration_seconds if latest_execution else None,
                        "error": latest_execution.error_message if latest_execution else None,
                    }
                    if latest_execution
                    else None
                ),
                "copies": [
                    {
                        "type": copy.copy_type,
                        "media": copy.media_type,
                        "status": copy.status,
                        "last_backup": copy.last_backup_date,
                        "size": copy.last_backup_size,
                        "path": copy.storage_path,
                    }
                    for copy in copies
                ],
                "updated_at": job.updated_at,
            }

        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Validate API key for AOMEI PowerShell script integration

        Note: This is a placeholder implementation.
        In production, implement proper API key management with database storage.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        # TODO: Implement proper API key validation
        # For now, check against environment variable or config
        from flask import current_app

        valid_key = current_app.config.get("AOMEI_API_KEY", "")

        if not valid_key:
            logger.warning("AOMEI_API_KEY not configured - API key validation disabled")
            return True  # Allow for development

        is_valid = api_key == valid_key

        if not is_valid:
            logger.warning("Invalid AOMEI API key attempt")

        return is_valid
