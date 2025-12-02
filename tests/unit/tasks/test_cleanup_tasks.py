"""
Unit tests for cleanup tasks.
Phase 11: Asynchronous Task Processing
"""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestCleanupOldLogsTask:
    """Tests for cleanup_old_logs task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_cleanup_logs_no_directory(self, app, celery_app):
        """Test cleanup when logs directory doesn't exist."""
        from app.tasks.cleanup_tasks import cleanup_old_logs

        with patch("app.tasks.cleanup_tasks.Path") as mock_path:
            mock_path.return_value.__truediv__.return_value.exists.return_value = False

            with app.app_context():
                result = cleanup_old_logs(retention_days=90)

                assert result["status"] == "skipped"

    def test_cleanup_logs_with_old_files(self, app, celery_app):
        """Test cleanup deletes old log files."""
        from app.tasks.cleanup_tasks import cleanup_old_logs

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create old log file
            old_log = Path(tmpdir) / "old.log"
            old_log.write_text("old log content")

            # Set modification time to 100 days ago
            old_time = (datetime.now() - timedelta(days=100)).timestamp()
            os.utime(old_log, (old_time, old_time))

            # Create recent log file
            recent_log = Path(tmpdir) / "recent.log"
            recent_log.write_text("recent log content")

            with patch("app.tasks.cleanup_tasks.Path") as mock_path:
                logs_dir = Path(tmpdir)
                mock_path.return_value.__truediv__.return_value = logs_dir
                mock_path.return_value.__truediv__.return_value.exists.return_value = True
                mock_path.return_value.__truediv__.return_value.glob.return_value = [old_log, recent_log]

                with app.app_context():
                    result = cleanup_old_logs(retention_days=90)

                    # Old file should be deleted
                    assert result["status"] == "completed"


class TestCleanupOldNotificationsTask:
    """Tests for cleanup_old_notifications task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_cleanup_notifications_success(self, app, celery_app):
        """Test cleanup of old notification records."""
        from app.tasks.cleanup_tasks import cleanup_old_notifications

        with patch("app.tasks.cleanup_tasks.NotificationLog") as mock_model:
            mock_query = Mock()
            mock_query.filter.return_value.delete.return_value = 10
            mock_model.query = mock_query

            with patch("app.tasks.cleanup_tasks.db") as mock_db:
                with app.app_context():
                    result = cleanup_old_notifications(retention_days=30)

                    assert result["status"] == "completed"
                    assert result["deleted_count"] == 10
                    mock_db.session.commit.assert_called_once()


class TestCleanupOldAlertsTask:
    """Tests for cleanup_old_alerts task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_cleanup_alerts_read_only(self, app, celery_app):
        """Test cleanup of only read alerts."""
        from app.tasks.cleanup_tasks import cleanup_old_alerts

        with patch("app.tasks.cleanup_tasks.Alert") as mock_model:
            mock_query = Mock()
            mock_query.filter.return_value.filter.return_value.delete.return_value = 5
            mock_model.query = mock_query

            with patch("app.tasks.cleanup_tasks.db") as mock_db:
                with app.app_context():
                    result = cleanup_old_alerts(retention_days=90, only_read=True)

                    assert result["status"] == "completed"
                    assert result["only_read"] is True


class TestVacuumDatabaseTask:
    """Tests for vacuum_database task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_vacuum_sqlite(self, app, celery_app):
        """Test vacuum for SQLite database."""
        from app.tasks.cleanup_tasks import vacuum_database

        with patch("app.tasks.cleanup_tasks.current_app") as mock_app:
            mock_app.config.get.return_value = "sqlite:///test.db"

            with patch("app.tasks.cleanup_tasks.db") as mock_db:
                with app.app_context():
                    result = vacuum_database()

                    assert result["status"] == "completed"
                    assert result["database_type"] == "sqlite"


class TestCheckDiskSpaceTask:
    """Tests for check_disk_space task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_check_disk_space_ok(self, app, celery_app):
        """Test disk space check when space is OK."""
        from app.tasks.cleanup_tasks import check_disk_space

        with patch("shutil.disk_usage") as mock_usage:
            # 100GB total, 20GB used, 80GB free
            mock_usage.return_value = (100 * 1024**3, 20 * 1024**3, 80 * 1024**3)

            with app.app_context():
                result = check_disk_space(
                    warning_threshold_gb=10.0,
                    critical_threshold_gb=5.0,
                )

                assert result["status"] == "ok"
                assert result["disk_space"]["free_gb"] == 80.0

    def test_check_disk_space_warning(self, app, celery_app):
        """Test disk space check when low (warning)."""
        from app.tasks.cleanup_tasks import check_disk_space

        with patch("shutil.disk_usage") as mock_usage:
            # 100GB total, 92GB used, 8GB free
            mock_usage.return_value = (100 * 1024**3, 92 * 1024**3, 8 * 1024**3)

            with patch("app.tasks.cleanup_tasks._create_disk_space_alert") as mock_alert:
                with app.app_context():
                    result = check_disk_space(
                        warning_threshold_gb=10.0,
                        critical_threshold_gb=5.0,
                    )

                    assert result["status"] == "warning"
                    mock_alert.assert_called_once()

    def test_check_disk_space_critical(self, app, celery_app):
        """Test disk space check when critically low."""
        from app.tasks.cleanup_tasks import check_disk_space

        with patch("shutil.disk_usage") as mock_usage:
            # 100GB total, 97GB used, 3GB free
            mock_usage.return_value = (100 * 1024**3, 97 * 1024**3, 3 * 1024**3)

            with patch("app.tasks.cleanup_tasks._create_disk_space_alert") as mock_alert:
                with app.app_context():
                    result = check_disk_space(
                        warning_threshold_gb=10.0,
                        critical_threshold_gb=5.0,
                    )

                    assert result["status"] == "critical"
                    mock_alert.assert_called_with(3.0, "critical")


class TestRunAllMaintenanceTask:
    """Tests for run_all_maintenance task."""

    @pytest.fixture
    def celery_app(self, app):
        """Configure Celery for testing."""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_run_all_maintenance_queues_tasks(self, app, celery_app):
        """Test that all maintenance tasks are queued."""
        from app.tasks.cleanup_tasks import run_all_maintenance

        with patch("app.tasks.cleanup_tasks.cleanup_old_logs") as mock_logs:
            with patch("app.tasks.cleanup_tasks.cleanup_old_reports") as mock_reports:
                with patch("app.tasks.cleanup_tasks.cleanup_old_notifications") as mock_notif:
                    with patch("app.tasks.cleanup_tasks.cleanup_old_alerts") as mock_alerts:
                        with patch("app.tasks.cleanup_tasks.vacuum_database") as mock_vacuum:
                            for mock in [mock_logs, mock_reports, mock_notif, mock_alerts, mock_vacuum]:
                                mock.apply_async.return_value = Mock(id="task-id")

                            with app.app_context():
                                result = run_all_maintenance()

                                assert result["status"] == "queued"
                                assert result["queued_tasks"] == 5
                                assert len(result["subtasks"]) == 5
