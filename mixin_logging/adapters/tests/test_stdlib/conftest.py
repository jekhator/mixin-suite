"""Stdlib-specific pytest fixtures for adapter tests.

Used by TestFlushOnWarningConfigValidation, the TestFlushOnWarningHandler* classes and
TestStdlibLoggingClient.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator

import pytest

from mixin_logging import clear_correlation_id
from mixin_logging.tests.helpers import FakeClock, RecordCollector


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def make_record() -> Callable[..., logging.LogRecord]:
    """Factory for log records with a fixed logger name, path and line number.

    Used by TestFlushOnWarningHandlerBuffering, TestFlushOnWarningHandlerCapacity,
    TestFlushOnWarningHandlerTTL and TestFlushOnWarningHandlerNullCorrelation.
    """

    def build(message: str, level: int = logging.DEBUG) -> logging.LogRecord:
        """Build one record with the given message and level."""
        return logging.LogRecord(
            name="test",
            level=level,
            pathname="test.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )

    return build


@pytest.fixture
def record_target() -> RecordCollector:
    """Capturing target handler that flushed records are emitted to.

    Used by every TestFlushOnWarningHandler* class.
    """
    return RecordCollector()


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    """Fake clock installed as time.time for the duration of one test.

    Used by TestFlushOnWarningHandlerTTL.
    """
    clock = FakeClock()
    monkeypatch.setattr(time, "time", clock.time)
    return clock
