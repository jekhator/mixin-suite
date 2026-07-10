"""Aiohttp-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Iterator
from unittest import mock

import aiohttp
import pytest

from mixin_logging import clear_correlation_id


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def make_trace_params() -> Callable[..., Any]:
    """Factory fixture for creating aiohttp.TraceRequestStartParams mock."""

    def factory(
        headers: dict[str, str] | None = None,
    ) -> aiohttp.TraceRequestStartParams:
        """Create a minimal aiohttp.TraceRequestStartParams mock for testing."""
        params = mock.MagicMock(spec=aiohttp.TraceRequestStartParams)
        params.headers = headers or {}
        return params

    return factory
