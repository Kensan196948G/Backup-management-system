"""
Caching Utilities

Provides caching functionality for improved performance:
- Flask-Caching integration
- Redis support
- Memory caching fallback
- Cache key generation
- TTL management
"""
import hashlib
import json
import logging
from functools import wraps
from typing import Callable, Optional

from flask import current_app
from flask_caching import Cache

logger = logging.getLogger(__name__)

# Initialize cache instance
cache = Cache()


def init_cache(app):
    """
    Initialize cache with Flask app.

    Args:
        app: Flask application instance
    """
    cache_config = {
        "CACHE_TYPE": app.config.get("CACHE_TYPE", "SimpleCache"),
        "CACHE_DEFAULT_TIMEOUT": app.config.get("CACHE_DEFAULT_TIMEOUT", 300),
    }

    # Redis configuration
    if cache_config["CACHE_TYPE"] == "redis":
        cache_config.update(
            {
                "CACHE_REDIS_HOST": app.config.get("REDIS_HOST", "localhost"),
                "CACHE_REDIS_PORT": app.config.get("REDIS_PORT", 6379),
                "CACHE_REDIS_DB": app.config.get("REDIS_DB", 0),
                "CACHE_REDIS_PASSWORD": app.config.get("REDIS_PASSWORD"),
                "CACHE_KEY_PREFIX": app.config.get("CACHE_KEY_PREFIX", "bms_"),
            }
        )

    cache.init_app(app, config=cache_config)
    logger.info(f"Cache initialized with type: {cache_config['CACHE_TYPE']}")


def make_cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    try:
        # Create a deterministic representation
        key_data = {
            "args": [str(arg) for arg in args],
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
        }

        # Create hash
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]

        return f"cache_{key_hash}"

    except Exception as e:
        logger.warning(f"Error generating cache key: {str(e)}")
        # Fallback to simple string concatenation
        return f"cache_{'_'.join(str(arg) for arg in args)}"


def cached(
    timeout: Optional[int] = None,
    key_prefix: Optional[str] = None,
    unless: Optional[Callable] = None,
    query_string: bool = False,
):
    """
    Decorator to cache function results.

    Args:
        timeout: Cache timeout in seconds (None = use default)
        key_prefix: Prefix for cache key
        unless: Function that returns True to skip caching
        query_string: Include query string in cache key

    Example:
        @cached(timeout=300, key_prefix='user_data')
        def get_user_data(user_id):
            return expensive_operation(user_id)
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if caching should be skipped
            if unless and unless():
                return f(*args, **kwargs)

            # Generate cache key
            if key_prefix:
                cache_key = f"{key_prefix}_{make_cache_key(*args, **kwargs)}"
            else:
                cache_key = f"{f.__name__}_{make_cache_key(*args, **kwargs)}"

            # Try to get from cache
            try:
                cached_value = cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
            except Exception as e:
                logger.warning(f"Cache get error: {str(e)}")

            # Execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = f(*args, **kwargs)

            # Store in cache
            try:
                cache.set(cache_key, result, timeout=timeout)
            except Exception as e:
                logger.warning(f"Cache set error: {str(e)}")

            return result

        return decorated_function

    return decorator


def invalidate_cache(key_pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.

    Args:
        key_pattern: Pattern to match cache keys

    Returns:
        Number of invalidated entries
    """
    try:
        # This is a simplified version
        # For Redis, you would use SCAN and DEL
        cache.delete(key_pattern)
        logger.info(f"Invalidated cache: {key_pattern}")
        return 1
    except Exception as e:
        logger.error(f"Error invalidating cache: {str(e)}")
        return 0


def cache_job_data(timeout: int = 300):
    """
    Cache decorator specifically for job-related data.

    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)
    """
    return cached(timeout=timeout, key_prefix="job_data")


def cache_report_data(timeout: int = 600):
    """
    Cache decorator specifically for report data.

    Args:
        timeout: Cache timeout in seconds (default: 10 minutes)
    """
    return cached(timeout=timeout, key_prefix="report_data")


def cache_compliance_data(timeout: int = 1800):
    """
    Cache decorator specifically for compliance data.

    Args:
        timeout: Cache timeout in seconds (default: 30 minutes)
    """
    return cached(timeout=timeout, key_prefix="compliance_data")


class CacheManager:
    """
    Centralized cache management.

    Provides methods for:
    - Cache warming
    - Cache invalidation
    - Cache statistics
    """

    def __init__(self):
        """Initialize cache manager"""
        self.cache = cache

    def warm_cache(self, keys_data: dict) -> int:
        """
        Pre-populate cache with data.

        Args:
            keys_data: Dictionary of {key: value} to cache

        Returns:
            Number of keys cached
        """
        count = 0
        for key, value in keys_data.items():
            try:
                self.cache.set(key, value)
                count += 1
            except Exception as e:
                logger.error(f"Error warming cache for key {key}: {str(e)}")

        logger.info(f"Warmed {count} cache entries")
        return count

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., 'job_data_*')

        Returns:
            Number of keys invalidated
        """
        return invalidate_cache(pattern)

    def clear_all(self) -> bool:
        """
        Clear entire cache.

        Returns:
            True if successful
        """
        try:
            self.cache.clear()
            logger.info("Cleared entire cache")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            # This depends on cache backend
            # For SimpleCache, limited stats available
            return {
                "backend": current_app.config.get("CACHE_TYPE", "SimpleCache"),
                "default_timeout": current_app.config.get("CACHE_DEFAULT_TIMEOUT", 300),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}


# Global cache manager instance
cache_manager = CacheManager()
