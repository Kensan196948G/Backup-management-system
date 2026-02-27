"""
Unit tests for report tasks.
Phase 15B: テストカバレッジ向上

report_tasks.py の Celery タスクの単体テスト。
generate_pdf_report / generate_daily_report / generate_monthly_report /
schedule_report の各タスクをカバー。
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class ComparisonMock(Mock):
    """SQLAlchemy カラム属性の比較演算子をサポートするモック。"""

    def __lt__(self, other):
        return Mock()

    def __le__(self, other):
        return Mock()

    def __gt__(self, other):
        return Mock()

    def __ge__(self, other):
        return Mock()

    def __or__(self, other):
        return Mock()

    def __and__(self, other):
        return Mock()

    def is_(self, other):
        return Mock()

    def asc(self):
        m = Mock()
        m.nullsfirst = lambda: Mock()
        return m


class TestGeneratePdfReportTask:
    """generate_pdf_report タスクのテスト。"""

    @pytest.fixture
    def celery_app(self, app):
        """Celery をテスト用に設定する。"""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_generate_pdf_report_unknown_type(self, app, celery_app):
        """未知のレポートタイプを指定した場合に failed を返す。"""
        from app.tasks.report_tasks import generate_pdf_report

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen_class.return_value = mock_gen

            with app.app_context():
                result = generate_pdf_report(
                    report_type="unknown_type",
                )

                assert result["status"] == "failed"
                assert "Unknown report type" in result["error"]
                assert result["report_type"] == "unknown_type"

    def test_generate_pdf_report_compliance_success(self, app, celery_app):
        """compliance レポート生成が成功するケース。"""
        from app.tasks.report_tasks import generate_pdf_report

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"PDF content")

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate_compliance_report.return_value = tmp_path
            mock_gen_class.return_value = mock_gen

            with patch("app.tasks.report_tasks._record_report"):
                with patch("app.tasks.report_tasks._send_report_notification"):
                    with app.app_context():
                        result = generate_pdf_report(
                            report_type="compliance",
                        )

                        assert result["status"] == "completed"
                        assert result["file_path"] == tmp_path
                        assert "file_size" in result
                        assert "completed_at" in result

    def test_generate_pdf_report_daily_success(self, app, celery_app):
        """daily レポート生成が成功するケース。"""
        from app.tasks.report_tasks import generate_pdf_report

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"Daily PDF content")

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate_daily_report.return_value = tmp_path
            mock_gen_class.return_value = mock_gen

            with patch("app.tasks.report_tasks._record_report"):
                with app.app_context():
                    result = generate_pdf_report(
                        report_type="daily",
                        params={"date": "2025-01-15"},
                    )

                    assert result["status"] == "completed"
                    assert result["report_type"] == "daily"

    def test_generate_pdf_report_monthly_success(self, app, celery_app):
        """monthly レポート生成が成功するケース。"""
        from app.tasks.report_tasks import generate_pdf_report

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"Monthly PDF")

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate_monthly_report.return_value = tmp_path
            mock_gen_class.return_value = mock_gen

            with patch("app.tasks.report_tasks._record_report"):
                with app.app_context():
                    result = generate_pdf_report(
                        report_type="monthly",
                        params={"year": 2025, "month": 1},
                    )

                    assert result["status"] == "completed"
                    assert result["report_type"] == "monthly"

    def test_generate_pdf_report_audit_success(self, app, celery_app):
        """audit レポート生成が成功するケース。"""
        from app.tasks.report_tasks import generate_pdf_report

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"Audit PDF")

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate_audit_report.return_value = tmp_path
            mock_gen_class.return_value = mock_gen

            with patch("app.tasks.report_tasks._record_report"):
                with app.app_context():
                    result = generate_pdf_report(
                        report_type="audit",
                    )

                    assert result["status"] == "completed"
                    assert result["report_type"] == "audit"

    def test_generate_pdf_report_backup_summary_success(self, app, celery_app):
        """backup_summary レポート生成が成功するケース。"""
        from app.tasks.report_tasks import generate_pdf_report

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"Summary PDF")

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate_backup_summary_report.return_value = tmp_path
            mock_gen_class.return_value = mock_gen

            with patch("app.tasks.report_tasks._record_report"):
                with app.app_context():
                    result = generate_pdf_report(
                        report_type="backup_summary",
                    )

                    assert result["status"] == "completed"

    def test_generate_pdf_report_file_not_exist(self, app, celery_app):
        """ファイルが存在しない場合に failed を返す。"""
        from app.tasks.report_tasks import generate_pdf_report

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            # 存在しないパスを返す
            mock_gen.generate_compliance_report.return_value = "/nonexistent/report.pdf"
            mock_gen_class.return_value = mock_gen

            with app.app_context():
                result = generate_pdf_report(
                    report_type="compliance",
                )

                assert result["status"] == "failed"
                assert "no file" in result["error"].lower()

    def test_generate_pdf_report_generator_returns_none(self, app, celery_app):
        """PDF生成器が None を返す場合に failed を返す。"""
        from app.tasks.report_tasks import generate_pdf_report

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate_daily_report.return_value = None
            mock_gen_class.return_value = mock_gen

            with app.app_context():
                result = generate_pdf_report(
                    report_type="daily",
                )

                assert result["status"] == "failed"

    def test_generate_pdf_report_with_notify_email(self, app, celery_app):
        """notify_email が指定された場合に通知が送信されることを確認。"""
        from app.tasks.report_tasks import generate_pdf_report

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"PDF with notification")

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate_compliance_report.return_value = tmp_path
            mock_gen_class.return_value = mock_gen

            with patch("app.tasks.report_tasks._record_report"):
                with patch("app.tasks.report_tasks._send_report_notification") as mock_send:
                    with app.app_context():
                        result = generate_pdf_report(
                            report_type="compliance",
                            notify_email="admin@example.com",
                        )

                        assert result["status"] == "completed"
                        mock_send.assert_called_once_with(
                            recipient="admin@example.com",
                            report_type="compliance",
                            file_path=tmp_path,
                        )

    def test_generate_pdf_report_no_notify_email(self, app, celery_app):
        """notify_email が指定されない場合に通知が送信されないことを確認。"""
        from app.tasks.report_tasks import generate_pdf_report

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"PDF without notification")

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate_compliance_report.return_value = tmp_path
            mock_gen_class.return_value = mock_gen

            with patch("app.tasks.report_tasks._record_report"):
                with patch("app.tasks.report_tasks._send_report_notification") as mock_send:
                    with app.app_context():
                        result = generate_pdf_report(
                            report_type="compliance",
                            notify_email=None,
                        )

                        assert result["status"] == "completed"
                        mock_send.assert_not_called()

    def test_generate_pdf_report_exception_handling(self, app, celery_app):
        """例外発生時に error ステータスを返す。"""
        from app.tasks.report_tasks import generate_pdf_report

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen_class.side_effect = Exception("PDF generator error")

            # Disable retries so the exception result is returned without re-raising
            with patch.object(generate_pdf_report, "max_retries", 0):
                with app.app_context():
                    result = generate_pdf_report(
                        report_type="compliance",
                    )

                    assert result["status"] == "error"
                    assert "error" in result

    def test_generate_pdf_report_result_contains_started_at(self, app, celery_app):
        """結果に started_at が含まれることを確認。"""
        from app.tasks.report_tasks import generate_pdf_report

        with patch("app.services.pdf_generator.PDFGenerator") as mock_gen_class:
            mock_gen_class.side_effect = Exception("Forced error")

            # Disable retries so the result is returned instead of re-raising
            with patch.object(generate_pdf_report, "max_retries", 0):
                with app.app_context():
                    result = generate_pdf_report(
                        report_type="compliance",
                    )

                    # エラーでも started_at が含まれる
                    assert "started_at" in result


class TestGenerateDailyReportTask:
    """generate_daily_report タスクのテスト。"""

    @pytest.fixture
    def celery_app(self, app):
        """Celery をテスト用に設定する。"""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def _make_job_query_mock(self, count):
        """BackupJob.query チェーンのモックを返すヘルパー。filter/count をサポートする。"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = count
        return mock_query

    def test_generate_daily_report_success(self, app, celery_app):
        """日次レポートの正常生成テスト。"""
        from app.tasks.report_tasks import generate_daily_report

        with patch("app.models.BackupJob") as mock_job_class:
            mock_query = self._make_job_query_mock(5)
            mock_job_class.query = mock_query
            mock_job_class.created_at = ComparisonMock()
            mock_job_class.status = ComparisonMock()

            with patch("app.models.Alert") as mock_alert_class:
                mock_alert_query = self._make_job_query_mock(2)
                mock_alert_class.query = mock_alert_query
                mock_alert_class.created_at = ComparisonMock()

                with patch("app.services.compliance_checker.ComplianceChecker") as mock_checker_class:
                    mock_checker = Mock()
                    mock_checker.check_all_rules.return_value = {
                        "overall_status": "compliant",
                        "score": 95,
                    }
                    mock_checker_class.return_value = mock_checker

                    with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
                        mock_pdf.apply_async.return_value = Mock(id="pdf-task-123")

                        with app.app_context():
                            result = generate_daily_report()

                            assert result["status"] == "completed"
                            assert "stats" in result
                            assert "report_task_id" in result
                            assert "report_date" in result

    def test_generate_daily_report_stats_zero_jobs(self, app, celery_app):
        """ジョブが0件のときの成功率が100%になることを確認。"""
        from app.tasks.report_tasks import generate_daily_report

        with patch("app.models.BackupJob") as mock_job_class:
            mock_query = self._make_job_query_mock(0)
            mock_job_class.query = mock_query
            mock_job_class.created_at = ComparisonMock()
            mock_job_class.status = ComparisonMock()

            with patch("app.models.Alert") as mock_alert_class:
                mock_alert_query = self._make_job_query_mock(0)
                mock_alert_class.query = mock_alert_query
                mock_alert_class.created_at = ComparisonMock()

                with patch("app.services.compliance_checker.ComplianceChecker") as mock_checker_class:
                    mock_checker = Mock()
                    mock_checker.check_all_rules.return_value = {"overall_status": "unknown", "score": 0}
                    mock_checker_class.return_value = mock_checker

                    with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
                        mock_pdf.apply_async.return_value = Mock(id="pdf-task-456")

                        with app.app_context():
                            result = generate_daily_report()

                            assert result["status"] == "completed"
                            # ジョブが0件のときは成功率100%
                            assert result["stats"]["success_rate"] == 100.0

    def test_generate_daily_report_compliance_check_failure(self, app, celery_app):
        """コンプライアンスチェックが失敗しても daily report は成功する。"""
        from app.tasks.report_tasks import generate_daily_report

        with patch("app.models.BackupJob") as mock_job_class:
            mock_query = self._make_job_query_mock(3)
            mock_job_class.query = mock_query
            mock_job_class.created_at = ComparisonMock()
            mock_job_class.status = ComparisonMock()

            with patch("app.models.Alert") as mock_alert_class:
                mock_alert_query = self._make_job_query_mock(0)
                mock_alert_class.query = mock_alert_query
                mock_alert_class.created_at = ComparisonMock()

                with patch("app.services.compliance_checker.ComplianceChecker") as mock_checker_class:
                    # コンプライアンスチェッカーが例外を発生させる
                    mock_checker = Mock()
                    mock_checker.check_all_rules.side_effect = Exception("Compliance error")
                    mock_checker_class.return_value = mock_checker

                    with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
                        mock_pdf.apply_async.return_value = Mock(id="pdf-task-789")

                        with app.app_context():
                            result = generate_daily_report()

                            # コンプライアンスエラーがあっても全体は成功
                            assert result["status"] == "completed"
                            assert result["stats"]["compliance_status"] == "unknown"

    def test_generate_daily_report_exception_handling(self, app, celery_app):
        """例外発生時に error ステータスを返す。"""
        from app.tasks.report_tasks import generate_daily_report

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.filter.side_effect = Exception("Database error")
            mock_job_class.created_at = ComparisonMock()
            mock_job_class.status = ComparisonMock()

            # Disable retries to get the result dict back
            with patch.object(generate_daily_report, "max_retries", 0):
                with app.app_context():
                    result = generate_daily_report()

                    assert result["status"] == "error"
                    assert "error" in result

    def test_generate_daily_report_result_contains_report_date(self, app, celery_app):
        """結果に report_date が含まれることを確認。"""
        from app.tasks.report_tasks import generate_daily_report

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.filter.side_effect = Exception("DB error")
            mock_job_class.created_at = ComparisonMock()
            mock_job_class.status = ComparisonMock()

            # Disable retries to get the result dict back
            with patch.object(generate_daily_report, "max_retries", 0):
                with app.app_context():
                    result = generate_daily_report()

                    assert "report_date" in result


