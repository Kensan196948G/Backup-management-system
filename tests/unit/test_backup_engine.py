"""
Unit tests for app/core/backup_engine.py
BackupEngine: copy_file, verify_copy, _calculate_checksum, get_backup_stats.
"""

import hashlib
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call


class TestBackupEngineInit:
    """Tests for BackupEngine initialization"""

    def test_default_config(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()
            assert engine.buffer_size == 64 * 1024 * 1024  # 64MB
            assert engine.max_retries == 3
            assert len(engine.retry_intervals) == 3

    def test_accepts_dependencies(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            mock_session = MagicMock()
            mock_storage = MagicMock()
            mock_verify = MagicMock()
            engine = BackupEngine(
                db_session=mock_session,
                storage_registry=mock_storage,
                verification_service=mock_verify,
            )
            assert engine.db is mock_session
            assert engine.storage_registry is mock_storage
            assert engine.verification_service is mock_verify


class TestBackupEngineGetStats:
    """Tests for get_backup_stats()"""

    def test_stats_structure(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()
            stats = engine.get_backup_stats()

            assert "buffer_size" in stats
            assert "max_retries" in stats
            assert "retry_intervals" in stats
            assert "agent" in stats
            assert "version" in stats

    def test_stats_values_match_config(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()
            stats = engine.get_backup_stats()

            assert stats["buffer_size"] == engine.buffer_size
            assert stats["max_retries"] == engine.max_retries
            assert stats["retry_intervals"] == engine.retry_intervals


class TestCalculateChecksum:
    """Tests for _calculate_checksum()"""

    def test_sha256_checksum(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as f:
                f.write(b"Hello, backup world!")
                tmpfile = f.name

            try:
                result = engine._calculate_checksum(tmpfile)
                # Verify manually
                expected = hashlib.sha256(b"Hello, backup world!").hexdigest()
                assert result == expected
            finally:
                os.unlink(tmpfile)

    def test_sha512_checksum(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as f:
                f.write(b"Test data for sha512")
                tmpfile = f.name

            try:
                result = engine._calculate_checksum(tmpfile, algorithm="sha512")
                expected = hashlib.sha512(b"Test data for sha512").hexdigest()
                assert result == expected
            finally:
                os.unlink(tmpfile)

    def test_empty_file_checksum(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()

            with tempfile.NamedTemporaryFile(delete=False) as f:
                tmpfile = f.name  # empty file

            try:
                result = engine._calculate_checksum(tmpfile)
                expected = hashlib.sha256(b"").hexdigest()
                assert result == expected
            finally:
                os.unlink(tmpfile)

    def test_md5_checksum(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as f:
                f.write(b"md5 test content")
                tmpfile = f.name

            try:
                result = engine._calculate_checksum(tmpfile, algorithm="md5")
                expected = hashlib.md5(b"md5 test content").hexdigest()
                assert result == expected
            finally:
                os.unlink(tmpfile)


class TestVerifyCopy:
    """Tests for verify_copy()"""

    def test_identical_files_pass(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()

            content = b"Backup content to verify " * 100

            with tempfile.NamedTemporaryFile(delete=False) as orig:
                orig.write(content)
                orig_path = orig.name

            with tempfile.NamedTemporaryFile(delete=False) as copy:
                copy.write(content)
                copy_path = copy.name

            try:
                result = engine.verify_copy(orig_path, copy_path)
                assert result is True
            finally:
                os.unlink(orig_path)
                os.unlink(copy_path)

    def test_different_content_raises(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            from app.core.exceptions import VerificationFailedError
            engine = BackupEngine()

            with tempfile.NamedTemporaryFile(delete=False) as orig:
                orig.write(b"original content")
                orig_path = orig.name

            with tempfile.NamedTemporaryFile(delete=False) as copy:
                copy.write(b"different content")
                copy_path = copy.name

            try:
                with pytest.raises(VerificationFailedError):
                    engine.verify_copy(orig_path, copy_path)
            finally:
                os.unlink(orig_path)
                os.unlink(copy_path)

    def test_missing_original_raises(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            from app.core.exceptions import VerificationFailedError
            engine = BackupEngine()

            with tempfile.NamedTemporaryFile(delete=False) as copy:
                copy_path = copy.name

            try:
                with pytest.raises(VerificationFailedError):
                    engine.verify_copy("/nonexistent/original.bak", copy_path)
            finally:
                os.unlink(copy_path)

    def test_missing_copy_raises(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            from app.core.exceptions import VerificationFailedError
            engine = BackupEngine()

            with tempfile.NamedTemporaryFile(delete=False) as orig:
                orig.write(b"content")
                orig_path = orig.name

            try:
                with pytest.raises(VerificationFailedError):
                    engine.verify_copy(orig_path, "/nonexistent/copy.bak")
            finally:
                os.unlink(orig_path)

    def test_size_mismatch_raises(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            from app.core.exceptions import VerificationFailedError
            engine = BackupEngine()

            with tempfile.NamedTemporaryFile(delete=False) as orig:
                orig.write(b"longer original content")
                orig_path = orig.name

            with tempfile.NamedTemporaryFile(delete=False) as copy:
                copy.write(b"short")
                copy_path = copy.name

            try:
                with pytest.raises(VerificationFailedError):
                    engine.verify_copy(orig_path, copy_path)
            finally:
                os.unlink(orig_path)
                os.unlink(copy_path)


class TestCopyFile:
    """Tests for copy_file()"""

    def test_copy_small_file(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()

            content = b"Small backup file content"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bak") as src:
                src.write(content)
                src_path = src.name

            with tempfile.TemporaryDirectory() as tmpdir:
                dest_path = os.path.join(tmpdir, "backup_copy.bak")
                try:
                    result = engine.copy_file(src_path, dest_path)

                    assert result["bytes_copied"] == len(content)
                    assert "checksum" in result
                    assert "duration" in result

                    # Verify file was actually copied
                    assert os.path.exists(dest_path)
                    assert open(dest_path, "rb").read() == content
                finally:
                    os.unlink(src_path)

    def test_copy_nonexistent_source_raises(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            from app.core.exceptions import CopyOperationError
            engine = BackupEngine()

            with tempfile.TemporaryDirectory() as tmpdir:
                dest_path = os.path.join(tmpdir, "copy.bak")
                with pytest.raises(CopyOperationError):
                    engine.copy_file("/nonexistent/source.bak", dest_path)

    def test_progress_callback_called(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()

            content = b"Progress test content " * 100
            with tempfile.NamedTemporaryFile(delete=False) as src:
                src.write(content)
                src_path = src.name

            progress_calls = []

            def progress_callback(bytes_copied, total):
                progress_calls.append((bytes_copied, total))

            with tempfile.TemporaryDirectory() as tmpdir:
                dest_path = os.path.join(tmpdir, "progress.bak")
                try:
                    engine.copy_file(src_path, dest_path, progress_callback=progress_callback)
                    assert len(progress_calls) > 0
                    # Final call should have full content
                    final_bytes, total_bytes = progress_calls[-1]
                    assert final_bytes == len(content)
                finally:
                    os.unlink(src_path)

    def test_checksum_matches_content(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            engine = BackupEngine()

            content = b"Checksum verification content"
            with tempfile.NamedTemporaryFile(delete=False) as src:
                src.write(content)
                src_path = src.name

            with tempfile.TemporaryDirectory() as tmpdir:
                dest_path = os.path.join(tmpdir, "checksum.bak")
                try:
                    result = engine.copy_file(src_path, dest_path)
                    expected_checksum = hashlib.sha256(content).hexdigest()
                    assert result["checksum"] == expected_checksum
                finally:
                    os.unlink(src_path)


class TestExecuteBackup:
    """Tests for execute_backup()"""

    def test_nonexistent_job_raises(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            from app.core.exceptions import BackupEngineError

            with patch("app.models.db") as mock_db:
                mock_db.session.get.return_value = None

                engine = BackupEngine()
                with pytest.raises(BackupEngineError):
                    engine.execute_backup(99999)

    def test_nonexistent_source_path_raises(self, app):
        with app.app_context():
            from app.core.backup_engine import BackupEngine
            from app.core.exceptions import BackupEngineError

            mock_job = MagicMock()
            mock_job.source_path = "/nonexistent/source/path"
            mock_job.destination_paths = ""

            with patch("app.models.db") as mock_db:
                mock_db.session.get.return_value = mock_job

                engine = BackupEngine()
                with pytest.raises(BackupEngineError):
                    engine.execute_backup(1)
