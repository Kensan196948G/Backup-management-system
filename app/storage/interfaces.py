"""
Storage Provider Interfaces
ISO 27001 A.12.3準拠のストレージプロバイダーインターフェース
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional


class StorageType(Enum):
    """ストレージタイプ定義（3-2-1-1-0ルールの「2」に対応）"""

    LOCAL_DISK = "local_disk"
    NAS_SMB = "nas_smb"
    NAS_NFS = "nas_nfs"
    CLOUD_S3 = "cloud_s3"
    CLOUD_AZURE = "cloud_azure"
    CLOUD_GCP = "cloud_gcp"
    TAPE = "tape"
    IMMUTABLE = "immutable"
    USB_EXTERNAL = "usb_external"


class StorageLocation(Enum):
    """ストレージ配置場所（3-2-1-1-0ルールの「1（オフサイト）」に対応）"""

    ONSITE = "onsite"  # オンサイト（本番と同じ場所）
    OFFSITE = "offsite"  # オフサイト（別の物理的場所）
    OFFLINE = "offline"  # オフライン（常時接続されていない）
    CLOUD = "cloud"  # クラウド（クラウドプロバイダーのデータセンター）


@dataclass
class CopyResult:
    """コピー操作の結果"""

    success: bool
    bytes_copied: int
    checksum: str
    duration_seconds: float
    error_message: Optional[str] = None


@dataclass
class StorageInfo:
    """ストレージ情報"""

    total_bytes: int
    available_bytes: int
    used_bytes: int
    usage_percent: float


class IStorageProvider(ABC):
    """
    ストレージプロバイダーインターフェース

    すべてのストレージタイプ（ローカル、NAS、クラウド、テープ等）に
    統一されたインターフェースを提供する。
    """

    @property
    @abstractmethod
    def storage_type(self) -> StorageType:
        """ストレージタイプを取得"""
        pass

    @property
    @abstractmethod
    def storage_location(self) -> StorageLocation:
        """ストレージ配置場所を取得"""
        pass

    @property
    @abstractmethod
    def is_immutable(self) -> bool:
        """イミュータブルストレージか（3-2-1-1-0の「1（オフライン）」）"""
        pass

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """プロバイダーID（一意識別子）"""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """
        ストレージに接続

        Returns:
            接続成功ならTrue

        Raises:
            ConnectionError: 接続失敗
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """ストレージから切断"""
        pass

    @abstractmethod
    def copy_file(self, source: str, destination: str, callback: Optional[Callable] = None) -> CopyResult:
        """
        ファイルをコピー

        Args:
            source: ソースファイルパス
            destination: 送信先ファイルパス
            callback: 進捗コールバック(bytes_copied, total_bytes)

        Returns:
            CopyResult

        Raises:
            CopyOperationError: コピー失敗
            InsufficientStorageError: 容量不足
        """
        pass

    @abstractmethod
    def delete_file(self, path: str) -> bool:
        """
        ファイルを削除

        Args:
            path: 削除対象パス

        Returns:
            削除成功ならTrue
        """
        pass

    @abstractmethod
    def get_available_space(self) -> int:
        """
        利用可能な容量を取得（バイト単位）

        Returns:
            利用可能バイト数
        """
        pass

    @abstractmethod
    def get_storage_info(self) -> StorageInfo:
        """
        ストレージ情報を取得

        Returns:
            StorageInfo（容量、使用量等）
        """
        pass

    @abstractmethod
    def verify_file(self, path: str, expected_checksum: str) -> bool:
        """
        ファイルの整合性を検証

        Args:
            path: 検証対象ファイルパス
            expected_checksum: 期待されるチェックサム

        Returns:
            検証成功ならTrue
        """
        pass

    @abstractmethod
    def list_files(self, path: str, pattern: str = "*") -> list:
        """
        ファイル一覧を取得

        Args:
            path: ディレクトリパス
            pattern: ファイル名パターン（glob）

        Returns:
            ファイル情報のリスト
        """
        pass

    def is_online(self) -> bool:
        """
        ストレージがオンラインか

        Returns:
            オンラインならTrue（3-2-1-1-0の「1（オフライン）」判定用）
        """
        return self.storage_location != StorageLocation.OFFLINE

    def supports_immutable(self) -> bool:
        """
        イミュータブル機能をサポートするか

        Returns:
            サポートするならTrue
        """
        return self.is_immutable