class TestGenerateMonthlyReportTask:
    """generate_monthly_report タスクのテスト。"""

    @pytest.fixture
    def celery_app(self, app):
        """Celery をテスト用に設定する。"""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_generate_monthly_report_with_explicit_year_month(self, app, celery_app):
        """年月を明示的に指定した場合のテスト。"""
        from app.tasks.report_tasks import generate_monthly_report

        with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
            mock_pdf.apply_async.return_value = Mock(id="pdf-monthly-123")

            with app.app_context():
                result = generate_monthly_report(year=2025, month=6)

                assert result["status"] == "queued"
                assert result["year"] == 2025
                assert result["month"] == 6
                assert "report_task_id" in result

    def test_generate_monthly_report_defaults_to_previous_month(self, app, celery_app):
        """year/month を指定しない場合、前月のレポートが生成される。"""
        from app.tasks.report_tasks import generate_monthly_report

        with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
            mock_pdf.apply_async.return_value = Mock(id="pdf-monthly-456")

            with app.app_context():
                result = generate_monthly_report()

                assert result["status"] == "queued"
                assert "year" in result
                assert "month" in result
                # year と month は有効な値
                assert 1 <= result["month"] <= 12
                assert result["year"] >= 2024

    def test_generate_monthly_report_january_wraps_to_previous_year(self, app, celery_app):
        """1月にデフォルト実行すると前年12月を参照することを確認。"""
        from datetime import UTC, datetime

        from app.tasks.report_tasks import generate_monthly_report

        # 1月にパッチ
        mock_now = datetime(2026, 1, 15, tzinfo=UTC)

        with patch("app.tasks.report_tasks.datetime") as mock_dt_class:
            mock_dt_class.now.return_value = mock_now
            mock_dt_class.combine = datetime.combine
            mock_dt_class.min = datetime.min

            with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
                mock_pdf.apply_async.return_value = Mock(id="pdf-monthly-789")

                with app.app_context():
                    result = generate_monthly_report()

                    assert result["status"] == "queued"
                    assert result["year"] == 2025
                    assert result["month"] == 12

    def test_generate_monthly_report_queues_pdf_generation(self, app, celery_app):
        """generate_pdf_report タスクがキューに追加されることを確認。"""
        from app.tasks.report_tasks import generate_monthly_report

        with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
            mock_pdf.apply_async.return_value = Mock(id="pdf-check-999")

            with app.app_context():
                result = generate_monthly_report(year=2025, month=3)

                mock_pdf.apply_async.assert_called_once()
                call_kwargs = mock_pdf.apply_async.call_args[1]["kwargs"]
                assert call_kwargs["report_type"] == "monthly"
                assert call_kwargs["params"]["year"] == 2025
                assert call_kwargs["params"]["month"] == 3

    def test_generate_monthly_report_exception_handling(self, app, celery_app):
        """例外発生時に error ステータスを返す。"""
        from app.tasks.report_tasks import generate_monthly_report

        with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
            mock_pdf.apply_async.side_effect = Exception("Queue error")

            # Disable retries to get the result dict back instead of re-raising
            with patch.object(generate_monthly_report, "max_retries", 0):
                with app.app_context():
                    result = generate_monthly_report(year=2025, month=4)

                    assert result["status"] == "error"
                    assert "error" in result

    def test_generate_monthly_report_result_contains_timestamp(self, app, celery_app):
        """結果に timestamp が含まれることを確認。"""
        from app.tasks.report_tasks import generate_monthly_report

        with patch("app.tasks.report_tasks.generate_pdf_report") as mock_pdf:
            mock_pdf.apply_async.return_value = Mock(id="pdf-ts-001")

            with app.app_context():
                result = generate_monthly_report(year=2025, month=5)

                assert "timestamp" in result


