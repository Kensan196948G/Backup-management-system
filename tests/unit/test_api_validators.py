"""
Unit tests for app/api/validators.py
Pure validation functions - no Flask/DB dependencies.
"""

import pytest
from datetime import datetime


class TestValidateRequiredFields:
    """Tests for validate_required_fields()"""

    def test_all_present(self):
        from app.api.validators import validate_required_fields
        data = {"name": "test", "source": "/data"}
        errors = validate_required_fields(data, ["name", "source"])
        assert errors == {}

    def test_missing_field(self):
        from app.api.validators import validate_required_fields
        data = {"name": "test"}
        errors = validate_required_fields(data, ["name", "source"])
        assert "source" in errors

    def test_none_value(self):
        from app.api.validators import validate_required_fields
        data = {"name": None}
        errors = validate_required_fields(data, ["name"])
        assert "name" in errors

    def test_empty_string(self):
        from app.api.validators import validate_required_fields
        data = {"name": "   "}
        errors = validate_required_fields(data, ["name"])
        assert "name" in errors

    def test_empty_required_list(self):
        from app.api.validators import validate_required_fields
        errors = validate_required_fields({}, [])
        assert errors == {}

    def test_multiple_missing(self):
        from app.api.validators import validate_required_fields
        errors = validate_required_fields({}, ["a", "b", "c"])
        assert len(errors) == 3


class TestValidateEnumField:
    """Tests for validate_enum_field()"""

    def test_valid_value(self):
        from app.api.validators import validate_enum_field
        data = {"type": "full"}
        result = validate_enum_field(data, "type", ["full", "incremental"])
        assert result is None

    def test_invalid_value(self):
        from app.api.validators import validate_enum_field
        data = {"type": "mirror"}
        result = validate_enum_field(data, "type", ["full", "incremental"])
        assert result is not None
        assert "full" in result

    def test_field_absent(self):
        from app.api.validators import validate_enum_field
        data = {}
        result = validate_enum_field(data, "type", ["full"])
        assert result is None


class TestValidateIntegerField:
    """Tests for validate_integer_field()"""

    def test_valid_integer(self):
        from app.api.validators import validate_integer_field
        data = {"count": 5}
        result = validate_integer_field(data, "count", min_value=1, max_value=10)
        assert result is None

    def test_below_min(self):
        from app.api.validators import validate_integer_field
        data = {"count": 0}
        result = validate_integer_field(data, "count", min_value=1)
        assert result is not None
        assert "1" in result

    def test_above_max(self):
        from app.api.validators import validate_integer_field
        data = {"count": 200}
        result = validate_integer_field(data, "count", max_value=100)
        assert result is not None
        assert "100" in result

    def test_non_integer(self):
        from app.api.validators import validate_integer_field
        data = {"count": "abc"}
        result = validate_integer_field(data, "count")
        assert result is not None

    def test_field_absent(self):
        from app.api.validators import validate_integer_field
        result = validate_integer_field({}, "count")
        assert result is None

    def test_field_none(self):
        from app.api.validators import validate_integer_field
        result = validate_integer_field({"count": None}, "count")
        assert result is None

    def test_string_integer(self):
        from app.api.validators import validate_integer_field
        data = {"count": "5"}
        result = validate_integer_field(data, "count", min_value=1, max_value=10)
        assert result is None


class TestValidateDateField:
    """Tests for validate_date_field()"""

    def test_valid_date(self):
        from app.api.validators import validate_date_field
        data = {"date": "2025-01-15"}
        result = validate_date_field(data, "date")
        assert result is None

    def test_invalid_date_format(self):
        from app.api.validators import validate_date_field
        data = {"date": "15/01/2025"}
        result = validate_date_field(data, "date")
        assert result is not None

    def test_field_absent(self):
        from app.api.validators import validate_date_field
        result = validate_date_field({}, "date")
        assert result is None

    def test_empty_string(self):
        from app.api.validators import validate_date_field
        result = validate_date_field({"date": ""}, "date")
        assert result is None

    def test_custom_format(self):
        from app.api.validators import validate_date_field
        data = {"date": "15-01-2025"}
        result = validate_date_field(data, "date", date_format="%d-%m-%Y")
        assert result is None


class TestValidateDatetimeField:
    """Tests for validate_datetime_field()"""

    def test_valid_iso_datetime(self):
        from app.api.validators import validate_datetime_field
        data = {"dt": "2025-01-15T10:30:00"}
        result = validate_datetime_field(data, "dt")
        assert result is None

    def test_valid_utc_datetime(self):
        from app.api.validators import validate_datetime_field
        data = {"dt": "2025-01-15T10:30:00Z"}
        result = validate_datetime_field(data, "dt")
        assert result is None

    def test_invalid_datetime(self):
        from app.api.validators import validate_datetime_field
        data = {"dt": "not-a-date"}
        result = validate_datetime_field(data, "dt")
        assert result is not None

    def test_field_absent(self):
        from app.api.validators import validate_datetime_field
        result = validate_datetime_field({}, "dt")
        assert result is None


class TestValidateBooleanField:
    """Tests for validate_boolean_field()"""

    def test_true_value(self):
        from app.api.validators import validate_boolean_field
        result = validate_boolean_field({"flag": True}, "flag")
        assert result is None

    def test_false_value(self):
        from app.api.validators import validate_boolean_field
        result = validate_boolean_field({"flag": False}, "flag")
        assert result is None

    def test_string_true_invalid(self):
        from app.api.validators import validate_boolean_field
        result = validate_boolean_field({"flag": "true"}, "flag")
        assert result is not None

    def test_field_absent(self):
        from app.api.validators import validate_boolean_field
        result = validate_boolean_field({}, "flag")
        assert result is None

    def test_none_value(self):
        from app.api.validators import validate_boolean_field
        result = validate_boolean_field({"flag": None}, "flag")
        assert result is None


