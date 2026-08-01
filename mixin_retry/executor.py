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
        operation: Callable[..., T],
        /,
        policy: RetryPolicy,
    ) -> Callable[..., T]:
        """Wrap function with retry logic (rebind once, call many).

        Returns a wrapper preserving operation's signature via functools.wraps.
        Supports both sync and async functions.

        Args:
            operation: Function to wrap.
            policy: Retry policy configuration.

        Returns:
            Wrapped function with retry logic.
        """
        if inspect.iscoroutinefunction(operation):
            return self._wrap_async(operation, policy)
        return self._wrap_sync(operation, policy)

    def _wrap_sync(
        self,
        operation: Callable[..., T],
        policy: RetryPolicy,
    ) -> Callable[..., T]:
        """Wrap a synchronous function."""

        @functools.wraps(operation)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: BaseException | None = None
            for attempt in range(policy.max_attempts):
                try:
                    return operation(*args, **kwargs)
                except BaseException as error:
                    last_error = error
                    if attempt == policy.max_attempts - 1:
                        raise
                    if not self._should_retry(error, policy):
                        raise
                    backoff = self._calculate_backoff(attempt, policy)
                    time.sleep(backoff)
            assert last_error is not None  # pragma: no cover
            raise last_error  # pragma: no cover

        return wrapper

    def _wrap_async(
        self,
        operation: Callable[..., Any],
        policy: RetryPolicy,
    ) -> Callable[..., Any]:
        """Wrap an asynchronous function."""

        @functools.wraps(operation)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: BaseException | None = None
            for attempt in range(policy.max_attempts):
                try:
                    return await operation(*args, **kwargs)
                except BaseException as error:
                    last_error = error
                    if attempt == policy.max_attempts - 1:
                        raise
                    if not self._should_retry(error, policy):
                        raise
                    backoff = self._calculate_backoff(attempt, policy)
                    await asyncio.sleep(backoff)
            assert last_error is not None  # pragma: no cover
            raise last_error  # pragma: no cover

        return wrapper

    def call(
        self,
        operation: Callable[..., T],
        /,
        *args: Any,
        policy: RetryPolicy | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute operation with retry (per-call convenience form).

        Args:
            operation: Function to execute.
            *args: Positional arguments to operation.
            policy: Retry policy configuration. Required.
            **kwargs: Keyword arguments to operation.

        Returns:
            Function result.

        Raises:
            ValueError: If policy is None.
            BaseException: Original exception if all retries exhausted.
        """
        if policy is None:
            raise ValueError(const.ERR_RETRY_POLICY_REQUIRED)
        wrapped = self.wrap(operation, policy)
        return wrapped(*args, **kwargs)

    def _should_retry(
        self,
        error: BaseException,
        policy: RetryPolicy,
    ) -> bool:
        """Determine if exception is retryable.

        The predicate receives the caught exception as-is and owns any
        unwrapping of __cause__ chains.
        """
        if policy.should_retry is not None:
            return policy.should_retry(error)
        if policy.retry_on:
            return isinstance(error, policy.retry_on)
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
