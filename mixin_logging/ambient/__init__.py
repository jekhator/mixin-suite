"""Ambient contextvar logger with auto-injected correlation_id."""

from mixin_logging.ambient.ambient_client import (
    AmbientLogger,
    log_debug,
    log_error,
    log_exception,
    log_info,
    log_warning,
)

__all__ = [
    "AmbientLogger",
    "log_debug",
    "log_error",
    "log_exception",
    "log_info",
    "log_warning",
]
