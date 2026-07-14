"""Tests for @retried decorator and RetryClient."""

import asyncio
import time
from typing import Callable

import pytest

from mixin_retry.decorators.constants import retried as const
from mixin_retry.decorators.retried import RetryClient, retried


class TestRetried:
    """Test @retried decorator on functions, methods, and classes."""

    def test_function_decoration_success(self) -> None:
        """Decorate a function and call it successfully."""

        def simple_function() -> str:
            """Simple function for testing."""
            return "function result"

        decorated = retried(max_attempts=3)(simple_function)
        result = decorated()
        assert result == "function result"

    def test_function_decoration_preserves_metadata(self) -> None:
        """@retried preserves original function metadata via functools.wraps."""

        def my_function() -> str:
            """My docstring."""
            return "result"

        decorated = retried()(my_function)
        assert decorated.__name__ == "my_function"
        assert "My docstring" in decorated.__doc__

    def test_function_retry_on_exception(self) -> None:
        """Retry on exception and eventually succeed."""
        call_count = 0

        def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        decorated = retried(max_attempts=5)(eventually_succeeds)
        result = decorated()
        assert result == "success"
        assert call_count == 3

    def test_function_exhausts_retries(self) -> None:
        """Function exceeding max_attempts raises final exception."""

        def always_fails() -> None:
            raise ValueError("Always fails")

        decorated = retried(max_attempts=2)(always_fails)

        with pytest.raises(ValueError, match="Always fails"):
            decorated()

    def test_function_negative_control_no_decorator(self) -> None:
        """Without decorator, function fails on first attempt."""

        call_count = 0

        def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Fail")
            return "success"

        with pytest.raises(ValueError):
            eventually_succeeds()

        assert call_count == 1

    def test_method_decoration_success(self, service) -> None:
        """Decorate a service method and call it successfully."""
        decorated_method = retried(max_attempts=3)(service.success_method)
        result = decorated_method()
        assert result == "success"

    def test_method_retry_on_exception(self, service, call_counter) -> None:
        """Retry on exception and eventually succeed."""
        decorated = retried(max_attempts=5)(call_counter.eventually_succeeds)
        result = decorated(fail_until=2)
        assert "success" in result
        assert call_counter.count == 3

    def test_class_level_decoration(self) -> None:
        """Apply @retried to a class to decorate all public methods."""

        @retried(max_attempts=3)
        class MyService:
            """Test service class."""

            def __init__(self) -> None:
                """Initialize."""
                self.count = 0

            def _private_method(self) -> str:
                """Should not be decorated."""
                return "private"

            def public_method(self) -> str:
                """Should be decorated."""
                return "public"

            def eventually_succeeds(self) -> str:
                """Method that fails then succeeds."""
                self.count += 1
                if self.count < 2:
                    raise ValueError("Fail")
                return "success"

        service = MyService()
        assert service.public_method() == "public"
        assert service.eventually_succeeds() == "success"
        assert service._private_method() == "private"

    def test_decorated_method_has_marker(self) -> None:
        """Decorated methods have the retry marker attribute."""
        decorated = retried(max_attempts=3)(lambda: "result")
        assert hasattr(decorated, const.ATTRIBUTE_MARKER)
        assert getattr(decorated, const.ATTRIBUTE_MARKER) is True

    def test_class_methods_are_not_double_decorated(self) -> None:
        """Already decorated methods are skipped on class decoration."""

        @retried(max_attempts=2)
        class MyService:
            """Service with pre-decorated method."""

            @retried(max_attempts=3)
            def method(self) -> str:
                """Pre-decorated method."""
                return "result"

        service = MyService()
        result = service.method()
        assert result == "result"

    def test_retry_on_predicate_true_retries(self) -> None:
        """retry_on predicate returning True causes retry."""
        call_count = 0

        def sometimes_fails() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Fail")
            return "success"

        retry_on = lambda exc: isinstance(exc, ValueError)
        decorated = retried(max_attempts=5, retry_on=retry_on)(
            sometimes_fails
        )
        result = decorated()
        assert result == "success"
        assert call_count == 3

    def test_retry_on_predicate_false_does_not_retry(self) -> None:
        """retry_on predicate returning False raises immediately."""

        def always_fails() -> None:
            raise ValueError("Fail")

        retry_on = lambda exc: isinstance(exc, IOError)
        decorated = retried(max_attempts=5, retry_on=retry_on)(always_fails)

        with pytest.raises(ValueError, match="Fail"):
            decorated()

    def test_retry_on_predicate_selective_exception(self) -> None:
        """retry_on can selectively retry on specific exception types."""

        def raises_value_error() -> None:
            raise ValueError("value error")

        def raises_io_error() -> None:
            raise IOError("io error")

        retry_on_io = lambda exc: isinstance(exc, IOError)

        with pytest.raises(ValueError):
            retried(max_attempts=5, retry_on=retry_on_io)(
                raises_value_error
            )()

    def test_keyboard_interrupt_never_retries(self) -> None:
        """KeyboardInterrupt is never retried."""

        def raises_interrupt() -> None:
            raise KeyboardInterrupt()

        decorated = retried(max_attempts=10)(raises_interrupt)

        with pytest.raises(KeyboardInterrupt):
            decorated()

    def test_system_exit_never_retries(self) -> None:
        """SystemExit is never retried."""

        def raises_exit() -> None:
            raise SystemExit(1)

        decorated = retried(max_attempts=10)(raises_exit)

        with pytest.raises(SystemExit):
            decorated()

    def test_exponential_backoff_timing(self) -> None:
        """Backoff delay increases exponentially."""
        call_times = []

        def track_calls() -> str:
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Fail")
            return "success"

        decorated = retried(
            max_attempts=5,
            base_delay_s=0.05,
            max_delay_s=1.0,
            jitter=False,
        )(track_calls)

        start = time.time()
        result = decorated()
        total_time = time.time() - start

        assert result == "success"
        assert len(call_times) == 3
        assert total_time >= 0.1

    def test_jitter_varies_delays(self) -> None:
        """Jitter causes varying delays across attempts."""
        call_count = 0

        def track_calls() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 10:
                raise ValueError("Fail")
            return "success"

        decorated = retried(
            max_attempts=12,
            base_delay_s=0.05,
            max_delay_s=0.5,
            jitter=True,
        )(track_calls)

        result = decorated()
        assert result == "success"
        assert call_count == 10

    def test_max_delay_s_caps_backoff(self) -> None:
        """max_delay_s parameter caps exponential delay growth."""
        call_count = 0
        start_time = time.time()

        def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Fail")
            return "success"

        decorated = retried(
            max_attempts=6,
            base_delay_s=1.0,
            max_delay_s=0.5,
            jitter=False,
        )(eventually_succeeds)

        result = decorated()
        elapsed = time.time() - start_time

        assert result == "success"
        assert elapsed < 5.0

    def test_max_attempts_validation(self) -> None:
        """max_attempts must be >= 1."""
        with pytest.raises(ValueError, match="positive integer"):
            retried(max_attempts=0)(lambda: None)

        with pytest.raises(ValueError, match="positive integer"):
            retried(max_attempts=-1)(lambda: None)

    def test_retry_on_validation(self) -> None:
        """retry_on must be callable if provided."""
        with pytest.raises(ValueError, match="callable"):
            retried(retry_on="not callable")(lambda: None)  # type: ignore[arg-type]

    def test_invalid_target_type(self) -> None:
        """@retried on invalid target raises TypeError."""
        client = RetryClient(
            max_attempts=3,
            base_delay_s=1.0,
            max_delay_s=60.0,
            jitter=True,
        )

        with pytest.raises(TypeError):
            client("not a class or callable")

    def test_static_method_decoration(self) -> None:
        """Decorate a static method within a class."""

        @retried(max_attempts=3)
        class MyService:
            """Service with static method."""

            @staticmethod
            def static_method() -> str:
                """Static method."""
                return "static"

        assert MyService.static_method() == "static"

    def test_static_method_with_retry(self) -> None:
        """Static method can retry on exception."""
        counter = {"count": 0}

        @retried(max_attempts=5)
        class MyService:
            """Service with failing static method."""

            @staticmethod
            def failing_static() -> str:
                """Static method that fails then succeeds."""
                counter["count"] += 1
                if counter["count"] < 3:
                    raise ValueError("Fail")
                return "static success"

        assert MyService.failing_static() == "static success"
        assert counter["count"] == 3

    def test_class_method_decoration(self) -> None:
        """Decorate a class method within a class."""

        @retried(max_attempts=3)
        class MyService:
            """Service with class method."""

            @classmethod
            def class_method(cls) -> str:
                """Class method."""
                return "class"

        assert MyService.class_method() == "class"

    def test_class_method_with_retry(self) -> None:
        """Class method can retry on exception."""
        counter = {"count": 0}

        @retried(max_attempts=5)
        class MyService:
            """Service with failing class method."""

            @classmethod
            def failing_class_method(cls) -> str:
                """Class method that fails then succeeds."""
                counter["count"] += 1
                if counter["count"] < 3:
                    raise ValueError("Fail")
                return "class success"

        assert MyService.failing_class_method() == "class success"

    def test_property_skipped(self) -> None:
        """Properties are skipped during class decoration."""

        @retried(max_attempts=3)
        class MyService:
            """Service with property."""

            @property
            def my_property(self) -> str:
                """A property."""
                return "property"

        service = MyService()
        assert service.my_property == "property"

    def test_nested_class_skipped(self) -> None:
        """Nested classes are skipped during class decoration."""

        @retried(max_attempts=3)
        class OuterService:
            """Outer service with nested class."""

            class NestedClass:
                """Nested class."""

                def method(self) -> str:
                    """Nested method."""
                    return "nested"

            def public_method(self) -> str:
                """Public method."""
                return "public"

        service = OuterService()
        assert service.public_method() == "public"
        nested = service.NestedClass()
        assert nested.method() == "nested"

    def test_marker_attribute_not_set_on_undecorated(self) -> None:
        """Undecorated function does not have marker attribute."""

        def plain_function() -> str:
            return "plain"

        assert not hasattr(plain_function, const.ATTRIBUTE_MARKER)


