"""FastAPI middleware constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "CORRELATION_ID_HEADER",
    "CORRELATION_ID_MAX_LENGTH",
    "ERR_CORRELATION_ID_EMPTY",
    "UNSAFE_HEADER_CHARS",
]


"""Correlation ID validation."""

CORRELATION_ID_MAX_LENGTH: Final = 128


"""FastAPI header field names."""

CORRELATION_ID_HEADER: Final = "x-correlation-id"


"""Unsafe header characters: rejected to prevent CRLF injection / null-byte attacks."""

UNSAFE_HEADER_CHARS: Final = frozenset({"\r", "\n", "\0"})


"""Error messages raised at the API surface (source-side; tests match against these via const.ERR_*)."""

ERR_CORRELATION_ID_EMPTY: Final = "correlation_id must not be empty"
