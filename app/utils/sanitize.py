"""
Input Sanitization and Validation Utilities

Provides functions to sanitize and validate user inputs to prevent
injection attacks and ensure data integrity.

Phase 15D Security Enhancement
"""

import re
from typing import Optional


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Remove potentially dangerous characters and truncate string.

    Removes null bytes and truncates to max_length.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length (default 255)

    Returns:
        Sanitized string, empty string if input is not a str
    """
    if not isinstance(value, str):
        return ""
    # Remove null bytes
    value = value.replace("\x00", "")
    # Truncate to max_length
    return value[:max_length]


def sanitize_strip(value: str, max_length: int = 255) -> str:
    """
    Sanitize string and strip surrounding whitespace.

    Args:
        value: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized and stripped string
    """
    return sanitize_string(value, max_length).strip()


def validate_job_name(name: str) -> Optional[str]:
    """
    Validate and sanitize a backup job name.

    Allows alphanumeric characters, spaces, hyphens, underscores,
    and common Japanese Unicode ranges.

    Args:
        name: Backup job name to validate

    Returns:
        Sanitized name on success, None if invalid or empty
    """
    if not name or not isinstance(name, str):
        return None

    sanitized = sanitize_strip(name, max_length=100)

    if not sanitized:
        return None

    # Allow alphanumeric, spaces, hyphens, underscores, and Japanese characters
    # (Hiragana U+3040-U+309F, Katakana U+30A0-U+30FF, CJK U+4E00-U+9FFF)
    if not re.match(r"^[a-zA-Z0-9\s\-_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+$", sanitized):
        return None

    return sanitized


def validate_username(username: str) -> Optional[str]:
    """
    Validate a username.

    Usernames must be 3-50 characters, consisting of alphanumeric
    characters, hyphens, underscores, and periods.

    Args:
        username: Username to validate

    Returns:
        Sanitized username on success, None if invalid
    """
    if not username or not isinstance(username, str):
        return None

    sanitized = sanitize_strip(username, max_length=50)

    if len(sanitized) < 3:
        return None

    if not re.match(r"^[a-zA-Z0-9\-_.]+$", sanitized):
        return None

    return sanitized


def validate_path(path: str, max_length: int = 500) -> Optional[str]:
    """
    Validate and sanitize a file system path.

    Rejects paths with null bytes or path traversal sequences.

    Args:
        path: File system path to validate
        max_length: Maximum path length

    Returns:
        Sanitized path on success, None if invalid
    """
    if not path or not isinstance(path, str):
        return None

    sanitized = sanitize_string(path, max_length=max_length)

    # Reject path traversal attempts
    if ".." in sanitized:
        return None

    return sanitized.strip()


def sanitize_search_query(query: str, max_length: int = 200) -> str:
    """
    Sanitize a search query string.

    Strips control characters and truncates to max_length.

    Args:
        query: Search query string
        max_length: Maximum length

    Returns:
        Sanitized query string
    """
    if not isinstance(query, str):
        return ""

    sanitized = sanitize_string(query, max_length)

    # Remove control characters (keep printable ASCII and Unicode)
    sanitized = re.sub(r"[\x00-\x1f\x7f]", "", sanitized)

    return sanitized.strip()
