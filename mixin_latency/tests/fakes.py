"""Fake clocks for mixin_latency tests."""

from __future__ import annotations


class FakePerfCounter:
    """Settable stand-in for time.perf_counter."""

    def __init__(self) -> None:
        """Start the fake counter at zero seconds."""
        self.now_seconds = 0.0

    def now(self) -> float:
        """Return the current fake counter value in seconds."""
        return self.now_seconds

    def advance(self, seconds: float) -> None:
        """Move the fake counter forward by the given number of seconds."""
        self.now_seconds += seconds
