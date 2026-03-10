"""
Unit tests for app/storage/interfaces.py
StorageType, StorageLocation, CopyResult, StorageInfo, IStorageProvider.
"""

import pytest
from unittest.mock import MagicMock


class TestStorageType:
    """Tests for StorageType enum"""

    def test_all_values_exist(self):
        from app.storage.interfaces import StorageType
        assert StorageType.LOCAL_DISK.value == "local_disk"
        assert StorageType.NAS_SMB.value == "nas_smb"
        assert StorageType.NAS_NFS.value == "nas_nfs"
        assert StorageType.CLOUD_S3.value == "cloud_s3"
        assert StorageType.CLOUD_AZURE.value == "cloud_azure"
        assert StorageType.CLOUD_GCP.value == "cloud_gcp"
        assert StorageType.TAPE.value == "tape"
        assert StorageType.IMMUTABLE.value == "immutable"
        assert StorageType.USB_EXTERNAL.value == "usb_external"

    def test_nine_types_defined(self):
        from app.storage.interfaces import StorageType
        assert len(StorageType) == 9

    def test_enum_comparison(self):
        from app.storage.interfaces import StorageType
        assert StorageType.LOCAL_DISK == StorageType.LOCAL_DISK
        assert StorageType.LOCAL_DISK != StorageType.NAS_SMB


class TestStorageLocation:
    """Tests for StorageLocation enum"""

    def test_all_values_exist(self):
        from app.storage.interfaces import StorageLocation
        assert StorageLocation.ONSITE.value == "onsite"
        assert StorageLocation.OFFSITE.value == "offsite"
        assert StorageLocation.OFFLINE.value == "offline"
        assert StorageLocation.CLOUD.value == "cloud"

    def test_four_locations_defined(self):
        from app.storage.interfaces import StorageLocation
        assert len(StorageLocation) == 4

    def test_offline_is_not_online(self):
        from app.storage.interfaces import StorageLocation
        assert StorageLocation.OFFLINE != StorageLocation.ONSITE

    def test_enum_identity(self):
        from app.storage.interfaces import StorageLocation
        assert StorageLocation.CLOUD is StorageLocation.CLOUD


class TestCopyResult:
    """Tests for CopyResult dataclass"""

    def test_success_result(self):
        from app.storage.interfaces import CopyResult
        result = CopyResult(
            success=True,
            bytes_copied=1024,
            checksum="abc123",
            duration_seconds=0.5,
        )
        assert result.success is True
        assert result.bytes_copied == 1024
        assert result.checksum == "abc123"
        assert result.duration_seconds == 0.5
        assert result.error_message is None  # default

    def test_failure_result_with_error(self):
        from app.storage.interfaces import CopyResult
        result = CopyResult(
            success=False,
            bytes_copied=0,
            checksum="",
            duration_seconds=0.1,
            error_message="Disk full",
        )
        assert result.success is False
        assert result.error_message == "Disk full"

    def test_default_error_message_is_none(self):
        from app.storage.interfaces import CopyResult
        result = CopyResult(
            success=True,
            bytes_copied=512,
            checksum="deadbeef",
            duration_seconds=0.01,
        )
        assert result.error_message is None

    def test_zero_bytes_copy(self):
        from app.storage.interfaces import CopyResult
        result = CopyResult(
            success=True,
            bytes_copied=0,
            checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            duration_seconds=0.001,
        )
        assert result.bytes_copied == 0


class TestStorageInfo:
    """Tests for StorageInfo dataclass"""

    def test_basic_storage_info(self):
        from app.storage.interfaces import StorageInfo
        info = StorageInfo(
            total_bytes=1_000_000_000,
            available_bytes=500_000_000,
            used_bytes=500_000_000,
            usage_percent=50.0,
        )
        assert info.total_bytes == 1_000_000_000
        assert info.available_bytes == 500_000_000
        assert info.used_bytes == 500_000_000
        assert info.usage_percent == 50.0

    def test_full_storage(self):
        from app.storage.interfaces import StorageInfo
        total = 1_000_000_000
        info = StorageInfo(
            total_bytes=total,
            available_bytes=0,
            used_bytes=total,
            usage_percent=100.0,
        )
        assert info.usage_percent == 100.0
        assert info.available_bytes == 0

    def test_empty_storage(self):
        from app.storage.interfaces import StorageInfo
        total = 500_000_000
        info = StorageInfo(
            total_bytes=total,
            available_bytes=total,
            used_bytes=0,
            usage_percent=0.0,
        )
        assert info.usage_percent == 0.0
        assert info.used_bytes == 0


