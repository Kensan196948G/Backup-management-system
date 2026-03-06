"""
FileValidator ユニットテスト

app/verification/validator.py のカバレッジ向上テスト
"""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.verification.interfaces import ChecksumAlgorithm, VerificationStatus
from app.verification.validator import FileValidator


class TestFileValidator:
    """FileValidator の基本動作テスト"""

    @pytest.fixture
    def validator(self):
        return FileValidator()

    @pytest.fixture
    def temp_dir(self):
        """テスト用一時ディレクトリ"""
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d, ignore_errors=True)

    @pytest.fixture
    def matching_files(self, temp_dir):
        """同一コンテンツのソース・ターゲットファイル"""
        content = b"Test content for file validation"
        source = temp_dir / "source.txt"
        target = temp_dir / "target.txt"
        source.write_bytes(content)
        target.write_bytes(content)
        return source, target

    def test_default_initialization(self, validator):
        """デフォルト初期化の確認"""
        assert validator.verify_metadata_default is True
        assert validator.verify_permissions is False
        assert validator.validation_stats["total_validations"] == 0

    def test_custom_initialization(self):
        """カスタム初期化の確認"""
        v = FileValidator(verify_metadata=False, verify_permissions=True)
        assert v.verify_metadata_default is False
        assert v.verify_permissions is True

    def test_calculate_checksum_delegates(self, validator, matching_files):
        """calculate_checksum がChecksumServiceに委譲する"""
        source, _ = matching_files
        checksum = validator.calculate_checksum(source)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256

    def test_verify_file_success(self, validator, matching_files):
        """同一ファイルの検証が成功する"""
        source, target = matching_files
        status, details = validator.verify_file(source, target)
        assert status == VerificationStatus.SUCCESS
        assert "source_checksum" in details
        assert "target_checksum" in details

    def test_verify_file_source_not_found(self, validator, temp_dir):
        """ソースファイルが存在しない場合"""
        nonexistent = temp_dir / "nonexistent.txt"
        target = temp_dir / "target.txt"
        target.write_bytes(b"content")
        status, details = validator.verify_file(nonexistent, target)
        assert status == VerificationStatus.FILE_NOT_FOUND
        assert "Source file not found" in details.get("error", "")

    def test_verify_file_target_not_found(self, validator, temp_dir):
        """ターゲットファイルが存在しない場合"""
        source = temp_dir / "source.txt"
        source.write_bytes(b"content")
        nonexistent = temp_dir / "nonexistent.txt"
        status, details = validator.verify_file(source, nonexistent)
        assert status == VerificationStatus.FILE_NOT_FOUND
        assert "Target file not found" in details.get("error", "")

    def test_verify_file_size_mismatch(self, validator, temp_dir):
        """サイズが異なる場合"""
        source = temp_dir / "source.txt"
        target = temp_dir / "target.txt"
        source.write_bytes(b"Short content")
        target.write_bytes(b"Longer content than source")
        status, details = validator.verify_file(source, target)
        assert status == VerificationStatus.SIZE_MISMATCH

    def test_verify_file_checksum_mismatch(self, validator, temp_dir):
        """サイズは同じだがチェックサムが異なる場合"""
        source = temp_dir / "source.txt"
        target = temp_dir / "target.txt"
        source.write_bytes(b"Content A!!!")  # 同じ長さ
        target.write_bytes(b"Content B!!!")  # 同じ長さ、異なる内容
        status, details = validator.verify_file(source, target)
        assert status == VerificationStatus.CHECKSUM_MISMATCH

    def test_verify_file_updates_stats(self, validator, matching_files):
        """検証後に統計が更新される"""
        source, target = matching_files
        initial_count = validator.validation_stats["total_validations"]
        validator.verify_file(source, target)
        assert validator.validation_stats["total_validations"] == initial_count + 1
        assert validator.validation_stats["successful"] == 1

    def test_verify_file_with_sha512(self, validator, matching_files):
        """SHA512アルゴリズムでの検証"""
        source, target = matching_files
        status, details = validator.verify_file(source, target, ChecksumAlgorithm.SHA512)
        assert status == VerificationStatus.SUCCESS
        assert details["algorithm"] == "sha512"

    def test_verify_file_no_metadata(self, temp_dir):
        """メタデータ検証なしの設定"""
        validator = FileValidator(verify_metadata=False)
        content = b"Test content"
        source = temp_dir / "source.txt"
        target = temp_dir / "target.txt"
        source.write_bytes(content)
        target.write_bytes(content)
        status, details = validator.verify_file(source, target)
        assert status == VerificationStatus.SUCCESS
        assert "metadata" not in details

    def test_verify_backup_success(self, validator, temp_dir):
        """バックアップ全体の検証成功"""
        sources = []
        targets = []
        for i in range(3):
            content = f"File content {i}".encode()
            s = temp_dir / f"source_{i}.txt"
            t = temp_dir / f"target_{i}.txt"
            s.write_bytes(content)
            t.write_bytes(content)
            sources.append(s)
            targets.append(t)

        result = validator.verify_backup(sources, targets)
        assert result["total_files"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0
        assert result["success_rate"] == 100.0

    def test_verify_backup_count_mismatch(self, validator, temp_dir):
        """ソース・ターゲットファイル数が異なる場合はValueError"""
        source = temp_dir / "source.txt"
        source.write_bytes(b"content")
        with pytest.raises(ValueError):
            validator.verify_backup([source], [])

    def test_verify_backup_with_failures(self, validator, temp_dir):
        """一部失敗のバックアップ検証"""
        s1 = temp_dir / "s1.txt"
        t1 = temp_dir / "t1.txt"
        s2 = temp_dir / "s2.txt"
        t2 = temp_dir / "t2_diff.txt"
        s1.write_bytes(b"same content")
        t1.write_bytes(b"same content")
        s2.write_bytes(b"Content A!")
        t2.write_bytes(b"Content B!")
        result = validator.verify_backup([s1, s2], [t1, t2])
        assert result["total_files"] == 2
        assert result["successful"] == 1

    def test_verify_metadata_success(self, validator, temp_dir):
        """メタデータ検証成功"""
        content = b"Test metadata"
        source = temp_dir / "source.txt"
        target = temp_dir / "target.txt"
        source.write_bytes(content)
        target.write_bytes(content)
        # ファイルのmtimeをほぼ同じにする
        import os
        mtime = source.stat().st_mtime
        os.utime(str(target), (mtime, mtime))
        status, details = validator.verify_metadata(source, target)
        assert status == VerificationStatus.SUCCESS

    def test_verify_metadata_size_mismatch(self, validator, temp_dir):
        """メタデータ検証でサイズ不一致"""
        source = temp_dir / "source.txt"
        target = temp_dir / "target.txt"
        source.write_bytes(b"short")
        target.write_bytes(b"longer content here")
        status, details = validator.verify_metadata(source, target)
        assert status == VerificationStatus.SIZE_MISMATCH

    def test_verify_metadata_with_permissions(self, temp_dir):
        """パーミッション検証が有効な場合"""
        validator = FileValidator(verify_permissions=True)
        content = b"Test permissions"
        source = temp_dir / "source.txt"
        target = temp_dir / "target.txt"
        source.write_bytes(content)
        target.write_bytes(content)
        import os
        mtime = source.stat().st_mtime
        os.utime(str(target), (mtime, mtime))
        status, details = validator.verify_metadata(source, target)
        assert status == VerificationStatus.SUCCESS
        assert "source_permissions" in details

    def test_detect_corruption_not_corrupted(self, validator, temp_dir):
        """正常ファイルの破損チェック"""
        f = temp_dir / "file.txt"
        f.write_bytes(b"Normal content")
        expected = validator.calculate_checksum(f)
        result = validator.detect_corruption(f, expected)
        assert result is False

    def test_detect_corruption_corrupted(self, validator, temp_dir):
        """破損ファイルの検出"""
        f = temp_dir / "file.txt"
        f.write_bytes(b"Normal content")
        wrong_checksum = "a" * 64  # 間違ったチェックサム
        result = validator.detect_corruption(f, wrong_checksum)
        assert result is True

    def test_detect_corruption_file_not_found(self, validator, temp_dir):
        """存在しないファイルは破損とみなす"""
        nonexistent = temp_dir / "nonexistent.txt"
        result = validator.detect_corruption(nonexistent, "abc123")
        assert result is True

    def test_detect_corruption_case_insensitive(self, validator, temp_dir):
        """大文字小文字を区別しないチェックサム比較"""
        f = temp_dir / "file.txt"
        f.write_bytes(b"Content")
        expected = validator.calculate_checksum(f).upper()
        result = validator.detect_corruption(f, expected)
        assert result is False

    def test_calculate_checksums_parallel_delegates(self, validator, temp_dir):
        """calculate_checksums_parallel が委譲する"""
        files = []
        for i in range(2):
            f = temp_dir / f"file_{i}.txt"
            f.write_bytes(f"Content {i}".encode())
            files.append(f)
        result = validator.calculate_checksums_parallel(files)
        assert len(result) == 2

    def test_validation_stats_tracking(self, validator, temp_dir):
        """検証統計の追跡"""
        # 成功するケース
        content = b"content"
        s = temp_dir / "s.txt"
        t = temp_dir / "t.txt"
        s.write_bytes(content)
        t.write_bytes(content)
        validator.verify_file(s, t)
        assert validator.validation_stats["successful"] == 1
        assert validator.validation_stats["last_validation"] is not None

        # 失敗するケース
        s2 = temp_dir / "s2.txt"
        t2 = temp_dir / "t2.txt"
        s2.write_bytes(b"AAA!!")
        t2.write_bytes(b"BBB!!")
        validator.verify_file(s2, t2)
        assert validator.validation_stats["failed"] >= 1
