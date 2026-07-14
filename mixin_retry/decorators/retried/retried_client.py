"""@retried: exponential backoff retry decorator with full jitter."""

from __future__ import annotations

import asyncio
import functools
import inspect
import random
import time
from typing import TYPE_CHECKING, Any, Callable, Concatenate, ParamSpec, TypeVar

from mixin_retry.decorators.constants import retried as const
from mixin_retry.decorators.retried import retried_objects as objs
from mixin_retry.decorators.retried.retry_inspection import RetryInspection

if TYPE_CHECKING:
    from collections.abc import Awaitable

Params = ParamSpec("Params")
Return = TypeVar("Return")


class RetryClient:
    """Exponential backoff retry decorator with full jitter."""

    def __init__(
        self,
        max_attempts: int,
        base_delay_s: float,
        max_delay_s: float,
        jitter: bool,
        retry_on: Callable[[BaseException], bool] | None = None,
    ) -> None:
        """Initialize retry parameters.

        Args:
            max_attempts: Maximum number of attempts (must be >= 1).
            base_delay_s: Base delay in seconds for exponential backoff.
            max_delay_s: Maximum delay in seconds (capped backoff).
            jitter: Enable full jitter in backoff calculation.
            retry_on: Predicate callable(exception) -> bool.
                Default retries on any Exception.
        """
        if max_attempts < 1:
            raise ValueError(const.ERROR_MSG_MAX_ATTEMPTS_INVALID)

        if retry_on is not None and not callable(retry_on):
            raise ValueError(const.ERROR_MSG_INVALID_PREDICATE)

        self.container = objs.RetryContainer(
            max_attempts=max_attempts,
            base_delay_s=base_delay_s,
            max_delay_s=max_delay_s,
            jitter=jitter,
        )
        self.retry_on = retry_on if retry_on is not None else self._default_retry_on

    @classmethod
    def with_params(
        cls,
        max_attempts: int = 3,
        base_delay_s: float = const.BASE_DELAY_DEFAULT,
        max_delay_s: float = const.MAX_DELAY_DEFAULT,
        jitter: bool = const.JITTER_DEFAULT,
        retry_on: Callable[[BaseException], bool] | None = None,
    ) -> RetryClient:
        """Create a RetryClient with exponential backoff parameters.

        Args:
            max_attempts: Maximum number of attempts (default 3).
            base_delay_s: Base delay in seconds (default 1.0).
            max_delay_s: Maximum delay in seconds (default 60.0).
            jitter: Enable full jitter (default True).
            retry_on: Predicate callable(exception) -> bool.
                Default retries on any Exception.

        Returns:
            RetryClient instance configured with the given parameters.
        """
        return cls(
            max_attempts=max_attempts,
            base_delay_s=base_delay_s,
            max_delay_s=max_delay_s,
            jitter=jitter,
            retry_on=retry_on,
        )

    @staticmethod
    def _default_retry_on(exc: BaseException) -> bool:
        """Default retry predicate: retry on Exception, not BaseException."""
        if not RetryInspection.should_retry_exception(exc):
            return False

        return isinstance(exc, Exception)

    def __call__(self, target: Any) -> Any:
        """Wrap a callable or fan out to all public methods of a class."""
        if inspect.isclass(target):
            return self._decorate_class(target)

        if callable(target):
            is_standalone = RetryInspection.is_standalone_callable(target)
            return self._wrap_callable(target, for_static_or_class=is_standalone)

        msg = const.ERROR_MSG_TARGET_NOT_CLASS_OR_CALLABLE
        raise TypeError(msg)

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number using exponential backoff.

        Args:
            attempt: Attempt number (0-indexed).

        Returns:
            Delay in seconds, capped at max_delay_s.
        """
        exponential_delay = self.container.base_delay_s * (2**attempt)
        capped_delay = min(exponential_delay, self.container.max_delay_s)

        if not self.container.jitter:
            return capped_delay

        return random.uniform(0, capped_delay)

    def _wrap_callable(  # type: ignore[misc]
        self,
        method: Callable[Concatenate[Any, Params], Return],
        for_static_or_class: bool = False,
    ) -> Callable[Concatenate[Any, Params], Return]:
        """Wrap a single callable with retry logic.

        Args:
            method: The callable to wrap.
            for_static_or_class: If True, wrap without self binding.

        Returns:
            Wrapped callable with retry behavior.
        """
        if for_static_or_class:
            if asyncio.iscoroutinefunction(method):

                @functools.wraps(method)
                async def async_static_wrapper(
                    *args: Params.args, **kwargs: Params.kwargs
                ) -> Return:
                    return await self._execute_async(method, *args, **kwargs)

                setattr(async_static_wrapper, const.ATTRIBUTE_MARKER, True)
                return async_static_wrapper  # type: ignore[return-value]

            @functools.wraps(method)
            def static_wrapper(*args: Params.args, **kwargs: Params.kwargs) -> Return:
                return self._execute_sync(method, *args, **kwargs)

            setattr(static_wrapper, const.ATTRIBUTE_MARKER, True)
            return static_wrapper  # type: ignore[return-value]

        if asyncio.iscoroutinefunction(method):

            @functools.wraps(method)
            async def async_wrapper(
                instance: Any,
                *args: Params.args,
                **kwargs: Params.kwargs,
            ) -> Return:
                return await self._execute_async(method, instance, *args, **kwargs)

            setattr(async_wrapper, const.ATTRIBUTE_MARKER, True)
            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(method)
        def wrapper(
            instance: Any,
            *args: Params.args,
            **kwargs: Params.kwargs,
        ) -> Return:
            return self._execute_sync(method, instance, *args, **kwargs)

        setattr(wrapper, const.ATTRIBUTE_MARKER, True)
        return wrapper

    def _execute_sync(
        self,
        method: Callable[Concatenate[Any, Params], Return],
        *args: Params.args,
        **kwargs: Params.kwargs,
    ) -> Return:
        """Execute synchronous call with retry logic.

        Args:
            method: The callable to execute.
            args: Positional arguments to pass.
            kwargs: Keyword arguments to pass.

        Returns:
            Result from successful call.

        Raises:
            Final exception after all retries exhausted.
        """
        for attempt in range(self.container.max_attempts):
            try:
                return method(*args, **kwargs)  # type: ignore[return-value]
            except BaseException as exc:
                if not RetryInspection.should_retry_exception(exc):
                    raise

                if not self.retry_on(exc):
                    raise

                if attempt >= self.container.max_attempts - 1:
                    raise

                delay = self._calculate_delay(attempt)
                time.sleep(delay)

        return method(*args, **kwargs)  # type: ignore[return-value]

    async def _execute_async(
        self,
        method: Callable[..., Awaitable[Return]],
        *args: Any,
        **kwargs: Any,
    ) -> Return:
        """Execute asynchronous call with retry logic.

        Args:
            method: The async callable to execute.
            args: Positional arguments to pass.
            kwargs: Keyword arguments to pass.

        Returns:
            Result from successful call.

        Raises:
            Final exception after all retries exhausted.
        """
        for attempt in range(self.container.max_attempts):
            try:
                return await method(*args, **kwargs)  # type: ignore[return-value]
            except BaseException as exc:
                if not RetryInspection.should_retry_exception(exc):
                    raise

                if not self.retry_on(exc):
                    raise

                if attempt >= self.container.max_attempts - 1:
                    raise

                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)

        return await method(*args, **kwargs)  # type: ignore[return-value]

    def _decorate_class(self, cls: type) -> type:
        """Fan out decorator to all public methods of a class."""
        for name, value in cls.__dict__.items():
            if RetryInspection.should_skip_member(name, value):
                continue

            if hasattr(value, const.ATTRIBUTE_MARKER):
                continue

            if isinstance(value, classmethod):
                wrapped = self._wrap_callable(
                    value.__func__,
                    for_static_or_class=True,
                )
                setattr(cls, name, classmethod(wrapped))
            elif isinstance(value, staticmethod):
                wrapped = self._wrap_callable(
                    value.__func__,
                    for_static_or_class=True,
                )
                setattr(cls, name, staticmethod(wrapped))
            elif callable(value):
                wrapped = self._wrap_callable(value)
                setattr(cls, name, wrapped)

        return cls
