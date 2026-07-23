"""Tests for RetryExecutor capability."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import patch

from mixin_retry.executor import RetryExecutor
from mixin_retry.policy import (
    ERR_RETRY_BACKOFF_BASE,
    ERR_RETRY_BACKOFF_MAX,
    ERR_RETRY_BACKOFF_MULTIPLIER,
    ERR_RETRY_MAX_ATTEMPTS,
    RetryPolicy,
)


class TestRetryPolicy:
    """Test RetryPolicy validation."""

    def test_policy_valid_construction(self) -> None:
        """RetryPolicy constructs with valid parameters."""
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.1,
            backoff_multiplier=2.0,
            backoff_max_seconds=10.0,
            jitter=True,
        )
        assert policy.max_attempts == 3
        assert policy.backoff_base_seconds == 0.1

    def test_policy_invalid_max_attempts_zero(self) -> None:
        """RetryPolicy rejects max_attempts < 1."""
        with pytest.raises(ValueError, match=ERR_RETRY_MAX_ATTEMPTS):
            RetryPolicy(
                max_attempts=0,
                backoff_base_seconds=0.1,
                backoff_multiplier=2.0,
                backoff_max_seconds=10.0,
                jitter=False,
            )

    def test_policy_invalid_backoff_base_zero(self) -> None:
        """RetryPolicy rejects backoff_base_seconds <= 0."""
        with pytest.raises(ValueError, match=ERR_RETRY_BACKOFF_BASE):
            RetryPolicy(
                max_attempts=3,
                backoff_base_seconds=0.0,
                backoff_multiplier=2.0,
                backoff_max_seconds=10.0,
                jitter=False,
            )

    def test_policy_invalid_backoff_multiplier_zero(self) -> None:
        """RetryPolicy rejects backoff_multiplier <= 0."""
        with pytest.raises(ValueError, match=ERR_RETRY_BACKOFF_MULTIPLIER):
            RetryPolicy(
                max_attempts=3,
                backoff_base_seconds=0.1,
                backoff_multiplier=0.0,
                backoff_max_seconds=10.0,
                jitter=False,
            )

    def test_policy_invalid_backoff_max_zero(self) -> None:
        """RetryPolicy rejects backoff_max_seconds <= 0."""
        with pytest.raises(ValueError, match=ERR_RETRY_BACKOFF_MAX):
            RetryPolicy(
                max_attempts=3,
                backoff_base_seconds=0.1,
                backoff_multiplier=2.0,
                backoff_max_seconds=0.0,
                jitter=False,
            )


class TestRetryExecutor:
    """Test RetryExecutor sync and async capabilities."""

    def test_wrap_sync_success_no_retry(self) -> None:
        """Wrap sync function that succeeds immediately."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.01,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.1,
            jitter=False,
            retry_on=(ConnectionError,),
        )

        call_count = 0

        def success_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        wrapped = executor.wrap(success_fn, policy=policy)
        result = wrapped()

        assert result == "ok"
        assert call_count == 1

    def test_wrap_sync_retries_then_succeeds(self) -> None:
        """Wrap sync function that fails then succeeds."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
            retry_on=(ValueError,),
        )

        call_count = 0

        def flaky_fn() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "ok"

        wrapped = executor.wrap(flaky_fn, policy=policy)

        with patch("time.sleep") as mock_sleep:
            result = wrapped()

        assert result == "ok"
        assert call_count == 2
        assert mock_sleep.called

    def test_wrap_sync_max_attempts_exhausted(self) -> None:
        """Wrap sync function that always fails."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=2,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
            retry_on=(ValueError,),
        )

        call_count = 0

        def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        wrapped = executor.wrap(always_fail, policy=policy)

        with patch("time.sleep"):
            with pytest.raises(ValueError, match="fail"):
                wrapped()

        assert call_count == 2

    def test_wrap_sync_should_retry_predicate(self) -> None:
        """Wrap sync function with should_retry predicate."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
            should_retry=lambda exc: isinstance(
                exc, ConnectionError
            ),
        )

        call_count = 0

        def fails_with_connection_error() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("no connection")
            return "ok"

        wrapped = executor.wrap(fails_with_connection_error, policy=policy)

        with patch("time.sleep"):
            result = wrapped()

        assert result == "ok"
        assert call_count == 2

    def test_wrap_sync_should_retry_with_cause_chain(self) -> None:
        """Wrap sync with should_retry unwrapping __cause__."""
        executor = RetryExecutor()

        def is_connection_error(exc: BaseException) -> bool:
            return isinstance(exc, ConnectionError)

        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
            should_retry=is_connection_error,
        )

        call_count = 0

        def fails_with_chain() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                try:
                    raise ConnectionError("root")
                except ConnectionError as e:
                    raise ValueError("wrapped") from e
            return "ok"

        wrapped = executor.wrap(fails_with_chain, policy=policy)

        with patch("time.sleep"):
            result = wrapped()

        assert result == "ok"
        assert call_count == 2

    def test_wrap_sync_no_retry_on_excluded_exception(self) -> None:
        """Wrap sync that raises non-retryable exception."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
            retry_on=(ConnectionError,),
        )

        def fails_with_value_error() -> None:
            raise ValueError("not retryable")

        wrapped = executor.wrap(fails_with_value_error, policy=policy)

        with pytest.raises(ValueError, match="not retryable"):
            wrapped()

    def test_wrap_async_success_no_retry(self) -> None:
        """Wrap async function that succeeds immediately."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
            retry_on=(ConnectionError,),
        )

        call_count = 0

        async def success_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        wrapped = executor.wrap(success_fn, policy=policy)
        result = asyncio.run(wrapped())

        assert result == "ok"
        assert call_count == 1

    def test_wrap_async_retries_then_succeeds(self) -> None:
        """Wrap async function that fails then succeeds."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.0001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.0001,
            jitter=False,
            retry_on=(ValueError,),
        )

        call_count = 0

        async def flaky_fn() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "ok"

        wrapped = executor.wrap(flaky_fn, policy=policy)
        result = asyncio.run(wrapped())

        assert result == "ok"
        assert call_count == 2

    def test_wrap_async_max_attempts_exhausted(self) -> None:
        """Wrap async function that always fails."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=2,
            backoff_base_seconds=0.0001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.0001,
            jitter=False,
            retry_on=(ValueError,),
        )

        call_count = 0

        async def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        wrapped = executor.wrap(always_fail, policy=policy)

        with pytest.raises(ValueError, match="fail"):
            asyncio.run(wrapped())

        assert call_count == 2

    def test_call_requires_policy(self) -> None:
        """call() method requires policy argument."""
        executor = RetryExecutor()

        def dummy_fn() -> None:
            pass

        with pytest.raises(ValueError, match="policy is required"):
            executor.call(dummy_fn)

    def test_call_with_policy_sync(self) -> None:
        """call() method with policy on sync function."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=2,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
            retry_on=(ValueError,),
        )

        def add(a: int, b: int) -> int:
            return a + b

        with patch("time.sleep"):
            result = executor.call(add, 2, 3, policy=policy)

        assert result == 5

    def test_backoff_calculation_no_jitter(self) -> None:
        """Backoff calculation without jitter."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=1.0,
            backoff_multiplier=2.0,
            backoff_max_seconds=10.0,
            jitter=False,
        )

        assert executor._calculate_backoff(0, policy) == 1.0
        assert executor._calculate_backoff(1, policy) == 2.0
        assert executor._calculate_backoff(2, policy) == 4.0

    def test_backoff_calculation_respects_max(self) -> None:
        """Backoff calculation respects max_seconds."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=4,
            backoff_base_seconds=1.0,
            backoff_multiplier=2.0,
            backoff_max_seconds=3.0,
            jitter=False,
        )

        assert executor._calculate_backoff(0, policy) == 1.0
        assert executor._calculate_backoff(1, policy) == 2.0
        assert executor._calculate_backoff(2, policy) == 3.0
        assert executor._calculate_backoff(3, policy) == 3.0

    def test_backoff_with_jitter_in_bounds(self) -> None:
        """Backoff with jitter stays within bounds."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=2,
            backoff_base_seconds=1.0,
            backoff_multiplier=2.0,
            backoff_max_seconds=10.0,
            jitter=True,
        )

        for _ in range(10):
            backoff = executor._calculate_backoff(0, policy)
            assert 0.9 <= backoff <= 1.1

    def test_wrap_async_no_retry_on_excluded_exception(self) -> None:
        """Wrap async that raises non-retryable exception."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.0001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.0001,
            jitter=False,
            retry_on=(ConnectionError,),
        )

        async def fails_with_value_error() -> None:
            raise ValueError("not retryable")

        wrapped = executor.wrap(fails_with_value_error, policy=policy)

        with pytest.raises(ValueError, match="not retryable"):
            asyncio.run(wrapped())

    def test_no_retry_when_neither_predicate_nor_retry_on_set(self) -> None:
        """_should_retry returns False when no retry condition is set."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=2,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
        )

        def always_fails() -> None:
            raise ValueError("fail")

        wrapped = executor.wrap(always_fails, policy=policy)

        with pytest.raises(ValueError, match="fail"):
            wrapped()

    def test_wrap_preserves_function_metadata(self) -> None:
        """Wrap preserves original function metadata."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=1,
            backoff_base_seconds=0.001,
            backoff_multiplier=1.0,
            backoff_max_seconds=0.01,
            jitter=False,
        )

        def my_function() -> str:
            """Original docstring."""
            return "result"

        wrapped = executor.wrap(my_function, policy=policy)

        assert wrapped.__name__ == "my_function"
        assert wrapped.__doc__ == "Original docstring."

    def test_no_retry_on_no_should_retry_raises_immediately(self) -> None:
        """Policy with no retry_on and no should_retry raises immediately."""
        executor = RetryExecutor()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.001,
            backoff_multiplier=2.0,
            backoff_max_seconds=0.01,
            jitter=False,
        )

        def fails() -> None:
            raise ValueError("fail")

        wrapped = executor.wrap(fails, policy=policy)

        with pytest.raises(ValueError, match="fail"):
            wrapped()
