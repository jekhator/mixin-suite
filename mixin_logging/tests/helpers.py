"""Test helpers for mixin-logging test suite."""

from __future__ import annotations

import logging


class _RecordCollector(logging.Handler):
    """In-memory handler collecting emitted log records for assertion."""

    __slots__ = ("records",)

    def __init__(self) -> None:
        """Initialize handler with empty records list."""
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Append the emitted record to the collected list."""
        self.records.append(record)
