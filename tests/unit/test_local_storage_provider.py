"""
Unit tests for app/storage/providers/local_storage.py
LocalStorageProvider: connect, copy_file, delete_file, verify_file, list_files.
"""

import hashlib
import os
import tempfile
from pathlib import Path

import pytest


class TestLocalStorageProviderInit:
    """Tests for LocalStorageProvider initialization"""

    def test_default_location(self):
        from app.storage.providers.local_storage import LocalStorageProvider
        from app.storage.interfaces import StorageLocation

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("test_id", tmpdir)
            assert provider.provider_id == "test_id"
            assert provider.storage_location == StorageLocation.ONSITE

    def test_custom_location(self):
        from app.storage.providers.local_storage import LocalStorageProvider
        from app.storage.interfaces import StorageLocation

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir, location=StorageLocation.OFFSITE)
            assert provider.storage_location == StorageLocation.OFFSITE

    def test_storage_type_is_local_disk(self):
        from app.storage.providers.local_storage import LocalStorageProvider
        from app.storage.interfaces import StorageType

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            assert provider.storage_type == StorageType.LOCAL_DISK

    def test_is_not_immutable(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            assert provider.is_immutable is False

    def test_is_online(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            assert provider.is_online() is True

    def test_supports_immutable_false(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            assert provider.supports_immutable() is False


class TestLocalStorageProviderConnect:
    """Tests for connect() and disconnect()"""

    def test_connect_existing_dir(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            result = provider.connect()
            assert result is True

    def test_connect_creates_missing_dir(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = os.path.join(tmpdir, "new_subdir", "nested")
            provider = LocalStorageProvider("p1", new_path)
            result = provider.connect()
            assert result is True
            assert os.path.exists(new_path)

    def test_disconnect_sets_connected_false(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            provider.connect()
            provider.disconnect()
            assert provider._connected is False


class TestLocalStorageProviderCopyFile:
    """Tests for copy_file()"""

    def test_copy_small_file(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as srcdir:
            with tempfile.TemporaryDirectory() as destdir:
                # Create source file
                src_file = os.path.join(srcdir, "test.bak")
                content = b"Hello backup world!"
                with open(src_file, "wb") as f:
                    f.write(content)

                provider = LocalStorageProvider("p1", destdir)
                result = provider.copy_file(src_file, "test.bak")

                assert result.success is True
                assert result.bytes_copied == len(content)
                assert result.checksum == hashlib.sha256(content).hexdigest()
                assert result.duration_seconds >= 0

    def test_copy_creates_destination_directories(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as srcdir:
            with tempfile.TemporaryDirectory() as destdir:
                src_file = os.path.join(srcdir, "file.bak")
                with open(src_file, "wb") as f:
                    f.write(b"data")

                provider = LocalStorageProvider("p1", destdir)
                result = provider.copy_file(src_file, "subdir/nested/file.bak")

                assert result.success is True
                assert os.path.exists(os.path.join(destdir, "subdir", "nested", "file.bak"))

    def test_copy_with_progress_callback(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        progress_calls = []

        def callback(bytes_done, total):
            progress_calls.append((bytes_done, total))

        with tempfile.TemporaryDirectory() as srcdir:
            with tempfile.TemporaryDirectory() as destdir:
                src_file = os.path.join(srcdir, "file.bak")
                content = b"callback test content " * 100
                with open(src_file, "wb") as f:
                    f.write(content)

                provider = LocalStorageProvider("p1", destdir)
                result = provider.copy_file(src_file, "file.bak", callback=callback)

                assert result.success is True
                assert len(progress_calls) > 0
                last_bytes, total = progress_calls[-1]
                assert last_bytes == len(content)

    def test_copy_nonexistent_source_raises(self):
        from app.storage.providers.local_storage import LocalStorageProvider
        import pytest

        with tempfile.TemporaryDirectory() as destdir:
            provider = LocalStorageProvider("p1", destdir)
            # stat() is called before try-except, so FileNotFoundError propagates
            with pytest.raises((FileNotFoundError, OSError)):
                provider.copy_file("/nonexistent/file.bak", "dest.bak")


class TestLocalStorageProviderDeleteFile:
    """Tests for delete_file()"""

    def test_delete_existing_file(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file
            test_file = os.path.join(tmpdir, "to_delete.bak")
            with open(test_file, "wb") as f:
                f.write(b"data")

            provider = LocalStorageProvider("p1", tmpdir)
            result = provider.delete_file("to_delete.bak")

            assert result is True
            assert not os.path.exists(test_file)

    def test_delete_nonexistent_file_returns_false(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            result = provider.delete_file("nonexistent.bak")
            assert result is False


class TestLocalStorageProviderStorageInfo:
    """Tests for get_available_space() and get_storage_info()"""

    def test_get_available_space_returns_positive(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            provider.connect()
            space = provider.get_available_space()
            assert space > 0

    def test_get_storage_info_structure(self):
        from app.storage.providers.local_storage import LocalStorageProvider
        from app.storage.interfaces import StorageInfo

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            provider.connect()
            info = provider.get_storage_info()

            assert isinstance(info, StorageInfo)
            assert info.total_bytes > 0
            assert info.available_bytes >= 0
            assert 0 <= info.usage_percent <= 100

    def test_storage_info_consistency(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            provider.connect()
            info = provider.get_storage_info()

            assert info.total_bytes == info.used_bytes + info.available_bytes


class TestLocalStorageProviderVerifyFile:
    """Tests for verify_file()"""

    def test_verify_correct_checksum(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            content = b"Verification content"
            test_file = os.path.join(tmpdir, "verify.bak")
            with open(test_file, "wb") as f:
                f.write(content)

            expected = hashlib.sha256(content).hexdigest()
            provider = LocalStorageProvider("p1", tmpdir)
            result = provider.verify_file("verify.bak", expected)
            assert result is True

    def test_verify_wrong_checksum(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            content = b"Verification content"
            test_file = os.path.join(tmpdir, "verify.bak")
            with open(test_file, "wb") as f:
                f.write(content)

            provider = LocalStorageProvider("p1", tmpdir)
            result = provider.verify_file("verify.bak", "wrong_checksum_value")
            assert result is False

    def test_verify_nonexistent_file(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            result = provider.verify_file("nonexistent.bak", "any_checksum")
            assert result is False


class TestLocalStorageProviderListFiles:
    """Tests for list_files()"""

    def test_list_existing_files(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in a subdirectory
            subdir = os.path.join(tmpdir, "backups")
            os.makedirs(subdir)
            for name in ["a.bak", "b.bak", "c.bak"]:
                with open(os.path.join(subdir, name), "wb") as f:
                    f.write(b"data")

            provider = LocalStorageProvider("p1", tmpdir)
            files = provider.list_files("backups")

            assert len(files) == 3

    def test_list_with_pattern(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "backups")
            os.makedirs(subdir)
            for name in ["file.bak", "file.log", "other.bak"]:
                with open(os.path.join(subdir, name), "wb") as f:
                    f.write(b"data")

            provider = LocalStorageProvider("p1", tmpdir)
            files = provider.list_files("backups", pattern="*.bak")

            assert len(files) == 2
            for f in files:
                assert f.endswith(".bak")

    def test_list_nonexistent_dir_returns_empty(self):
        from app.storage.providers.local_storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider("p1", tmpdir)
            files = provider.list_files("nonexistent_dir")
            assert files == []
