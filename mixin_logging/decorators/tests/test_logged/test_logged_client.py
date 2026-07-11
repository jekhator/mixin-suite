"""Tests for @logged decorator + LoggedClient."""

from __future__ import annotations

import pytest

from mixin_logging import (
    LoggedClient,
    LoggingMixin,
    logged,
)
from mixin_logging.common.constants import tests as test_const


class CustomError(Exception):
    """Custom exception with a code attribute for testing."""

    code = test_const.ERROR_CODE_CUSTOM


class TestLoggedDecorator:
    """Tests for @logged class-based decorator on LoggingMixin methods."""

    def test_logged_emits_start_event(self, log_capture_factory) -> None:
        """@logged emits <event>.start before method execution."""

        class Svc(LoggingMixin):
            """Test service instance for @logged decorator testing."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def do_work(self) -> None:
                pass

        svc = Svc()
        collector = log_capture_factory(svc)
        svc.do_work()

        assert len(collector.records) >= 1
        assert any(
            rec.getMessage() == test_const.EVENT_PROCESS_START
            for rec in collector.records
        )

    def test_logged_emits_error_event_on_exception(
        self,
        log_capture_factory,
    ) -> None:
        """@logged emits <event>.error with error_type and code fields."""

        class Svc(LoggingMixin):
            """Test service instance for @logged decorator testing."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def do_work(self) -> None:
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise CustomError(msg)

        svc = Svc()
        collector = log_capture_factory(svc)

        with pytest.raises(CustomError):
            svc.do_work()

        error_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_ERROR
        ]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "CustomError"
        assert error_records[0].__dict__["code"] == test_const.ERROR_CODE_CUSTOM

    def test_logged_reraises_exception_unchanged(
        self,
        log_capture_factory,
    ) -> None:
        """@logged re-raises the exception unchanged."""

        class Svc(LoggingMixin):
            """Test service instance for @logged decorator testing."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def do_work(self) -> None:
                msg = test_const.RAISE_MATCH_TEST_ERROR
                raise ValueError(msg)

        svc = Svc()
        log_capture_factory(svc)

        with pytest.raises(
            ValueError,
            match=test_const.RAISE_MATCH_TEST_ERROR,
        ):
            svc.do_work()

    def test_logged_preserves_method_signature(self) -> None:
        """@logged preserves the wrapped method's signature."""

        class Svc(LoggingMixin):
            """Test service instance for @logged decorator testing."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def do_work(self, arg: int, value: str) -> str:
                return f"{arg}-{value}"

        svc = Svc()
        method = svc.do_work
        assert hasattr(method, "__wrapped__")

    def test_logged_with_positional_and_keyword_args(self, log_capture_factory) -> None:
        """@logged preserves both *args and **kwargs."""

        class Svc(LoggingMixin):
            """Test service instance for @logged decorator testing."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def do_work(
                self,
                arg: int,
                *args: int,
                value: str = "default",
                **kwargs: str,
            ) -> tuple[int, tuple[int, ...], str, dict[str, str]]:
                return (arg, args, value, kwargs)

        svc = Svc()
        collector = log_capture_factory(svc)

        result = svc.do_work(1, 2, 3, value="custom", extra="value")

        assert result == (1, (2, 3), "custom", {"extra": "value"})
        assert len(collector.records) >= 1
        assert any(
            rec.getMessage() == test_const.EVENT_PROCESS_START
            for rec in collector.records
        )

    def test_logged_with_return_value(self, log_capture_factory) -> None:
        """@logged returns the original method's return value unchanged."""

        class Svc(LoggingMixin):
            """Test service instance for return value preservation testing."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def do_work(self, value: int) -> int:
                return value * 2

        svc = Svc()
        log_capture_factory(svc)

        result = svc.do_work(21)

        assert result == 42

    def test_logged_with_exception_without_code_attribute(
        self,
        log_capture_factory,
    ) -> None:
        """@logged handles exceptions without code attribute."""

        class Svc(LoggingMixin):
            """Test service instance for exception handling without code attribute."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def do_work(self) -> None:
                msg = test_const.ERROR_MSG_RUNTIME_NO_CODE
                raise RuntimeError(msg)

        svc = Svc()
        collector = log_capture_factory(svc)

        with pytest.raises(RuntimeError):
            svc.do_work()

        error_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_ERROR
        ]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "RuntimeError"
        assert error_records[0].__dict__["code"] is None

    def test_logged_async_instance_method_emits_events(
        self,
        log_capture_factory,
    ) -> None:
        """@logged on async instance method emits start/error events."""
        import asyncio

        class Svc(LoggingMixin):
            """Test service instance for async @logged decorator testing."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            async def do_work_async(self) -> str:
                await asyncio.sleep(0)
                return "done"

        svc = Svc()
        collector = log_capture_factory(svc)
        result = asyncio.run(svc.do_work_async())

        assert result == "done"
        assert len(collector.records) >= 1
        assert any(
            rec.getMessage() == test_const.EVENT_PROCESS_START
            for rec in collector.records
        )

    def test_logged_async_instance_method_emits_error_event(
        self,
        log_capture_factory,
    ) -> None:
        """@logged on async instance method emits error event on exception."""
        import asyncio

        class Svc(LoggingMixin):
            """Test service instance for async @logged exception handling."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            async def do_work_async(self) -> None:
                await asyncio.sleep(0)
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise ValueError(msg)

        svc = Svc()
        collector = log_capture_factory(svc)

        with pytest.raises(ValueError):
            asyncio.run(svc.do_work_async())

        error_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_ERROR
        ]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "ValueError"


