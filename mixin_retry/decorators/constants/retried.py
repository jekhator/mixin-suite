"""Retry decorator constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "ATTRIBUTE_MARKER",
    "ATTRIBUTE_MAX_ATTEMPTS",
    "BASE_DELAY_DEFAULT",
    "ERROR_MSG_INVALID_PREDICATE",
    "ERROR_MSG_MAX_ATTEMPTS_INVALID",
    "ERROR_MSG_TARGET_NOT_CLASS_OR_CALLABLE",
    "JITTER_DEFAULT",
    "MAX_DELAY_DEFAULT",
]


"""Backoff and retry parameters."""

BASE_DELAY_DEFAULT: Final = 1.0
"""Default base delay in seconds for exponential backoff."""

MAX_DELAY_DEFAULT: Final = 60.0
"""Default maximum delay in seconds for exponential backoff."""

JITTER_DEFAULT: Final = True
"""Default enable full jitter in backoff calculation."""


"""Decorator attribute names."""

ATTRIBUTE_MARKER: Final = "__retried_decorated__"
"""Method attribute name marking explicit @retried decoration."""

ATTRIBUTE_MAX_ATTEMPTS: Final = "_max_attempts"
"""Container attribute name for max attempts."""


"""Validation error messages."""

ERROR_MSG_MAX_ATTEMPTS_INVALID: Final = (
    "max_attempts must be a positive integer"
)
"""Error message for invalid max_attempts."""

ERROR_MSG_INVALID_PREDICATE: Final = (
    "retry_on predicate must be callable"
)
"""Error message for invalid retry_on predicate."""

ERROR_MSG_TARGET_NOT_CLASS_OR_CALLABLE: Final = (
    "@retried target must be a class or callable"
)
"""Error message for invalid decoration target."""
