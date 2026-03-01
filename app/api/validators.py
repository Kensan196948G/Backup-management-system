"""
API Input Validators
Common validation functions for API endpoints
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, str]:
    """
    Validate that required fields are present in request data

    Args:
        data: Request data dictionary
        required_fields: List of required field names

    Returns:
        Dictionary of validation errors (empty if valid)
    """
    errors = {}
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            errors[field] = f"{field} is required"
    return errors


def validate_enum_field(data: Dict[str, Any], field: str, valid_values: List[str]) -> Optional[str]:
    """
    Validate that a field value is one of the allowed values

    Args:
        data: Request data dictionary
        field: Field name to validate
        valid_values: List of valid values

    Returns:
        Error message if invalid, None if valid or field not present
    """
    if field in data and data[field] not in valid_values:
        return f'Must be one of: {", ".join(valid_values)}'
    return None


def validate_integer_field(
    data: Dict[str, Any], field: str, min_value: Optional[int] = None, max_value: Optional[int] = None
) -> Optional[str]:
    """
    Validate that a field is a valid integer within range

    Args:
        data: Request data dictionary
        field: Field name to validate
        min_value: Minimum allowed value (optional)
        max_value: Maximum allowed value (optional)

    Returns:
        Error message if invalid, None if valid or field not present
    """
    if field not in data or data[field] is None:
        return None

    try:
        value = int(data[field])
        if min_value is not None and value < min_value:
            return f"Must be at least {min_value}"
        if max_value is not None and value > max_value:
            return f"Must be at most {max_value}"
    except (ValueError, TypeError):
        return "Must be a valid integer"

    return None


def validate_date_field(data: Dict[str, Any], field: str, date_format: str = "%Y-%m-%d") -> Optional[str]:
    """
    Validate that a field is a valid date string

    Args:
        data: Request data dictionary
        field: Field name to validate
        date_format: Expected date format (default: YYYY-MM-DD)

    Returns:
        Error message if invalid, None if valid or field not present
    """
    if field not in data or not data[field]:
        return None

    try:
        datetime.strptime(data[field], date_format)
    except ValueError:
        return f"Invalid date format. Use {date_format}"

    return None


def validate_datetime_field(data: Dict[str, Any], field: str) -> Optional[str]:
    """
    Validate that a field is a valid ISO 8601 datetime string

    Args:
        data: Request data dictionary
        field: Field name to validate

    Returns:
        Error message if invalid, None if valid or field not present
    """
    if field not in data or not data[field]:
        return None

    try:
        datetime.fromisoformat(data[field].replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return "Invalid datetime format. Use ISO 8601 format"

    return None


def validate_boolean_field(data: Dict[str, Any], field: str) -> Optional[str]:
    """
    Validate that a field is a valid boolean

    Args:
        data: Request data dictionary
        field: Field name to validate

    Returns:
        Error message if invalid, None if valid or field not present
    """
    if field not in data or data[field] is None:
        return None

    if not isinstance(data[field], bool):
        return "Must be a boolean (true/false)"

    return None


def validate_email_field(data: Dict[str, Any], field: str) -> Optional[str]:
    """
    Validate that a field is a valid email address

    Args:
        data: Request data dictionary
        field: Field name to validate

    Returns:
        Error message if invalid, None if valid or field not present
    """
    if field not in data or not data[field]:
        return None

    email = data[field]
    if not isinstance(email, str):
        return "Must be a string"

    # Simple email validation
    if "@" not in email or "." not in email.split("@")[1]:
        return "Must be a valid email address"

    return None


def validate_string_length(
    data: Dict[str, Any], field: str, min_length: Optional[int] = None, max_length: Optional[int] = None
) -> Optional[str]:
    """
    Validate string length

    Args:
        data: Request data dictionary
        field: Field name to validate
        min_length: Minimum length (optional)
        max_length: Maximum length (optional)

    Returns:
        Error message if invalid, None if valid or field not present
    """
    if field not in data or data[field] is None:
        return None

    value = str(data[field])
    length = len(value)

    if min_length is not None and length < min_length:
        return f"Must be at least {min_length} characters"
    if max_length is not None and length > max_length:
        return f"Must be at most {max_length} characters"

    return None


def validate_list_field(
    data: Dict[str, Any], field: str, min_items: Optional[int] = None, max_items: Optional[int] = None
) -> Optional[str]:
    """
    Validate that a field is a list with item count within range

    Args:
        data: Request data dictionary
        field: Field name to validate
        min_items: Minimum number of items (optional)
        max_items: Maximum number of items (optional)

    Returns:
        Error message if invalid, None if valid or field not present
    """
    if field not in data or data[field] is None:
        return None

    if not isinstance(data[field], list):
        return "Must be a list"

    length = len(data[field])

    if min_items is not None and length < min_items:
        return f"Must contain at least {min_items} item(s)"
    if max_items is not None and length > max_items:
        return f"Must contain at most {max_items} item(s)"

    return None


def parse_date_safe(date_string: str, date_format: str = "%Y-%m-%d") -> Optional[datetime]:
    """
    Safely parse a date string, returning None if invalid

    Args:
        date_string: Date string to parse
        date_format: Expected date format

    Returns:
        datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(date_string, date_format)
    except (ValueError, TypeError, AttributeError):
        return None


def parse_datetime_safe(datetime_string: str) -> Optional[datetime]:
    """
    Safely parse an ISO 8601 datetime string, returning None if invalid

    Args:
        datetime_string: Datetime string to parse

    Returns:
        datetime object or None if parsing fails
    """
    try:
        return datetime.fromisoformat(datetime_string.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a string value by stripping whitespace and optionally truncating

    Args:
        value: String value to sanitize
        max_length: Maximum length (optional)

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    if max_length and len(value) > max_length:
        value = value[:max_length]

    return value


def validate_pagination_params(page: int, per_page: int, max_per_page: int = 100) -> Dict[str, str]:
    """
    Validate pagination parameters

    Args:
        page: Page number
        per_page: Items per page
        max_per_page: Maximum items per page

    Returns:
        Dictionary of validation errors (empty if valid)
    """
    errors = {}

    if page < 1:
        errors["page"] = "Page must be at least 1"

    if per_page < 1:
        errors["per_page"] = "per_page must be at least 1"
    elif per_page > max_per_page:
        errors["per_page"] = f"per_page must be at most {max_per_page}"

    return errors
