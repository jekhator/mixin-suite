"""AiohttpCorrelation value object for aiohttp adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from mixin_logging import get_correlation_id
from mixin_logging.adapters.constants import aiohttp as const

__all__ = ["AiohttpCorrelation"]


@dataclass(frozen=True, slots=True)
class AiohttpCorrelation:
    """Value object capturing the correlation_id to inject into outbound aiohttp requests."""

    correlation_id: str

    def __post_init__(self) -> None:
        """Validate correlation_id against safety rules; raise on invariant breach."""
        if not self._is_safe(self.correlation_id):
            raise ValueError(const.ERR_CORRELATION_ID_UNSAFE)

    @classmethod
    def from_context(cls) -> Self | None:
        """Read correlation_id from ContextVar; return instance or None if unset or unsafe."""
        raw_value = get_correlation_id()
        if raw_value is None or not cls._is_safe(raw_value):
            return None
        return cls(correlation_id=raw_value)

    @property
    def header_tuple(self) -> tuple[str, str]:
        """Return (header_name, correlation_id) ready for outbound request header injection."""
        return (const.CORRELATION_ID_HEADER, self.correlation_id)

    @staticmethod
    def _is_safe(value: str) -> bool:
        """Return True if value is non-empty, within length cap, free of CRLF/null chars."""
        if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:
            return False
        return not any(char in const.UNSAFE_HEADER_CHARS for char in value)
