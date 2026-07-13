"""FastAPI correlation-ID extraction and validation + value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import uuid4

from mixin_logging.adapters.constants import fastapi as const


@dataclass(frozen=True, slots=True)
class FastApiCorrelation:
    """Extracted or generated correlation ID from FastAPI request."""

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
    def from_headers(cls, headers: dict[str, str]) -> Self:
        """Extract X-Correlation-ID from headers; validate or fall back to uuid4."""
        raw = headers.get(const.CORRELATION_ID_HEADER)
        if isinstance(raw, str) and cls._is_safe(raw):
            return cls(correlation_id=raw, from_header=True)
        return cls(correlation_id=uuid4().hex[:12], from_header=False)

    @property
    def response_header(self) -> tuple[str, str]:
        """Return correlation ID as HTTP response header tuple."""
        return (const.CORRELATION_ID_HEADER, self.correlation_id)
