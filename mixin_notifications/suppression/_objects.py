"""Suppression policy and tracking for duplicate notifications."""

from __future__ import annotations

from dataclasses import dataclass, field


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

    def is_suppressed(
        self, category: str, fingerprint: str, current_time: float
    ) -> bool:
        """Check if (category, fingerprint) is within suppression window.

        Args:
            category: Event category.
            fingerprint: Event fingerprint.
            current_time: Current time in seconds (from time.time()).

        Returns:
            True if within window and seen recently; False otherwise.
        """
        last_seen = self._seen.get((category, fingerprint))
        return last_seen is not None and current_time - last_seen < self.window_seconds

    def record(self, category: str, fingerprint: str, current_time: float) -> None:
        """Record a (category, fingerprint) seen at current_time.

        Args:
            category: Event category.
            fingerprint: Event fingerprint.
            current_time: Current time in seconds.
        """
        key = (category, fingerprint)
        # Re-inserting moves the key to the end, so the first key is the least recent.
        self._seen.pop(key, None)
        self._seen[key] = current_time

        if len(self._seen) > self.max_capacity:
            del self._seen[next(iter(self._seen))]
