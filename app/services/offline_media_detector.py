"""
Offline Media Detector Service
Automatically detects and manages offline backup media
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.models import BackupCopy, BackupJob, OfflineMedia, db

logger = logging.getLogger(__name__)


class OfflineMediaDetector:
    """
    Detects and manages offline backup media.

    Responsibilities:
    - Auto-detect offline media from backup copies
    - Update media inventory
    - Track media rotation
    - Alert on stale offline backups
    """

    def __init__(self, warning_days: int = 7):
        """
        Initialize offline media detector.

        Args:
            warning_days: Days before alerting on stale media
        """
        self.warning_days = warning_days

    def detect_offline_media(self) -> List[Dict]:
        """
        Detect all offline media from backup copies.

        Returns:
            List of detected offline media with metadata
        """
        try:
            logger.info("Starting offline media detection...")

            # Query backup copies marked as offline or tape
            offline_copies = BackupCopy.query.filter(
                db.or_(BackupCopy.copy_type == "offline", BackupCopy.media_type == "tape")
            ).all()

            detected_media = []

            for copy in offline_copies:
                # Extract media identifier from storage path
                media_id = self._extract_media_id(copy.storage_path)

                if not media_id:
                    logger.warning(f"Could not extract media ID from path: {copy.storage_path}")
                    continue

                # Check if media already exists
                media = OfflineMedia.query.filter_by(media_id=media_id).first()

                if not media:
                    # Create new media record
                    media = self._create_media_record(copy, media_id)
                    logger.info(f"New offline media detected: {media_id}")
                else:
                    # Update existing media record
                    self._update_media_record(media, copy)
                    logger.debug(f"Updated offline media: {media_id}")

                detected_media.append(
                    {
                        "media_id": media.media_id,
                        "media_type": media.media_type,
                        "storage_location": media.storage_location,
                        "current_status": media.current_status,
                        "last_backup_date": copy.last_backup_date,
                        "capacity_bytes": media.capacity_bytes,
                        "used_bytes": media.used_bytes,
                    }
                )

            db.session.commit()

            logger.info(f"Offline media detection completed: {len(detected_media)} media found")

            return detected_media

        except Exception as e:
            logger.error(f"Error detecting offline media: {str(e)}", exc_info=True)
            db.session.rollback()
            return []

    def check_stale_media(self) -> List[Dict]:
        """
        Check for stale offline media that haven't been updated.

        Returns:
            List of stale media with alert information
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.warning_days)

            # Find media with old backup dates
            stale_media = OfflineMedia.query.filter(
                OfflineMedia.current_status.in_(["in_use", "stored"]),
                db.or_(OfflineMedia.last_used_date < cutoff_date, OfflineMedia.last_used_date.is_(None)),
            ).all()

            alerts = []

            for media in stale_media:
                age_days = None
                if media.last_used_date:
                    age_days = (datetime.utcnow() - media.last_used_date).days

                alert = {
                    "media_id": media.media_id,
                    "media_type": media.media_type,
                    "storage_location": media.storage_location,
                    "last_used_date": media.last_used_date.isoformat() if media.last_used_date else None,
                    "age_days": age_days,
                    "warning_threshold_days": self.warning_days,
                    "message": f"Offline media '{media.media_id}' has not been updated for " f"{age_days or 'unknown'} days",
                }

                alerts.append(alert)

            if alerts:
                logger.warning(f"Found {len(alerts)} stale offline media")

            return alerts

        except Exception as e:
            logger.error(f"Error checking stale media: {str(e)}", exc_info=True)
            return []

    def sync_media_with_copies(self) -> Dict:
        """
        Synchronize offline media inventory with backup copies.

        Returns:
            Statistics about the synchronization
        """
        try:
            logger.info("Synchronizing offline media with backup copies...")

            stats = {"total_media": 0, "updated_media": 0, "new_media": 0, "retired_media": 0, "errors": 0}

            # Get all offline media
            all_media = OfflineMedia.query.all()
            stats["total_media"] = len(all_media)

            # Detect and update from copies
            detected = self.detect_offline_media()
            stats["new_media"] = len([m for m in detected if m])

            # Mark media as retired if no recent copies
            cutoff_date = datetime.utcnow() - timedelta(days=90)  # 90 days

            for media in all_media:
                # Find related copies
                recent_copies = BackupCopy.query.filter(
                    BackupCopy.storage_path.contains(media.media_id), BackupCopy.last_backup_date >= cutoff_date
                ).count()

                if recent_copies == 0 and media.current_status != "retired":
                    media.current_status = "retired"
                    stats["retired_media"] += 1
                    logger.info(f"Media {media.media_id} marked as retired (no recent backups)")

            db.session.commit()

            logger.info(f"Media synchronization completed: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Error synchronizing media: {str(e)}", exc_info=True)
            db.session.rollback()
            return {"error": str(e)}

    def get_media_inventory(self) -> Dict:
        """
        Get current offline media inventory summary.

        Returns:
            Inventory statistics
        """
        try:
            all_media = OfflineMedia.query.all()

            inventory = {
                "total_media": len(all_media),
                "by_status": {"in_use": 0, "available": 0, "stored": 0, "retired": 0, "lent": 0},
                "by_type": {"tape": 0, "external_hdd": 0, "usb": 0, "optical": 0, "other": 0},
                "total_capacity_gb": 0,
                "total_used_gb": 0,
                "media_list": [],
            }

            for media in all_media:
                # Count by status
                if media.current_status in inventory["by_status"]:
                    inventory["by_status"][media.current_status] += 1

                # Count by type
                media_type = media.media_type or "other"
                if media_type in inventory["by_type"]:
                    inventory["by_type"][media_type] += 1
                else:
                    inventory["by_type"]["other"] += 1

                # Calculate capacity
                if media.capacity_bytes:
                    inventory["total_capacity_gb"] += media.capacity_bytes / (1024**3)
                if media.used_bytes:
                    inventory["total_used_gb"] += media.used_bytes / (1024**3)

                # Add to list
                inventory["media_list"].append(
                    {
                        "media_id": media.media_id,
                        "media_type": media.media_type,
                        "status": media.current_status,
                        "location": media.storage_location,
                        "last_used": media.last_used_date.isoformat() if media.last_used_date else None,
                    }
                )

            inventory["total_capacity_gb"] = round(inventory["total_capacity_gb"], 2)
            inventory["total_used_gb"] = round(inventory["total_used_gb"], 2)

            return inventory

        except Exception as e:
            logger.error(f"Error getting media inventory: {str(e)}", exc_info=True)
            return {}

    def _extract_media_id(self, storage_path: str) -> Optional[str]:
        """
        Extract media identifier from storage path.

        Args:
            storage_path: Storage path string

        Returns:
            Media ID or None
        """
        if not storage_path:
            return None

        # Common patterns for media identifiers
        # Examples:
        # - "\\\\nas\\tape001\\backup.tar"
        # - "/mnt/external/USB-001/data"
        # - "E:\\Backup\\Media-A01"

        parts = storage_path.replace("\\", "/").split("/")

        # Look for parts with identifiable patterns
        for part in parts:
            # Check for tape identifiers
            if "tape" in part.lower() and any(c.isdigit() for c in part):
                return part

            # Check for USB identifiers
            if "usb" in part.lower() and any(c.isdigit() for c in part):
                return part

            # Check for media identifiers
            if "media" in part.lower() and any(c.isdigit() for c in part):
                return part

            # Check for drive letters
            if len(part) == 2 and part[1] == ":" and part[0].isalpha():
                return f"Drive-{part[0]}"

        # Fallback: use the first meaningful directory name
        for part in parts:
            if part and part not in [".", "..", ""]:
                return part[:50]  # Limit length

        return None

    def _create_media_record(self, copy: BackupCopy, media_id: str) -> OfflineMedia:
        """
        Create new offline media record.

        Args:
            copy: BackupCopy object
            media_id: Media identifier

        Returns:
            Created OfflineMedia object
        """
        media = OfflineMedia(
            media_id=media_id,
            media_type=copy.media_type or "external_hdd",
            storage_location=copy.storage_path,
            current_status="in_use" if copy.status == "active" else "available",
            last_used_date=copy.last_backup_date or datetime.utcnow(),
            capacity_bytes=None,  # Unknown initially
            used_bytes=copy.backup_size_bytes or 0,
            purchase_date=datetime.utcnow(),
        )

        db.session.add(media)

        return media

    def _update_media_record(self, media: OfflineMedia, copy: BackupCopy) -> None:
        """
        Update existing offline media record.

        Args:
            media: OfflineMedia object
            copy: BackupCopy object
        """
        # Update last used date
        if copy.last_backup_date and (not media.last_used_date or copy.last_backup_date > media.last_used_date):
            media.last_used_date = copy.last_backup_date

        # Update used bytes
        if copy.backup_size_bytes:
            media.used_bytes = max(media.used_bytes or 0, copy.backup_size_bytes)

        # Update status
        if copy.status == "active" and media.current_status == "available":
            media.current_status = "in_use"

        # Update storage location if changed
        if copy.storage_path != media.storage_location:
            media.storage_location = copy.storage_path
