"""
Verification and Validation Module

This module provides comprehensive file integrity verification and validation
services for the backup management system.

Features:
- Multiple checksum algorithms (SHA-256, SHA-512, BLAKE2)
- Streaming checksum calculation for large files
- Parallel processing for multiple files
- File integrity validation
- Metadata verification
- Bit rot detection
- Full restore testing
- Partial restore testing
- Integrity-only verification
"""

from enum import Enum
from typing import Dict

from .checksum import ChecksumService
from .interfaces import ChecksumAlgorithm, IVerificationService, VerificationStatus
from .validator import FileValidator

__all__ = [
    "IVerificationService",
    "ChecksumService",
    "FileValidator",
    "ChecksumAlgorithm",
    "VerificationStatus",
    "VerificationType",
    "TestResult",
    "evaluate_verification_result",
]

__version__ = "1.1.0"


class VerificationType(Enum):
    """
    Verification test type enumeration.

    - FULL_RESTORE: Complete backup restoration test
    - PARTIAL: Selective file restoration test
    - INTEGRITY: Checksum-only validation without restoration
    """

    FULL_RESTORE = "full_restore"
    PARTIAL = "partial"
    INTEGRITY = "integrity"


class TestResult(Enum):
    """
    Test result status enumeration.

    - SUCCESS: All tests passed
    - FAILED: Critical failures detected
    - WARNING: Some issues but not critical
    - ERROR: Test execution error
    """

    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


def evaluate_verification_result(
    test_type: VerificationType, verified_count: int, total_count: int, errors: list
) -> TestResult:
    """
    Evaluate verification test result based on metrics.

    Args:
        test_type: Type of verification test
        verified_count: Number of successfully verified items
        total_count: Total number of items tested
        errors: List of errors encountered

    Returns:
        TestResult enum indicating overall test result

    Logic:
        - SUCCESS: 100% verification rate, no errors
        - WARNING: 70-99% verification rate or minor errors
        - FAILED: < 70% verification rate or critical errors
        - ERROR: Test execution errors

    Examples:
        >>> evaluate_verification_result(VerificationType.INTEGRITY, 100, 100, [])
        TestResult.SUCCESS

        >>> evaluate_verification_result(VerificationType.FULL_RESTORE, 85, 100, [])
        TestResult.WARNING

        >>> evaluate_verification_result(VerificationType.PARTIAL, 5, 100, [])
        TestResult.FAILED
    """
    if total_count == 0:
        return TestResult.ERROR if errors else TestResult.SUCCESS

    verification_rate = (verified_count / total_count) * 100

    # Check for critical errors
    has_critical_errors = any("critical" in str(e).lower() or "fatal" in str(e).lower() for e in errors)

    if has_critical_errors:
        return TestResult.FAILED

    # Evaluate based on verification rate
    if verification_rate == 100.0 and not errors:
        return TestResult.SUCCESS
    elif verification_rate >= 70.0:
        # Good verification rate but some issues
        return TestResult.WARNING if errors else TestResult.SUCCESS
    else:
        # Low verification rate
        return TestResult.FAILED


def get_verification_thresholds() -> Dict[str, float]:
    """
    Get verification success thresholds for different test types.

    Returns:
        Dictionary mapping test type to success threshold percentage

    Thresholds:
        - full_restore: 95% (strict - full restoration should be highly reliable)
        - partial: 90% (moderate - sample testing allows some margin)
        - integrity: 98% (very strict - checksums should be nearly perfect)
    """
    return {
        VerificationType.FULL_RESTORE.value: 95.0,
        VerificationType.PARTIAL.value: 90.0,
        VerificationType.INTEGRITY.value: 98.0,
    }


def is_verification_successful(test_type: VerificationType, verification_rate: float) -> bool:
    """
    Check if verification meets success threshold for test type.

    Args:
        test_type: Type of verification test
        verification_rate: Verification success rate (0-100)

    Returns:
        True if verification meets threshold, False otherwise

    Examples:
        >>> is_verification_successful(VerificationType.INTEGRITY, 99.0)
        True

        >>> is_verification_successful(VerificationType.FULL_RESTORE, 85.0)
        False
    """
    thresholds = get_verification_thresholds()
    threshold = thresholds.get(test_type.value, 95.0)
    return verification_rate >= threshold
