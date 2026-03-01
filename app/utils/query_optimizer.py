"""
Database Query Optimizer

Provides utilities for optimizing database queries:
- N+1 query detection and prevention
- Eager loading helpers
- Query performance monitoring
- Index recommendations
"""

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Callable, List, Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import joinedload, selectinload

logger = logging.getLogger(__name__)


class QueryPerformanceMonitor:
    """
    Monitor and log slow database queries.

    Helps identify performance bottlenecks.
    """

    def __init__(self, threshold_ms: float = 100):
        """
        Initialize query monitor.

        Args:
            threshold_ms: Log queries slower than this threshold (milliseconds)
        """
        self.threshold_ms = threshold_ms
        self.query_count = 0
        self.slow_query_count = 0

    def setup_monitoring(self, app):
        """
        Setup query performance monitoring.

        Args:
            app: Flask application instance
        """

        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault("query_start_time", []).append(time.time())
            self.query_count += 1

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - conn.info["query_start_time"].pop(-1)
            total_time_ms = total_time * 1000

            if total_time_ms > self.threshold_ms:
                self.slow_query_count += 1
                logger.warning(
                    f"Slow query ({total_time_ms:.2f}ms): {statement[:200]}",
                    extra={"query_time_ms": total_time_ms, "query": statement},
                )

            if app.config.get("DEBUG"):
                logger.debug(f"Query ({total_time_ms:.2f}ms): {statement[:100]}")

        logger.info(f"Query performance monitoring enabled (threshold: {self.threshold_ms}ms)")

    def get_stats(self) -> dict:
        """
        Get query statistics.

        Returns:
            Dictionary with query stats
        """
        return {
            "total_queries": self.query_count,
            "slow_queries": self.slow_query_count,
            "threshold_ms": self.threshold_ms,
        }


# Global query monitor instance
query_monitor = QueryPerformanceMonitor()


