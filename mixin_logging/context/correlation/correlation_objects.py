"""Correlation context value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    """Correlation context value carried across async boundaries."""

    correlation_id: str | None

    @property
    def is_set(self) -> bool:
        """Return True when a correlation id is present."""
        return self.correlation_id is not None
