"""Correlation context constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "CORRELATION_CONTEXT_VAR_NAME",
    "CORRELATION_ID_KEY",
    "UNSET_CORRELATION_ID",
]


"""Correlation ID log-record key and unset sentinel."""

CORRELATION_ID_KEY: Final = "correlation_id"
UNSET_CORRELATION_ID: Final = "-"


"""ContextVar name for correlation context."""

CORRELATION_CONTEXT_VAR_NAME: Final = "correlation_ctx"
