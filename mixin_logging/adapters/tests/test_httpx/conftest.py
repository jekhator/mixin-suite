"""Httpx-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx as httpx_lib
import pytest

from mixin_logging import clear_correlation_id


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def make_request() -> Callable[..., Any]:
    """Factory fixture for creating httpx.Request with method/url defaults."""

    def factory(
        method: str = "GET",
        url: str = "https://example.com/test",
    ) -> httpx_lib.Request:
        """Create a minimal httpx.Request for testing."""
        return httpx_lib.Request(method=method, url=url)

    return factory
