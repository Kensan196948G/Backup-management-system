"""
Core Backup Engine - Custom Exceptions
ISO 27001 A.12.3 準拠のバックアップエンジン用例外クラス
"""


class BackupEngineError(Exception):
    """バックアップエンジンの基底例外クラス"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self):
        """例外情報を辞書形式で返す（ログ記録用）"""
        return {"error_type": self.__class__.__name__, "message": self.message, "details": self.details}


class CopyOperationError(BackupEngineError):
    """コピー操作エラー"""

    def __init__(self, source: str, destination: str, reason: str, details: dict = None):
        message = f"Copy operation failed: {source} -> {destination}: {reason}"
        details = details or {}
        details.update({"source": source, "destination": destination, "reason": reason})
        super().__init__(message, details)


class InsufficientStorageError(BackupEngineError):
    """ストレージ容量不足エラー"""

    def __init__(self, required_bytes: int, available_bytes: int, storage_path: str):
        message = f"Insufficient storage: required {required_bytes} bytes, available {available_bytes} bytes"
        details = {"required_bytes": required_bytes, "available_bytes": available_bytes, "storage_path": storage_path}
        super().__init__(message, details)


class VerificationFailedError(BackupEngineError):
    """バックアップ検証失敗エラー"""

    def __init__(self, backup_id: int, verification_type: str, reason: str):
        message = f"Backup verification failed for backup {backup_id}: {reason}"
        details = {"backup_id": backup_id, "verification_type": verification_type, "reason": reason}
        super().__init__(message, details)


class Rule321110ViolationError(BackupEngineError):
    """3-2-1-1-0ルール違反エラー"""

    def __init__(self, job_id: int, violations: dict):
        violation_messages = []

        if not violations.get("min_copies"):
            violation_messages.append("最低3コピー未満")

        if not violations.get("different_media"):
            violation_messages.append("2種類以上の異なるメディア未使用")

        if not violations.get("offsite_copy"):
            violation_messages.append("オフサイトコピーなし")

        if not violations.get("offline_copy"):
            violation_messages.append("オフラインコピーなし")

        if not violations.get("zero_errors"):
            violation_messages.append("検証エラーあり")

        message = f"3-2-1-1-0 rule violation for job {job_id}: {', '.join(violation_messages)}"
        details = {"job_id": job_id, "violations": violations}
        super().__init__(message, details)


class BackupJobNotFoundError(BackupEngineError):
    """バックアップジョブが見つからないエラー"""

    def __init__(self, job_id: int):
        message = f"Backup job not found: {job_id}"
        details = {"job_id": job_id}
        super().__init__(message, details)


class RetryExhaustedError(BackupEngineError):
    """リトライ回数超過エラー"""

    def __init__(self, operation: str, max_retries: int, last_error: str):
        message = f"Retry exhausted for {operation} after {max_retries} attempts: {last_error}"
        details = {"operation": operation, "max_retries": max_retries, "last_error": last_error}
        super().__init__(message, details)