class TestRetriedAsync:
    """Test @retried decorator on async functions and methods."""

    @pytest.mark.asyncio
    async def test_async_function_success(self) -> None:
        """Decorate an async function and call it successfully."""

        async def async_func() -> str:
            """Async function."""
            return "async result"

        decorated = retried(max_attempts=3)(async_func)
        result = await decorated()
        assert result == "async result"

    @pytest.mark.asyncio
    async def test_async_function_retry_on_exception(self) -> None:
        """Async function retries on exception."""
        call_count = 0

        async def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Async failure")
            return "async success"

        decorated = retried(max_attempts=5)(eventually_succeeds)
        result = await decorated()
        assert result == "async success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_exhausts_retries(self) -> None:
        """Async function exceeding max_attempts raises final exception."""

        async def always_fails() -> None:
            raise ValueError("Always fails")

        decorated = retried(max_attempts=2)(always_fails)

        with pytest.raises(ValueError, match="Always fails"):
            await decorated()

    @pytest.mark.asyncio
    async def test_async_method_decoration(self, service) -> None:
        """Decorate an async method and call it."""
        decorated = retried(max_attempts=3)(service.async_success)
        result = await decorated()
        assert result == "async success"

    @pytest.mark.asyncio
    async def test_async_method_retry(
        self, service, call_counter
    ) -> None:
        """Async method retries and eventually succeeds."""
        decorated = retried(max_attempts=5)(
            call_counter.async_eventually_succeeds
        )
        result = await decorated(fail_until=2)
        assert "async success" in result
        assert call_counter.count == 3

    @pytest.mark.asyncio
    async def test_async_cancelled_error_never_retries(self) -> None:
        """asyncio.CancelledError is never retried."""

        async def raises_cancelled() -> None:
            raise asyncio.CancelledError()

        decorated = retried(max_attempts=10)(raises_cancelled)

        with pytest.raises(asyncio.CancelledError):
            await decorated()

    @pytest.mark.asyncio
    async def test_async_exponential_backoff(self) -> None:
        """Async backoff delay increases exponentially."""
        call_count = 0

        async def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Fail")
            return "success"

        start = time.time()
        decorated = retried(
            max_attempts=5,
            base_delay_s=0.05,
            max_delay_s=1.0,
            jitter=False,
        )(eventually_succeeds)

        result = await decorated()
        total_time = time.time() - start

        assert result == "success"
        assert call_count == 3
        assert total_time >= 0.1

    @pytest.mark.asyncio
    async def test_async_class_decoration(self) -> None:
        """Apply @retried to a class with async methods."""

        @retried(max_attempts=3)
        class AsyncService:
            """Service with async methods."""

            def __init__(self) -> None:
                """Initialize."""
                self.count = 0

            async def public_method(self) -> str:
                """Async method."""
                return "async public"

            async def eventually_succeeds(self) -> str:
                """Async method that fails then succeeds."""
                self.count += 1
                if self.count < 2:
                    raise ValueError("Async fail")
                return "async success"

        service = AsyncService()
        assert await service.public_method() == "async public"
        assert await service.eventually_succeeds() == "async success"

    @pytest.mark.asyncio
    async def test_async_function_negative_control(self) -> None:
        """Undecorated async function fails on first attempt."""

        call_count = 0

        async def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Fail")
            return "success"

        with pytest.raises(ValueError):
            await eventually_succeeds()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_has_marker_attribute(self) -> None:
        """Decorated async function has marker attribute."""

        async def async_func() -> str:
            return "result"

        decorated = retried()(async_func)
        assert hasattr(decorated, const.ATTRIBUTE_MARKER)
        assert getattr(decorated, const.ATTRIBUTE_MARKER) is True

    @pytest.mark.asyncio
    async def test_async_max_delay_s_caps_backoff(self) -> None:
        """Async max_delay_s parameter caps exponential delay."""
        call_count = 0

        async def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Fail")
            return "success"

        decorated = retried(
            max_attempts=6,
            base_delay_s=1.0,
            max_delay_s=0.5,
            jitter=False,
        )(eventually_succeeds)

        start = time.time()
        result = await decorated()
        elapsed = time.time() - start

        assert result == "success"
        assert elapsed < 5.0
