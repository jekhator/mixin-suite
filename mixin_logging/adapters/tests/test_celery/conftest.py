"""Celery-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Iterator

import pytest
from celery import Celery

from mixin_logging import clear_correlation_id


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


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
