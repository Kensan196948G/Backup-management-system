"""
Storage Health REST API (v1)
Provides endpoints for storage health monitoring and capacity alerting.

Endpoints:
- GET /api/v1/storage/health    - Health status for all storage providers
- GET /api/v1/storage/capacity  - Capacity info (used/total/percent) per provider
- GET /api/v1/storage/alerts    - Active storage capacity alerts (>80% usage)
"""

import logging
from datetime import datetime, timezone

from flask import jsonify

from app.api import api_bp
from app.api.auth import jwt_required, role_required
from app.api.errors import error_response
from app.models import StorageProvider, db

logger = logging.getLogger(__name__)

# Threshold at which a storage provider is considered in alert state
STORAGE_ALERT_THRESHOLD_PERCENT = 80.0


def _usage_percent(provider: StorageProvider) -> float | None:
    """Return used-capacity percentage for a provider, or None if data is unavailable."""
    if provider.total_capacity and provider.total_capacity > 0 and provider.used_capacity is not None:
        return round((provider.used_capacity / provider.total_capacity) * 100, 2)
    return None


def _health_status(provider: StorageProvider) -> str:
    """
    Derive a simple health status string from provider fields.

    Returns one of: "healthy", "warning", "critical", "unknown"
    """
    if not provider.is_active:
        return "unknown"
    if provider.connection_status == "offline":
        return "critical"

    pct = _usage_percent(provider)
    if pct is not None:
        if pct >= 95:
            return "critical"
        if pct >= STORAGE_ALERT_THRESHOLD_PERCENT:
            return "warning"

    if provider.connection_status == "online":
        return "healthy"
    return "unknown"


# ---------------------------------------------------------------------------
# GET /api/v1/storage/health
# ---------------------------------------------------------------------------


@api_bp.route("/v1/storage/health", methods=["GET"])
@jwt_required
def get_storage_health(current_user):
    """
    Return health status for all storage providers.

    Returns:
        200: List of providers with health status
        401: Authentication required
        500: Internal server error
    """
    try:
        providers = StorageProvider.query.order_by(StorageProvider.name).all()

        result = []
        for p in providers:
            pct = _usage_percent(p)
            result.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "provider_type": p.provider_type,
                    "is_active": p.is_active,
                    "connection_status": p.connection_status,
                    "health_status": _health_status(p),
                    "usage_percent": pct,
                    "last_check": p.last_check.isoformat() if p.last_check else None,
                    "success_rate": p.success_rate,
                }
            )

        return (
            jsonify(
                {
                    "success": True,
                    "data": result,
                    "total": len(result),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting storage health: {e}", exc_info=True)
        return error_response(500, "Failed to get storage health", "INTERNAL_ERROR")


# ---------------------------------------------------------------------------
# GET /api/v1/storage/capacity
# ---------------------------------------------------------------------------


@api_bp.route("/v1/storage/capacity", methods=["GET"])
@jwt_required
def get_storage_capacity(current_user):
    """
    Return capacity information (used/total/percent) per storage provider.

    Returns:
        200: Capacity info per provider
        401: Authentication required
        500: Internal server error
    """
    try:
        providers = StorageProvider.query.filter_by(is_active=True).order_by(StorageProvider.name).all()

        result = []
        for p in providers:
            pct = _usage_percent(p)
            free_bytes = None
            if p.total_capacity is not None and p.used_capacity is not None:
                free_bytes = p.total_capacity - p.used_capacity

            result.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "provider_type": p.provider_type,
                    "total_bytes": p.total_capacity,
                    "used_bytes": p.used_capacity,
                    "free_bytes": free_bytes,
                    "usage_percent": pct,
                    "backup_count": p.backup_count,
                    "last_check": p.last_check.isoformat() if p.last_check else None,
                }
            )

        return (
            jsonify(
                {
                    "success": True,
                    "data": result,
                    "total": len(result),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting storage capacity: {e}", exc_info=True)
        return error_response(500, "Failed to get storage capacity", "INTERNAL_ERROR")


# ---------------------------------------------------------------------------
# GET /api/v1/storage/alerts
# ---------------------------------------------------------------------------


@api_bp.route("/v1/storage/alerts", methods=["GET"])
@jwt_required
@role_required("admin", "operator")
def get_storage_alerts(current_user):
    """
    Return active storage capacity alerts for providers exceeding 80% usage.

    Returns:
        200: List of providers with active capacity alerts
        401: Authentication required
        403: Insufficient permissions
        500: Internal server error
    """
    try:
        providers = StorageProvider.query.filter_by(is_active=True).all()

        alerts = []
        for p in providers:
            pct = _usage_percent(p)
            if pct is not None and pct >= STORAGE_ALERT_THRESHOLD_PERCENT:
                severity = "critical" if pct >= 95 else "warning"
                free_bytes = None
                if p.total_capacity is not None and p.used_capacity is not None:
                    free_bytes = p.total_capacity - p.used_capacity

                alerts.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "provider_type": p.provider_type,
                        "connection_status": p.connection_status,
                        "total_bytes": p.total_capacity,
                        "used_bytes": p.used_capacity,
                        "free_bytes": free_bytes,
                        "usage_percent": pct,
                        "severity": severity,
                        "alert_message": (
                            f"Storage '{p.name}' is at {pct:.1f}% capacity "
                            f"({'critical' if pct >= 95 else 'high'} usage)"
                        ),
                        "last_check": p.last_check.isoformat() if p.last_check else None,
                    }
                )

        # Sort by usage descending (most critical first)
        alerts.sort(key=lambda x: x["usage_percent"], reverse=True)

        return (
            jsonify(
                {
                    "success": True,
                    "data": alerts,
                    "total": len(alerts),
                    "threshold_percent": STORAGE_ALERT_THRESHOLD_PERCENT,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error getting storage alerts: {e}", exc_info=True)
        return error_response(500, "Failed to get storage alerts", "INTERNAL_ERROR")
