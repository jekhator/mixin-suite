"""Httpx-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx as httpx_lib
import pytest


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
