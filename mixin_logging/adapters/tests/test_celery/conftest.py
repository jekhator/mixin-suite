"""Celery-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from celery import Celery
from celery.signals import before_task_publish, task_postrun, task_prerun

from mixin_logging.adapters.celery import celery_client


@pytest.fixture
def celery_app() -> Callable[..., Any]:
    """Factory fixture for creating a test Celery app with eager mode."""

    def factory() -> Celery:
        """Create a minimal Celery app with task_always_eager=True."""
        app = Celery()
        app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return app

    return factory


@pytest.fixture
def connected_celery_signals() -> Iterator[None]:
    """Connect the correlation signal handlers for one test and disconnect them afterwards.

    Used by TestCorrelationSignalsRealCeleryIntegration so no handler leaks into later tests.
    """
    celery_client.CorrelationSignals.connect()
    yield
    before_task_publish.disconnect(celery_client.CorrelationSignals.inject_on_publish)
    task_prerun.disconnect(celery_client.CorrelationSignals.restore_on_prerun)
    task_postrun.disconnect(celery_client.CorrelationSignals.clear_on_postrun)
