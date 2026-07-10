"""WebSocketCorrelation value object for WebSocket adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import uuid4

from mixin_logging.adapters.constants import websocket as const

__all__ = ["Headers", "WebSocketCorrelation"]

Headers = list[tuple[bytes, bytes]]


@dataclass(frozen=True, slots=True)
class WebSocketCorrelation:
    """Correlation-ID value object resolved from WS handshake headers or generated."""

    correlation_id: str
    extracted: bool

    def __post_init__(self) -> None:
        """Validate correlation_id against safety rules; raise on invariant breach."""
        if not self._is_safe(self.correlation_id):
            raise ValueError(const.ERR_CORRELATION_ID_UNSAFE)

    @classmethod
    def from_headers(cls, headers: Headers) -> Self:
        """Extract correlation_id from WS handshake headers; generate if absent or unsafe."""
        target = const.CORRELATION_ID_HEADER.encode()
        candidate = next(
            (value for key, value in headers if key.lower() == target),
            None,
        )
        if candidate is not None:
            decoded = candidate.decode(errors="ignore")
            if cls._is_safe(decoded):
                return cls(correlation_id=decoded, extracted=True)
        return cls(
            correlation_id=uuid4().hex[: const.GENERATED_ID_LENGTH],
            extracted=False,
        )

    @staticmethod
    def _is_safe(value: str) -> bool:
        """Check if correlation_id is safe (non-empty, within length, no CRLF/null)."""
        if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:
            return False
        return not any(char in const.UNSAFE_HEADER_CHARS for char in value)
