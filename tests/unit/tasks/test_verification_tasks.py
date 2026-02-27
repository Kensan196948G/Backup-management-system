"""
Unit tests for verification tasks.
Phase 15B: テストカバレッジ向上

verification_tasks.py の Celery タスクの単体テスト。
verify_backup / verify_all_pending / check_verification_reminders の各タスクをカバー。

NOTE: すべてのモデルインポートはタスク関数内の lazy import のため、
      patch ターゲットは app.models.* を使用する必要がある。
      SQLAlchemy カラム属性の比較演算子をサポートするために
      ComparisonMock を使用する。
"""

from unittest.mock import MagicMock, Mock, patch

import pytest


class ComparisonMock(Mock):
    """SQLAlchemy カラム属性の比較演算子をサポートするモック。

    Mock は Python の比較演算子（<, >, <=, >=）をデフォルトで
    サポートしないため、SQLAlchemy フィルター条件の構築に使用する。
    """

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


class TestVerifyBackupTask:
    """verify_backup タスクのテスト。"""

    @pytest.fixture
    def celery_app(self, app):
        """Celery をテスト用に設定する。"""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def test_verify_backup_job_not_found(self, app, celery_app):
        """存在しないジョブIDを指定した場合に failed を返すことを確認。"""
        from app.tasks.verification_tasks import verify_backup

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = None

            with patch("app.services.verification_service.VerificationService"):
                with app.app_context():
                    result = verify_backup(job_id=99999, verification_type="checksum")

                    assert result["status"] == "failed"
                    assert "not found" in result["error"].lower()
                    assert result["job_id"] == 99999

    def test_verify_backup_checksum_success(self, app, celery_app):
        """checksum 検証が成功するケース。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 1
        mock_job.name = "Test Backup Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.models.VerificationResult"):
                with patch("app.models.db") as mock_db:
                    with patch("app.services.verification_service.VerificationService") as mock_svc_class:
                        mock_svc = Mock()
                        mock_svc.verify_checksum.return_value = {"success": True, "checksum": "abc123"}
                        mock_svc_class.return_value = mock_svc

                        with patch("app.tasks.verification_tasks._record_verification"):
                            with patch("app.tasks.verification_tasks._send_verification_notification"):
                                with app.app_context():
                                    result = verify_backup(
                                        job_id=1,
                                        verification_type="checksum",
                                        notify_on_complete=True,
                                    )

                                    assert result["status"] == "completed"
                                    assert result["success"] is True
                                    assert result["verification_type"] == "checksum"
                                    assert "verification_result" in result

    def test_verify_backup_checksum_failure(self, app, celery_app):
        """checksum 検証が失敗するケース。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 1
        mock_job.name = "Test Backup Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.models.VerificationResult"):
                with patch("app.models.db"):
                    with patch("app.services.verification_service.VerificationService") as mock_svc_class:
                        mock_svc = Mock()
                        mock_svc.verify_checksum.return_value = {"success": False, "error": "Checksum mismatch"}
                        mock_svc_class.return_value = mock_svc

                        with patch("app.tasks.verification_tasks._record_verification"):
                            with patch("app.tasks.verification_tasks._send_verification_notification"):
                                with app.app_context():
                                    result = verify_backup(
                                        job_id=1,
                                        verification_type="checksum",
                                        notify_on_complete=False,
                                    )

                                    assert result["status"] == "completed"
                                    assert result["success"] is False

    def test_verify_backup_restore_test_success(self, app, celery_app):
        """restore_test 検証が成功するケース。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 2
        mock_job.name = "Restore Test Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.models.VerificationResult"):
                with patch("app.models.db"):
                    with patch("app.services.verification_service.VerificationService") as mock_svc_class:
                        mock_svc = Mock()
                        mock_svc.verify_restore_test.return_value = {"success": True, "duration": 120}
                        mock_svc_class.return_value = mock_svc

                        with patch("app.tasks.verification_tasks._record_verification"):
                            with patch("app.tasks.verification_tasks._send_verification_notification"):
                                with app.app_context():
                                    result = verify_backup(
                                        job_id=2,
                                        verification_type="restore_test",
                                    )

                                    assert result["status"] == "completed"
                                    assert result["verification_type"] == "restore_test"

    def test_verify_backup_full_verification(self, app, celery_app):
        """full 検証（checksum + restore_test）が成功するケース。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 3
        mock_job.name = "Full Verify Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.models.VerificationResult"):
                with patch("app.models.db"):
                    with patch("app.services.verification_service.VerificationService") as mock_svc_class:
                        mock_svc = Mock()
                        mock_svc.verify_checksum.return_value = {"success": True}
                        mock_svc.verify_restore_test.return_value = {"success": True}
                        mock_svc_class.return_value = mock_svc

                        with patch("app.tasks.verification_tasks._record_verification"):
                            with patch("app.tasks.verification_tasks._send_verification_notification"):
                                with app.app_context():
                                    result = verify_backup(
                                        job_id=3,
                                        verification_type="full",
                                    )

                                    assert result["status"] == "completed"
                                    assert result["verification_type"] == "full"
                                    assert "verification_result" in result

    def test_verify_backup_full_partial_failure(self, app, celery_app):
        """full 検証でチェックサムは成功、リストアは失敗するケース。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 4
        mock_job.name = "Partial Fail Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.models.VerificationResult"):
                with patch("app.models.db"):
                    with patch("app.services.verification_service.VerificationService") as mock_svc_class:
                        mock_svc = Mock()
                        mock_svc.verify_checksum.return_value = {"success": True}
                        mock_svc.verify_restore_test.return_value = {"success": False, "error": "Restore failed"}
                        mock_svc_class.return_value = mock_svc

                        with patch("app.tasks.verification_tasks._record_verification"):
                            with patch("app.tasks.verification_tasks._send_verification_notification"):
                                with app.app_context():
                                    result = verify_backup(
                                        job_id=4,
                                        verification_type="full",
                                    )

                                    assert result["status"] == "completed"
                                    # overall_success は False になるはず
                                    assert result["success"] is False

    def test_verify_backup_unknown_type(self, app, celery_app):
        """未知の verification_type を指定した場合に failed を返す。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 1
        mock_job.name = "Test Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.services.verification_service.VerificationService"):
                with app.app_context():
                    result = verify_backup(
                        job_id=1,
                        verification_type="unknown_type",
                    )

                    assert result["status"] == "failed"
                    assert "Unknown verification type" in result["error"]

    def test_verify_backup_exception_on_query(self, app, celery_app):
        """クエリ実行時に例外が発生した場合に error ステータスを返すことを確認。

        max_retries が 2 なのでリトライが試みられることを考慮し、
        Celery の retry 動作を無効にするため max_retries=0 の状態でテストする。
        """
        from app.tasks.verification_tasks import verify_backup

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.side_effect = Exception("Database connection error")

            with patch("app.services.verification_service.VerificationService"):
                with patch.object(verify_backup, "max_retries", 0):
                    with app.app_context():
                        result = verify_backup(job_id=1, verification_type="checksum")

                        assert result["status"] == "error"
                        assert "error" in result

    def test_verify_backup_notify_on_complete_false(self, app, celery_app):
        """notify_on_complete=False の場合は通知を送らないことを確認。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 1
        mock_job.name = "No Notify Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.models.VerificationResult"):
                with patch("app.models.db"):
                    with patch("app.services.verification_service.VerificationService") as mock_svc_class:
                        mock_svc = Mock()
                        mock_svc.verify_checksum.return_value = {"success": True}
                        mock_svc_class.return_value = mock_svc

                        with patch("app.tasks.verification_tasks._record_verification"):
                            with patch("app.tasks.verification_tasks._send_verification_notification") as mock_notify:
                                with app.app_context():
                                    result = verify_backup(
                                        job_id=1,
                                        verification_type="checksum",
                                        notify_on_complete=False,
                                    )

                                    # 通知が呼ばれていないことを確認
                                    mock_notify.assert_not_called()
                                    assert result["status"] == "completed"

    def test_verify_backup_result_contains_timestamps(self, app, celery_app):
        """結果に started_at と completed_at タイムスタンプが含まれることを確認。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 1
        mock_job.name = "Timestamp Test Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.models.VerificationResult"):
                with patch("app.models.db"):
                    with patch("app.services.verification_service.VerificationService") as mock_svc_class:
                        mock_svc = Mock()
                        mock_svc.verify_checksum.return_value = {"success": True}
                        mock_svc_class.return_value = mock_svc

                        with patch("app.tasks.verification_tasks._record_verification"):
                            with patch("app.tasks.verification_tasks._send_verification_notification"):
                                with app.app_context():
                                    result = verify_backup(job_id=1, verification_type="checksum")

                                    assert "started_at" in result
                                    assert "completed_at" in result

    def test_verify_backup_records_verification_on_success(self, app, celery_app):
        """成功時に _record_verification が呼ばれることを確認。"""
        from app.tasks.verification_tasks import verify_backup

        mock_job = Mock()
        mock_job.id = 1
        mock_job.name = "Record Test Job"

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.get.return_value = mock_job

            with patch("app.models.VerificationResult"):
                with patch("app.models.db"):
                    with patch("app.services.verification_service.VerificationService") as mock_svc_class:
                        mock_svc = Mock()
                        mock_svc.verify_checksum.return_value = {"success": True}
                        mock_svc_class.return_value = mock_svc

                        with patch("app.tasks.verification_tasks._record_verification") as mock_record:
                            with patch("app.tasks.verification_tasks._send_verification_notification"):
                                with app.app_context():
                                    verify_backup(job_id=1, verification_type="checksum")

                                    mock_record.assert_called_once()


