"""Mixin-specific pytest fixtures."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from mixin_logging import LoggingMixin, clear_correlation_id
from mixin_logging.common.utils.record_collector import _RecordCollector


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
        """Bare LoggingMixin subclass for mixin tests."""

        __slots__ = ()

    return Svc


@pytest.fixture
def log_capture(
    service_class: type[LoggingMixin],
) -> tuple[LoggingMixin, _RecordCollector]:
    """Service instance + collector handler attached at DEBUG level."""
    svc = service_class()
    collector = _RecordCollector()
    svc._logger.addHandler(collector)
    svc._logger.setLevel(logging.DEBUG)
    return svc, collector
