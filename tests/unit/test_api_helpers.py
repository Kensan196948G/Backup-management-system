"""
Unit tests for app/api/helpers.py
Pure utility functions for API endpoints.
"""

import pytest
from datetime import datetime, date, timezone
from unittest.mock import MagicMock, patch


class TestFormatDatetime:
    """Tests for format_datetime()"""

    def test_none_returns_none(self, app):
        with app.app_context():
            from app.api.helpers import format_datetime
            assert format_datetime(None) is None

    def test_datetime_appends_z(self, app):
        with app.app_context():
            from app.api.helpers import format_datetime
            dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            result = format_datetime(dt)
            assert result.endswith("Z")
            assert "2025-01-15" in result
            assert "10:30:00" in result

    def test_naive_datetime(self, app):
        with app.app_context():
            from app.api.helpers import format_datetime
            dt = datetime(2025, 6, 1, 0, 0, 0)
            result = format_datetime(dt)
            assert result.endswith("Z")
            assert "2025-06-01" in result


class TestFormatDate:
    """Tests for format_date()"""

    def test_none_returns_none(self, app):
        with app.app_context():
            from app.api.helpers import format_date
            assert format_date(None) is None

    def test_date_returns_iso_string(self, app):
        with app.app_context():
            from app.api.helpers import format_date
            d = date(2025, 3, 15)
            result = format_date(d)
            assert result == "2025-03-15"


class TestFormatBytes:
    """Tests for format_bytes()"""

    def test_none_returns_none(self, app):
        with app.app_context():
            from app.api.helpers import format_bytes
            assert format_bytes(None) is None

    def test_zero_bytes(self, app):
        with app.app_context():
            from app.api.helpers import format_bytes
            assert format_bytes(0) == "0 B"

    def test_bytes(self, app):
        with app.app_context():
            from app.api.helpers import format_bytes
            assert format_bytes(512) == "512.00 B"

    def test_kilobytes(self, app):
        with app.app_context():
            from app.api.helpers import format_bytes
            assert format_bytes(1024) == "1.00 KB"

    def test_megabytes(self, app):
        with app.app_context():
            from app.api.helpers import format_bytes
            result = format_bytes(1024 * 1024)
            assert result == "1.00 MB"

    def test_gigabytes(self, app):
        with app.app_context():
            from app.api.helpers import format_bytes
            result = format_bytes(1024 ** 3)
            assert result == "1.00 GB"

    def test_terabytes(self, app):
        with app.app_context():
            from app.api.helpers import format_bytes
            result = format_bytes(1024 ** 4)
            assert result == "1.00 TB"

    def test_large_value(self, app):
        with app.app_context():
            from app.api.helpers import format_bytes
            result = format_bytes(1536)  # 1.5 KB
            assert result == "1.50 KB"


class TestFormatDuration:
    """Tests for format_duration()"""

    def test_none_returns_none(self, app):
        with app.app_context():
            from app.api.helpers import format_duration
            assert format_duration(None) is None

    def test_zero_seconds(self, app):
        with app.app_context():
            from app.api.helpers import format_duration
            assert format_duration(0) == "0s"

    def test_seconds_only(self, app):
        with app.app_context():
            from app.api.helpers import format_duration
            assert format_duration(45) == "45s"

    def test_minutes_and_seconds(self, app):
        with app.app_context():
            from app.api.helpers import format_duration
            result = format_duration(90)  # 1m 30s
            assert "1m" in result
            assert "30s" in result

    def test_hours_minutes_seconds(self, app):
        with app.app_context():
            from app.api.helpers import format_duration
            result = format_duration(3661)  # 1h 1m 1s
            assert "1h" in result
            assert "1m" in result
            assert "1s" in result

    def test_exact_hour(self, app):
        with app.app_context():
            from app.api.helpers import format_duration
            result = format_duration(3600)
            assert "1h" in result
            assert "0m" not in result
            assert "0s" not in result


