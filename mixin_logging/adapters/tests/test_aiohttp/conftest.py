"""Aiohttp-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest import mock

import aiohttp
import pytest


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
