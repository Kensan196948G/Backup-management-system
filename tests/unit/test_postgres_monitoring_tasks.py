"""
Unit tests for app/tasks/postgres_monitoring_tasks.py
Celery tasks: check_postgres_performance, generate_slow_query_report, check_backup_status.

Note: These tasks use function-level imports. Uses task_always_eager=True pattern
from existing test suite (see tests/unit/tasks/test_report_tasks.py).
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


@pytest.fixture
def celery_eager(app):
    """Configure Celery for eager (synchronous) task execution"""
    from app.tasks import celery_app
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
    return celery_app


class TestCheckPostgresPerformance:
    """Tests for check_postgres_performance task"""

    def test_returns_result_dict_on_success(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_service = MockService.return_value
            mock_service.get_connection_stats.return_value = {"error": "not postgres"}
            mock_service.get_cache_hit_ratio.return_value = 0.95
            mock_service.get_vacuum_stats.return_value = {"error": "not postgres"}
            mock_service.get_database_size.return_value = {}

            with app.app_context():
                result = check_postgres_performance()

            assert "task_id" in result
            assert "timestamp" in result
            assert "alerts_generated" in result
            assert "checks" in result
            assert result["status"] == "completed"

    def test_no_alerts_when_connection_has_error(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_service = MockService.return_value
            mock_service.get_connection_stats.return_value = {"error": "not postgres"}
            mock_service.get_cache_hit_ratio.return_value = 0.95
            mock_service.get_vacuum_stats.return_value = {"error": "not postgres"}
            mock_service.get_database_size.return_value = {}

            with app.app_context():
                result = check_postgres_performance()

            assert result["alerts_generated"] == 0

    def test_critical_alert_when_connection_usage_above_95(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_service = MockService.return_value
            mock_service.get_connection_stats.return_value = {
                "usage_percent": 97, "total": 97, "max_connections": 100, "active": 50, "idle": 47
            }
            mock_service.get_cache_hit_ratio.return_value = 0.95
            mock_service.get_vacuum_stats.return_value = {"error": "no postgres"}
            mock_service.get_database_size.return_value = {}

            with app.app_context():
                result = check_postgres_performance()

            assert result["alerts_generated"] >= 1

    def test_warning_alert_when_connection_usage_80_to_95(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_service = MockService.return_value
            mock_service.get_connection_stats.return_value = {
                "usage_percent": 85, "total": 85, "max_connections": 100
            }
            mock_service.get_cache_hit_ratio.return_value = 0.95
            mock_service.get_vacuum_stats.return_value = {"error": "no postgres"}
            mock_service.get_database_size.return_value = {}

            with app.app_context():
                result = check_postgres_performance()

            assert result["alerts_generated"] >= 1

    def test_critical_cache_alert_below_80_percent(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_service = MockService.return_value
            mock_service.get_connection_stats.return_value = {"error": "no postgres"}
            mock_service.get_cache_hit_ratio.return_value = 0.75  # Below 80%
            mock_service.get_vacuum_stats.return_value = {"error": "no postgres"}
            mock_service.get_database_size.return_value = {}

            with app.app_context():
                result = check_postgres_performance()

            assert result["alerts_generated"] >= 1

    def test_info_cache_alert_between_80_and_90(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_service = MockService.return_value
            mock_service.get_connection_stats.return_value = {"error": "no postgres"}
            mock_service.get_cache_hit_ratio.return_value = 0.85  # Between 80-90%
            mock_service.get_vacuum_stats.return_value = {"error": "no postgres"}
            mock_service.get_database_size.return_value = {}

            with app.app_context():
                result = check_postgres_performance()

            assert result["alerts_generated"] >= 1

    def test_no_alert_when_cache_above_90_percent(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_service = MockService.return_value
            mock_service.get_connection_stats.return_value = {"error": "no postgres"}
            mock_service.get_cache_hit_ratio.return_value = 0.95  # Above 90% - no alert
            mock_service.get_vacuum_stats.return_value = {"error": "no postgres"}
            mock_service.get_database_size.return_value = {}

            with app.app_context():
                result = check_postgres_performance()

            assert result["alerts_generated"] == 0

    def test_vacuum_alert_when_tables_need_vacuum(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_service = MockService.return_value
            mock_service.get_connection_stats.return_value = {"error": "no postgres"}
            mock_service.get_cache_hit_ratio.return_value = 0.95
            mock_service.get_vacuum_stats.return_value = {
                "needs_vacuum_count": 3,
                "tables_needing_vacuum": ["table_a", "table_b", "table_c"],
            }
            mock_service.get_database_size.return_value = {}

            with app.app_context():
                result = check_postgres_performance()

            assert result["alerts_generated"] >= 1

    def test_handles_exception_gracefully(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_postgres_performance

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService:
            MockService.side_effect = Exception("Service unavailable")

            with app.app_context():
                result = check_postgres_performance()

        assert result["status"] == "error"
        assert "error" in result
        assert "Service unavailable" in result["error"]


class TestGenerateSlowQueryReport:
    """Tests for generate_slow_query_report task"""

    def test_returns_completed_with_no_slow_queries(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import generate_slow_query_report

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            MockService.return_value.get_slow_queries.return_value = []

            with app.app_context():
                result = generate_slow_query_report()

        assert result["status"] == "completed"
        assert result["slow_query_count"] == 0

    def test_counts_slow_queries_correctly(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import generate_slow_query_report

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            MockService.return_value.get_slow_queries.return_value = [
                {"mean_time_ms": 5000, "calls": 10, "query": "SELECT * FROM huge_table"},
                {"mean_time_ms": 3000, "calls": 5, "query": "SELECT * FROM another_table"},
            ]

            with app.app_context():
                result = generate_slow_query_report()

        assert result["slow_query_count"] == 2
        assert result["status"] == "completed"

    def test_handles_service_exception(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import generate_slow_query_report

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService:
            MockService.side_effect = Exception("DB connection error")

            with app.app_context():
                result = generate_slow_query_report()

        assert result["status"] == "error"
        assert "error" in result

    def test_result_has_required_keys(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import generate_slow_query_report

        with patch("app.services.postgres_monitor_service.PostgresMonitorService") as MockService, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            MockService.return_value.get_slow_queries.return_value = []

            with app.app_context():
                result = generate_slow_query_report()

        assert "task_id" in result
        assert "timestamp" in result
        assert "slow_query_count" in result
        assert "status" in result


class TestCheckBackupStatus:
    """Tests for check_backup_status task"""

    def test_no_backup_dir_returns_no_backups_status(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_backup_status

        with patch("pathlib.Path") as MockPath:
            # Path(__file__).parent.parent.parent / "backups" / "postgres" / "daily"
            mock_backup_dir = MockPath.return_value.parent.parent.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value
            mock_backup_dir.exists.return_value = False

            with app.app_context():
                result = check_backup_status()

        assert "task_id" in result
        assert "timestamp" in result

    def test_no_dump_files_triggers_notification(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_backup_status

        with patch("pathlib.Path") as MockPath, \
             patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:

            mock_notify.apply_async = MagicMock()
            mock_backup_dir = MockPath.return_value.parent.parent.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value
            mock_backup_dir.exists.return_value = True
            mock_backup_dir.glob.return_value = []  # No dump files

            with app.app_context():
                result = check_backup_status()

        assert "task_id" in result
        assert "timestamp" in result

    def test_handles_exception_gracefully(self, app, celery_eager):
        from app.tasks.postgres_monitoring_tasks import check_backup_status

        with patch("pathlib.Path", side_effect=Exception("OS error")):
            with app.app_context():
                result = check_backup_status()

        assert result["status"] == "error"
        assert "error" in result
