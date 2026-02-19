"""
Local Storage Provider Implementation
ローカルディスク用ストレージプロバイダー
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Callable, Optional

from app.storage.interfaces import (
    CopyResult,
    IStorageProvider,
    StorageInfo,
    StorageLocation,
    StorageType,
)


class LocalStorageProvider(IStorageProvider):
    """ローカルストレージプロバイダー"""

    def __init__(self, provider_id: str, base_path: str, location: StorageLocation = StorageLocation.ONSITE):
        """
        Args:
            provider_id: プロバイダーID
            base_path: ベースパス
            location: ストレージ配置場所
        """
        self._provider_id = provider_id
        self.base_path = Path(base_path)
        self._location = location
        self._connected = False

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def storage_type(self) -> StorageType:
        return StorageType.LOCAL_DISK

    @property
    def storage_location(self) -> StorageLocation:
        return self._location

    @property
    def is_immutable(self) -> bool:
        return False  # ローカルディスクはイミュータブルではない

    def connect(self) -> bool:
        """ローカルストレージに接続"""
        try:
            # ベースパスの存在確認
            if not self.base_path.exists():
                self.base_path.mkdir(parents=True, exist_ok=True)

            self._connected = True
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to local storage: {e}")

    def disconnect(self) -> None:
        """切断（ローカルストレージでは何もしない）"""
        self._connected = False

    def copy_file(self, source: str, destination: str, callback: Optional[Callable] = None) -> CopyResult:
        """ファイルをコピー"""
        from datetime import datetime

        start_time = datetime.now()
        source_path = Path(source)
        dest_path = self.base_path / destination

        # 送信先ディレクトリ作成
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # チェックサム計算しながらコピー
        sha256_hash = hashlib.sha256()
        bytes_copied = 0
        source_size = source_path.stat().st_size

        try:
            with open(source_path, "rb") as src:
                with open(dest_path, "wb") as dst:
                    while True:
                        chunk = src.read(64 * 1024 * 1024)  # 64MB
                        if not chunk:
                            break
                        dst.write(chunk)
                        sha256_hash.update(chunk)
                        bytes_copied += len(chunk)

                        if callback:
                            callback(bytes_copied, source_size)

            duration = (datetime.now() - start_time).total_seconds()

            return CopyResult(
                success=True, bytes_copied=bytes_copied, checksum=sha256_hash.hexdigest(), duration_seconds=duration
            )

        except Exception as e:
            return CopyResult(success=False, bytes_copied=bytes_copied, checksum="", duration_seconds=0, error_message=str(e))

    def delete_file(self, path: str) -> bool:
        """ファイルを削除"""
        try:
            file_path = self.base_path / path
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False

    def get_available_space(self) -> int:
        """利用可能容量を取得（バイト）"""
        stat = os.statvfs(str(self.base_path))
        return stat.f_bavail * stat.f_frsize

    def get_storage_info(self) -> StorageInfo:
        """ストレージ情報を取得"""
        stat = os.statvfs(str(self.base_path))

        total = stat.f_blocks * stat.f_frsize
        available = stat.f_bavail * stat.f_frsize
        used = total - available
        usage_percent = (used / total * 100) if total > 0 else 0

        return StorageInfo(total_bytes=total, available_bytes=available, used_bytes=used, usage_percent=usage_percent)

    def verify_file(self, path: str, expected_checksum: str) -> bool:
        """ファイル整合性を検証"""
        file_path = self.base_path / path

        if not file_path.exists():
            return False

        actual_checksum = self._calculate_checksum(str(file_path))
        return actual_checksum == expected_checksum

    def list_files(self, path: str, pattern: str = "*") -> list:
        """ファイル一覧を取得"""
        dir_path = self.base_path / path

        if not dir_path.exists():
            return []

        return [str(f.relative_to(self.base_path)) for f in dir_path.glob(pattern)]

    def _calculate_checksum(self, file_path: str) -> str:
        """チェックサム計算"""
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(64 * 1024 * 1024)
                if not chunk:
                    break
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()
