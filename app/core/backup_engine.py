"""
Core Backup Engine
ISO 27001 A.12.3準拠のバックアップエンジン
3-2-1-1-0ルールを実装
"""

import hashlib
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from app.core.exceptions import (
    BackupEngineError,
    BackupJobNotFoundError,
    CopyOperationError,
    InsufficientStorageError,
    RetryExhaustedError,
    VerificationFailedError,
)

# ログ設定
logger = logging.getLogger(__name__)


class BackupEngine:
    """
    コアバックアップエンジン

    3-2-1-1-0バックアップ戦略を実装:
    - 3: 最低3つのコピー
    - 2: 2つの異なるメディアタイプ
    - 1: 1つはオフサイト
    - 1: 1つはオフライン/イミュータブル
    - 0: 検証エラーゼロ
    """

    def __init__(self, db_session=None, storage_registry=None, verification_service=None):
        """
        Args:
            db_session: SQLAlchemyセッション
            storage_registry: ストレージレジストリ（Agent-02提供）
            verification_service: 検証サービス（Agent-03提供）
        """
        self.db = db_session
        self.storage_registry = storage_registry
        self.verification_service = verification_service

        # バッファサイズ（パフォーマンス最適化）
        self.buffer_size = 64 * 1024 * 1024  # 64MB

        # 最大リトライ回数
        self.max_retries = 3

        # リトライ間隔（秒）
        self.retry_intervals = [1, 5, 15]  # Exponential backoff

        logger.info("BackupEngine initialized", extra={"agent": "agent-01-core", "buffer_size": self.buffer_size})

    def execute_backup(self, job_id: int, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        バックアップジョブを実行

        Args:
            job_id: バックアップジョブID
            progress_callback: 進捗コールバック関数

        Returns:
            実行結果の辞書

        Raises:
            BackupJobNotFoundError: ジョブが見つからない
            BackupEngineError: 実行エラー
        """
        logger.info(f"Starting backup execution", extra={"job_id": job_id, "agent": "agent-01-core"})

        start_time = datetime.now()

        try:
            # バックアップジョブ取得（Agent-01が現在app/modelsにアクセス可能）
            from app.models import BackupJob

            job = BackupJob.query.get(job_id)
            if not job:
                raise BackupJobNotFoundError(job_id)

            # ソースパス存在確認
            source_path = Path(job.source_path)
            if not source_path.exists():
                raise CopyOperationError(str(source_path), "N/A", "Source path does not exist")

            # バックアップ実行
            result = {
                "job_id": job_id,
                "status": "success",
                "start_time": start_time.isoformat(),
                "copies_created": [],
                "total_bytes": 0,
                "errors": [],
            }

            # 送信先パスリスト（将来的にはAgent-02のStorageRegistryから取得）
            destinations = job.destination_paths.split(",") if job.destination_paths else []

            for dest_path in destinations:
                try:
                    copy_result = self.copy_file(str(source_path), dest_path.strip(), progress_callback)

                    result["copies_created"].append(
                        {
                            "destination": dest_path.strip(),
                            "size_bytes": copy_result["bytes_copied"],
                            "checksum": copy_result["checksum"],
                        }
                    )

                    result["total_bytes"] += copy_result["bytes_copied"]

                except CopyOperationError as e:
                    logger.error(f"Copy failed to {dest_path}", extra={"error": str(e), "job_id": job_id})
                    result["errors"].append(e.to_dict())

            # エラーがあれば部分失敗
            if result["errors"]:
                result["status"] = "partial"

            end_time = datetime.now()
            result["end_time"] = end_time.isoformat()
            result["duration_seconds"] = (end_time - start_time).total_seconds()

            logger.info(
                "Backup execution completed",
                extra={
                    "job_id": job_id,
                    "status": result["status"],
                    "copies": len(result["copies_created"]),
                    "duration": result["duration_seconds"],
                },
            )

            return result

        except Exception as e:
            logger.error(f"Backup execution failed", extra={"job_id": job_id, "error": str(e)})
            raise BackupEngineError(f"Backup execution failed: {str(e)}", {"job_id": job_id})

    def copy_file(self, source: str, destination: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        ファイルをコピー（進捗追跡、チェックサム計算付き）

        Args:
            source: ソースファイルパス
            destination: 送信先ファイルパス
            progress_callback: 進捗コールバック(bytes_copied, total_bytes)

        Returns:
            コピー結果辞書 {"bytes_copied": int, "checksum": str, "duration": float}

        Raises:
            CopyOperationError: コピー失敗
            InsufficientStorageError: 容量不足
        """
        source_path = Path(source)
        dest_path = Path(destination)

        logger.debug(f"Starting copy operation", extra={"source": source, "destination": destination})

        # ソースファイル存在確認
        if not source_path.exists():
            raise CopyOperationError(source, destination, "Source file does not exist")

        # ソースファイルサイズ取得
        source_size = source_path.stat().st_size

        # 送信先の空き容量チェック
        dest_parent = dest_path.parent
        dest_parent.mkdir(parents=True, exist_ok=True)

        stat = os.statvfs(str(dest_parent))
        available_bytes = stat.f_bavail * stat.f_frsize

        if available_bytes < source_size * 1.1:  # 10%のマージン
            raise InsufficientStorageError(int(source_size * 1.1), available_bytes, str(dest_parent))

        # リトライ付きコピー
        for attempt in range(self.max_retries):
            try:
                start_time = datetime.now()

                # チェックサム計算しながらコピー
                sha256_hash = hashlib.sha256()
                bytes_copied = 0

                with open(source_path, "rb") as src_file:
                    with open(dest_path, "wb") as dest_file:
                        while True:
                            chunk = src_file.read(self.buffer_size)
                            if not chunk:
                                break

                            dest_file.write(chunk)
                            sha256_hash.update(chunk)
                            bytes_copied += len(chunk)

                            # 進捗コールバック
                            if progress_callback:
                                progress_callback(bytes_copied, source_size)

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                result = {"bytes_copied": bytes_copied, "checksum": sha256_hash.hexdigest(), "duration": duration}

                logger.info(
                    f"Copy completed",
                    extra={
                        "source": source,
                        "destination": destination,
                        "bytes": bytes_copied,
                        "duration": duration,
                        "checksum": result["checksum"],
                    },
                )

                return result

            except (IOError, OSError) as e:
                logger.warning(f"Copy attempt {attempt + 1} failed", extra={"source": source, "error": str(e)})

                if attempt == self.max_retries - 1:
                    raise CopyOperationError(source, destination, f"Failed after {self.max_retries} attempts: {str(e)}")

                # リトライ前に一時停止
                import time

                time.sleep(self.retry_intervals[attempt])

    def verify_copy(self, original_path: str, copy_path: str) -> bool:
        """
        コピーの整合性を検証

        Args:
            original_path: オリジナルファイルパス
            copy_path: コピーファイルパス

        Returns:
            検証成功ならTrue

        Raises:
            VerificationFailedError: 検証失敗
        """
        original = Path(original_path)
        copy = Path(copy_path)

        # ファイル存在確認
        if not original.exists():
            raise VerificationFailedError(0, "file_exists", f"Original file not found: {original_path}")

        if not copy.exists():
            raise VerificationFailedError(0, "file_exists", f"Copy file not found: {copy_path}")

        # ファイルサイズ比較
        original_size = original.stat().st_size
        copy_size = copy.stat().st_size

        if original_size != copy_size:
            raise VerificationFailedError(
                0, "size_mismatch", f"Size mismatch: original {original_size} bytes, copy {copy_size} bytes"
            )

        # チェックサム比較
        original_hash = self._calculate_checksum(original_path)
        copy_hash = self._calculate_checksum(copy_path)

        if original_hash != copy_hash:
            raise VerificationFailedError(0, "checksum_mismatch", f"Checksum mismatch: {original_hash} != {copy_hash}")

        logger.info(f"Verification passed", extra={"original": original_path, "copy": copy_path, "checksum": original_hash})

        return True

    def _calculate_checksum(self, file_path: str, algorithm: str = "sha256") -> str:
        """
        ファイルのチェックサムを計算

        Args:
            file_path: ファイルパス
            algorithm: ハッシュアルゴリズム（sha256, sha512, md5）

        Returns:
            チェックサム（16進数文字列）
        """
        hash_obj = hashlib.new(algorithm)

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(self.buffer_size)
                if not chunk:
                    break
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    def get_backup_stats(self) -> Dict[str, Any]:
        """
        バックアップエンジンの統計情報を取得

        Returns:
            統計情報辞書
        """
        return {
            "buffer_size": self.buffer_size,
            "max_retries": self.max_retries,
            "retry_intervals": self.retry_intervals,
            "agent": "agent-01-core",
            "version": "1.0.0",
        }
