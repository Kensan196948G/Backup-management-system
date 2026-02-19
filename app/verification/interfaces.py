"""
Verification Service Interfaces

This module defines abstract interfaces for verification and validation services,
providing a contract for concrete implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ChecksumAlgorithm(Enum):
    """Supported checksum algorithms"""

    SHA256 = "sha256"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    MD5 = "md5"  # Legacy support only, not recommended


class VerificationStatus(Enum):
    """Verification result status"""

    SUCCESS = "success"
    FAILED = "failed"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    FILE_NOT_FOUND = "file_not_found"
    SIZE_MISMATCH = "size_mismatch"
    METADATA_MISMATCH = "metadata_mismatch"
    CORRUPTED = "corrupted"
    PARTIAL = "partial"


class IVerificationService(ABC):
    """
    Abstract interface for verification services.

    This interface defines the contract for all verification operations
    including checksum calculation, file validation, and integrity checks.
    """

    @abstractmethod
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

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
            IOError: If file read fails
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def verify_file(
        self, source_path: Path, target_path: Path, algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256
    ) -> Tuple[VerificationStatus, Dict]:
        """
        Verify file integrity by comparing checksums.

        Args:
            source_path: Original file path
            target_path: Copied/backup file path
            algorithm: Checksum algorithm to use

        Returns:
            Tuple of (status, details_dict)
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def verify_metadata(self, source_path: Path, target_path: Path) -> Tuple[VerificationStatus, Dict]:
        """
        Verify file metadata (size, timestamps, permissions).

        Args:
            source_path: Original file path
            target_path: Copied/backup file path

        Returns:
            Tuple of (status, details_dict)
        """
        pass

    @abstractmethod
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
        pass


class IChecksumStorage(ABC):
    """Interface for storing and retrieving checksums"""

    @abstractmethod
    def store_checksum(self, file_path: Path, checksum: str, algorithm: ChecksumAlgorithm) -> None:
        """Store checksum for a file"""
        pass

    @abstractmethod
    def retrieve_checksum(self, file_path: Path, algorithm: ChecksumAlgorithm) -> Optional[str]:
        """Retrieve stored checksum for a file"""
        pass

    @abstractmethod
    def delete_checksum(self, file_path: Path) -> None:
        """Delete stored checksum for a file"""
        pass