class TestScheduleReportTask:
    """schedule_report タスクのテスト。"""

    @pytest.fixture
    def celery_app(self, app):
        """Celery をテスト用に設定する。"""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_schedule_report_success(self, app, celery_app):
        """レポートスケジュールの正常登録テスト。"""
        from app.tasks.report_tasks import schedule_report

        with patch("app.models.ScheduledReport") as mock_sched_class:
            mock_sched = Mock()
            mock_sched.id = 42
            mock_sched_class.return_value = mock_sched

            with patch("app.models.db") as mock_db:
                with app.app_context():
                    result = schedule_report(
                        report_type="daily",
                        schedule_type="daily",
                        recipients=["admin@example.com", "manager@example.com"],
                    )

                    assert result["status"] == "scheduled"
                    assert result["scheduled_report_id"] == 42
                    mock_db.session.add.assert_called_once()
                    mock_db.session.commit.assert_called_once()

    def test_schedule_report_with_params(self, app, celery_app):
        """パラメータ付きでのスケジュール登録テスト。"""
        from app.tasks.report_tasks import schedule_report

        with patch("app.models.ScheduledReport") as mock_sched_class:
            mock_sched = Mock()
            mock_sched.id = 10
            mock_sched_class.return_value = mock_sched

            with patch("app.models.db") as mock_db:
                with app.app_context():
                    result = schedule_report(
                        report_type="monthly",
                        schedule_type="monthly",
                        recipients=["audit@example.com"],
                        params={"include_details": True, "format": "pdf"},
                    )

                    assert result["status"] == "scheduled"
                    assert result["report_type"] == "monthly"
                    assert result["schedule_type"] == "monthly"

    def test_schedule_report_exception_handling(self, app, celery_app):
        """例外発生時に error ステータスを返す。"""
        from app.tasks.report_tasks import schedule_report

        with patch("app.models.ScheduledReport") as mock_sched_class:
            mock_sched_class.side_effect = Exception("Model error")

            with app.app_context():
                result = schedule_report(
                    report_type="daily",
                    schedule_type="daily",
                    recipients=["test@example.com"],
                )

                assert result["status"] == "error"
                assert "error" in result

    def test_schedule_report_result_contains_recipients(self, app, celery_app):
        """結果に recipients が含まれることを確認。"""
        from app.tasks.report_tasks import schedule_report

        with patch("app.models.ScheduledReport") as mock_sched_class:
            mock_sched = Mock()
            mock_sched.id = 5
            mock_sched_class.return_value = mock_sched

            with patch("app.models.db"):
                with app.app_context():
                    result = schedule_report(
                        report_type="weekly",
                        schedule_type="weekly",
                        recipients=["a@test.com", "b@test.com"],
                    )

                    assert result["recipients"] == ["a@test.com", "b@test.com"]


