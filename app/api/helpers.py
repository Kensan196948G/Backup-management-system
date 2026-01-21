"""
API Helper Functions
Common utility functions for API endpoints
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import jsonify, request, url_for


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime object to ISO 8601 string with Z suffix

    Args:
        dt: datetime object

    Returns:
        ISO 8601 formatted string or None
    """
    if dt is None:
        return None
    return dt.isoformat() + "Z"


def format_date(date_obj) -> Optional[str]:
    """
    Format date object to ISO 8601 date string

    Args:
        date_obj: date object

    Returns:
        ISO 8601 formatted date string or None
    """
    if date_obj is None:
        return None
    return date_obj.isoformat()


def get_pagination_params(default_per_page: int = 20, max_per_page: int = 100) -> tuple:
    """
    Extract and validate pagination parameters from request

    Args:
        default_per_page: Default items per page
        max_per_page: Maximum items per page

    Returns:
        Tuple of (page, per_page)
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", default_per_page, type=int)

    # Ensure valid values
    page = max(1, page)
    per_page = min(max(1, per_page), max_per_page)

    return page, per_page


def format_pagination_response(pagination) -> Dict[str, Any]:
    """
    Format SQLAlchemy pagination object to API response format

    Args:
        pagination: SQLAlchemy pagination object

    Returns:
        Dictionary with pagination metadata
    """
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


def create_success_response(message: str, data: Optional[Dict[str, Any]] = None, status_code: int = 200) -> tuple:
    """
    Create a standardized success response

    Args:
        message: Success message
        data: Additional data to include
        status_code: HTTP status code

    Returns:
        Tuple of (response, status_code)
    """
    response = {"message": message}
    if data:
        response.update(data)
    return jsonify(response), status_code


def create_list_response(
    items: List[Dict[str, Any]], pagination=None, additional_data: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a standardized list response with optional pagination

    Args:
        items: List of items
        pagination: SQLAlchemy pagination object (optional)
        additional_data: Additional data to include

    Returns:
        Tuple of (response, status_code)
    """
    response = {"items": items}

    if pagination:
        response["pagination"] = format_pagination_response(pagination)

    if additional_data:
        response.update(additional_data)

    return jsonify(response), 200


def format_bytes(bytes_value: Optional[int]) -> Optional[str]:
    """
    Format bytes to human-readable string

    Args:
        bytes_value: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB") or None
    """
    if bytes_value is None:
        return None

    if bytes_value == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(bytes_value)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: Optional[int]) -> Optional[str]:
    """
    Format duration in seconds to human-readable string

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2h 30m 15s") or None
    """
    if seconds is None:
        return None

    if seconds == 0:
        return "0s"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def parse_boolean_param(param_name: str, default: bool = False) -> bool:
    """
    Parse boolean query parameter from request

    Args:
        param_name: Parameter name
        default: Default value if not present

    Returns:
        Boolean value
    """
    value = request.args.get(param_name, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    return default


def get_filter_params(allowed_filters: List[str]) -> Dict[str, str]:
    """
    Extract filter parameters from request

    Args:
        allowed_filters: List of allowed filter parameter names

    Returns:
        Dictionary of filter parameters
    """
    filters = {}
    for param in allowed_filters:
        if param in request.args:
            filters[param] = request.args[param]
    return filters


def build_resource_url(endpoint: str, resource_id: int, _external: bool = False) -> str:
    """
    Build URL for a resource

    Args:
        endpoint: Flask endpoint name
        resource_id: Resource ID
        _external: Whether to generate absolute URL

    Returns:
        Resource URL
    """
    return url_for(endpoint, id=resource_id, _external=_external)


def validate_json_request() -> Optional[tuple]:
    """
    Validate that request contains JSON data

    Returns:
        Error response tuple if invalid, None if valid
    """
    if not request.is_json:
        return jsonify({"error": {"code": "INVALID_CONTENT_TYPE", "message": "Content-Type must be application/json"}}), 400

    data = request.get_json()
    if data is None:
        return jsonify({"error": {"code": "INVALID_JSON", "message": "Request body must contain valid JSON"}}), 400

    return None


def extract_sort_params(
    default_sort: str = "created_at", default_order: str = "desc", allowed_fields: Optional[List[str]] = None
) -> tuple:
    """
    Extract sorting parameters from request

    Args:
        default_sort: Default sort field
        default_order: Default sort order (asc/desc)
        allowed_fields: List of allowed sort fields

    Returns:
        Tuple of (sort_field, sort_order)
    """
    sort_field = request.args.get("sort", default_sort)
    sort_order = request.args.get("order", default_order).lower()

    # Validate sort field
    if allowed_fields and sort_field not in allowed_fields:
        sort_field = default_sort

    # Validate sort order
    if sort_order not in ("asc", "desc"):
        sort_order = default_order

    return sort_field, sort_order


def calculate_percentage(part: int, total: int, decimal_places: int = 2) -> float:
    """
    Calculate percentage safely (avoiding division by zero)

    Args:
        part: Part value
        total: Total value
        decimal_places: Number of decimal places

    Returns:
        Percentage value
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, decimal_places)


def get_date_range_params() -> tuple:
    """
    Extract date range parameters from request

    Returns:
        Tuple of (date_from, date_to) as strings or (None, None)
    """
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    return date_from, date_to


def create_link_header(pagination, endpoint: str, **kwargs) -> str:
    """
    Create Link header for pagination (RFC 5988)

    Args:
        pagination: SQLAlchemy pagination object
        endpoint: Flask endpoint name
        **kwargs: Additional URL parameters

    Returns:
        Link header string
    """
    links = []

    # First page
    url = url_for(endpoint, page=1, per_page=pagination.per_page, _external=True, **kwargs)
    links.append(f'<{url}>; rel="first"')

    # Previous page
    if pagination.has_prev:
        url = url_for(endpoint, page=pagination.prev_num, per_page=pagination.per_page, _external=True, **kwargs)
        links.append(f'<{url}>; rel="prev"')

    # Next page
    if pagination.has_next:
        url = url_for(endpoint, page=pagination.next_num, per_page=pagination.per_page, _external=True, **kwargs)
        links.append(f'<{url}>; rel="next"')

    # Last page
    url = url_for(endpoint, page=pagination.pages, per_page=pagination.per_page, _external=True, **kwargs)
    links.append(f'<{url}>; rel="last"')

    return ", ".join(links)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing unsafe characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re

    # Remove or replace unsafe characters
    filename = re.sub(r"[^\w\s\-\.]", "", filename)
    filename = re.sub(r"[\s]+", "_", filename)
    return filename


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if string is a valid UUID

    Args:
        uuid_string: String to check

    Returns:
        True if valid UUID, False otherwise
    """
    import re

    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
    return bool(uuid_pattern.match(uuid_string))
