"""Correlation-specific pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mixin_logging import clear_correlation_id

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()
