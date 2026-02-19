"""
Prometheus Metrics

Provides application metrics for monitoring:
- Request metrics (response time, status codes)
- Business metrics (backup success rate, job counts)
- Custom metrics (alerts, compliance)
- System metrics (database connections, cache hits)
"""

import logging
from functools import wraps
from typing import Callable

from flask import Flask
from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
)
from prometheus_flask_exporter import PrometheusMetrics

logger = logging.getLogger(__name__)


class BackupSystemMetrics:
    """
    Custom metrics for backup management system.

    Provides business-specific metrics beyond standard HTTP metrics.
    """

    def __init__(self, app: Flask = None):
        """
        Initialize metrics.

        Args:
            app: Flask application instance
        """
        # Business Metrics
        self.backup_jobs_total = Gauge(
            "backup_jobs_total",
            "Total number of backup jobs",
            ["status"],  # active, inactive
        )

        self.backup_executions_total = Counter(
            "backup_executions_total",
            "Total number of backup executions",
            ["result"],  # success, failed, warning
        )

        self.backup_execution_duration = Histogram(
            "backup_execution_duration_seconds",
            "Backup execution duration in seconds",
            ["job_name"],
            buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],
        )

        self.backup_size = Histogram(
            "backup_size_bytes",
            "Backup size in bytes",
            ["job_name"],
            buckets=[
                1e6,  # 1MB
                10e6,  # 10MB
                100e6,  # 100MB
                1e9,  # 1GB
                10e9,  # 10GB
                100e9,  # 100GB
                1e12,  # 1TB
            ],
        )

        self.backup_success_rate = Gauge(
            "backup_success_rate",
            "Backup success rate (0-1)",
            ["period"],  # daily, weekly, monthly
        )

        # Alert Metrics
        self.alerts_total = Counter(
            "alerts_total",
            "Total number of alerts generated",
            ["severity", "alert_type"],
        )

        self.alerts_unacknowledged = Gauge(
            "alerts_unacknowledged",
            "Number of unacknowledged alerts",
            ["severity"],
        )

        # Compliance Metrics
        self.compliance_status = Gauge(
            "compliance_status",
            "Compliance status (1=compliant, 0=non-compliant)",
            ["job_name", "rule"],  # rule: 3copies, 2media, 1offsite, 1immutable, 0errors
        )

        self.compliance_rate = Gauge(
            "compliance_rate",
            "Overall compliance rate (0-1)",
        )

        # Verification Metrics
        self.verification_tests_total = Counter(
            "verification_tests_total",
            "Total number of verification tests",
            ["result"],  # success, failed
        )

        self.verification_duration = Histogram(
            "verification_duration_seconds",
            "Verification test duration in seconds",
            buckets=[10, 30, 60, 120, 300, 600],
        )

        # Job Queue Metrics
        self.active_jobs = Gauge(
            "active_jobs",
            "Number of currently running backup jobs",
        )

        self.queued_jobs = Gauge(
            "queued_jobs",
            "Number of jobs waiting to run",
        )

        # Database Metrics
        self.db_connection_pool_size = Gauge(
            "db_connection_pool_size",
            "Database connection pool size",
        )

        self.db_query_duration = Histogram(
            "db_query_duration_seconds",
            "Database query duration",
            ["query_type"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
        )

        # Cache Metrics
        self.cache_hits = Counter(
            "cache_hits_total",
            "Total cache hits",
            ["cache_key_prefix"],
        )

        self.cache_misses = Counter(
            "cache_misses_total",
            "Total cache misses",
            ["cache_key_prefix"],
        )

        # System Info
        self.app_info = Info(
            "backup_management_system",
            "Backup Management System information",
        )

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """
        Initialize metrics with Flask app.

        Args:
            app: Flask application instance
        """
        # Set app info
        self.app_info.info(
            {
                "version": app.config.get("VERSION", "unknown"),
                "environment": app.config.get("FLASK_ENV", "production"),
            }
        )

        logger.info("Backup system metrics initialized")

    # Metric update methods

    def record_backup_execution(self, job_name: str, result: str, duration: float, size_bytes: int):
        """
        Record backup execution metrics.

        Args:
            job_name: Name of the backup job
            result: Execution result (success, failed, warning)
            duration: Execution duration in seconds
            size_bytes: Backup size in bytes
        """
        self.backup_executions_total.labels(result=result).inc()
        self.backup_execution_duration.labels(job_name=job_name).observe(duration)
        self.backup_size.labels(job_name=job_name).observe(size_bytes)

    def record_alert(self, severity: str, alert_type: str):
        """
        Record alert generation.

        Args:
            severity: Alert severity
            alert_type: Type of alert
        """
        self.alerts_total.labels(severity=severity, alert_type=alert_type).inc()

    def update_unacknowledged_alerts(self, severity: str, count: int):
        """
        Update unacknowledged alert count.

        Args:
            severity: Alert severity
            count: Number of unacknowledged alerts
        """
        self.alerts_unacknowledged.labels(severity=severity).set(count)

    def record_verification_test(self, result: str, duration: float):
        """
        Record verification test metrics.

        Args:
            result: Test result (success, failed)
            duration: Test duration in seconds
        """
        self.verification_tests_total.labels(result=result).inc()
        self.verification_duration.observe(duration)

    def update_compliance(self, job_name: str, rule: str, is_compliant: bool):
        """
        Update compliance status.

        Args:
            job_name: Name of the backup job
            rule: Compliance rule
            is_compliant: Whether job is compliant
        """
        self.compliance_status.labels(job_name=job_name, rule=rule).set(1 if is_compliant else 0)

    def update_success_rate(self, period: str, rate: float):
        """
        Update backup success rate.

        Args:
            period: Time period (daily, weekly, monthly)
            rate: Success rate (0-1)
        """
        self.backup_success_rate.labels(period=period).set(rate)

    def update_job_counts(self, active: int, inactive: int):
        """
        Update backup job counts.

        Args:
            active: Number of active jobs
            inactive: Number of inactive jobs
        """
        self.backup_jobs_total.labels(status="active").set(active)
        self.backup_jobs_total.labels(status="inactive").set(inactive)

    def update_queue_metrics(self, active: int, queued: int):
        """
        Update job queue metrics.

        Args:
            active: Number of running jobs
            queued: Number of queued jobs
        """
        self.active_jobs.set(active)
        self.queued_jobs.set(queued)

    def record_cache_hit(self, key_prefix: str):
        """
        Record cache hit.

        Args:
            key_prefix: Cache key prefix
        """
        self.cache_hits.labels(cache_key_prefix=key_prefix).inc()

    def record_cache_miss(self, key_prefix: str):
        """
        Record cache miss.

        Args:
            key_prefix: Cache key prefix
        """
        self.cache_misses.labels(cache_key_prefix=key_prefix).inc()


# Global metrics instance
backup_metrics = BackupSystemMetrics()


def init_metrics(app: Flask):
    """
    Initialize Prometheus metrics for Flask app.

    Args:
        app: Flask application instance
    """
    # Initialize PrometheusMetrics for automatic HTTP metrics
    metrics = PrometheusMetrics(app)

    # Add custom metrics endpoint info
    metrics.info("backup_management_system", "Backup Management System", version=app.config.get("VERSION", "1.0.0"))

    # Initialize custom business metrics
    backup_metrics.init_app(app)

    # Add metrics endpoint
    @app.route("/metrics")
    def metrics_endpoint():
        """Expose Prometheus metrics"""
        return generate_latest(REGISTRY)

    logger.info("Prometheus metrics initialized")

    return metrics


def track_execution_time(metric_name: str = None):
    """
    Decorator to track function execution time.

    Args:
        metric_name: Name for the metric (default: function name)

    Example:
        @track_execution_time('backup_operation')
        def perform_backup():
            pass
    """

    def decorator(f: Callable) -> Callable:
        name = metric_name or f.__name__

        # Create a histogram for this function
        histogram = Histogram(
            f"{name}_duration_seconds",
            f"Duration of {name} in seconds",
        )

        @wraps(f)
        def wrapper(*args, **kwargs):
            with histogram.time():
                return f(*args, **kwargs)

        return wrapper

    return decorator


def count_calls(metric_name: str = None, labels: dict = None):
    """
    Decorator to count function calls.

    Args:
        metric_name: Name for the metric (default: function name)
        labels: Dictionary of label names and values

    Example:
        @count_calls('api_calls', labels={'endpoint': 'jobs'})
        def get_jobs():
            pass
    """

    def decorator(f: Callable) -> Callable:
        name = metric_name or f.__name__

        # Create a counter for this function
        if labels:
            counter = Counter(
                f"{name}_total",
                f"Total calls to {name}",
                list(labels.keys()),
            )
        else:
            counter = Counter(
                f"{name}_total",
                f"Total calls to {name}",
            )

        @wraps(f)
        def wrapper(*args, **kwargs):
            if labels:
                counter.labels(**labels).inc()
            else:
                counter.inc()

            return f(*args, **kwargs)

        return wrapper

    return decorator
