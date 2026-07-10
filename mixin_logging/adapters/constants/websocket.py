"""WebSocket adapter constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "CORRELATION_ID_HEADER",
    "CORRELATION_ID_MAX_LENGTH",
    "ERR_CORRELATION_ID_UNSAFE",
    "GENERATED_ID_LENGTH",
    "HEADERS_KEY",
    "TYPE_KEY",
    "UNSAFE_HEADER_CHARS",
    "WEBSOCKET_SCOPE_TYPE",
]


"""ASGI scope and message keys."""

TYPE_KEY: Final = "type"
HEADERS_KEY: Final = "headers"


"""WebSocket scope types."""

WEBSOCKET_SCOPE_TYPE: Final = "websocket"


"""Handshake header name."""

CORRELATION_ID_HEADER: Final = "x-correlation-id"


"""Validation."""

CORRELATION_ID_MAX_LENGTH: Final = 128
GENERATED_ID_LENGTH: Final = 12
UNSAFE_HEADER_CHARS: Final = frozenset({"\r", "\n", "\0"})


"""Error messages raised at the API surface (source-side; tests match against these via const.ERR_*)."""

ERR_CORRELATION_ID_UNSAFE: Final = (
    "correlation_id must be non-empty, within length cap, free of unsafe chars"
)