class TestRecordReportHelper:
    """_record_report ヘルパー関数のテスト。"""

    def test_record_report_success(self, app):
        """レポート記録が成功するケース。"""
        from app.tasks.report_tasks import _record_report

        with patch("app.models.Report") as mock_report_class:
            mock_report = Mock()
            mock_report.id = 1
            mock_report_class.return_value = mock_report

            with patch("app.models.db") as mock_db:
                with app.app_context():
                    _record_report(
                        report_type="compliance",
                        file_path="/reports/compliance.pdf",
                        task_id="task-rpt-001",
                        status="completed",
                    )

                    mock_db.session.add.assert_called_once()
                    mock_db.session.commit.assert_called_once()

    def test_record_report_exception_is_handled(self, app):
        """例外発生時にロールバックされることを確認。"""
        from app.tasks.report_tasks import _record_report

        with patch("app.models.Report") as mock_report_class:
            mock_report_class.side_effect = Exception("Model error")

            with patch("app.models.db") as mock_db:
                with app.app_context():
                    # 例外が外部に伝播しないことを確認
                    _record_report(
                        report_type="daily",
                        file_path="/reports/daily.pdf",
                        task_id="task-rpt-002",
                        status="completed",
                    )
                    mock_db.session.rollback.assert_called_once()


