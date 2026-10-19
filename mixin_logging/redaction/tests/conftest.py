"""Fixtures for redaction filter tests.

Used by TestRedactionClient and TestRedactionFilter.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator

import pytest

from mixin_logging.redaction import RedactionFilter
from mixin_logging.tests.helpers import RecordCollector


@pytest.fixture
def redaction_logger() -> Iterator[logging.Logger]:
    """Named logger at DEBUG with no handlers or filters, cleared again after the test.

    Each TestRedactionClient test attaches a filter here, so the filter list is reset on teardown.
    """
    logger = logging.getLogger("mixin_logging_test.redaction")
    logger.handlers.clear()
    logger.filters.clear()
    logger.setLevel(logging.DEBUG)
    yield logger
    logger.handlers.clear()
    logger.filters.clear()
    logger.setLevel(logging.NOTSET)


@pytest.fixture
def redaction_collector(redaction_logger: logging.Logger) -> RecordCollector:
    """Collector handler attached to redaction_logger for the test."""
    collector = RecordCollector()
    redaction_logger.addHandler(collector)
    return collector


@pytest.fixture
def make_record() -> Callable[..., logging.LogRecord]:
    """Factory for bare log records used when calling a filter directly."""

    def build(message: str = "test", level: int = logging.INFO) -> logging.LogRecord:
        """Build one record with the given message and level."""
        return logging.LogRecord(
            name="test",
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )

    return build


@pytest.fixture
def redaction_filter() -> RedactionFilter:
    """Create a RedactionFilter with default patterns."""
    return RedactionFilter.with_defaults()
