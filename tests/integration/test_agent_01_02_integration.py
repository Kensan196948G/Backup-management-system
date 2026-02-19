"""
Agent-01とAgent-02の統合テスト
Core Backup Engine と Storage Management の連携テスト
"""

import os
import tempfile
from pathlib import Path

import pytest

from app.core.backup_engine import BackupEngine
from app.core.rule_validator import Rule321110Validator
from app.storage.interfaces import StorageLocation, StorageType
from app.storage.providers.local_storage import LocalStorageProvider


class TestAgent0102Integration:
    """Agent-01とAgent-02の統合テスト"""

    @pytest.fixture
    def temp_dirs(self):
        """テスト用一時ディレクトリ"""
        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as backup_dir:
                yield source_dir, backup_dir

    @pytest.fixture
    def test_file(self, temp_dirs):
        """テスト用ファイル作成"""
        source_dir, _ = temp_dirs
        test_file = Path(source_dir) / "test_file.txt"
        test_file.write_text("This is a test file for backup integration testing.")
        return test_file

    def test_backup_with_local_storage_provider(self, temp_dirs, test_file):
        """LocalStorageProviderを使用したバックアップテスト"""
        source_dir, backup_dir = temp_dirs

        # Agent-02: LocalStorageProvider初期化
        storage = LocalStorageProvider(provider_id="test_local_storage", base_path=backup_dir, location=StorageLocation.ONSITE)

        # 接続
        assert storage.connect() is True

        # Agent-01: BackupEngine初期化
        engine = BackupEngine()

        # ファイルコピー実行
        result = engine.copy_file(str(test_file), "backup_copy.txt")

        # 検証
        assert result["bytes_copied"] > 0
        assert result["checksum"] != ""
        assert result["duration"] > 0

        # コピーされたファイルの存在確認
        backup_file = Path(backup_dir) / "backup_copy.txt"
        assert backup_file.exists()

        # 内容の一致確認
        assert backup_file.read_text() == test_file.read_text()

    def test_copy_verification(self, temp_dirs, test_file):
        """コピー検証機能のテスト"""
        source_dir, backup_dir = temp_dirs

        # バックアップエンジン
        engine = BackupEngine()

        # コピー実行
        backup_path = Path(backup_dir) / "verified_copy.txt"
        engine.copy_file(str(test_file), str(backup_path))

        # 検証実行
        assert engine.verify_copy(str(test_file), str(backup_path)) is True

    def test_storage_capacity_check(self, temp_dirs):
        """ストレージ容量チェックのテスト"""
        _, backup_dir = temp_dirs

        # LocalStorageProvider
        storage = LocalStorageProvider(provider_id="capacity_test", base_path=backup_dir)
        storage.connect()

        # 容量情報取得
        available = storage.get_available_space()
        assert available > 0

        # 詳細情報取得
        info = storage.get_storage_info()
        assert info.total_bytes > 0
        assert info.available_bytes > 0
        assert 0 <= info.usage_percent <= 100

    def test_storage_type_location_properties(self):
        """ストレージタイプとロケーションのプロパティテスト"""
        storage = LocalStorageProvider(provider_id="prop_test", base_path="/tmp/test", location=StorageLocation.ONSITE)

        # プロパティ確認
        assert storage.storage_type == StorageType.LOCAL_DISK
        assert storage.storage_location == StorageLocation.ONSITE
        assert storage.is_immutable is False
        assert storage.is_online() is True

    def test_321110_rule_validation_integration(self):
        """3-2-1-1-0ルール検証の統合テスト（モック使用）"""
        # このテストは実際のBackupJobとBackupExecutionが必要
        # 現時点ではスケルトンとして定義

        validator = Rule321110Validator()

        # モックデータを使用した検証
        # 実装は次のフェーズで追加
        pass


class TestEndToEndWorkflow:
    """エンドツーエンドワークフローテスト"""

    def test_complete_backup_workflow(self):
        """完全なバックアップワークフロー

        1. Agent-01: BackupEngineでバックアップ実行
        2. Agent-02: LocalStorageProviderに保存
        3. Agent-01: チェックサムで検証
        4. Agent-03: FileValidatorで整合性チェック（次フェーズ）
        """
        # 次のフェーズで実装
        pass

    def test_multi_storage_backup(self):
        """複数ストレージへのバックアップ（3-2-1-1-0の「2」をテスト）"""
        # 次のフェーズで実装
        pass

    def test_offsite_offline_backup(self):
        """オフサイト・オフラインバックアップ（3-2-1-1-0の「1-1」をテスト）"""
        # 次のフェーズで実装
        pass