class TestIStorageProviderConcreteMethodsIsOnline:
    """Tests for IStorageProvider.is_online() concrete method"""

    def _make_provider(self, location):
        """Create a minimal concrete implementation for testing"""
        from app.storage.interfaces import IStorageProvider, StorageType, StorageInfo, CopyResult

        class ConcreteProvider(IStorageProvider):
            @property
            def storage_type(self):
                return StorageType.LOCAL_DISK

            @property
            def storage_location(self):
                return location

            @property
            def is_immutable(self):
                return False

            @property
            def provider_id(self):
                return "test_provider"

            def connect(self):
                return True

            def disconnect(self):
                pass

            def copy_file(self, source, destination, callback=None):
                return CopyResult(True, 0, "", 0.0)

            def delete_file(self, path):
                return True

            def get_available_space(self):
                return 1000

            def get_storage_info(self):
                return StorageInfo(1000, 1000, 0, 0.0)

            def verify_file(self, path, expected_checksum):
                return True

            def list_files(self, path, pattern="*"):
                return []

        return ConcreteProvider()

    def test_onsite_is_online(self):
        from app.storage.interfaces import StorageLocation
        provider = self._make_provider(StorageLocation.ONSITE)
        assert provider.is_online() is True

    def test_offsite_is_online(self):
        from app.storage.interfaces import StorageLocation
        provider = self._make_provider(StorageLocation.OFFSITE)
        assert provider.is_online() is True

    def test_cloud_is_online(self):
        from app.storage.interfaces import StorageLocation
        provider = self._make_provider(StorageLocation.CLOUD)
        assert provider.is_online() is True

    def test_offline_is_not_online(self):
        from app.storage.interfaces import StorageLocation
        provider = self._make_provider(StorageLocation.OFFLINE)
        assert provider.is_online() is False


class TestIStorageProviderConcreteMethodsSupportsImmutable:
    """Tests for IStorageProvider.supports_immutable() concrete method"""

    def _make_provider(self, immutable_flag):
        from app.storage.interfaces import IStorageProvider, StorageType, StorageLocation, StorageInfo, CopyResult

        class ConcreteProvider(IStorageProvider):
            @property
            def storage_type(self):
                return StorageType.LOCAL_DISK

            @property
            def storage_location(self):
                return StorageLocation.ONSITE

            @property
            def is_immutable(self):
                return immutable_flag

            @property
            def provider_id(self):
                return "test_provider"

            def connect(self):
                return True

            def disconnect(self):
                pass

            def copy_file(self, source, destination, callback=None):
                return CopyResult(True, 0, "", 0.0)

            def delete_file(self, path):
                return True

            def get_available_space(self):
                return 1000

            def get_storage_info(self):
                return StorageInfo(1000, 1000, 0, 0.0)

            def verify_file(self, path, expected_checksum):
                return True

            def list_files(self, path, pattern="*"):
                return []

        return ConcreteProvider()

    def test_immutable_supports_immutable(self):
        provider = self._make_provider(True)
        assert provider.supports_immutable() is True

    def test_non_immutable_does_not_support(self):
        provider = self._make_provider(False)
        assert provider.supports_immutable() is False

    def test_supports_immutable_delegates_to_is_immutable(self):
        """supports_immutable() should return exactly is_immutable"""
        provider_true = self._make_provider(True)
        provider_false = self._make_provider(False)
        assert provider_true.supports_immutable() == provider_true.is_immutable
        assert provider_false.supports_immutable() == provider_false.is_immutable