class TestSendReportNotificationHelper:
    """_send_report_notification ヘルパー関数のテスト。"""

    def test_send_report_notification_queues_email(self, app):
        """レポート通知がメール送信タスクをキューに追加することを確認。"""
        from app.tasks.report_tasks import _send_report_notification

        with patch("app.tasks.email_tasks.send_email") as mock_send:
            mock_send.apply_async.return_value = Mock(id="email-rpt-001")

            with app.app_context():
                _send_report_notification(
                    recipient="admin@example.com",
                    report_type="compliance",
                    file_path="/reports/compliance_2025.pdf",
                )

                mock_send.apply_async.assert_called_once()
                call_kwargs = mock_send.apply_async.call_args[1]["kwargs"]
                assert call_kwargs["to"] == "admin@example.com"
                assert "compliance" in call_kwargs["subject"]

    def test_send_report_notification_contains_filename_in_body(self, app):
        """メール本文にファイル名が含まれることを確認。"""
        from app.tasks.report_tasks import _send_report_notification

        with patch("app.tasks.email_tasks.send_email") as mock_send:
            mock_send.apply_async.return_value = Mock(id="email-rpt-002")

            with app.app_context():
                _send_report_notification(
                    recipient="user@example.com",
                    report_type="daily",
                    file_path="/reports/daily_report_2025.pdf",
                )

                call_kwargs = mock_send.apply_async.call_args[1]["kwargs"]
                # ファイル名がHTML本文に含まれている
                assert "daily_report_2025.pdf" in call_kwargs["html_body"]
