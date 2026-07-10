"""CloudCorrelation value object for cloud adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self
from uuid import uuid4

from mixin_logging.adapters.constants import cloud as const


@dataclass(frozen=True, slots=True)
class CloudCorrelation:
    """Correlation-ID value object resolved from cloud events or generated."""

    correlation_id: str
    extracted: bool

    def __post_init__(self) -> None:
        """Validate correlation_id against safety rules; raise on invariant breach."""
        if not self._is_safe(self.correlation_id):
            raise ValueError(const.ERR_CORRELATION_ID_UNSAFE)

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> Self:
        """Extract correlation_id from cloud event by AWS-source precedence; generate if none present or unsafe."""
        headers = event.get(const.EVENT_KEY_HEADERS) or {}
        candidate = next(
            (
                value
                for key, value in headers.items()
                if key.lower() == const.CORRELATION_ID_HEADER.lower()
            ),
            None,
        )
        if candidate is None:
            records = event.get(const.EVENT_KEY_RECORDS) or []
            if records:
                attributes = (
                    records[0].get(const.EVENT_KEY_MESSAGE_ATTRIBUTES_SQS)
                    or records[0]
                    .get(const.EVENT_KEY_SNS, {})
                    .get(const.EVENT_KEY_MESSAGE_ATTRIBUTES_SNS)
                    or {}
                )
                entry = attributes.get(const.CORRELATION_ID_HEADER) or {}
                candidate = entry.get(
                    const.MESSAGE_ATTRIBUTE_STRING_VALUE_KEY_SQS
                ) or entry.get(const.MESSAGE_ATTRIBUTE_VALUE_KEY_SNS)
        if candidate is None:
            candidate = (event.get(const.EVENT_KEY_DETAIL) or {}).get(
                const.CORRELATION_ID_KEY,
            )
        if candidate is None:
            candidate = event.get(const.CORRELATION_ID_KEY)
        if isinstance(candidate, str) and cls._is_safe(candidate):
            return cls(correlation_id=candidate, extracted=True)
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
