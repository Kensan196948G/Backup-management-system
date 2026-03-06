"""
Unit tests for SSE service
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.sse_service import generate_all_jobs_stream, generate_job_progress_stream


class TestGenerateJobProgressStream:
    """Tests for job-specific SSE stream"""

    def test_initial_connected_event(self, app):
        """Test that the stream starts with a connected event"""
        with app.app_context():
            with patch("app.services.sse_service.BackupExecution") as mock_exec:
                mock_exec.query.filter_by.return_value.order_by.return_value.first.return_value = None

                stream = generate_job_progress_stream(1)
                first_event = next(stream)

                assert "event: connected" in first_event
                data = json.loads(first_event.split("data: ")[1])
                assert data["status"] == "connected"
                assert data["job_id"] == 1

    def test_waiting_when_no_execution(self, app):
        """Test waiting status when no execution found"""
        with app.app_context():
            with patch("app.services.sse_service.BackupExecution") as mock_exec:
                mock_exec.query.filter_by.return_value.order_by.return_value.first.return_value = None

                stream = generate_job_progress_stream(1)
                next(stream)  # skip connected
                second_event = next(stream)

                assert "event: progress" in second_event
                data = json.loads(second_event.split("data: ")[1])
                assert data["status"] == "waiting"

    def test_progress_event_contains_execution_data(self, app):
        """Test that progress event includes actual execution fields"""
        with app.app_context():
            mock_execution = MagicMock()
            mock_execution.id = 42
            mock_execution.execution_result = "running"
            mock_execution.execution_date = datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc)
            mock_execution.duration_seconds = None
            mock_execution.backup_size_bytes = None
            mock_execution.source_system = "scheduled"
            mock_execution.error_message = None

            with patch("app.services.sse_service.BackupExecution") as mock_exec:
                mock_exec.query.filter_by.return_value.order_by.return_value.first.return_value = mock_execution

                stream = generate_job_progress_stream(1)
                next(stream)  # skip connected
                progress_event = next(stream)

                assert "event: progress" in progress_event
                data = json.loads(progress_event.split("data: ")[1])
                assert data["execution_id"] == 42
                assert data["job_id"] == 1
                assert data["status"] == "running"
                assert data["source_system"] == "scheduled"

    def test_finished_event_on_success_execution(self, app):
        """Test that finished event is sent when execution succeeds"""
        with app.app_context():
            mock_execution = MagicMock()
            mock_execution.id = 1
            mock_execution.execution_result = "success"
            mock_execution.execution_date = datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc)
            mock_execution.duration_seconds = 120
            mock_execution.backup_size_bytes = 1024 * 1024
            mock_execution.source_system = "powershell"
            mock_execution.error_message = None

            with patch("app.services.sse_service.BackupExecution") as mock_exec:
                mock_exec.query.filter_by.return_value.order_by.return_value.first.return_value = mock_execution

                events = list(generate_job_progress_stream(1))
                # Should have: connected, progress, finished, timeout
                assert len(events) >= 3

                # Find finished event
                finished_events = [e for e in events if "event: finished" in e]
                assert len(finished_events) >= 1
                data = json.loads(finished_events[0].split("data: ")[1])
                assert data["final_status"] == "success"

    def test_finished_event_on_failed_execution(self, app):
        """Test that finished event is sent when execution fails"""
        with app.app_context():
            mock_execution = MagicMock()
            mock_execution.id = 2
            mock_execution.execution_result = "failed"
            mock_execution.execution_date = datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc)
            mock_execution.duration_seconds = 30
            mock_execution.backup_size_bytes = None
            mock_execution.source_system = "manual"
            mock_execution.error_message = "Disk full"

            with patch("app.services.sse_service.BackupExecution") as mock_exec:
                mock_exec.query.filter_by.return_value.order_by.return_value.first.return_value = mock_execution

                events = list(generate_job_progress_stream(1))

                finished_events = [e for e in events if "event: finished" in e]
                assert len(finished_events) >= 1
                data = json.loads(finished_events[0].split("data: ")[1])
                assert data["final_status"] == "failed"

    def test_error_event_on_exception(self, app):
        """Test that error event is sent when an exception occurs"""
        with app.app_context():
            with patch("app.services.sse_service.BackupExecution") as mock_exec:
                mock_exec.query.filter_by.return_value.order_by.return_value.first.side_effect = Exception(
                    "Database connection lost"
                )

                stream = generate_job_progress_stream(1)
                next(stream)  # skip connected
                error_event = next(stream)

                assert "event: error" in error_event
                data = json.loads(error_event.split("data: ")[1])
                assert data["status"] == "error"
                assert "Database connection lost" in data["message"]

    def test_sse_format_double_newline(self, app):
        """Test that SSE messages end with double newline"""
        with app.app_context():
            with patch("app.services.sse_service.BackupExecution") as mock_exec:
                mock_exec.query.filter_by.return_value.order_by.return_value.first.return_value = None

                stream = generate_job_progress_stream(1)
                first_event = next(stream)
                # SSE format requires messages to end with \n\n
                assert first_event.endswith("\n\n")


class TestGenerateAllJobsStream:
    """Tests for dashboard SSE stream"""

    def test_initial_connected_event(self, app):
        """Test that dashboard stream starts with connected event"""
        with app.app_context():
            with patch("app.services.sse_service.BackupJob") as mock_job:
                mock_job.query.filter_by.return_value.all.return_value = []

                stream = generate_all_jobs_stream()
                first_event = next(stream)

                assert "event: connected" in first_event
                data = json.loads(first_event.split("data: ")[1])
                assert data["status"] == "connected"

    def test_empty_jobs_list(self, app):
        """Test dashboard with no active jobs"""
        with app.app_context():
            with patch("app.services.sse_service.BackupJob") as mock_job:
                mock_job.query.filter_by.return_value.all.return_value = []

                stream = generate_all_jobs_stream()
                next(stream)  # skip connected
                second_event = next(stream)

                data = json.loads(second_event.split("data: ")[1])
                assert data["total"] == 0
                assert data["jobs"] == []

    def test_jobs_list_contains_active_jobs(self, app):
        """Test dashboard returns active job data"""
        with app.app_context():
            mock_job1 = MagicMock()
            mock_job1.id = 1
            mock_job1.job_name = "Daily DB Backup"

            mock_job2 = MagicMock()
            mock_job2.id = 2
            mock_job2.job_name = "Weekly Full Backup"

            mock_exec1 = MagicMock()
            mock_exec1.execution_result = "success"
            mock_exec1.execution_date = datetime(2026, 3, 6, 8, 0, 0, tzinfo=timezone.utc)

            with patch("app.services.sse_service.BackupJob") as mock_job_cls, patch(
                "app.services.sse_service.BackupExecution"
            ) as mock_exec_cls:
                mock_job_cls.query.filter_by.return_value.all.return_value = [mock_job1, mock_job2]
                # First job has execution, second does not
                mock_exec_cls.query.filter_by.return_value.order_by.return_value.first.side_effect = [
                    mock_exec1,
                    None,
                ]

                stream = generate_all_jobs_stream()
                next(stream)  # skip connected
                update_event = next(stream)

                data = json.loads(update_event.split("data: ")[1])
                assert data["total"] == 2
                assert len(data["jobs"]) == 2
                assert data["jobs"][0]["job_name"] == "Daily DB Backup"
                assert data["jobs"][0]["last_status"] == "success"
                assert data["jobs"][1]["last_status"] == "never_run"

    def test_update_event_has_timestamp(self, app):
        """Test that update events include a timestamp"""
        with app.app_context():
            with patch("app.services.sse_service.BackupJob") as mock_job:
                mock_job.query.filter_by.return_value.all.return_value = []

                stream = generate_all_jobs_stream()
                next(stream)  # skip connected
                update_event = next(stream)

                data = json.loads(update_event.split("data: ")[1])
                assert "timestamp" in data

    def test_sse_format_double_newline(self, app):
        """Test that dashboard SSE messages end with double newline"""
        with app.app_context():
            with patch("app.services.sse_service.BackupJob") as mock_job:
                mock_job.query.filter_by.return_value.all.return_value = []

                stream = generate_all_jobs_stream()
                first_event = next(stream)
                assert first_event.endswith("\n\n")
