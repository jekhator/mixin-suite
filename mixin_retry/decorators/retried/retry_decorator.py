"""@retried decorator factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from mixin_retry.decorators.constants import retried as const
from mixin_retry.decorators.retried.retried_client import RetryClient

if TYPE_CHECKING:
    pass


def retried(
    max_attempts: int = 3,
    base_delay_s: float = const.BASE_DELAY_DEFAULT,
    max_delay_s: float = const.MAX_DELAY_DEFAULT,
    jitter: bool = const.JITTER_DEFAULT,
    retry_on: Callable[[BaseException], bool] | None = None,
) -> Callable[[Any], Any]:
    """Create a @retried decorator with exponential backoff parameters.

    Args:
        max_attempts: Maximum number of attempts (default 3).
        base_delay_s: Base delay in seconds (default 1.0).
        max_delay_s: Maximum delay in seconds (default 60.0).
        jitter: Enable full jitter (default True).
        retry_on: Predicate callable(exception) -> bool.
            Default retries on any Exception.

    Returns:
        Decorator that wraps functions, methods, or classes.

    Example:
        @retried(max_attempts=5, retry_on=lambda e: isinstance(e, IOError))
        def might_fail():
            pass
    """
    client = RetryClient(
        max_attempts=max_attempts,
        base_delay_s=base_delay_s,
        max_delay_s=max_delay_s,
        jitter=jitter,
        retry_on=retry_on,
    )
    return client
