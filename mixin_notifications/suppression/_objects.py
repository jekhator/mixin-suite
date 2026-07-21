"""Suppression policy and tracking for duplicate notifications."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass(frozen=True, slots=True)
class SuppressionPolicy:
    """Policy for suppressing duplicate notifications."""

    window_seconds: int


@dataclass(slots=True)
class SuppressionTracker:
    """In-memory tracker of suppressed (category, fingerprint) pairs."""

    window_seconds: int
    max_capacity: int = 10000
    _seen: dict[tuple[str, str], float] = field(default_factory=dict)

    def is_suppressed(self, category: str, fingerprint: str, current_time: float) -> bool:
        """Check if (category, fingerprint) is within suppression window.

        Args:
            category: Event category.
            fingerprint: Event fingerprint.
            current_time: Current time in seconds (from time.time()).

        Returns:
            True if within window and seen recently; False otherwise.
        """
        key = (category, fingerprint)
        if key in self._seen:
            last_seen = self._seen[key]
            if current_time - last_seen < self.window_seconds:
                return True
        return False

    def record(self, category: str, fingerprint: str, current_time: float) -> None:
        """Record a (category, fingerprint) seen at current_time.

        Args:
            category: Event category.
            fingerprint: Event fingerprint.
            current_time: Current time in seconds.
        """
        key = (category, fingerprint)
        self._seen[key] = current_time

        if len(self._seen) > self.max_capacity:
            oldest_key = min(self._seen.keys(), key=lambda k: self._seen[k])
            del self._seen[oldest_key]
