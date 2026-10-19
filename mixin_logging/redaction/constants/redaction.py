"""Redaction filter constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "DEFAULT_SENSITIVE_PATTERNS",
    "MASK_TOKEN",
]


"""Redaction masking parameters."""

MASK_TOKEN: Final = "***REDACTED***"
"""Token used to replace sensitive field values."""


"""Default case-insensitive substrings that mark a field name as sensitive."""

DEFAULT_SENSITIVE_PATTERNS: Final = frozenset(
    {
        "password",
        "secret",
        "api_key",
        "token",
        "auth",
        "credential",
        "key",
    },
)
