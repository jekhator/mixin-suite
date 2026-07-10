"""stdlib logging adapter constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "CORRELATION_RECORD_ATTR",
    "UNSET_CORRELATION_ID",
]


"""LogRecord attribute field name."""

CORRELATION_RECORD_ATTR: Final = "correlation_id"


"""Unset correlation ID sentinel (stamped when context is empty)."""

UNSET_CORRELATION_ID: Final = "-"
