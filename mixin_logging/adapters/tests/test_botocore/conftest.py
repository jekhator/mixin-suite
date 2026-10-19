"""Botocore-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from botocore.awsrequest import AWSRequest


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
