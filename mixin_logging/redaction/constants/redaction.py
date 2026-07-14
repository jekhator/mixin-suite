"""Redaction filter constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "MASK_TOKEN",
]


"""Redaction masking parameters."""

MASK_TOKEN: Final = "***REDACTED***"
"""Token used to replace sensitive field values."""
