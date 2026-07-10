"""ASGI scope/message/app type aliases + AsgiCorrelation value object."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from typing import Any, Self
from uuid import uuid4

from mixin_logging.adapters.constants import asgi as const

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
App = Callable[[Scope, Receive, Send], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class AsgiCorrelation:
    """Extracted or generated correlation ID from ASGI request."""

    correlation_id: str
    from_header: bool

    def __post_init__(self) -> None:
        """Validate correlation_id is not empty."""
        if not self.correlation_id:
            raise ValueError(const.ERR_CORRELATION_ID_EMPTY)

    @staticmethod
    def _is_safe(value: str) -> bool:
        """Check if a correlation ID value is safe for logging and HTTP headers."""
        if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:
            return False
        if any(char in const.UNSAFE_HEADER_CHARS for char in value):
            return False
        return True

    @classmethod
    def from_scope(cls, scope: Scope) -> Self:
        """Extract X-Correlation-ID from scope; validate or fall back to uuid4."""
        headers = scope.get(const.HEADERS_KEY, [])
        for header_name, header_value in headers:
            if not isinstance(header_name, bytes) or not isinstance(
                header_value, bytes
            ):
                continue
            if header_name.lower() == const.CORRELATION_ID_HEADER:
                try:
                    decoded_id = header_value.decode("utf-8")
                except UnicodeDecodeError:
                    break
                if cls._is_safe(decoded_id):
                    return cls(
                        correlation_id=decoded_id,
                        from_header=True,
                    )
                break
        return cls(
            correlation_id=uuid4().hex[:12],
            from_header=False,
        )

    @property
    def response_header(self) -> tuple[bytes, bytes]:
        """Return correlation ID as HTTP response header tuple."""
        return (const.CORRELATION_ID_HEADER, self.correlation_id.encode())
