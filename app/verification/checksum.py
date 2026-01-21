"""
Checksum Calculation Service

This module provides high-performance checksum calculation with support for
multiple algorithms, streaming processing, and parallel execution.
"""

import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

from .interfaces import ChecksumAlgorithm, IVerificationService, VerificationStatus

logger = logging.getLogger(__name__)


class ChecksumService:
    """
    Service for calculating file checksums with multiple algorithms.

    Supports:
    - SHA-256, SHA-512 (recommended)
    - BLAKE2b, BLAKE2s (fast and secure)
    - MD5 (legacy support only)
    - Streaming calculation for large files
    - Parallel processing for multiple files
    """

    # Default chunk size for streaming (64KB)
    DEFAULT_CHUNK_SIZE = 65536

    # Algorithm to hashlib mapping
    ALGORITHM_MAP = {
        ChecksumAlgorithm.SHA256: hashlib.sha256,
        ChecksumAlgorithm.SHA512: hashlib.sha512,
        ChecksumAlgorithm.BLAKE2B: hashlib.blake2b,
        ChecksumAlgorithm.BLAKE2S: hashlib.blake2s,
        ChecksumAlgorithm.MD5: hashlib.md5,
    }

    def __init__(self, default_algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256):
        """
        Initialize checksum service.

        Args:
            default_algorithm: Default checksum algorithm to use
        """
        self.default_algorithm = default_algorithm
        self.stats = {"total_calculated": 0, "total_bytes_processed": 0, "total_time": 0.0, "errors": 0}

    def calculate_checksum(
        self, file_path: Path, algorithm: Optional[ChecksumAlgorithm] = None, chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> str:
        """
        Calculate checksum for a single file using streaming.

        This method reads the file in chunks to handle large files efficiently
        without loading the entire file into memory.

        Args:
            file_path: Path to the file
            algorithm: Checksum algorithm to use (defaults to instance default)
            chunk_size: Size of chunks for streaming calculation (bytes)

        Returns:
            Hexadecimal checksum string

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
            IOError: If file read fails
            ValueError: If algorithm is not supported
        """
        algorithm = algorithm or self.default_algorithm

        if algorithm not in self.ALGORITHM_MAP:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        start_time = time.time()
        bytes_processed = 0

        try:
            # Create hash object
            hash_obj = self.ALGORITHM_MAP[algorithm]()

            # Stream file in chunks
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hash_obj.update(chunk)
                    bytes_processed += len(chunk)

            checksum = hash_obj.hexdigest()

            # Update statistics
            elapsed_time = time.time() - start_time
            self.stats["total_calculated"] += 1
            self.stats["total_bytes_processed"] += bytes_processed
            self.stats["total_time"] += elapsed_time

            logger.debug(
                f"Calculated {algorithm.value} checksum for {file_path.name}: "
                f"{checksum} ({bytes_processed} bytes in {elapsed_time:.2f}s)"
            )

            return checksum

        except PermissionError as e:
            self.stats["errors"] += 1
            logger.error(f"Permission denied reading {file_path}: {e}")
            raise

        except IOError as e:
            self.stats["errors"] += 1
            logger.error(f"IO error reading {file_path}: {e}")
            raise

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Unexpected error calculating checksum for {file_path}: {e}")
            raise

    def calculate_checksums_parallel(
        self,
        file_paths: List[Path],
        algorithm: Optional[ChecksumAlgorithm] = None,
        max_workers: Optional[int] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> Dict[Path, str]:
        """
        Calculate checksums for multiple files in parallel.

        Uses ThreadPoolExecutor to process multiple files concurrently,
        significantly improving performance for large file sets.

        Args:
            file_paths: List of file paths
            algorithm: Checksum algorithm to use
            max_workers: Maximum number of parallel workers (defaults to CPU count)
            chunk_size: Size of chunks for streaming calculation

        Returns:
            Dictionary mapping file paths to checksums
        """
        algorithm = algorithm or self.default_algorithm
        results = {}
        errors = {}

        if not file_paths:
            return results

        logger.info(
            f"Calculating {algorithm.value} checksums for {len(file_paths)} files " f"with {max_workers or 'auto'} workers"
        )

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self.calculate_checksum, path, algorithm, chunk_size): path for path in file_paths
            }

            # Collect results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    checksum = future.result()
                    results[path] = checksum
                except Exception as e:
                    errors[path] = str(e)
                    logger.error(f"Failed to calculate checksum for {path}: {e}")

        elapsed_time = time.time() - start_time

        logger.info(f"Completed {len(results)}/{len(file_paths)} checksums in {elapsed_time:.2f}s " f"({len(errors)} errors)")

        if errors:
            logger.warning(f"Errors occurred for {len(errors)} files: {list(errors.keys())}")

        return results

    def calculate_directory_checksums(
        self,
        directory: Path,
        pattern: str = "*",
        recursive: bool = True,
        algorithm: Optional[ChecksumAlgorithm] = None,
        max_workers: Optional[int] = None,
    ) -> Dict[Path, str]:
        """
        Calculate checksums for all files in a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for file matching
            recursive: Whether to search recursively
            algorithm: Checksum algorithm to use
            max_workers: Maximum number of parallel workers

        Returns:
            Dictionary mapping file paths to checksums
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Find all matching files
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))

        # Filter to only files
        files = [f for f in files if f.is_file()]

        logger.info(f"Found {len(files)} files in {directory} matching pattern '{pattern}'")

        return self.calculate_checksums_parallel(files, algorithm=algorithm, max_workers=max_workers)

    def verify_checksum(self, file_path: Path, expected_checksum: str, algorithm: Optional[ChecksumAlgorithm] = None) -> bool:
        """
        Verify a file's checksum against an expected value.

        Args:
            file_path: Path to the file
            expected_checksum: Expected checksum value
            algorithm: Checksum algorithm to use

        Returns:
            True if checksum matches, False otherwise
        """
        try:
            actual_checksum = self.calculate_checksum(file_path, algorithm)
            matches = actual_checksum.lower() == expected_checksum.lower()

            if not matches:
                logger.warning(f"Checksum mismatch for {file_path}: " f"expected {expected_checksum}, got {actual_checksum}")

            return matches

        except Exception as e:
            logger.error(f"Error verifying checksum for {file_path}: {e}")
            return False

    def get_statistics(self) -> Dict:
        """
        Get service statistics.

        Returns:
            Dictionary containing statistics
        """
        stats = self.stats.copy()

        if stats["total_time"] > 0:
            stats["avg_throughput_mb_s"] = stats["total_bytes_processed"] / (1024 * 1024) / stats["total_time"]
        else:
            stats["avg_throughput_mb_s"] = 0.0

        return stats

    def reset_statistics(self) -> None:
        """Reset service statistics."""
        self.stats = {"total_calculated": 0, "total_bytes_processed": 0, "total_time": 0.0, "errors": 0}

    @staticmethod
    def get_supported_algorithms() -> List[ChecksumAlgorithm]:
        """
        Get list of supported checksum algorithms.

        Returns:
            List of supported algorithms
        """
        return list(ChecksumService.ALGORITHM_MAP.keys())

    @staticmethod
    def get_recommended_algorithm() -> ChecksumAlgorithm:
        """
        Get recommended checksum algorithm.

        Returns:
            Recommended algorithm (SHA-256)
        """
        return ChecksumAlgorithm.SHA256

    def __repr__(self) -> str:
        return (
            f"ChecksumService(algorithm={self.default_algorithm.value}, "
            f"calculated={self.stats['total_calculated']}, "
            f"errors={self.stats['errors']})"
        )
