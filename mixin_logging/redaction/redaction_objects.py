"""RedactionFilter: logging filter that masks sensitive fields."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mixin_logging.redaction.constants import redaction as const


@dataclass(frozen=True, slots=True)
class RedactionFilter(logging.Filter):
    """Logging filter that masks fields with sensitive field names."""

    sensitive_patterns: frozenset[str]

    @classmethod
    def with_defaults(cls) -> RedactionFilter:
        """Create a filter with default sensitive field name patterns.

        Returns:
            RedactionFilter configured with common sensitive field names.
        """
        patterns = frozenset(
            [
                "password",
                "secret",
                "api_key",
                "token",
                "auth",
                "credential",
                "key",
            ]
        )
        return cls(sensitive_patterns=patterns)

    def filter(self, record: logging.LogRecord) -> bool:
        """Apply redaction to LogRecord and return True to allow emission.

        Args:
            record: LogRecord to filter and potentially redact.

        Returns:
            True to allow record emission (filter contract).
        """
        self._redact_record(record)
        return True

    def _redact_record(self, record: logging.LogRecord) -> None:
        """Redact sensitive fields in the LogRecord.

        Args:
            record: LogRecord to modify in place.
        """
        for key in list(record.__dict__.keys()):
            if key.startswith("_"):
                continue

            if self._is_sensitive_field_name(key):
                record.__dict__[key] = const.MASK_TOKEN

    def _is_sensitive_field_name(self, name: str) -> bool:
        """Check if a field name matches sensitive patterns.

        Args:
            name: Field name to check.

        Returns:
            True if name matches any sensitive pattern.
        """
        name_lower = name.lower()
        return any(pattern in name_lower for pattern in self.sensitive_patterns)
