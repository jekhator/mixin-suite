"""Stdlib-specific pytest fixtures for adapter tests.

Used by TestFlushOnWarningConfigValidation, the TestFlushOnWarningHandler* classes and
TestStdlibLoggingClient.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator

import pytest

from mixin_logging.tests.helpers import FakeClock, RecordCollector


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


@pytest.fixture
def scratch_logger_factory(
    request: pytest.FixtureRequest,
) -> Iterator[Callable[[str], logging.Logger]]:
    """Factory for loggers scoped to one test: named after the test, detached from the root logger.

    Each logger is created with propagate disabled, and its handlers and filters are cleared
    before the test and again after it, so nothing attached during a test outlives it.
    Used by TestCorrelationLogFilterAddCorrelationFilter and TestCorrelationLogFilterRealLoggingIntegration.
    """
    created: list[logging.Logger] = []

    def make(suffix: str) -> logging.Logger:
        """Create a fresh logger for this test with the given suffix."""
        logger = logging.getLogger(f"mixin_logging_test.{request.node.name}.{suffix}")
        logger.handlers.clear()
        logger.filters.clear()
        logger.setLevel(logging.INFO)
        logger.propagate = False
        created.append(logger)
        return logger

    yield make
    for logger in created:
        logger.handlers.clear()
        logger.filters.clear()
        logger.setLevel(logging.NOTSET)
        logger.propagate = True