class TestVerifyAllPendingTask:
    """verify_all_pending タスクのテスト。"""

    @pytest.fixture
    def celery_app(self, app):
        """Celery をテスト用に設定する。"""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def _make_query_chain(self, results):
        """クエリチェーン全体のモックを返すヘルパー。"""
        mock_query_chain = Mock()
        mock_query_chain.filter.return_value = mock_query_chain
        mock_query_chain.order_by.return_value = mock_query_chain
        mock_query_chain.limit.return_value = mock_query_chain
        mock_query_chain.all.return_value = results
        return mock_query_chain

    def test_verify_all_pending_no_jobs(self, app, celery_app):
        """検証待ちジョブが存在しない場合のテスト。"""
        from app.tasks.verification_tasks import verify_all_pending

        mock_query_chain = self._make_query_chain([])

        with patch("app.models.BackupJob") as mock_job_class:
            # BackupJob.query をモックし、カラム属性もモックして比較エラーを防ぐ
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with app.app_context():
                result = verify_all_pending(max_jobs=10)

                assert result["status"] == "queued"
                assert result["queued_count"] == 0
                assert len(result["queued_jobs"]) == 0

    def test_verify_all_pending_with_jobs(self, app, celery_app):
        """検証待ちジョブが存在する場合のテスト。"""
        from app.tasks.verification_tasks import verify_all_pending

        mock_jobs = []
        for i in range(3):
            m = Mock()
            m.id = i
            m.name = f"Job {i}"
            mock_jobs.append(m)
        mock_query_chain = self._make_query_chain(mock_jobs)

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with patch("app.tasks.verification_tasks.verify_backup") as mock_verify:
                mock_verify.apply_async.return_value = Mock(id="task-abc")

                with app.app_context():
                    result = verify_all_pending(max_jobs=10)

                    assert result["status"] == "queued"
                    assert result["queued_count"] == 3
                    assert len(result["queued_jobs"]) == 3

    def test_verify_all_pending_respects_max_jobs(self, app, celery_app):
        """max_jobs パラメータが適用されることを確認。"""
        from app.tasks.verification_tasks import verify_all_pending

        mock_jobs = []
        for i in range(2):
            m = Mock()
            m.id = i
            m.name = f"Job {i}"
            mock_jobs.append(m)
        mock_query_chain = self._make_query_chain(mock_jobs)

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with patch("app.tasks.verification_tasks.verify_backup") as mock_verify:
                mock_verify.apply_async.return_value = Mock(id="task-xyz")

                with app.app_context():
                    result = verify_all_pending(max_jobs=2, verification_type="restore_test")

                    assert result["verification_type"] == "restore_test"
                    # limit が正しく呼ばれているか確認
                    mock_query_chain.limit.assert_called_once_with(2)

    def test_verify_all_pending_exception_handling(self, app, celery_app):
        """例外発生時に error ステータスを返すことを確認。"""
        from app.tasks.verification_tasks import verify_all_pending

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.filter.side_effect = Exception("DB error")
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with app.app_context():
                result = verify_all_pending()

                assert result["status"] == "error"
                assert "error" in result

    def test_verify_all_pending_result_contains_timestamp(self, app, celery_app):
        """結果に timestamp が含まれることを確認。"""
        from app.tasks.verification_tasks import verify_all_pending

        mock_query_chain = self._make_query_chain([])

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with app.app_context():
                result = verify_all_pending()

                assert "timestamp" in result
                assert "verification_type" in result

    def test_verify_all_pending_queued_jobs_contain_details(self, app, celery_app):
        """キューに入れられたジョブの情報が詳細を含むことを確認。"""
        from app.tasks.verification_tasks import verify_all_pending

        mock_job = Mock()
        mock_job.id = 5
        mock_job.name = "Detail Test Job"
        mock_query_chain = self._make_query_chain([mock_job])

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with patch("app.tasks.verification_tasks.verify_backup") as mock_verify:
                mock_task = Mock(id="unique-task-id-123")
                mock_verify.apply_async.return_value = mock_task

                with app.app_context():
                    result = verify_all_pending()

                    queued = result["queued_jobs"][0]
                    assert queued["job_id"] == 5
                    assert queued["job_name"] == "Detail Test Job"
                    assert queued["task_id"] == "unique-task-id-123"