class TestCalculatePercentage:
    """Tests for calculate_percentage()"""

    def test_normal_percentage(self, app):
        with app.app_context():
            from app.api.helpers import calculate_percentage
            assert calculate_percentage(50, 100) == 50.0

    def test_zero_total_returns_zero(self, app):
        with app.app_context():
            from app.api.helpers import calculate_percentage
            assert calculate_percentage(10, 0) == 0.0

    def test_full_percentage(self, app):
        with app.app_context():
            from app.api.helpers import calculate_percentage
            assert calculate_percentage(100, 100) == 100.0

    def test_decimal_places(self, app):
        with app.app_context():
            from app.api.helpers import calculate_percentage
            result = calculate_percentage(1, 3, decimal_places=4)
            assert result == round((1/3) * 100, 4)

    def test_partial_percentage(self, app):
        with app.app_context():
            from app.api.helpers import calculate_percentage
            result = calculate_percentage(1, 4)
            assert result == 25.0


class TestSanitizeFilename:
    """Tests for sanitize_filename()"""

    def test_normal_filename(self, app):
        with app.app_context():
            from app.api.helpers import sanitize_filename
            result = sanitize_filename("backup_2025.log")
            assert result == "backup_2025.log"

    def test_spaces_replaced(self, app):
        with app.app_context():
            from app.api.helpers import sanitize_filename
            result = sanitize_filename("my backup file.tar.gz")
            assert " " not in result
            assert "_" in result

    def test_special_chars_removed(self, app):
        with app.app_context():
            from app.api.helpers import sanitize_filename
            result = sanitize_filename("file@#$%.txt")
            assert "@" not in result
            assert "#" not in result
            assert "$" not in result

    def test_valid_chars_kept(self, app):
        with app.app_context():
            from app.api.helpers import sanitize_filename
            result = sanitize_filename("backup-2025_01.tar.gz")
            assert "backup" in result
            assert "2025" in result


class TestIsValidUuid:
    """Tests for is_valid_uuid()"""

    def test_valid_uuid(self, app):
        with app.app_context():
            from app.api.helpers import is_valid_uuid
            assert is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_invalid_uuid_short(self, app):
        with app.app_context():
            from app.api.helpers import is_valid_uuid
            assert is_valid_uuid("not-a-uuid") is False

    def test_empty_string(self, app):
        with app.app_context():
            from app.api.helpers import is_valid_uuid
            assert is_valid_uuid("") is False

    def test_uuid_uppercase(self, app):
        with app.app_context():
            from app.api.helpers import is_valid_uuid
            assert is_valid_uuid("550E8400-E29B-41D4-A716-446655440000") is True

    def test_uuid_without_dashes(self, app):
        with app.app_context():
            from app.api.helpers import is_valid_uuid
            assert is_valid_uuid("550e8400e29b41d4a716446655440000") is False


class TestGetPaginationParams:
    """Tests for get_pagination_params()"""

    def test_defaults(self, client):
        with client.application.test_request_context("/?"):
            from app.api.helpers import get_pagination_params
            page, per_page = get_pagination_params()
            assert page == 1
            assert per_page == 20

    def test_custom_values(self, client):
        with client.application.test_request_context("/?page=3&per_page=50"):
            from app.api.helpers import get_pagination_params
            page, per_page = get_pagination_params()
            assert page == 3
            assert per_page == 50

    def test_page_minimum_1(self, client):
        with client.application.test_request_context("/?page=0"):
            from app.api.helpers import get_pagination_params
            page, per_page = get_pagination_params()
            assert page == 1

    def test_per_page_capped_at_max(self, client):
        with client.application.test_request_context("/?per_page=500"):
            from app.api.helpers import get_pagination_params
            page, per_page = get_pagination_params(max_per_page=100)
            assert per_page == 100

    def test_per_page_minimum_1(self, client):
        with client.application.test_request_context("/?per_page=0"):
            from app.api.helpers import get_pagination_params
            page, per_page = get_pagination_params()
            assert per_page == 1


