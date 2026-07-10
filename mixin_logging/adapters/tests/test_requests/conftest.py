"""Requests-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Iterator

import pytest
import requests as requests_lib  # type: ignore[import-untyped]

from mixin_logging import clear_correlation_id


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def make_prepared_request() -> Callable[..., Any]:
    """Factory fixture for creating a requests.PreparedRequest with method/url defaults."""

    def factory(
        method: str = "GET",
        url: str = "https://example.com/test",
    ) -> requests_lib.PreparedRequest:
        """Create a minimal requests.PreparedRequest for testing."""
        request = requests_lib.Request(method=method, url=url)
        return request.prepare()

    return factory