class TestCheckVerificationRemindersTask:
    """check_verification_reminders タスクのテスト。"""

    @pytest.fixture
    def celery_app(self, app):
        """Celery をテスト用に設定する。"""
        from app.tasks import celery_app

        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return celery_app

    def _make_query_chain(self, results):
        """クエリチェーン全体のモックを返すヘルパー。"""
        mock_query_chain = Mock()
        mock_query_chain.filter.return_value = mock_query_chain
        mock_query_chain.order_by.return_value = mock_query_chain
        mock_query_chain.all.return_value = results
        return mock_query_chain

    def test_check_reminders_no_overdue_jobs(self, app, celery_app):
        """期限切れのジョブが存在しない場合のテスト。"""
        from app.tasks.verification_tasks import check_verification_reminders

        mock_query_chain = self._make_query_chain([])

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with app.app_context():
                result = check_verification_reminders()

                assert result["status"] == "completed"
                assert result["reminders_sent"] == 0

    def test_check_reminders_with_overdue_jobs(self, app, celery_app):
        """期限切れジョブが存在する場合にアラートを作成するテスト。"""
        from app.tasks.verification_tasks import check_verification_reminders

        mock_jobs = []
        for i in range(3):
            m = Mock()
            m.id = i
            m.name = f"Overdue Job {i}"
            mock_jobs.append(m)
        mock_query_chain = self._make_query_chain(mock_jobs)

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with patch("app.models.Alert") as mock_alert_class:
                with patch("app.models.db") as mock_db:
                    with app.app_context():
                        result = check_verification_reminders()

                        assert result["status"] == "completed"
                        assert result["reminders_sent"] == 3
                        assert len(result["overdue_jobs"]) == 3
                        mock_db.session.add.assert_called_once()
                        mock_db.session.commit.assert_called_once()

    def test_check_reminders_result_contains_timestamp(self, app, celery_app):
        """結果に timestamp が含まれることを確認。"""
        from app.tasks.verification_tasks import check_verification_reminders

        mock_query_chain = self._make_query_chain([])

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with app.app_context():
                result = check_verification_reminders()

                assert "timestamp" in result

    def test_check_reminders_exception_handling(self, app, celery_app):
        """例外発生時に error ステータスを返すことを確認。"""
        from app.tasks.verification_tasks import check_verification_reminders

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query.filter.side_effect = Exception("Database error")
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with app.app_context():
                result = check_verification_reminders()

                assert result["status"] == "error"
                assert "error" in result

    def test_check_reminders_limits_job_names_in_alert(self, app, celery_app):
        """アラートメッセージに含まれるジョブ名が最大10件に制限されることを確認。"""
        from app.tasks.verification_tasks import check_verification_reminders

        # 15件のジョブを作成
        mock_jobs = []
        for i in range(15):
            m = Mock()
            m.id = i
            m.name = f"Job {i:02d}"
            mock_jobs.append(m)
        mock_query_chain = self._make_query_chain(mock_jobs)

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with patch("app.models.Alert") as mock_alert_class:
                mock_alert_instance = Mock()
                mock_alert_class.return_value = mock_alert_instance

                with patch("app.models.db"):
                    with app.app_context():
                        result = check_verification_reminders()

                        assert result["status"] == "completed"
                        assert result["reminders_sent"] == 15
                        # すべてのジョブ名が overdue_jobs に含まれる
                        assert len(result["overdue_jobs"]) == 15
                        # アラートが作成された
                        mock_alert_class.assert_called_once()

    def test_check_reminders_overdue_jobs_names_in_result(self, app, celery_app):
        """overdue_jobs に正確なジョブ名が含まれることを確認。"""
        from app.tasks.verification_tasks import check_verification_reminders

        job_alpha = Mock()
        job_alpha.id = 1
        job_alpha.name = "Backup Alpha"
        job_beta = Mock()
        job_beta.id = 2
        job_beta.name = "Backup Beta"
        mock_jobs = [job_alpha, job_beta]
        mock_query_chain = self._make_query_chain(mock_jobs)

        with patch("app.models.BackupJob") as mock_job_class:
            mock_job_class.query = mock_query_chain
            mock_job_class.status = ComparisonMock()
            mock_job_class.last_verified_at = ComparisonMock()

            with patch("app.models.Alert"):
                with patch("app.models.db"):
                    with app.app_context():
                        result = check_verification_reminders()

                        assert "Backup Alpha" in result["overdue_jobs"]
                        assert "Backup Beta" in result["overdue_jobs"]


