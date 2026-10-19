"""Test helpers for mixin-logging test suite."""

from __future__ import annotations

import logging


class RecordCollector(logging.Handler):
    """In-memory handler collecting emitted log records for assertion."""

    __slots__ = ("records",)

    def __init__(self) -> None:
        """Initialize handler with empty records list."""
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Append the emitted record to the collected list."""
        self.records.append(record)


class FakeClock:
    """Manually advanced clock that stands in for time.time in TTL tests."""

    def __init__(self, now: float = 0.0) -> None:
        """Start the clock at the given time."""
        self.now = now

    def time(self) -> float:
        """Return the current fake time."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake time forward by the given number of seconds."""
        self.now += seconds
