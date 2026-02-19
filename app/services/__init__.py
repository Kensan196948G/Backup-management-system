"""
Business Logic Services Package

This package contains the core business logic for the Backup Management System:
- ComplianceChecker: 3-2-1-1-0 rule compliance checking
- AlertManager: Alert generation and notification
- ReportGenerator: Report generation (HTML/PDF/CSV)
- AOMEIService: AOMEI Backupper integration
- VerificationService: Backup verification and restore testing
"""

from .alert_manager import AlertManager
from .aomei_service import AOMEIService
from .compliance_checker import ComplianceChecker
from .report_generator import ReportGenerator
from .verification_service import VerificationService, get_verification_service

__all__ = [
    "ComplianceChecker",
    "AlertManager",
    "ReportGenerator",
    "AOMEIService",
    "VerificationService",
    "get_verification_service",
]
