"""Execute functions with exponential backoff retry."""

from __future__ import annotations

import asyncio
import functools
import inspect
import math
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any, cast

from mixin_retry.common.constants import backoff as backoff_const, errors as const
from mixin_retry.policy import RetryPolicy


class RetryExecutor:
    """Execute functions with exponential backoff retry logic."""

    def wrap[OperationReturnType](
        self,
        operation: Callable[..., OperationReturnType],
        /,
        policy: RetryPolicy,
    ) -> Callable[..., OperationReturnType]:
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
            async_operation = cast("Callable[..., Awaitable[Any]]", operation)
            return cast(
                "Callable[..., OperationReturnType]",
                self._wrap_async(async_operation, policy),
            )
        return self._wrap_sync(operation, policy)

    def _wrap_sync[OperationReturnType](
        self,
        operation: Callable[..., OperationReturnType],
        policy: RetryPolicy,
    ) -> Callable[..., OperationReturnType]:
        """Wrap a synchronous function."""

        @functools.wraps(operation)
        def wrapper(*args: Any, **kwargs: Any) -> OperationReturnType:
            for attempt in range(policy.max_attempts - 1):
                try:
                    return operation(*args, **kwargs)
                except BaseException as error:
                    if not self._should_retry(error, policy):
                        raise
                    time.sleep(self._calculate_backoff(attempt, policy))
            return operation(*args, **kwargs)

        return wrapper

    def _wrap_async[AwaitedReturnType](
        self,
        operation: Callable[..., Awaitable[AwaitedReturnType]],
        policy: RetryPolicy,
    ) -> Callable[..., Awaitable[AwaitedReturnType]]:
        """Wrap an asynchronous function."""

        @functools.wraps(operation)
        async def wrapper(*args: Any, **kwargs: Any) -> AwaitedReturnType:
            for attempt in range(policy.max_attempts - 1):
                try:
                    return await operation(*args, **kwargs)
                except BaseException as error:
                    if not self._should_retry(error, policy):
                        raise
                    await asyncio.sleep(self._calculate_backoff(attempt, policy))
            return await operation(*args, **kwargs)

        return wrapper

    def call[OperationReturnType](
        self,
        operation: Callable[..., OperationReturnType],
        /,
        *args: Any,
        policy: RetryPolicy | None = None,
        **kwargs: Any,
    ) -> OperationReturnType:
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
        try:
            exponential = policy.backoff_base_seconds * (
                policy.backoff_multiplier**attempt
            )
        except OverflowError:
            # The growth term left float range, so it is above any finite cap.
            exponential = math.inf if policy.backoff_base_seconds > 0 else 0.0
        backoff = min(exponential, policy.backoff_max_seconds)
        if policy.jitter:
            jitter_factor = random.uniform(
                backoff_const.JITTER_MIN_FACTOR,
                backoff_const.JITTER_MAX_FACTOR,
            )
            backoff *= jitter_factor
        return backoff
