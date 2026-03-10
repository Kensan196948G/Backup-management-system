"""
Unit tests for app/services/postgres_monitor_service.py
PostgresMonitorService: SQLite環境での早期返却パスとPostgreSQLモックパス。
"""

import pytest
from unittest.mock import MagicMock, patch


class TestPostgresMonitorServiceInit:
    """Tests for PostgresMonitorService initialization"""

    def test_init_sqlite_not_postgres(self, app):
        with app.app_context():
            from app.services.postgres_monitor_service import PostgresMonitorService
            service = PostgresMonitorService()
            assert service.is_postgres is False

    def test_init_detects_postgres_uri(self, app):
        with app.app_context():
            with patch.dict(app.config, {"SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@localhost/db"}):
                from app.services.postgres_monitor_service import PostgresMonitorService
                service = PostgresMonitorService()
                assert service.is_postgres is True


class TestPostgresMonitorServiceSQLiteReturns:
    """Tests that verify SQLite environment returns 'PostgreSQL only' errors"""

    def _get_service(self, app):
        from app.services.postgres_monitor_service import PostgresMonitorService
        return PostgresMonitorService()

    def test_get_connection_stats_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_connection_stats()
            assert "error" in result

    def test_get_database_size_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_database_size()
            assert "error" in result

    def test_get_table_sizes_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_table_sizes()
            assert isinstance(result, list)
            assert result == []  # Returns empty list when not postgres

    def test_get_slow_queries_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_slow_queries()
            assert isinstance(result, list)

    def test_get_cache_hit_ratio_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_cache_hit_ratio()
            assert result == 0.0

    def test_get_index_usage_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_index_usage()
            assert isinstance(result, list)

    def test_get_active_locks_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_active_locks()
            assert isinstance(result, list)

    def test_get_table_bloat_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_table_bloat()
            assert isinstance(result, list)

    def test_get_index_recommendations_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_index_recommendations()
            assert isinstance(result, list)

    def test_get_vacuum_stats_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_vacuum_stats()
            assert "error" in result

    def test_get_transaction_stats_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.get_transaction_stats()
            assert "error" in result

    def test_reset_pg_stat_statements_not_postgres(self, app):
        with app.app_context():
            service = self._get_service(app)
            result = service.reset_pg_stat_statements()
            assert result is False


class TestPostgresMonitorServiceMockedPostgres:
    """Tests for PostgreSQL paths using mocked DB"""

    def _make_postgres_service(self, app):
        """Create service configured as postgres"""
        from app.services.postgres_monitor_service import PostgresMonitorService
        service = PostgresMonitorService()
        service.is_postgres = True  # Force postgres mode
        return service

    def test_get_connection_stats_db_error_handled(self, app):
        with app.app_context():
            service = self._make_postgres_service(app)
            with patch("app.services.postgres_monitor_service.db") as mock_db:
                mock_db.session.execute.side_effect = Exception("DB error")
                result = service.get_connection_stats()
                assert "error" in result

    def test_get_database_size_db_error_handled(self, app):
        with app.app_context():
            service = self._make_postgres_service(app)
            with patch("app.services.postgres_monitor_service.db") as mock_db:
                mock_db.session.execute.side_effect = Exception("DB error")
                result = service.get_database_size()
                assert "error" in result

    def test_get_connection_stats_returns_dict(self, app):
        with app.app_context():
            service = self._make_postgres_service(app)
            mock_row = MagicMock()
            # active, idle, idle_in_transaction, waiting, total, max_connections
            mock_row.__getitem__ = lambda self, i: [5, 10, 0, 1, 15, 100][i]

            with patch("app.services.postgres_monitor_service.db") as mock_db:
                mock_db.session.execute.return_value.fetchone.return_value = mock_row
                result = service.get_connection_stats()
                assert isinstance(result, dict)
                assert "timestamp" in result

    def test_get_cache_hit_ratio_db_error_returns_zero(self, app):
        with app.app_context():
            service = self._make_postgres_service(app)
            with patch("app.services.postgres_monitor_service.db") as mock_db:
                mock_db.session.execute.side_effect = Exception("error")
                result = service.get_cache_hit_ratio()
                assert result == 0.0

    def test_reset_pg_stat_statements_success(self, app):
        with app.app_context():
            service = self._make_postgres_service(app)
            with patch("app.services.postgres_monitor_service.db") as mock_db:
                mock_db.session.execute.return_value = MagicMock()
                mock_db.session.commit.return_value = None
                result = service.reset_pg_stat_statements()
                assert result is True

    def test_reset_pg_stat_statements_db_error(self, app):
        with app.app_context():
            service = self._make_postgres_service(app)
            with patch("app.services.postgres_monitor_service.db") as mock_db:
                mock_db.session.execute.side_effect = Exception("error")
                result = service.reset_pg_stat_statements()
                assert result is False

    def test_get_table_sizes_db_error_handled(self, app):
        with app.app_context():
            service = self._make_postgres_service(app)
            with patch("app.services.postgres_monitor_service.db") as mock_db:
                mock_db.session.execute.side_effect = Exception("DB error")
                result = service.get_table_sizes()
                assert isinstance(result, list)
                assert result == []  # Returns empty list on error

    def test_get_slow_queries_db_error_handled(self, app):
        with app.app_context():
            service = self._make_postgres_service(app)
            with patch("app.services.postgres_monitor_service.db") as mock_db:
                mock_db.session.execute.side_effect = Exception("DB error")
                result = service.get_slow_queries()
                assert isinstance(result, list)