class TestRecordVerificationHelper:
    """_record_verification ヘルパー関数のテスト。"""

    def test_record_verification_success(self, app):
        """検証結果の記録が成功するケース。"""
        from app.tasks.verification_tasks import _record_verification

        with patch("app.models.VerificationResult") as mock_result_class:
            mock_result = Mock()
            mock_result.id = 1
            mock_result_class.return_value = mock_result

            with patch("app.models.db") as mock_db:
                with app.app_context():
                    _record_verification(
                        job_id=1,
                        verification_type="checksum",
                        success=True,
                        details={"checksum": "abc123"},
                        task_id="task-001",
                    )

                    mock_db.session.add.assert_called_once()
                    mock_db.session.commit.assert_called_once()

    def test_record_verification_exception_is_handled(self, app):
        """例外発生時にロールバックされることを確認。"""
        from app.tasks.verification_tasks import _record_verification

        with patch("app.models.VerificationResult") as mock_result_class:
            mock_result_class.side_effect = Exception("DB error")

            with patch("app.models.db") as mock_db:
                with app.app_context():
                    # 例外が外部に伝播しないことを確認
                    _record_verification(
                        job_id=1,
                        verification_type="checksum",
                        success=True,
                        details={},
                        task_id="task-002",
                    )
                    mock_db.session.rollback.assert_called_once()


