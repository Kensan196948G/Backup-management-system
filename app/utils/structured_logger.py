"""
Structured Logging

Provides JSON-formatted structured logging:
- Correlation IDs for request tracking
- Structured context
- Log aggregation support
- Integration with Flask request context
"""

import logging
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import g, has_request_context, request
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """
    Structured logger with JSON output.

    Adds contextual information to all log messages:
    - Correlation ID
    - User ID
    - Request ID
    - Custom metadata
    """

    def __init__(self, name: str):
        """
        Initialize structured logger.

        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)

    def _get_context(self) -> Dict[str, Any]:
        """
        Get current logging context.

        Returns:
            Dictionary with context information
        """
        context = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add Flask request context if available
        if has_request_context():
            context.update(
                {
                    "correlation_id": self._get_correlation_id(),
                    "request_id": getattr(g, "request_id", None),
                    "user_id": getattr(g, "user_id", None),
                    "method": request.method,
                    "path": request.path,
                    "remote_addr": request.remote_addr,
                }
            )

        return context

    def _get_correlation_id(self) -> str:
        """
        Get or create correlation ID for request.

        Returns:
            Correlation ID string
        """
        if not hasattr(g, "correlation_id"):
            # Try to get from header
            correlation_id = request.headers.get("X-Correlation-ID")
            if not correlation_id:
                correlation_id = str(uuid.uuid4())
            g.correlation_id = correlation_id

        return g.correlation_id

    def debug(self, message: str, **kwargs):
        """
        Log debug message with context.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        extra = self._get_context()
        extra.update(kwargs)
        self.logger.debug(message, extra={"context": extra})

    def info(self, message: str, **kwargs):
        """
        Log info message with context.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        extra = self._get_context()
        extra.update(kwargs)
        self.logger.info(message, extra={"context": extra})

    def warning(self, message: str, **kwargs):
        """
        Log warning message with context.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        extra = self._get_context()
        extra.update(kwargs)
        self.logger.warning(message, extra={"context": extra})

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """
        Log error message with context.

        Args:
            message: Log message
            exc_info: Include exception info
            **kwargs: Additional context
        """
        extra = self._get_context()
        extra.update(kwargs)
        self.logger.error(message, exc_info=exc_info, extra={"context": extra})

    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """
        Log critical message with context.

        Args:
            message: Log message
            exc_info: Include exception info
            **kwargs: Additional context
        """
        extra = self._get_context()
        extra.update(kwargs)
        self.logger.critical(message, exc_info=exc_info, extra={"context": extra})


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logs.

    Adds custom fields and formatting.
    """

    def add_fields(self, log_record, record, message_dict):
        """
        Add custom fields to log record.

        Args:
            log_record: Output log record
            record: Input log record
            message_dict: Message dictionary
        """
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Add timestamp
        if not log_record.get("timestamp"):
            log_record["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Add log level
        if log_record.get("level"):
            log_record["level"] = log_record["level"].upper()
        else:
            log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add module and function
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Extract context if available
        if hasattr(record, "context"):
            log_record.update(record.context)


def setup_structured_logging(app):
    """
    Setup structured logging for Flask app.

    Args:
        app: Flask application instance
    """
    # Create JSON formatter
    formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(logger)s %(module)s %(function)s %(line)d %(message)s")

    # Configure root logger
    root_logger = logging.getLogger()

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set log level
    log_level = app.config.get("LOG_LEVEL", "INFO")
    root_logger.setLevel(getattr(logging, log_level))

    # Add request ID middleware
    @app.before_request
    def before_request():
        """Set request ID before each request"""
        g.request_id = str(uuid.uuid4())
        if hasattr(g, "user") and g.user:
            g.user_id = g.user.id

    # Add response correlation ID
    @app.after_request
    def after_request(response):
        """Add correlation ID to response"""
        if has_request_context():
            correlation_id = getattr(g, "correlation_id", None)
            if correlation_id:
                response.headers["X-Correlation-ID"] = correlation_id
        return response

    app.logger.info("Structured logging initialized")


def log_function_call(logger: Optional[StructuredLogger] = None):
    """
    Decorator to log function calls.

    Args:
        logger: StructuredLogger instance (optional)

    Example:
        @log_function_call()
        def my_function(arg1, arg2):
            pass
    """

    def decorator(f: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = StructuredLogger(f.__module__)

        @wraps(f)
        def wrapper(*args, **kwargs):
            logger.info(
                f"Calling {f.__name__}",
                function=f.__name__,
                args_count=len(args),
                kwargs_count=len(kwargs),
            )

            try:
                result = f(*args, **kwargs)
                logger.info(f"Completed {f.__name__}", function=f.__name__, status="success")
                return result

            except Exception as e:
                logger.error(
                    f"Error in {f.__name__}: {str(e)}",
                    exc_info=True,
                    function=f.__name__,
                    error=str(e),
                    status="error",
                )
                raise

        return wrapper

    return decorator


def log_with_context(**context_kwargs):
    """
    Decorator to add context to all logs within a function.

    Args:
        **context_kwargs: Context to add

    Example:
        @log_with_context(operation='backup', job_id=123)
        def perform_backup():
            pass
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Add context to g
            if has_request_context():
                if not hasattr(g, "log_context"):
                    g.log_context = {}
                g.log_context.update(context_kwargs)

            return f(*args, **kwargs)

        return wrapper

    return decorator


# Convenience function to get structured logger
def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
