"""Utility functions for retry logic."""

from __future__ import annotations

import asyncio
import functools


@functools.lru_cache(maxsize=None)
def should_retry_exception(exc: BaseException) -> bool:
    """Check if exception should trigger retry.

    Never retries BaseException-only members.
    """
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return False

    if isinstance(exc, asyncio.CancelledError):
        return False

    return True