class TestParseBooleanParam:
    """Tests for parse_boolean_param()"""

    def test_true_values(self, client):
        for val in ["true", "1", "yes", "on"]:
            with client.application.test_request_context(f"/?flag={val}"):
                from app.api.helpers import parse_boolean_param
                assert parse_boolean_param("flag") is True

    def test_false_values(self, client):
        for val in ["false", "0", "no", "off"]:
            with client.application.test_request_context(f"/?flag={val}"):
                from app.api.helpers import parse_boolean_param
                assert parse_boolean_param("flag") is False

    def test_default_when_absent(self, client):
        with client.application.test_request_context("/?"):
            from app.api.helpers import parse_boolean_param
            assert parse_boolean_param("flag", default=True) is True
            assert parse_boolean_param("flag", default=False) is False

    def test_unknown_value_uses_default(self, client):
        with client.application.test_request_context("/?flag=maybe"):
            from app.api.helpers import parse_boolean_param
            assert parse_boolean_param("flag", default=False) is False


class TestFormatPaginationResponse:
    """Tests for format_pagination_response()"""

    def test_basic_pagination(self, app):
        with app.app_context():
            from app.api.helpers import format_pagination_response
            mock_pagination = MagicMock()
            mock_pagination.page = 2
            mock_pagination.per_page = 10
            mock_pagination.total = 55
            mock_pagination.pages = 6
            mock_pagination.has_next = True
            mock_pagination.has_prev = True

            result = format_pagination_response(mock_pagination)
            assert result["page"] == 2
            assert result["per_page"] == 10
            assert result["total"] == 55
            assert result["pages"] == 6
            assert result["has_next"] is True
            assert result["has_prev"] is True


class TestGetFilterParams:
    """Tests for get_filter_params()"""

    def test_allowed_filters_extracted(self, client):
        with client.application.test_request_context("/?status=active&type=full"):
            from app.api.helpers import get_filter_params
            result = get_filter_params(["status", "type"])
            assert result["status"] == "active"
            assert result["type"] == "full"

    def test_disallowed_filters_excluded(self, client):
        with client.application.test_request_context("/?status=active&secret=value"):
            from app.api.helpers import get_filter_params
            result = get_filter_params(["status"])
            assert "secret" not in result
            assert "status" in result

    def test_empty_request(self, client):
        with client.application.test_request_context("/?"):
            from app.api.helpers import get_filter_params
            result = get_filter_params(["status", "type"])
            assert result == {}


class TestExtractSortParams:
    """Tests for extract_sort_params()"""

    def test_defaults(self, client):
        with client.application.test_request_context("/?"):
            from app.api.helpers import extract_sort_params
            sort_field, sort_order = extract_sort_params()
            assert sort_field == "created_at"
            assert sort_order == "desc"

    def test_custom_sort(self, client):
        with client.application.test_request_context("/?sort=name&order=asc"):
            from app.api.helpers import extract_sort_params
            sort_field, sort_order = extract_sort_params(allowed_fields=["name", "created_at"])
            assert sort_field == "name"
            assert sort_order == "asc"

    def test_invalid_sort_field_uses_default(self, client):
        with client.application.test_request_context("/?sort=invalid_field"):
            from app.api.helpers import extract_sort_params
            sort_field, sort_order = extract_sort_params(
                default_sort="id",
                allowed_fields=["id", "name"]
            )
            assert sort_field == "id"

    def test_invalid_order_uses_default(self, client):
        with client.application.test_request_context("/?order=sideways"):
            from app.api.helpers import extract_sort_params
            sort_field, sort_order = extract_sort_params(default_order="asc")
            assert sort_order == "asc"


class TestGetDateRangeParams:
    """Tests for get_date_range_params()"""

    def test_with_dates(self, client):
        with client.application.test_request_context("/?date_from=2025-01-01&date_to=2025-12-31"):
            from app.api.helpers import get_date_range_params
            date_from, date_to = get_date_range_params()
            assert date_from == "2025-01-01"
            assert date_to == "2025-12-31"

    def test_without_dates(self, client):
        with client.application.test_request_context("/?"):
            from app.api.helpers import get_date_range_params
            date_from, date_to = get_date_range_params()
            assert date_from is None
            assert date_to is None
