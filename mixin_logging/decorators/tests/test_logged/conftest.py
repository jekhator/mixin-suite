"""Logged-decorator-specific pytest fixtures."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from mixin_logging import LoggingMixin, clear_correlation_id
from mixin_logging.common.utils.record_collector import _RecordCollector

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


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
        """Bare LoggingMixin subclass for fixture testing."""

        __slots__ = ()

    return Svc


@pytest.fixture
def log_capture(
    service_class: type[LoggingMixin],
) -> tuple[LoggingMixin, _RecordCollector]:
    """Service instance + collector handler attached at DEBUG level."""
    svc = service_class()
    collector = _RecordCollector()
    svc._logger.addHandler(collector)  # noqa: SLF001
    svc._logger.setLevel(logging.DEBUG)  # noqa: SLF001
    return svc, collector


@pytest.fixture
def log_capture_factory() -> Callable[[LoggingMixin], _RecordCollector]:
    """Attach a collector to a service instance."""

    def attach(svc: LoggingMixin) -> _RecordCollector:
        collector = _RecordCollector()
        svc._logger.addHandler(collector)  # noqa: SLF001
        svc._logger.setLevel(logging.DEBUG)  # noqa: SLF001
        return collector

    return attach
