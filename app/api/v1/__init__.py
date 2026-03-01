"""
API v1 Module
RESTful API endpoints version 1 for Backup Management System

Endpoints:
- /api/v1/auth - Authentication (login, token refresh)
- /api/v1/backups - Backup job management
- /api/v1/storage - Storage provider management
- /api/v1/verify - Verification management
- /api/v1/compliance - Compliance status
- /api/v1/aomei - AOMEI Backupper integration
"""

from flask import Blueprint

# Note: v1 modules are imported when needed to avoid circular dependencies
# and blueprint registration issues.
# Auth blueprint is registered separately in app/__init__.py to preserve URL prefix.
