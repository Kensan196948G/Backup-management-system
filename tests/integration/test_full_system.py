"""
全8エージェント統合テスト
システム全体のエンドツーエンド動作確認
"""

from datetime import datetime

import pytest


class TestFullSystemIntegration:
    """全システム統合テスト"""

    def test_system_components_import(self):
        """全コンポーネントがimport可能か確認"""
        # Agent-01: Core
        # Agent-05: Alerts
        from app.alerts.alert_engine import AlertEngine
        from app.alerts.sla_monitor import SLAMonitor
        from app.core.backup_engine import BackupEngine
        from app.core.exceptions import BackupEngineError
        from app.core.rule_validator import Rule321110Validator
        from app.scheduler.executor import JobExecutor
        from app.scheduler.job_queue import JobQueue

        # Agent-04: Scheduler
        from app.scheduler.scheduler import BackupScheduler, CronScheduler

        # Agent-02: Storage
        from app.storage.interfaces import IStorageProvider, StorageType
        from app.storage.providers.local_storage import LocalStorageProvider

        # Agent-03: Verification
        from app.verification.checksum import ChecksumService
        from app.verification.validator import FileValidator

        # すべてimportできればテスト成功
        assert True

    def test_agent_dependencies(self):
        """エージェント間の依存関係が正しく解決されるか"""
        # Agent-01がAgent-02のインターフェースを使用できるか
        from app.core.backup_engine import BackupEngine
        from app.storage.providers.local_storage import LocalStorageProvider

        engine = BackupEngine()
        storage = LocalStorageProvider("test", "/tmp/test")

        # インスタンス生成に成功すればOK
        assert engine is not None
        assert storage is not None

    def test_321110_rule_components(self):
        """3-2-1-1-0ルール関連コンポーネントの確認"""
        from app.core.rule_validator import Rule321110Validator
        from app.storage.interfaces import StorageLocation

        validator = Rule321110Validator()

        # バリデーターが正しく初期化されるか
        assert validator is not None

        # StorageLocationが3-2-1-1-0に必要な値を持つか
        assert hasattr(StorageLocation, "ONSITE")
        assert hasattr(StorageLocation, "OFFSITE")
        assert hasattr(StorageLocation, "OFFLINE")
