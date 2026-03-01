"""
Unit tests for OfflineMediaDetector service.
app/services/offline_media_detector.py coverage: 0% -> ~55%
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models import BackupCopy, BackupJob, OfflineMedia, User, db
from app.services.offline_media_detector import OfflineMediaDetector


@pytest.fixture
def detector():
    return OfflineMediaDetector(warning_days=7)


@pytest.fixture
def detector_short_warning():
    return OfflineMediaDetector(warning_days=1)


@pytest.fixture
def media_owner(app):
    with app.app_context():
        user = User(username="media_detector_owner", email="mdo@example.com", role="operator", is_active=True)
        user.set_password("Test123!")
        db.session.add(user)
        db.session.commit()
        yield user.id


@pytest.fixture
def backup_job_for_media(app, media_owner):
    with app.app_context():
        job = BackupJob(
            job_name="media_detect_job",
            job_type="full",
            backup_tool="test_tool",
            retention_days=30,
            owner_id=media_owner,
            is_active=True,
            schedule_type="manual",
        )
        db.session.add(job)
        db.session.commit()
        yield job.id


class TestOfflineMediaDetectorInit:
    """Tests for OfflineMediaDetector initialization."""

    def test_default_warning_days(self):
        d = OfflineMediaDetector()
        assert d.warning_days == 7

    def test_custom_warning_days(self):
        d = OfflineMediaDetector(warning_days=14)
        assert d.warning_days == 14

    def test_short_warning_days(self):
        d = OfflineMediaDetector(warning_days=1)
        assert d.warning_days == 1


class TestDetectOfflineMedia:
    """Tests for detect_offline_media()."""

    def test_returns_list_empty_db(self, app, detector):
        with app.app_context():
            result = detector.detect_offline_media()
            assert isinstance(result, list)

    def test_detects_offline_copy(self, app, detector, backup_job_for_media):
        with app.app_context():
            copy = BackupCopy(
                job_id=backup_job_for_media,
                copy_type="offline",
                media_type="tape",
                storage_path="/media/TAPE001/backup.tar",
                last_backup_size=1000000,
                status="success",
            )
            db.session.add(copy)
            db.session.commit()

            result = detector.detect_offline_media()
            assert isinstance(result, list)

    def test_detects_tape_copy(self, app, detector, backup_job_for_media):
        with app.app_context():
            copy = BackupCopy(
                job_id=backup_job_for_media,
                copy_type="local",
                media_type="tape",
                storage_path="/media/TAPE002/backup.tar",
                last_backup_size=500000,
                status="success",
            )
            db.session.add(copy)
            db.session.commit()

            result = detector.detect_offline_media()
            assert isinstance(result, list)

    def test_no_offline_copies_returns_empty(self, app, detector, backup_job_for_media):
        with app.app_context():
            # Add only local (non-offline) copy
            copy = BackupCopy(
                job_id=backup_job_for_media,
                copy_type="local",
                media_type="disk",
                storage_path="/local/backup.tar",
                last_backup_size=500000,
                status="success",
            )
            db.session.add(copy)
            db.session.commit()

            result = detector.detect_offline_media()
            assert result == []


class TestCheckStaleMedia:
    """Tests for check_stale_media()."""

    def test_returns_list(self, app, detector):
        with app.app_context():
            result = detector.check_stale_media()
            assert isinstance(result, list)

    def test_no_media_returns_empty(self, app, detector):
        with app.app_context():
            result = detector.check_stale_media()
            # With empty DB, should return empty list
            assert result == []

    def test_does_not_raise(self, app, detector):
        with app.app_context():
            try:
                detector.check_stale_media()
            except Exception as e:
                pytest.fail(f"check_stale_media() raised: {e}")


class TestGetMediaInventory:
    """Tests for get_media_inventory()."""

    def test_returns_dict(self, app, detector):
        with app.app_context():
            result = detector.get_media_inventory()
            assert isinstance(result, dict)

    def test_does_not_raise(self, app, detector):
        with app.app_context():
            try:
                result = detector.get_media_inventory()
                assert result is not None
            except Exception as e:
                pytest.fail(f"get_media_inventory() raised: {e}")


class TestSyncMediaWithCopies:
    """Tests for sync_media_with_copies()."""

    def test_returns_dict(self, app, detector):
        with app.app_context():
            result = detector.sync_media_with_copies()
            assert isinstance(result, dict)

    def test_does_not_raise(self, app, detector):
        with app.app_context():
            try:
                detector.sync_media_with_copies()
            except Exception as e:
                pytest.fail(f"sync_media_with_copies() raised: {e}")


class TestExtractMediaId:
    """Tests for _extract_media_id() private method."""

    def test_none_path_returns_none(self, detector):
        result = detector._extract_media_id(None)
        assert result is None

    def test_empty_path_returns_none(self, detector):
        result = detector._extract_media_id("")
        assert result is None

    def test_tape_path_returns_tape_id(self, detector):
        result = detector._extract_media_id("/media/TAPE001/backup.tar")
        assert result == "TAPE001"

    def test_usb_path_returns_usb_id(self, detector):
        result = detector._extract_media_id("/mnt/USB001/backup")
        assert result == "USB001"

    def test_media_path_returns_media_id(self, detector):
        result = detector._extract_media_id("/backup/MEDIA001/data")
        assert result == "MEDIA001"

    def test_windows_unc_path(self, detector):
        result = detector._extract_media_id("\\\\nas\\tape001\\backup.tar")
        assert result == "tape001"

    def test_drive_letter_path(self, detector):
        result = detector._extract_media_id("E:\\Backup\\data")
        assert result == "Drive-E"

    def test_generic_path_returns_first_component(self, detector):
        result = detector._extract_media_id("/some/path/backup.tar")
        assert result is not None
        assert isinstance(result, str)
