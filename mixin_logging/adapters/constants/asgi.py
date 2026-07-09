"""ASGI middleware constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "CORRELATION_ID_HEADER",
    "CORRELATION_ID_MAX_LENGTH",
    "ERR_CORRELATION_ID_EMPTY",
    "HEADERS_KEY",
    "HTTP_SCOPE_TYPE",
    "RESPONSE_START_MESSAGE_TYPE",
    "RESPONSE_STATUS_KEY",
    "TYPE_KEY",
    "UNSAFE_HEADER_CHARS",
]


"""ASGI dict key names."""

HEADERS_KEY: Final = "headers"
RESPONSE_STATUS_KEY: Final = "status"
TYPE_KEY: Final = "type"


"""Correlation ID validation."""

CORRELATION_ID_MAX_LENGTH: Final = 128


"""ASGI header field names."""

CORRELATION_ID_HEADER: Final = b"x-correlation-id"


"""ASGI scope types."""

HTTP_SCOPE_TYPE: Final = "http"


"""ASGI message types."""

RESPONSE_START_MESSAGE_TYPE: Final = "http.response.start"


"""Unsafe header characters: rejected to prevent CRLF injection / null-byte attacks."""

UNSAFE_HEADER_CHARS: Final = frozenset({"\r", "\n", "\0"})


"""Error messages raised at the API surface (source-side; tests match against these via const.ERR_*)."""

ERR_CORRELATION_ID_EMPTY: Final = "correlation_id must not be empty"
