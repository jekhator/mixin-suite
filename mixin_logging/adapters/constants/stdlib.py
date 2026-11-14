"""stdlib logging adapter constants. Imported as const."""

from __future__ import annotations

import logging
from typing import Final

__all__ = [
    "CORRELATION_RECORD_ATTR",
    "DEFAULT_CAPACITY",
    "DEFAULT_FLUSH_LEVEL",
    "DEFAULT_MAX_CORRELATIONS",
    "DEFAULT_TTL_SECONDS",
    "ERR_CAPACITY_POSITIVE",
    "ERR_FLUSH_LEVEL_INVALID",
    "ERR_MAX_CORRELATIONS_POSITIVE",
    "ERR_TARGET_HANDLER_REQUIRED",
    "ERR_TTL_POSITIVE",
    "NULL_CORRELATION_ID",
    "UNSET_CORRELATION_ID",
]


"""LogRecord attribute field name."""

CORRELATION_RECORD_ATTR: Final = "correlation_id"


"""Unset correlation ID sentinel (stamped when context is empty)."""

UNSET_CORRELATION_ID: Final = "-"


"""Null correlation ID key for flush-handler buffers with no correlation set."""

NULL_CORRELATION_ID: Final = "-buffered-"


"""FlushOnWarningConfig default values."""

DEFAULT_FLUSH_LEVEL: Final = logging.WARNING
DEFAULT_TTL_SECONDS: Final = 300
DEFAULT_CAPACITY: Final = 1000
DEFAULT_MAX_CORRELATIONS: Final = 100


"""FlushOnWarningConfig validation messages."""

ERR_TARGET_HANDLER_REQUIRED: Final = "target_handler must not be None"
ERR_FLUSH_LEVEL_INVALID: Final = "flush_level must be >= logging.WARNING"
ERR_TTL_POSITIVE: Final = "ttl_seconds must be > 0"
ERR_CAPACITY_POSITIVE: Final = "capacity must be > 0"
ERR_MAX_CORRELATIONS_POSITIVE: Final = "max_correlations must be > 0"
