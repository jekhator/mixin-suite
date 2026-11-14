"""WSGI scope/message/app type aliases + WsgiCorrelation value object."""

from __future__ import annotations

from collections.abc import Callable, Iterable, MutableMapping
from dataclasses import dataclass
from typing import Any, Self
from uuid import uuid4

from mixin_logging.adapters.constants import wsgi as const

Environ = MutableMapping[str, Any]
Headers = list[tuple[str, str]]
ExcInfo = tuple[type, BaseException, Any]

StartResponse = Callable[[str, Headers, ExcInfo | None], Callable[[bytes], None]]
App = Callable[[Environ, StartResponse], Iterable[bytes]]


@dataclass(frozen=True, slots=True)
class WsgiCorrelation:
    """Extracted or generated correlation ID from WSGI request."""

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
        return const.UNSAFE_HEADER_CHARS.isdisjoint(value)

    @classmethod
    def from_environ(cls, environ: Environ) -> Self:
        """Extract X-Correlation-ID from environ; validate or fall back to uuid4."""
        raw = environ.get(const.CORRELATION_ID_ENVIRON_KEY)
        if isinstance(raw, str) and cls._is_safe(raw):
            return cls(correlation_id=raw, from_header=True)
        return cls(correlation_id=uuid4().hex[:12], from_header=False)

    @property
    def response_header(self) -> tuple[str, str]:
        """Return correlation ID as HTTP response header tuple."""
        return (const.CORRELATION_ID_HEADER, self.correlation_id)
