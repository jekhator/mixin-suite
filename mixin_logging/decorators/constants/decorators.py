"""Decorator constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "ATTRIBUTE_CODE",
    "ATTRIBUTE_LOGGED_MARKER",
    "ERROR_MSG_EVENT_EMPTY",
    "ERROR_MSG_TARGET_NOT_CLASS_OR_CALLABLE",
    "EVENT_SEPARATOR",
    "EVENT_SUFFIX_END",
    "EVENT_SUFFIX_ERROR",
    "EVENT_SUFFIX_START",
    "LOG_EVENT_EXTRACTION_FAILURE",
    "LOG_FIELD_ERROR_CODE",
    "LOG_FIELD_ERROR_TYPE",
    "LOG_FIELD_LATENCY_MS",
    "PAYLOAD_EXTRACTION_FAILURE_NON_DICT",
]


"""Log-event name suffixes and separators."""

EVENT_SUFFIX_START: Final = ".start"
"""Log-event suffix appended to base event name for start phase."""
EVENT_SUFFIX_END: Final = ".end"
"""Log-event suffix appended to base event name for success phase."""
EVENT_SUFFIX_ERROR: Final = ".error"
"""Log-event suffix appended to base event name for error phase."""

EVENT_SEPARATOR: Final = "."
"""Separator between root event and method name in class-level decoration."""


"""Log-record field keys."""

LOG_FIELD_ERROR_TYPE: Final = "error_type"
"""Log record field key for exception type name."""
LOG_FIELD_ERROR_CODE: Final = "code"
"""Log record field key for exception code attribute."""
LOG_FIELD_LATENCY_MS: Final = "latency_ms"
"""Log record field key for method execution latency in milliseconds."""


"""Extraction and payload event/error messages."""

LOG_EVENT_EXTRACTION_FAILURE: Final = "extraction.failure"
"""Log event name for payload extraction failures."""
PAYLOAD_EXTRACTION_FAILURE_NON_DICT: Final = "return_type_not_dict"
"""Extraction error type when extractor returns non-dict value."""


"""Exception and decorator attribute names."""

ATTRIBUTE_CODE: Final = "code"
"""Exception attribute name for code lookup."""

ATTRIBUTE_LOGGED_MARKER: Final = "__logged_decorated__"
"""Method attribute name marking explicit @logged decoration."""


"""Validation error messages."""

ERROR_MSG_EVENT_EMPTY: Final = "LoggedContainer.event must be non-empty"
"""Validation error: LoggedContainer.event must be non-empty."""

ERROR_MSG_TARGET_NOT_CLASS_OR_CALLABLE: Final = (
    "@logged target must be a class or callable"
)
"""Validation error: @logged requires a class or callable."""
