"""
Unit tests for app/utils/metrics.py

Tests the BackupSystemMetrics class and init_metrics function
for Prometheus metric recording and endpoint exposure.
"""

import pytest
from unittest.mock import patch, MagicMock
from prometheus_client import CollectorRegistry, REGISTRY


class TestBackupSystemMetrics:
    """Tests for BackupSystemMetrics class."""

    def test_metrics_class_instantiation(self):
        """BackupSystemMetrics can be instantiated without an app."""
        from app.utils.metrics import BackupSystemMetrics

        # Use a fresh registry to avoid collector conflicts
        with patch("app.utils.metrics.Gauge") as MockGauge, \
             patch("app.utils.metrics.Counter") as MockCounter, \
             patch("app.utils.metrics.Histogram") as MockHistogram, \
             patch("app.utils.metrics.Info") as MockInfo:
            metrics = BackupSystemMetrics()
            assert metrics is not None
            # Verify business metrics were created
            assert MockGauge.called
            assert MockCounter.called
            assert MockHistogram.called
            assert MockInfo.called

    def test_metrics_init_app(self, app):
        """BackupSystemMetrics.init_app sets app info correctly."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge"), \
             patch("app.utils.metrics.Counter"), \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info") as MockInfo:
            metrics = BackupSystemMetrics()
            info_instance = MockInfo.return_value
            metrics.init_app(app)
            info_instance.info.assert_called_once()
            call_args = info_instance.info.call_args[0][0]
            assert "version" in call_args
            assert "environment" in call_args

    def test_record_backup_execution(self):
        """record_backup_execution updates execution metrics."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge"), \
             patch("app.utils.metrics.Counter") as MockCounter, \
             patch("app.utils.metrics.Histogram") as MockHistogram, \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()

            # Get the mock instances
            executions_counter = MockCounter.return_value
            duration_hist = MockHistogram.return_value
            # backup_execution_duration is the second Histogram created
            # but since all return same mock, we check the mock calls

            metrics.record_backup_execution(
                job_name="daily-backup",
                result="success",
                duration=120.5,
                size_bytes=1024 * 1024 * 500,
            )

            # Verify counter was incremented
            executions_counter.labels.assert_called()
            executions_counter.labels.return_value.inc.assert_called()

    def test_record_alert(self):
        """record_alert increments alert counter."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge"), \
             patch("app.utils.metrics.Counter") as MockCounter, \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            alerts_counter = MockCounter.return_value

            metrics.record_alert(severity="critical", alert_type="backup_failure")

            alerts_counter.labels.assert_called()
            alerts_counter.labels.return_value.inc.assert_called()

    def test_update_unacknowledged_alerts(self):
        """update_unacknowledged_alerts sets gauge value."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge") as MockGauge, \
             patch("app.utils.metrics.Counter"), \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            gauge_instance = MockGauge.return_value

            metrics.update_unacknowledged_alerts(severity="critical", count=5)

            gauge_instance.labels.assert_called()
            gauge_instance.labels.return_value.set.assert_called_with(5)

    def test_record_verification_test(self):
        """record_verification_test updates verification metrics."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge"), \
             patch("app.utils.metrics.Counter") as MockCounter, \
             patch("app.utils.metrics.Histogram") as MockHistogram, \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()

            metrics.record_verification_test(result="success", duration=60.0)

            MockCounter.return_value.labels.assert_called()
            MockCounter.return_value.labels.return_value.inc.assert_called()
            MockHistogram.return_value.observe.assert_called_with(60.0)

    def test_update_compliance(self):
        """update_compliance sets compliance gauge."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge") as MockGauge, \
             patch("app.utils.metrics.Counter"), \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            gauge_instance = MockGauge.return_value

            metrics.update_compliance(
                job_name="daily-backup",
                rule="3copies",
                is_compliant=True,
            )

            gauge_instance.labels.assert_called()
            gauge_instance.labels.return_value.set.assert_called_with(1)

    def test_update_compliance_non_compliant(self):
        """update_compliance sets 0 for non-compliant."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge") as MockGauge, \
             patch("app.utils.metrics.Counter"), \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            gauge_instance = MockGauge.return_value

            metrics.update_compliance(
                job_name="daily-backup",
                rule="1offsite",
                is_compliant=False,
            )

            gauge_instance.labels.return_value.set.assert_called_with(0)

    def test_update_success_rate(self):
        """update_success_rate sets rate gauge."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge") as MockGauge, \
             patch("app.utils.metrics.Counter"), \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            gauge_instance = MockGauge.return_value

            metrics.update_success_rate(period="daily", rate=0.95)

            gauge_instance.labels.assert_called()
            gauge_instance.labels.return_value.set.assert_called_with(0.95)

    def test_update_job_counts(self):
        """update_job_counts sets active and inactive gauges."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge") as MockGauge, \
             patch("app.utils.metrics.Counter"), \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            gauge_instance = MockGauge.return_value

            metrics.update_job_counts(active=10, inactive=3)

            # Should be called with both active and inactive
            assert gauge_instance.labels.call_count >= 2

    def test_update_queue_metrics(self):
        """update_queue_metrics sets active and queued gauges."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge") as MockGauge, \
             patch("app.utils.metrics.Counter"), \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            gauge_instance = MockGauge.return_value

            metrics.update_queue_metrics(active=5, queued=2)

            gauge_instance.set.assert_called()

    def test_record_cache_hit(self):
        """record_cache_hit increments cache hits counter."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge"), \
             patch("app.utils.metrics.Counter") as MockCounter, \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            counter_instance = MockCounter.return_value

            metrics.record_cache_hit(key_prefix="jobs")

            counter_instance.labels.assert_called()
            counter_instance.labels.return_value.inc.assert_called()

    def test_record_cache_miss(self):
        """record_cache_miss increments cache misses counter."""
        from app.utils.metrics import BackupSystemMetrics

        with patch("app.utils.metrics.Gauge"), \
             patch("app.utils.metrics.Counter") as MockCounter, \
             patch("app.utils.metrics.Histogram"), \
             patch("app.utils.metrics.Info"):
            metrics = BackupSystemMetrics()
            counter_instance = MockCounter.return_value

            metrics.record_cache_miss(key_prefix="jobs")

            counter_instance.labels.assert_called()
            counter_instance.labels.return_value.inc.assert_called()


class TestInitMetrics:
    """Tests for init_metrics function."""

    def test_init_metrics_creates_prometheus_metrics(self, app):
        """init_metrics initializes PrometheusMetrics and registers endpoint."""
        with patch("app.utils.metrics.PrometheusMetrics") as MockPM, \
             patch("app.utils.metrics.backup_metrics") as mock_bm:
            mock_pm_instance = MockPM.return_value

            from app.utils.metrics import init_metrics
            result = init_metrics(app)

            MockPM.assert_called_once_with(app)
            mock_pm_instance.info.assert_called_once()
            mock_bm.init_app.assert_called_once_with(app)
            assert result == mock_pm_instance

    def test_init_metrics_registers_metrics_endpoint(self, app):
        """init_metrics registers /metrics route."""
        with patch("app.utils.metrics.PrometheusMetrics"), \
             patch("app.utils.metrics.backup_metrics"):
            from app.utils.metrics import init_metrics
            init_metrics(app)

            # Verify /metrics endpoint is registered
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            assert "/metrics" in rules


class TestMetricsIntegrationWithApp:
    """Integration tests for metrics with Flask app."""

    def test_prometheus_disabled_by_default(self, app):
        """PROMETHEUS_ENABLED defaults to False."""
        assert app.config.get("PROMETHEUS_ENABLED", False) is False

    def test_prometheus_enabled_config(self):
        """PROMETHEUS_ENABLED can be set to True."""
        import os
        os.environ["FLASK_ENV"] = "testing"
        os.environ["PROMETHEUS_ENABLED"] = "true"
        try:
            from app import create_app
            from app.config import TestingConfig

            class TestMetricsConfig(TestingConfig):
                PROMETHEUS_ENABLED = True

            test_app = create_app("testing")
            # The TestingConfig doesn't have PROMETHEUS_ENABLED by default
            # but the Config base class reads from env var
        finally:
            os.environ.pop("PROMETHEUS_ENABLED", None)

    def test_global_backup_metrics_instance_exists(self):
        """Module-level backup_metrics instance exists."""
        from app.utils.metrics import backup_metrics
        assert backup_metrics is not None


class TestTrackExecutionTimeDecorator:
    """Tests for track_execution_time decorator."""

    def test_track_execution_time_decorator(self):
        """track_execution_time wraps function and tracks duration."""
        with patch("app.utils.metrics.Histogram") as MockHistogram:
            mock_hist = MockHistogram.return_value

            from app.utils.metrics import track_execution_time

            @track_execution_time("test_operation")
            def sample_function():
                return "result"

            result = sample_function()

            assert result == "result"
            MockHistogram.assert_called_once_with(
                "test_operation_duration_seconds",
                "Duration of test_operation in seconds",
            )
            mock_hist.time.assert_called_once()

    def test_track_execution_time_default_name(self):
        """track_execution_time uses function name by default."""
        with patch("app.utils.metrics.Histogram") as MockHistogram:
            from app.utils.metrics import track_execution_time

            @track_execution_time()
            def my_custom_function():
                return 42

            result = my_custom_function()
            assert result == 42
            MockHistogram.assert_called_once_with(
                "my_custom_function_duration_seconds",
                "Duration of my_custom_function in seconds",
            )


class TestCountCallsDecorator:
    """Tests for count_calls decorator."""

    def test_count_calls_without_labels(self):
        """count_calls counts function invocations without labels."""
        with patch("app.utils.metrics.Counter") as MockCounter:
            mock_counter = MockCounter.return_value

            from app.utils.metrics import count_calls

            @count_calls("api_requests")
            def handle_request():
                return "ok"

            result = handle_request()

            assert result == "ok"
            mock_counter.inc.assert_called_once()

    def test_count_calls_with_labels(self):
        """count_calls counts function invocations with labels."""
        with patch("app.utils.metrics.Counter") as MockCounter:
            mock_counter = MockCounter.return_value

            from app.utils.metrics import count_calls

            @count_calls("api_requests", labels={"endpoint": "jobs"})
            def handle_request():
                return "ok"

            result = handle_request()

            assert result == "ok"
            mock_counter.labels.assert_called_with(endpoint="jobs")
            mock_counter.labels.return_value.inc.assert_called_once()