@contextmanager
def query_timer(description: str = "Query"):
    """
    Context manager to time database queries.

    Args:
        description: Description of the query

    Example:
        with query_timer("Fetch all jobs"):
            jobs = BackupJob.query.all()
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"{description} took {elapsed_ms:.2f}ms")


def eager_load_jobs(query):
    """
    Apply eager loading for BackupJob queries.

    Prevents N+1 queries by loading related data upfront.

    Args:
        query: SQLAlchemy query object

    Returns:
        Query with eager loading applied
    """
    return query.options(
        joinedload("owner"),  # Load user who owns the job
        selectinload("executions").joinedload("copies"),  # Load executions and their copies
        selectinload("compliance_statuses"),  # Load compliance statuses
    )


def eager_load_alerts(query):
    """
    Apply eager loading for Alert queries.

    Args:
        query: SQLAlchemy query object

    Returns:
        Query with eager loading applied
    """
    return query.options(
        joinedload("job"),  # Load related job
        joinedload("acknowledged_by_user"),  # Load user who acknowledged
    )


def eager_load_executions(query):
    """
    Apply eager loading for BackupExecution queries.

    Args:
        query: SQLAlchemy query object

    Returns:
        Query with eager loading applied
    """
    return query.options(
        joinedload("job").joinedload("owner"),  # Load job and its owner
        selectinload("copies"),  # Load backup copies
        selectinload("verification_tests"),  # Load verification tests
    )


def eager_load_reports(query):
    """
    Apply eager loading for Report queries.

    Args:
        query: SQLAlchemy query object

    Returns:
        Query with eager loading applied
    """
    return query.options(
        joinedload("generated_by_user"),  # Load user who generated report
    )


def paginate_query(query, page: int = 1, per_page: int = 50):
    """
    Apply pagination to query.

    Args:
        query: SQLAlchemy query object
        page: Page number (1-based)
        per_page: Items per page

    Returns:
        Pagination object
    """
    return query.paginate(page=page, per_page=per_page, error_out=False)


def optimize_job_list_query():
    """
    Optimized query for listing backup jobs.

    Returns:
        Query object with optimizations applied
    """
    from app.models import BackupJob

    with query_timer("Job list query"):
        query = BackupJob.query.options(
            joinedload("owner"),  # Load owner in same query
            # Don't load executions by default - too many records
        )
        return query


def optimize_alert_list_query(unacknowledged_only: bool = False):
    """
    Optimized query for listing alerts.

    Args:
        unacknowledged_only: Filter to unacknowledged alerts only

    Returns:
        Query object with optimizations applied
    """
    from app.models import Alert

    with query_timer("Alert list query"):
        query = Alert.query.options(
            joinedload("job"),  # Load related job
        )

        if unacknowledged_only:
            query = query.filter_by(is_acknowledged=False)

        return query


def optimize_execution_list_query(job_id: Optional[int] = None):
    """
    Optimized query for listing backup executions.

    Args:
        job_id: Filter by job ID

    Returns:
        Query object with optimizations applied
    """
    from app.models import BackupExecution

    with query_timer("Execution list query"):
        query = BackupExecution.query.options(
            joinedload("job"),  # Load job info
            # Load copies only when needed
        )

        if job_id:
            query = query.filter_by(job_id=job_id)

        return query


class QueryOptimizer:
    """
    Database query optimization utilities.

    Provides methods for:
    - Query analysis
    - Index recommendations
    - N+1 detection
    """

    @staticmethod
    def explain_query(query) -> dict:
        """
        Get query execution plan.

        Args:
            query: SQLAlchemy query object

        Returns:
            Dictionary with execution plan info
        """
        try:
            # Get SQL statement
            statement = str(query.statement.compile(compile_kwargs={"literal_binds": True}))

            # For PostgreSQL, you would execute EXPLAIN
            # For SQLite, you would use EXPLAIN QUERY PLAN
            # This is a simplified version

            return {
                "sql": statement,
                "note": "Use database-specific EXPLAIN for detailed analysis",
            }

        except Exception as e:
            logger.error(f"Error explaining query: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def recommend_indexes() -> List[str]:
        """
        Generate index recommendations based on common query patterns.

        Returns:
            List of index recommendations
        """
        recommendations = [
            # BackupJob indexes
            "CREATE INDEX IF NOT EXISTS idx_backup_job_active ON backup_job(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_backup_job_owner ON backup_job(owner_id);",
            "CREATE INDEX IF NOT EXISTS idx_backup_job_next_run ON backup_job(next_run_time);",
            # BackupExecution indexes
            "CREATE INDEX IF NOT EXISTS idx_execution_job_date ON backup_execution(job_id, execution_date);",
            "CREATE INDEX IF NOT EXISTS idx_execution_result ON backup_execution(execution_result);",
            "CREATE INDEX IF NOT EXISTS idx_execution_date ON backup_execution(execution_date);",
            # Alert indexes
            "CREATE INDEX IF NOT EXISTS idx_alert_acknowledged ON alert(is_acknowledged);",
            "CREATE INDEX IF NOT EXISTS idx_alert_job ON alert(job_id);",
            "CREATE INDEX IF NOT EXISTS idx_alert_severity ON alert(severity);",
            "CREATE INDEX IF NOT EXISTS idx_alert_created ON alert(created_at);",
            # BackupCopy indexes
            "CREATE INDEX IF NOT EXISTS idx_copy_execution ON backup_copy(execution_id);",
            "CREATE INDEX IF NOT EXISTS idx_copy_media ON backup_copy(media_id);",
            # ComplianceStatus indexes
            "CREATE INDEX IF NOT EXISTS idx_compliance_job_date ON compliance_status(job_id, check_date);",
            "CREATE INDEX IF NOT EXISTS idx_compliance_status ON compliance_status(overall_status);",
            # AuditLog indexes
            "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action_type);",
            "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);",
        ]

        return recommendations


# Global query optimizer instance
query_optimizer = QueryOptimizer()


def monitor_query_performance(f: Callable) -> Callable:
    """
    Decorator to monitor function query performance.

    Args:
        f: Function to monitor

    Returns:
        Wrapped function
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        start_queries = query_monitor.query_count
        start_time = time.time()

        result = f(*args, **kwargs)

        queries_executed = query_monitor.query_count - start_queries
        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(f"{f.__name__} executed {queries_executed} queries in {elapsed_ms:.2f}ms")

        if queries_executed > 10:
            logger.warning(f"{f.__name__} may have N+1 query problem: {queries_executed} queries")

        return result

    return wrapper
