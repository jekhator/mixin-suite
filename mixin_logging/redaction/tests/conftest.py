"""Fixtures for redaction filter tests."""

import logging

import pytest

from mixin_logging.redaction import RedactionClient, RedactionFilter


class TestHandler(logging.Handler):
    """Test handler that captures emitted records."""

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Capture the record."""
        self.records.append(record)


@pytest.fixture
def test_logger() -> logging.Logger:
    """Create a fresh logger for each test."""
    logger = logging.getLogger("test_redaction")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def test_handler() -> TestHandler:
    """Create a fresh test handler for each test."""
    return TestHandler()


@pytest.fixture
def redaction_filter() -> RedactionFilter:
    """Create a RedactionFilter with default patterns."""
    return RedactionFilter.with_defaults()
