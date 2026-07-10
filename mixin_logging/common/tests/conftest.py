"""Conftest for common-helpers tests with global test isolation."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from mixin_logging import clear_correlation_id


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()
