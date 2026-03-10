"""
Server-Sent Events Service for Real-time Backup Progress
"""

import json
import time
from datetime import datetime, timezone
from typing import Generator

from flask import current_app

from app.models import BackupExecution, BackupJob


def generate_job_progress_stream(job_id: int) -> Generator[str, None, None]:
    """
    Generate SSE stream for a specific backup job's progress.

    Args:
        job_id: BackupJob ID to monitor

    Yields:
        SSE formatted data strings
    """

    def format_sse(data: dict, event: str = "progress") -> str:
        """Format data as SSE message."""
        json_data = json.dumps(data, default=str)
        return f"event: {event}\ndata: {json_data}\n\n"

    # Initial connection event
    yield format_sse(
        {
            "status": "connected",
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        event="connected",
    )

    max_iterations = 300  # 5 minutes max (1 second intervals)

    for _ in range(max_iterations):
        try:
            # Get the latest execution for this job
            execution = BackupExecution.query.filter_by(job_id=job_id).order_by(BackupExecution.id.desc()).first()

            if execution is None:
                yield format_sse(
                    {
                        "status": "waiting",
                        "message": "ジョブの実行待ち中...",
                        "job_id": job_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                time.sleep(1)
                continue

            # Build progress data using actual model fields
            progress_data = {
                "execution_id": execution.id,
                "job_id": job_id,
                "status": execution.execution_result,
                "execution_date": (execution.execution_date.isoformat() if execution.execution_date else None),
                "duration_seconds": execution.duration_seconds,
                "backup_size_bytes": execution.backup_size_bytes,
                "source_system": execution.source_system,
                "error_message": execution.error_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            yield format_sse(progress_data)

            # Check if job is in a terminal state
            final_statuses = {"success", "failed", "warning"}
            if execution.execution_result in final_statuses:
                yield format_sse(
                    {
                        "status": "finished",
                        "job_id": job_id,
                        "final_status": execution.execution_result,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    event="finished",
                )
                break

            time.sleep(1)

        except Exception as e:
            current_app.logger.error(f"SSE stream error for job {job_id}: {e}")
            yield format_sse(
                {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                event="error",
            )
            break

    # Stream timeout
    yield format_sse(
        {
            "status": "timeout",
            "message": "ストリーム接続タイムアウト",
            "job_id": job_id,
        },
        event="finished",
    )


def generate_all_jobs_stream() -> Generator[str, None, None]:
    """
    Generate SSE stream for all active backup jobs dashboard.

    Yields:
        SSE formatted data strings with all jobs status
    """

    def format_sse(data: dict, event: str = "update") -> str:
        json_data = json.dumps(data, default=str)
        return f"event: {event}\ndata: {json_data}\n\n"

    yield format_sse(
        {
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        event="connected",
    )

    max_iterations = 60  # 1 minute dashboard refresh

    for _ in range(max_iterations):
        try:
            # Get all active jobs with their latest executions
            jobs = BackupJob.query.filter_by(is_active=True).all()

            jobs_data = []
            for job in jobs:
                latest_exec = BackupExecution.query.filter_by(job_id=job.id).order_by(BackupExecution.id.desc()).first()

                job_info = {
                    "id": job.id,
                    "job_name": job.job_name,
                    "last_status": (latest_exec.execution_result if latest_exec else "never_run"),
                    "last_run": (
                        latest_exec.execution_date.isoformat() if latest_exec and latest_exec.execution_date else None
                    ),
                }
                jobs_data.append(job_info)

            yield format_sse(
                {
                    "jobs": jobs_data,
                    "total": len(jobs_data),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            time.sleep(5)  # Dashboard updates every 5 seconds

        except Exception as e:
            current_app.logger.error(f"Dashboard SSE error: {e}")
            break
