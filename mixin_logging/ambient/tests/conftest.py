"""Ambient-specific pytest fixtures.

Used by TestAmbientLoggerCorrelationInjection and the other TestAmbientLogger* classes.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from mixin_logging.tests.helpers import LoggerFactory, RecordCollector


@pytest.fixture
def ambient_logger() -> Iterator[LoggerFactory]:
    """Factory for a named logger with a record collector attached at a given level.

    Handlers and levels are removed from every logger the factory touched when the test ends,
    so no capture state leaks into later tests.
    """
    attached: list[tuple[logging.Logger, RecordCollector, int]] = []

    def make(name: str, level: int) -> tuple[logging.Logger, RecordCollector]:
        """Attach a fresh collector to the named logger at the given level."""
        logger = logging.getLogger(name)
        previous_level = logger.level
        collector = RecordCollector()
        logger.addHandler(collector)
        logger.setLevel(level)
        attached.append((logger, collector, previous_level))
        return logger, collector

    yield make
    for logger, collector, previous_level in attached:
        logger.removeHandler(collector)
        logger.setLevel(previous_level)