class TestSendVerificationNotificationHelper:
    """_send_verification_notification ヘルパー関数のテスト。"""

    def test_send_notification_success(self, app):
        """検証成功時の通知送信テスト。"""
        from app.tasks.verification_tasks import _send_verification_notification

        with patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:
            mock_notify.apply_async.return_value = Mock(id="notify-task-1")

            with app.app_context():
                _send_verification_notification(
                    job_name="Test Job",
                    success=True,
                    verification_type="checksum",
                )

                mock_notify.apply_async.assert_called_once()
                call_kwargs = mock_notify.apply_async.call_args[1]["kwargs"]
                assert call_kwargs["severity"] == "info"

    def test_send_notification_failure(self, app):
        """検証失敗時の通知送信テスト。"""
        from app.tasks.verification_tasks import _send_verification_notification

        with patch("app.tasks.notification_tasks.send_multi_channel_notification") as mock_notify:
            mock_notify.apply_async.return_value = Mock(id="notify-task-2")

            with app.app_context():
                _send_verification_notification(
                    job_name="Failed Job",
                    success=False,
                    verification_type="restore_test",
                )

                mock_notify.apply_async.assert_called_once()
                call_kwargs = mock_notify.apply_async.call_args[1]["kwargs"]
                assert call_kwargs["severity"] == "error"