class TestValidateEmailField:
    """Tests for validate_email_field()"""

    def test_valid_email(self):
        from app.api.validators import validate_email_field
        result = validate_email_field({"email": "user@example.com"}, "email")
        assert result is None

    def test_missing_at_sign(self):
        from app.api.validators import validate_email_field
        result = validate_email_field({"email": "userexample.com"}, "email")
        assert result is not None

    def test_missing_dot_in_domain(self):
        from app.api.validators import validate_email_field
        result = validate_email_field({"email": "user@example"}, "email")
        assert result is not None

    def test_non_string(self):
        from app.api.validators import validate_email_field
        result = validate_email_field({"email": 12345}, "email")
        assert result is not None

    def test_field_absent(self):
        from app.api.validators import validate_email_field
        result = validate_email_field({}, "email")
        assert result is None

    def test_empty_string(self):
        from app.api.validators import validate_email_field
        result = validate_email_field({"email": ""}, "email")
        assert result is None


class TestValidateStringLength:
    """Tests for validate_string_length()"""

    def test_valid_length(self):
        from app.api.validators import validate_string_length
        result = validate_string_length({"name": "hello"}, "name", min_length=2, max_length=10)
        assert result is None

    def test_too_short(self):
        from app.api.validators import validate_string_length
        result = validate_string_length({"name": "a"}, "name", min_length=3)
        assert result is not None
        assert "3" in result

    def test_too_long(self):
        from app.api.validators import validate_string_length
        result = validate_string_length({"name": "x" * 50}, "name", max_length=20)
        assert result is not None
        assert "20" in result

    def test_field_absent(self):
        from app.api.validators import validate_string_length
        result = validate_string_length({}, "name", min_length=1)
        assert result is None

    def test_field_none(self):
        from app.api.validators import validate_string_length
        result = validate_string_length({"name": None}, "name", min_length=1)
        assert result is None


class TestValidateListField:
    """Tests for validate_list_field()"""

    def test_valid_list(self):
        from app.api.validators import validate_list_field
        result = validate_list_field({"items": [1, 2, 3]}, "items", min_items=1, max_items=5)
        assert result is None

    def test_not_a_list(self):
        from app.api.validators import validate_list_field
        result = validate_list_field({"items": "hello"}, "items")
        assert result is not None

    def test_too_few_items(self):
        from app.api.validators import validate_list_field
        result = validate_list_field({"items": []}, "items", min_items=1)
        assert result is not None

    def test_too_many_items(self):
        from app.api.validators import validate_list_field
        result = validate_list_field({"items": list(range(20))}, "items", max_items=10)
        assert result is not None

    def test_field_absent(self):
        from app.api.validators import validate_list_field
        result = validate_list_field({}, "items", min_items=1)
        assert result is None


class TestParseDateSafe:
    """Tests for parse_date_safe()"""

    def test_valid_date(self):
        from app.api.validators import parse_date_safe
        result = parse_date_safe("2025-01-15")
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_invalid_date(self):
        from app.api.validators import parse_date_safe
        result = parse_date_safe("not-a-date")
        assert result is None

    def test_custom_format(self):
        from app.api.validators import parse_date_safe
        result = parse_date_safe("15/01/2025", date_format="%d/%m/%Y")
        assert isinstance(result, datetime)

    def test_none_input(self):
        from app.api.validators import parse_date_safe
        result = parse_date_safe(None)
        assert result is None


class TestParseDatetimeSafe:
    """Tests for parse_datetime_safe()"""

    def test_valid_iso(self):
        from app.api.validators import parse_datetime_safe
        result = parse_datetime_safe("2025-01-15T10:30:00")
        assert isinstance(result, datetime)

    def test_utc_z(self):
        from app.api.validators import parse_datetime_safe
        result = parse_datetime_safe("2025-01-15T10:30:00Z")
        assert isinstance(result, datetime)

    def test_invalid(self):
        from app.api.validators import parse_datetime_safe
        result = parse_datetime_safe("not-a-datetime")
        assert result is None

    def test_none(self):
        from app.api.validators import parse_datetime_safe
        result = parse_datetime_safe(None)
        assert result is None


class TestSanitizeString:
    """Tests for sanitize_string()"""

    def test_strips_whitespace(self):
        from app.api.validators import sanitize_string
        assert sanitize_string("  hello  ") == "hello"

    def test_truncates_to_max_length(self):
        from app.api.validators import sanitize_string
        result = sanitize_string("hello world", max_length=5)
        assert result == "hello"
        assert len(result) == 5

    def test_non_string_converted(self):
        from app.api.validators import sanitize_string
        result = sanitize_string(12345)
        assert result == "12345"

    def test_no_max_length(self):
        from app.api.validators import sanitize_string
        result = sanitize_string("  test  ")
        assert result == "test"


class TestValidatePaginationParams:
    """Tests for validate_pagination_params()"""

    def test_valid_params(self):
        from app.api.validators import validate_pagination_params
        errors = validate_pagination_params(1, 20)
        assert errors == {}

    def test_page_zero(self):
        from app.api.validators import validate_pagination_params
        errors = validate_pagination_params(0, 20)
        assert "page" in errors

    def test_per_page_zero(self):
        from app.api.validators import validate_pagination_params
        errors = validate_pagination_params(1, 0)
        assert "per_page" in errors

    def test_per_page_exceeds_max(self):
        from app.api.validators import validate_pagination_params
        errors = validate_pagination_params(1, 500, max_per_page=100)
        assert "per_page" in errors

    def test_custom_max(self):
        from app.api.validators import validate_pagination_params
        errors = validate_pagination_params(1, 200, max_per_page=200)
        assert errors == {}
