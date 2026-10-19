"""Shared pytest fixtures for every mixin_logging test tree.

Used by all adapter, context, common, mixin and redaction test classes.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from mixin_logging import LoggingMixin, clear_correlation_id
from mixin_logging.tests.helpers import RecordCollector


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def service_class() -> type[LoggingMixin]:
    """Bare LoggingMixin subclass with slots: base for service-class tests."""

    class Svc(LoggingMixin):
        """Bare LoggingMixin subclass with no extra state."""

        __slots__ = ()

    return Svc


@pytest.fixture
def log_capture(
    service_class: type[LoggingMixin],
) -> Iterator[tuple[LoggingMixin, RecordCollector]]:
    """Service instance + collector handler attached at DEBUG level, detached after the test.

    Every service class built by service_class shares one logger name, so the handler
    and level are removed on teardown to keep one test's capture out of the next.
    """
    svc = service_class()
    collector = RecordCollector()
    previous_level = svc._logger.level
    svc._logger.addHandler(collector)
    svc._logger.setLevel(logging.DEBUG)
    yield svc, collector
    svc._logger.removeHandler(collector)
    svc._logger.setLevel(previous_level)