class TestLoggedClient:
    """Tests for LoggedClient: decorator factory and invocation."""

    def test_logged_client_for_event_factory(self) -> None:
        """Create LoggedClient via for_event factory."""
        client = LoggedClient.for_event(test_const.EVENT_VALIDATE)
        assert client.container.event == test_const.EVENT_VALIDATE

    def test_logged_client_for_event_container_properties(
        self,
    ) -> None:
        """LoggedClient container has correct start/error properties."""
        client = LoggedClient.for_event(test_const.EVENT_VALIDATE)
        assert client.container.start == test_const.EVENT_VALIDATE_START
        assert client.container.error == test_const.EVENT_VALIDATE_ERROR


class TestLoggedClassLevel:
    """Tests for @logged class-level decoration (fan-out to public methods)."""

    def test_logged_class_level_fans_out_to_public_methods(
        self,
        log_capture_factory,
    ) -> None:
        """@logged on class wraps all public methods."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with multiple public methods."""

            __slots__ = ()

            def do_work(self) -> str:
                return "work"

            def process_data(self) -> int:
                return 42

        svc = Svc()
        collector = log_capture_factory(svc)

        result1 = svc.do_work()
        assert result1 == "work"

        result2 = svc.process_data()
        assert result2 == 42

        assert len(collector.records) >= 2

    def test_logged_class_level_method_event_derivation(
        self,
        log_capture_factory,
    ) -> None:
        """Method event = f'{root}.{method_name}' for class-level decoration."""

        @logged(event=test_const.EVENT_AUDIT)
        class Svc(LoggingMixin):
            """Test service for event derivation."""

            __slots__ = ()

            def check_access(self) -> None:
                pass

        svc = Svc()
        collector = log_capture_factory(svc)
        svc.check_access()

        expected_start = f"{test_const.EVENT_AUDIT}.check_access.start"
        assert any(rec.getMessage() == expected_start for rec in collector.records)

    def test_logged_class_level_skips_private_methods(
        self,
        log_capture_factory,
    ) -> None:
        """@logged skips private methods (_*)."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with private and public methods."""

            __slots__ = ()

            def public_method(self) -> str:
                return self._private_method()

            def _private_method(self) -> str:
                return "private"

        svc = Svc()
        collector = log_capture_factory(svc)
        svc.public_method()

        private_logs = [
            rec for rec in collector.records if "_private_method" in rec.getMessage()
        ]
        assert len(private_logs) == 0

    def test_logged_class_level_skips_dunder_methods(
        self,
        log_capture_factory,
    ) -> None:
        """@logged skips dunder methods."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with dunder methods."""

            __slots__ = ()

            def __init__(self) -> None:
                super().__init__()

            def public_work(self) -> None:
                pass

        svc = Svc()
        collector = log_capture_factory(svc)
        svc.public_work()

        dunder_logs = [
            rec for rec in collector.records if "__init__" in rec.getMessage()
        ]
        assert len(dunder_logs) == 0

    def test_logged_class_level_skips_properties(
        self,
        log_capture_factory,
    ) -> None:
        """@logged skips property descriptors."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with property."""

            __slots__ = ()

            @property
            def computed_value(self) -> int:
                return 99

            def get_data(self) -> str:
                return "data"

        svc = Svc()
        collector = log_capture_factory(svc)

        assert svc.computed_value == 99
        svc.get_data()

        computed_logs = [
            rec for rec in collector.records if "computed_value" in rec.getMessage()
        ]
        assert len(computed_logs) == 0

    def test_logged_class_level_skips_nested_classes(
        self,
        log_capture_factory,
    ) -> None:
        """@logged skips nested class definitions."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with nested class."""

            __slots__ = ()

            class NestedClass:
                pass

            def do_work(self) -> None:
                pass

        svc = Svc()
        collector = log_capture_factory(svc)
        svc.do_work()

        nested_logs = [
            rec for rec in collector.records if "NestedClass" in rec.getMessage()
        ]
        assert len(nested_logs) == 0

    def test_logged_class_level_with_explicit_method_decorator(
        self,
        log_capture_factory,
    ) -> None:
        """Explicit method-level @logged overrides class-level fan-out."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with explicit method decorator."""

            __slots__ = ()

            @logged(event=test_const.EVENT_VALIDATE)
            def explicit_method(self) -> str:
                return "explicit"

            def implicit_method(self) -> str:
                return "implicit"

        svc = Svc()
        collector = log_capture_factory(svc)

        svc.explicit_method()
        svc.implicit_method()

        explicit_logs = [
            rec
            for rec in collector.records
            if test_const.EVENT_VALIDATE in rec.getMessage()
        ]
        implicit_logs = [
            rec
            for rec in collector.records
            if "process.implicit_method" in rec.getMessage()
        ]

        assert len(explicit_logs) > 0
        assert len(implicit_logs) > 0

    def test_logged_class_level_wraps_classmethod(
        self,
        log_capture_factory,
    ) -> None:
        """@logged on class wraps classmethods (preserves descriptor type, still callable)."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with classmethod."""

            __slots__ = ()

            @classmethod
            def create(cls) -> Svc:
                return cls()

            def instance_method(self) -> str:
                return "instance"

        svc_instance = Svc()
        log_capture_factory(svc_instance)
        result = Svc.create()

        assert isinstance(result, Svc)
        assert isinstance(Svc.__dict__["create"], classmethod)

    def test_logged_class_level_wraps_staticmethod(
        self,
        log_capture_factory,
    ) -> None:
        """@logged on class wraps staticmethods (preserves descriptor type, still callable)."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with staticmethod."""

            __slots__ = ()

            @staticmethod
            def helper() -> str:
                return "help"

            def instance_method(self) -> str:
                return "instance"

        svc = Svc()
        log_capture_factory(svc)
        result = svc.helper()

        assert result == "help"
        assert isinstance(Svc.__dict__["helper"], staticmethod)

    def test_logged_class_level_skips_inherited_methods(
        self,
        log_capture_factory,
    ) -> None:
        """@logged does not wrap inherited methods."""

        class BaseSvc(LoggingMixin):
            """Base service with a method."""

            __slots__ = ()

            def inherited_method(self) -> str:
                return "inherited"

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(BaseSvc):
            """Child service decorated at class level."""

            __slots__ = ()

            def own_method(self) -> str:
                return "own"

        svc = Svc()
        collector = log_capture_factory(svc)

        svc.inherited_method()
        svc.own_method()

        inherited_logs = [
            rec
            for rec in collector.records
            if "process.inherited_method" in rec.getMessage()
        ]
        own_logs = [
            rec for rec in collector.records if "process.own_method" in rec.getMessage()
        ]

        assert len(inherited_logs) == 0
        assert len(own_logs) > 0

    def test_logged_class_level_with_error_handling(
        self,
        log_capture_factory,
    ) -> None:
        """@logged on class emits error events for all wrapped methods."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service that raises errors."""

            __slots__ = ()

            def failing_work(self) -> None:
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise ValueError(msg)

        svc = Svc()
        collector = log_capture_factory(svc)

        with pytest.raises(ValueError):
            svc.failing_work()

        error_logs = [
            rec
            for rec in collector.records
            if "process.failing_work.error" in rec.getMessage()
        ]
        assert len(error_logs) == 1

    def test_logged_class_level_on_frozen_dataclass(
        self,
        log_capture_factory,
    ) -> None:
        """@logged works on frozen slots dataclass with LoggingMixin."""
        from dataclasses import dataclass

        @logged(event=test_const.EVENT_PROCESS)
        @dataclass(frozen=True, slots=True)
        class Svc(LoggingMixin):
            """Test service as frozen dataclass."""

            value: int = 0

            def compute(self) -> int:
                return self.value * 2

        svc = Svc(value=5)
        collector = log_capture_factory(svc)
        result = svc.compute()

        assert result == 10
        assert any(
            "process.compute.start" in rec.getMessage() for rec in collector.records
        )

    def test_logged_class_level_rejects_non_class_non_callable(self) -> None:
        """@logged raises TypeError for non-class non-callable target."""
        from mixin_logging.decorators.constants import decorators as const

        decorator = logged(event=test_const.EVENT_PROCESS)
        not_a_callable = 42

        with pytest.raises(
            TypeError,
            match=const.ERROR_MSG_TARGET_NOT_CLASS_OR_CALLABLE,
        ):
            decorator(not_a_callable)

    def test_logged_class_level_classmethod_emits_events(self) -> None:
        """@logged on class emits start/error events for classmethods."""
        import logging
        import logging.handlers

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with classmethod."""

            __slots__ = ()

            @classmethod
            def create(cls) -> Svc:
                return cls()

        collector = logging.handlers.MemoryHandler(1000)
        logger = logging.getLogger(Svc.__module__).getChild(Svc.__name__)
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)

        result = Svc.create()

        assert isinstance(result, Svc)
        assert len(collector.buffer) >= 1
        messages = [rec.getMessage() for rec in collector.buffer]
        assert any("process.create.start" in msg for msg in messages), (
            f"Expected start event in {messages}"
        )

    def test_logged_class_level_staticmethod_emits_events(self) -> None:
        """@logged on class emits start/error events for staticmethods."""
        import logging
        import logging.handlers

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with staticmethod."""

            __slots__ = ()

            @staticmethod
            def helper() -> str:
                return "help"

        collector = logging.handlers.MemoryHandler(1000)
        logger = logging.getLogger(Svc.__module__).getChild(Svc.__name__)
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)

        result = Svc.helper()

        assert result == "help"
        assert len(collector.buffer) >= 1
        messages = [rec.getMessage() for rec in collector.buffer]
        assert any("process.helper.start" in msg for msg in messages), (
            f"Expected start event in {messages}"
        )

    def test_logged_class_level_classmethod_error_event(self) -> None:
        """@logged on class emits error event when classmethod raises."""
        import logging
        import logging.handlers

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with failing classmethod."""

            __slots__ = ()

            @classmethod
            def create_failing(cls) -> Svc:
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise ValueError(msg)

        collector = logging.handlers.MemoryHandler(1000)
        logger = logging.getLogger(Svc.__module__).getChild(Svc.__name__)
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)

        with pytest.raises(ValueError):
            Svc.create_failing()

        error_records = [
            rec
            for rec in collector.buffer
            if "process.create_failing.error" in rec.getMessage()
        ]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "ValueError"

    def test_logged_class_level_staticmethod_error_event(self) -> None:
        """@logged on class emits error event when staticmethod raises."""
        import logging
        import logging.handlers

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with failing staticmethod."""

            __slots__ = ()

            @staticmethod
            def helper_failing() -> str:
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise RuntimeError(msg)

        collector = logging.handlers.MemoryHandler(1000)
        logger = logging.getLogger(Svc.__module__).getChild(Svc.__name__)
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)

        with pytest.raises(RuntimeError):
            Svc.helper_failing()

        error_records = [
            rec
            for rec in collector.buffer
            if "process.helper_failing.error" in rec.getMessage()
        ]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "RuntimeError"

    def test_logged_class_level_async_classmethod_emits_events(self) -> None:
        """@logged on class emits events for async classmethods."""
        import asyncio
        import logging
        import logging.handlers

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with async classmethod."""

            __slots__ = ()

            @classmethod
            async def create_async(cls) -> Svc:
                await asyncio.sleep(0)
                return cls()

        collector = logging.handlers.MemoryHandler(1000)
        logger = logging.getLogger(Svc.__module__).getChild(Svc.__name__)
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)

        result = asyncio.run(Svc.create_async())

        assert isinstance(result, Svc)
        assert len(collector.buffer) >= 1
        messages = [rec.getMessage() for rec in collector.buffer]
        assert any("process.create_async.start" in msg for msg in messages), (
            f"Expected start event in {messages}"
        )

    def test_logged_class_level_async_staticmethod_emits_events(self) -> None:
        """@logged on class emits events for async staticmethods."""
        import asyncio
        import logging
        import logging.handlers

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with async staticmethod."""

            __slots__ = ()

            @staticmethod
            async def helper_async() -> str:
                await asyncio.sleep(0)
                return "help"

        collector = logging.handlers.MemoryHandler(1000)
        logger = logging.getLogger(Svc.__module__).getChild(Svc.__name__)
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)

        result = asyncio.run(Svc.helper_async())

        assert result == "help"
        assert len(collector.buffer) >= 1
        messages = [rec.getMessage() for rec in collector.buffer]
        assert any("process.helper_async.start" in msg for msg in messages), (
            f"Expected start event in {messages}"
        )
