"""Botocore-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Iterator

import pytest
from botocore.awsrequest import AWSRequest

from mixin_logging import clear_correlation_id


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def make_request() -> Callable[..., Any]:
    """Factory fixture for creating a botocore AWSRequest with method/url defaults."""

    def factory(
        method: str = "GET",
        url: str = "https://example.com/test",
    ) -> AWSRequest:
        """Create a minimal botocore AWSRequest for testing."""
        return AWSRequest(method=method, url=url, headers={})

    return factory
