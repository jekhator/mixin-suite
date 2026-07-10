"""GraphQL adapter constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "CONTEXT_KEY",
]


"""Key under which correlation_id is exposed in resolver context."""

CONTEXT_KEY: Final = "correlation_id"
