"""Execute functions with exponential backoff retry."""

from __future__ import annotations

import asyncio
import functools
import inspect
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from mixin_retry.common.constants import errors as const
from mixin_retry.policy import RetryPolicy

T = TypeVar("T")


class RetryExecutor:
    """Execute functions with exponential backoff retry logic."""

    def wrap(
        self,
        fn: Callable[..., T],
        policy: RetryPolicy,
    ) -> Callable[..., T]:
        """Wrap function with retry logic (rebind once, call many).

        Returns a wrapper preserving fn's signature via functools.wraps.
        Supports both sync and async functions.

        Args:
            fn: Function to wrap.
            policy: Retry policy configuration.

        Returns:
            Wrapped function with retry logic.
        """
        if inspect.iscoroutinefunction(fn):
            return self._wrap_async(fn, policy)
        return self._wrap_sync(fn, policy)

    def _wrap_sync(
        self,
        fn: Callable[..., T],
        policy: RetryPolicy,
    ) -> Callable[..., T]:
        """Wrap a synchronous function."""

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt in range(policy.max_attempts):
                try:
                    return fn(*args, **kwargs)
                except BaseException as exc:
                    last_exc = exc
                    if attempt == policy.max_attempts - 1:
                        raise
                    if not self._should_retry(exc, policy):
                        raise
                    backoff = self._calculate_backoff(attempt, policy)
                    time.sleep(backoff)
            assert last_exc is not None  # pragma: no cover
            raise last_exc  # pragma: no cover

        return wrapper

    def _wrap_async(
        self,
        fn: Callable[..., Any],
        policy: RetryPolicy,
    ) -> Callable[..., Any]:
        """Wrap an asynchronous function."""

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt in range(policy.max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except BaseException as exc:
                    last_exc = exc
                    if attempt == policy.max_attempts - 1:
                        raise
                    if not self._should_retry(exc, policy):
                        raise
                    backoff = self._calculate_backoff(attempt, policy)
                    await asyncio.sleep(backoff)
            assert last_exc is not None  # pragma: no cover
            raise last_exc  # pragma: no cover

        return wrapper

    def call(
        self,
        fn: Callable[..., T],
        *args: Any,
        policy: RetryPolicy | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute fn with retry (per-call convenience form).

        Args:
            fn: Function to execute.
            *args: Positional arguments to fn.
            policy: Retry policy configuration. Required.
            **kwargs: Keyword arguments to fn.

        Returns:
            Function result.

        Raises:
            ValueError: If policy is None.
            BaseException: Original exception if all retries exhausted.
        """
        if policy is None:
            raise ValueError(const.ERR_RETRY_POLICY_REQUIRED)
        wrapped = self.wrap(fn, policy)
        return wrapped(*args, **kwargs)

    def _should_retry(
        self,
        exc: BaseException,
        policy: RetryPolicy,
    ) -> bool:
        """Determine if exception is retryable.

        The predicate receives the caught exception as-is and owns any
        unwrapping of __cause__ chains.
        """
        if policy.should_retry is not None:
            return policy.should_retry(exc)
        if policy.retry_on:
            return isinstance(exc, policy.retry_on)
        return False

    def _calculate_backoff(
        self,
        attempt: int,
        policy: RetryPolicy,
    ) -> float:
        """Calculate backoff delay with optional jitter."""
        backoff = min(
            policy.backoff_base_seconds * (policy.backoff_multiplier**attempt),
            policy.backoff_max_seconds,
        )
        if policy.jitter:
            jitter_factor = random.uniform(0.9, 1.1)
            backoff *= jitter_factor
        return backoff
