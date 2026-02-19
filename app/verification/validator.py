"""
File Integrity Validator

This module provides comprehensive file validation including checksum verification,
metadata comparison, and corruption detection.
"""

import logging
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .checksum import ChecksumService
from .interfaces import ChecksumAlgorithm, IVerificationService, VerificationStatus

logger = logging.getLogger(__name__)


class FileValidator(IVerificationService):
    """
    File integrity validator implementation.

    Provides comprehensive validation including:
    - Checksum verification
    - File size comparison
    - Metadata verification (timestamps, permissions)
    - Bit rot detection
    - Batch validation
    """

    def __init__(
        self,
        checksum_service: Optional[ChecksumService] = None,
        verify_metadata: bool = True,
        verify_permissions: bool = False,
    ):
        """
        Initialize file validator.

        Args:
            checksum_service: Checksum service instance (creates new if None)
            verify_metadata: Whether to verify metadata by default
            verify_permissions: Whether to verify file permissions
        """
        self.checksum_service = checksum_service or ChecksumService()
        self.verify_metadata_default = verify_metadata
        self.verify_permissions = verify_permissions

        self.validation_stats = {"total_validations": 0, "successful": 0, "failed": 0, "errors": 0, "last_validation": None}

    def calculate_checksum(
        self, file_path: Path, algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256, chunk_size: int = 65536
    ) -> str:
        """
        Calculate checksum for a single file.

        Args:
            file_path: Path to the file
            algorithm: Checksum algorithm to use
            chunk_size: Size of chunks for streaming calculation

        Returns:
            Hexadecimal checksum string
        """
        return self.checksum_service.calculate_checksum(file_path, algorithm, chunk_size)

    def calculate_checksums_parallel(
        self,
        file_paths: List[Path],
        algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256,
        max_workers: Optional[int] = None,
    ) -> Dict[Path, str]:
        """
        Calculate checksums for multiple files in parallel.

        Args:
            file_paths: List of file paths
            algorithm: Checksum algorithm to use
            max_workers: Maximum number of parallel workers

        Returns:
            Dictionary mapping file paths to checksums
        """
        return self.checksum_service.calculate_checksums_parallel(file_paths, algorithm, max_workers)

    def verify_file(
        self, source_path: Path, target_path: Path, algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256
    ) -> Tuple[VerificationStatus, Dict]:
        """
        Verify file integrity by comparing checksums and metadata.

        Args:
            source_path: Original file path
            target_path: Copied/backup file path
            algorithm: Checksum algorithm to use

        Returns:
            Tuple of (status, details_dict)
        """
        self.validation_stats["total_validations"] += 1
        self.validation_stats["last_validation"] = datetime.utcnow().isoformat()

        details = {
            "source": str(source_path),
            "target": str(target_path),
            "algorithm": algorithm.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Check if both files exist
            if not source_path.exists():
                self.validation_stats["failed"] += 1
                details["error"] = "Source file not found"
                return VerificationStatus.FILE_NOT_FOUND, details

            if not target_path.exists():
                self.validation_stats["failed"] += 1
                details["error"] = "Target file not found"
                return VerificationStatus.FILE_NOT_FOUND, details

            # Verify file sizes first (quick check)
            source_size = source_path.stat().st_size
            target_size = target_path.stat().st_size

            details["source_size"] = source_size
            details["target_size"] = target_size

            if source_size != target_size:
                self.validation_stats["failed"] += 1
                details["error"] = f"Size mismatch: {source_size} != {target_size}"
                logger.warning(f"Size mismatch for {source_path.name}: {details['error']}")
                return VerificationStatus.SIZE_MISMATCH, details

            # Calculate checksums
            logger.debug(f"Calculating checksums for {source_path.name}")

            source_checksum = self.checksum_service.calculate_checksum(source_path, algorithm)
            target_checksum = self.checksum_service.calculate_checksum(target_path, algorithm)

            details["source_checksum"] = source_checksum
            details["target_checksum"] = target_checksum

            # Compare checksums
            if source_checksum != target_checksum:
                self.validation_stats["failed"] += 1
                details["error"] = "Checksum mismatch"
                logger.error(f"Checksum mismatch for {source_path.name}: " f"{source_checksum} != {target_checksum}")
                return VerificationStatus.CHECKSUM_MISMATCH, details

            # Verify metadata if enabled
            if self.verify_metadata_default:
                metadata_status, metadata_details = self.verify_metadata(source_path, target_path)
                details["metadata"] = metadata_details

                if metadata_status != VerificationStatus.SUCCESS:
                    self.validation_stats["failed"] += 1
                    logger.warning(
                        f"Metadata mismatch for {source_path.name}: " f"{metadata_details.get('error', 'Unknown error')}"
                    )
                    return metadata_status, details

            # All checks passed
            self.validation_stats["successful"] += 1
            logger.info(f"Verification successful for {source_path.name}")
            return VerificationStatus.SUCCESS, details

        except Exception as e:
            self.validation_stats["errors"] += 1
            details["error"] = str(e)
            details["exception_type"] = type(e).__name__
            logger.error(f"Error verifying {source_path.name}: {e}", exc_info=True)
            return VerificationStatus.FAILED, details

    def verify_backup(
        self, source_files: List[Path], target_files: List[Path], algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256
    ) -> Dict:
        """
        Verify entire backup by comparing multiple files.

        Args:
            source_files: List of original file paths
            target_files: List of backup file paths
            algorithm: Checksum algorithm to use

        Returns:
            Dictionary containing verification results
        """
        if len(source_files) != len(target_files):
            raise ValueError(f"File count mismatch: {len(source_files)} source files, " f"{len(target_files)} target files")

        logger.info(f"Verifying backup: {len(source_files)} files with {algorithm.value}")

        results = {
            "total_files": len(source_files),
            "successful": 0,
            "failed": 0,
            "errors": 0,
            "algorithm": algorithm.value,
            "timestamp": datetime.utcnow().isoformat(),
            "details": [],
        }

        for source_path, target_path in zip(source_files, target_files):
            status, details = self.verify_file(source_path, target_path, algorithm)

            result_entry = {"source": str(source_path), "target": str(target_path), "status": status.value, "details": details}

            results["details"].append(result_entry)

            if status == VerificationStatus.SUCCESS:
                results["successful"] += 1
            elif status in [VerificationStatus.FILE_NOT_FOUND, VerificationStatus.FAILED]:
                results["errors"] += 1
            else:
                results["failed"] += 1

        results["success_rate"] = results["successful"] / results["total_files"] * 100 if results["total_files"] > 0 else 0.0

        logger.info(
            f"Backup verification complete: {results['successful']}/{results['total_files']} "
            f"successful ({results['success_rate']:.1f}%)"
        )

        return results

    def verify_metadata(self, source_path: Path, target_path: Path) -> Tuple[VerificationStatus, Dict]:
        """
        Verify file metadata (size, timestamps, permissions).

        Args:
            source_path: Original file path
            target_path: Copied/backup file path

        Returns:
            Tuple of (status, details_dict)
        """
        details = {
            "source": str(source_path),
            "target": str(target_path),
        }

        try:
            source_stat = source_path.stat()
            target_stat = target_path.stat()

            # File size
            details["source_size"] = source_stat.st_size
            details["target_size"] = target_stat.st_size

            if source_stat.st_size != target_stat.st_size:
                details["error"] = "Size mismatch"
                return VerificationStatus.SIZE_MISMATCH, details

            # Modification time (allow small differences for filesystem quirks)
            source_mtime = source_stat.st_mtime
            target_mtime = target_stat.st_mtime
            time_diff = abs(source_mtime - target_mtime)

            details["source_mtime"] = datetime.fromtimestamp(source_mtime).isoformat()
            details["target_mtime"] = datetime.fromtimestamp(target_mtime).isoformat()
            details["time_diff_seconds"] = time_diff

            # Allow up to 2 seconds difference for filesystem timestamp precision
            if time_diff > 2.0:
                details["warning"] = f"Modification time differs by {time_diff:.2f}s"
                logger.debug(f"Metadata warning for {source_path.name}: {details['warning']}")

            # Permissions (if enabled)
            if self.verify_permissions:
                source_mode = stat.filemode(source_stat.st_mode)
                target_mode = stat.filemode(target_stat.st_mode)

                details["source_permissions"] = source_mode
                details["target_permissions"] = target_mode

                if source_mode != target_mode:
                    details["warning"] = details.get("warning", "") + f" Permission mismatch: {source_mode} != {target_mode}"

            return VerificationStatus.SUCCESS, details

        except Exception as e:
            details["error"] = str(e)
            details["exception_type"] = type(e).__name__
            logger.error(f"Error verifying metadata for {source_path.name}: {e}")
            return VerificationStatus.FAILED, details

    def detect_corruption(
        self, file_path: Path, expected_checksum: str, algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256
    ) -> bool:
        """
        Detect file corruption by comparing with expected checksum.

        Args:
            file_path: Path to file to check
            expected_checksum: Expected checksum value
            algorithm: Checksum algorithm to use

        Returns:
            True if file is corrupted, False otherwise
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found for corruption check: {file_path}")
                return True

            actual_checksum = self.checksum_service.calculate_checksum(file_path, algorithm)

            is_corrupted = actual_checksum.lower() != expected_checksum.lower()

            if is_corrupted:
                logger.error(
                    f"Corruption detected in {file_path.name}: " f"expected {expected_checksum}, got {actual_checksum}"
                )
            else:
                logger.debug(f"No corruption detected in {file_path.name}")

            return is_corrupted

        except Exception as e:
            logger.error(f"Error checking corruption for {file_path}: {e}")
            return True  # Assume corrupted if we can't verify

    def batch_detect_corruption(
        self,
        file_checksums: Dict[Path, str],
        algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256,
        max_workers: Optional[int] = None,
    ) -> Dict[Path, bool]:
        """
        Detect corruption for multiple files in parallel.

        Args:
            file_checksums: Dictionary mapping file paths to expected checksums
            algorithm: Checksum algorithm to use
            max_workers: Maximum number of parallel workers

        Returns:
            Dictionary mapping file paths to corruption status (True = corrupted)
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}

        logger.info(f"Checking {len(file_checksums)} files for corruption with " f"{algorithm.value}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.detect_corruption, path, checksum, algorithm): path
                for path, checksum in file_checksums.items()
            }

            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    is_corrupted = future.result()
                    results[path] = is_corrupted
                except Exception as e:
                    logger.error(f"Error checking corruption for {path}: {e}")
                    results[path] = True  # Assume corrupted on error

        corrupted_count = sum(1 for corrupted in results.values() if corrupted)
        logger.info(f"Corruption check complete: {corrupted_count}/{len(results)} files corrupted")

        return results

    def get_validation_statistics(self) -> Dict:
        """
        Get validation statistics.

        Returns:
            Dictionary containing validation statistics
        """
        stats = self.validation_stats.copy()

        if stats["total_validations"] > 0:
            stats["success_rate"] = stats["successful"] / stats["total_validations"] * 100
            stats["failure_rate"] = stats["failed"] / stats["total_validations"] * 100
            stats["error_rate"] = stats["errors"] / stats["total_validations"] * 100
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
            stats["error_rate"] = 0.0

        return stats

    def reset_validation_statistics(self) -> None:
        """Reset validation statistics."""
        self.validation_stats = {"total_validations": 0, "successful": 0, "failed": 0, "errors": 0, "last_validation": None}

    def __repr__(self) -> str:
        return (
            f"FileValidator("
            f"validations={self.validation_stats['total_validations']}, "
            f"successful={self.validation_stats['successful']}, "
            f"failed={self.validation_stats['failed']})"
        )
