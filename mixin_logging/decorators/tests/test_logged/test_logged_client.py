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
        """LoggedClient container has correct start/end/error properties."""
        client = LoggedClient.for_event(test_const.EVENT_VALIDATE)
        assert client.container.start == test_const.EVENT_VALIDATE_START
        assert client.container.end == test_const.EVENT_VALIDATE_END
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

    def test_logged_class_level_async_classmethod_error_event(self) -> None:
        """@logged on class emits error event when async classmethod raises."""
        import asyncio
        import logging
        import logging.handlers

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with failing async classmethod."""

            __slots__ = ()

            @classmethod
            async def create_async_failing(cls) -> Svc:
                await asyncio.sleep(0)
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise ValueError(msg)

        collector = logging.handlers.MemoryHandler(1000)
        logger = logging.getLogger(Svc.__module__).getChild(Svc.__name__)
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)

        with pytest.raises(ValueError):
            asyncio.run(Svc.create_async_failing())

        error_records = [
            rec
            for rec in collector.buffer
            if "process.create_async_failing.error" in rec.getMessage()
        ]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "ValueError"

    def test_logged_class_level_async_staticmethod_error_event(self) -> None:
        """@logged on class emits error event when async staticmethod raises."""
        import asyncio
        import logging
        import logging.handlers

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with failing async staticmethod."""

            __slots__ = ()

            @staticmethod
            async def helper_async_failing() -> str:
                await asyncio.sleep(0)
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise RuntimeError(msg)

        collector = logging.handlers.MemoryHandler(1000)
        logger = logging.getLogger(Svc.__module__).getChild(Svc.__name__)
        logger.addHandler(collector)
        logger.setLevel(logging.DEBUG)

        with pytest.raises(RuntimeError):
            asyncio.run(Svc.helper_async_failing())

        error_records = [
            rec
            for rec in collector.buffer
            if "process.helper_async_failing.error" in rec.getMessage()
        ]
        assert len(error_records) == 1


class TestLoggedPayloadCallback:
    """Tests for @logged payload_from_result callback feature."""

    def test_logged_emits_end_event_when_payload_callback_provided(
        self,
        log_capture_factory,
    ) -> None:
        """@logged emits <event>.end with payload fields when callback provided."""

        def extract_payload(result: int) -> dict[str, object]:
            return {"result_value": result}

        class Svc(LoggingMixin):
            """Test service with payload callback."""

            __slots__ = ()

            @logged(test_const.EVENT_PROCESS, payload_from_result=extract_payload)
            def compute(self, x: int) -> int:
                return x * 2

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.compute(21)

        assert result == 42
        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 1
        assert end_records[0].__dict__["result_value"] == 42

    def test_logged_no_end_event_when_payload_callback_absent(
        self,
        log_capture_factory,
    ) -> None:
        """@logged emits NO .end event when payload_from_result is None."""

        class Svc(LoggingMixin):
            """Test service without payload callback."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def compute(self, x: int) -> int:
                return x * 2

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.compute(21)

        assert result == 42
        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 0

    def test_logged_error_event_unchanged_with_payload_callback(
        self,
        log_capture_factory,
    ) -> None:
        """@logged error event behavior unchanged when payload callback provided."""

        def extract_payload(result: int) -> dict[str, object]:
            return {"result": result}

        class Svc(LoggingMixin):
            """Test service with payload callback on failing method."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_result=extract_payload,
            )
            def compute(self) -> int:
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise CustomError(msg)

        svc = Svc()
        collector = log_capture_factory(svc)

        with pytest.raises(CustomError):
            svc.compute()

        error_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_ERROR
        ]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "CustomError"

        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 0

    def test_logged_async_emits_end_event_with_payload_callback(
        self,
        log_capture_factory,
    ) -> None:
        """@logged on async method emits .end event with payload when callback provided."""
        import asyncio

        def extract_payload(result: str) -> dict[str, object]:
            return {"result_length": len(result)}

        class Svc(LoggingMixin):
            """Test service with async method and payload callback."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_result=extract_payload,
            )
            async def compute_async(self) -> str:
                await asyncio.sleep(0)
                return "completed"

        svc = Svc()
        collector = log_capture_factory(svc)
        result = asyncio.run(svc.compute_async())

        assert result == "completed"
        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 1
        assert end_records[0].__dict__["result_length"] == 9

    def test_logged_payload_callback_receives_correct_result(
        self,
        log_capture_factory,
    ) -> None:
        """Payload callback receives the actual result value."""

        captured_results: list[object] = []

        def capture_payload(result: dict[str, int]) -> dict[str, object]:
            captured_results.append(result)
            return {"status": "ok"}

        class Svc(LoggingMixin):
            """Test service with capturing payload callback."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_result=capture_payload,
            )
            def return_dict(self, key: str, value: int) -> dict[str, int]:
                return {key: value}

        svc = Svc()
        log_capture_factory(svc)
        svc.return_dict("test", 123)

        assert len(captured_results) == 1
        assert captured_results[0] == {"test": 123}


class TestLoggedPayloadFromRequest:
    """Tests for @logged payload_from_request extraction feature."""

    def test_logged_payload_from_request_sync_instance_method(
        self,
        log_capture_factory,
    ) -> None:
        """@logged extracts fields from sync instance method request into .start event."""

        def extract_request(user_id: str) -> dict[str, object]:
            return {"user_id": user_id}

        class Svc(LoggingMixin):
            """Test service with payload_from_request on sync method."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_request=extract_request,
            )
            def process_user(self, user_id: str) -> str:
                return f"processed-{user_id}"

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.process_user("user-42")

        assert result == "processed-user-42"
        start_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_START
        ]
        assert len(start_records) == 1
        assert start_records[0].__dict__["user_id"] == "user-42"

    def test_logged_payload_from_request_async_instance_method(
        self,
        log_capture_factory,
    ) -> None:
        """@logged extracts fields from async instance method request into .start event."""
        import asyncio

        def extract_request(request_id: str) -> dict[str, object]:
            return {"request_id": request_id}

        class Svc(LoggingMixin):
            """Test service with payload_from_request on async method."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_request=extract_request,
            )
            async def process_async(self, request_id: str) -> str:
                await asyncio.sleep(0)
                return f"done-{request_id}"

        svc = Svc()
        collector = log_capture_factory(svc)
        result = asyncio.run(svc.process_async("req-123"))

        assert result == "done-req-123"
        start_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_START
        ]
        assert len(start_records) == 1
        assert start_records[0].__dict__["request_id"] == "req-123"

    def test_logged_payload_from_request_class_level_decoration(
        self,
        log_capture_factory,
    ) -> None:
        """@logged at class level inherits payload_from_request to public methods."""
        import asyncio

        def extract_request(action: str) -> dict[str, object]:
            return {"action": action}

        @logged(
            test_const.EVENT_PROCESS,
            payload_from_request=extract_request,
        )
        class Svc(LoggingMixin):
            """Test service with class-level payload_from_request."""

            __slots__ = ()

            def sync_method(self, action: str) -> str:
                return f"sync-{action}"

            async def async_method(self, action: str) -> str:
                await asyncio.sleep(0)
                return f"async-{action}"

        svc = Svc()
        collector = log_capture_factory(svc)

        result1 = svc.sync_method("create")
        assert result1 == "sync-create"

        result2 = asyncio.run(svc.async_method("delete"))
        assert result2 == "async-delete"

        start_records = [
            rec
            for rec in collector.records
            if rec.getMessage() in (
                f"{test_const.EVENT_PROCESS}.sync_method.start",
                f"{test_const.EVENT_PROCESS}.async_method.start",
            )
        ]
        assert len(start_records) == 2
        assert any(rec.__dict__["action"] == "create" for rec in start_records)
        assert any(rec.__dict__["action"] == "delete" for rec in start_records)

    def test_logged_payload_from_request_extractor_raises_exception(
        self,
        log_capture_factory,
    ) -> None:
        """@logged proceeds when payload_from_request raises; logs WARNING."""

        def bad_extractor(user_id: str) -> dict[str, object]:
            msg = "extraction failed"
            raise ValueError(msg)

        class Svc(LoggingMixin):
            """Test service with failing payload_from_request extractor."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_request=bad_extractor,
            )
            def process(self, user_id: str) -> str:
                return f"ok-{user_id}"

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.process("user-123")

        assert result == "ok-user-123"
        start_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_START
        ]
        assert len(start_records) == 1
        warning_records = [
            rec
            for rec in collector.records
            if rec.levelname == "WARNING" and "extraction.failure" in rec.getMessage()
        ]
        assert len(warning_records) == 1

    def test_logged_payload_from_request_extractor_returns_non_dict(
        self,
        log_capture_factory,
    ) -> None:
        """@logged handles non-dict return from payload_from_request; logs WARNING."""

        def bad_extractor(value: str) -> object:
            return f"string-{value}"

        class Svc(LoggingMixin):
            """Test service with non-dict payload_from_request return."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_request=bad_extractor,
            )
            def process(self, value: str) -> str:
                return f"result-{value}"

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.process("test")

        assert result == "result-test"
        warning_records = [
            rec
            for rec in collector.records
            if rec.levelname == "WARNING"
        ]
        assert len(warning_records) >= 1

    def test_logged_payload_from_request_none_default(
        self,
        log_capture_factory,
    ) -> None:
        """@logged with payload_from_request=None (default) skips extraction."""

        class Svc(LoggingMixin):
            """Test service without payload_from_request."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def process(self, user_id: str) -> str:
                return f"ok-{user_id}"

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.process("user-99")

        assert result == "ok-user-99"
        start_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_START
        ]
        assert len(start_records) == 1
        assert "user_id" not in start_records[0].__dict__


class TestLoggedTimed:
    """Tests for @logged timed feature (latency_ms tracking)."""

    def test_logged_timed_adds_latency_to_end_event(
        self,
        log_capture_factory,
    ) -> None:
        """@logged with timed=True adds latency_ms to .end event."""
        import time

        def extract_payload(result: int) -> dict[str, object]:
            return {"result": result}

        class Svc(LoggingMixin):
            """Test service with timed=True."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_result=extract_payload,
                timed=True,
            )
            def slow_compute(self) -> int:
                time.sleep(0.01)
                return 42

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.slow_compute()

        assert result == 42
        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 1
        assert "latency_ms" in end_records[0].__dict__
        latency = end_records[0].__dict__["latency_ms"]
        assert isinstance(latency, float)
        assert latency > 0

    def test_logged_timed_adds_latency_to_error_event(
        self,
        log_capture_factory,
    ) -> None:
        """@logged with timed=True adds latency_ms to .error event."""
        import time

        class Svc(LoggingMixin):
            """Test service with timed=True on failing method."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                timed=True,
            )
            def failing_compute(self) -> None:
                time.sleep(0.01)
                msg = test_const.ERROR_MSG_CUSTOM_WORK_FAILED
                raise ValueError(msg)

        svc = Svc()
        collector = log_capture_factory(svc)

        with pytest.raises(ValueError):
            svc.failing_compute()

        error_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_ERROR
        ]
        assert len(error_records) == 1
        assert "latency_ms" in error_records[0].__dict__
        latency = error_records[0].__dict__["latency_ms"]
        assert isinstance(latency, float)
        assert latency > 0

    def test_logged_timed_false_default(
        self,
        log_capture_factory,
    ) -> None:
        """@logged with timed=False (default) omits latency_ms from events."""

        def extract_payload(result: int) -> dict[str, object]:
            return {"result": result}

        class Svc(LoggingMixin):
            """Test service without timed."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_result=extract_payload,
            )
            def compute(self) -> int:
                return 99

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.compute()

        assert result == 99
        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 1
        assert "latency_ms" not in end_records[0].__dict__

    def test_logged_timed_async_method(
        self,
        log_capture_factory,
    ) -> None:
        """@logged with timed=True on async method includes latency_ms."""
        import asyncio

        def extract_payload(result: str) -> dict[str, object]:
            return {"length": len(result)}

        class Svc(LoggingMixin):
            """Test service with timed=True on async method."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_result=extract_payload,
                timed=True,
            )
            async def async_compute(self) -> str:
                await asyncio.sleep(0.01)
                return "result"

        svc = Svc()
        collector = log_capture_factory(svc)
        result = asyncio.run(svc.async_compute())

        assert result == "result"
        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 1
        assert "latency_ms" in end_records[0].__dict__
        latency = end_records[0].__dict__["latency_ms"]
        assert isinstance(latency, float)
        assert latency > 0


class TestLoggedCombinedEnrichment:
    """Tests for combined payload_from_request + timed + payload_from_result."""

    def test_logged_combined_all_enrichment_features(
        self,
        log_capture_factory,
    ) -> None:
        """@logged with all three enrichment features emits complete event data."""
        import time

        def extract_request(user_id: str) -> dict[str, object]:
            return {"user_id": user_id}

        def extract_result(result: dict[str, int]) -> dict[str, object]:
            return {"result_sum": result["sum"]}

        class Svc(LoggingMixin):
            """Test service with all enrichment features."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_request=extract_request,
                payload_from_result=extract_result,
                timed=True,
            )
            def compute_with_user(self, user_id: str) -> dict[str, int]:
                time.sleep(0.005)
                return {"sum": 100}

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.compute_with_user("user-77")

        assert result == {"sum": 100}

        start_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_START
        ]
        assert len(start_records) == 1
        assert start_records[0].__dict__["user_id"] == "user-77"

        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 1
        assert end_records[0].__dict__["result_sum"] == 100
        assert "latency_ms" in end_records[0].__dict__


class TestLoggedBackwardCompatibility:
    """Tests for backward compatibility with existing @logged behavior."""

    def test_logged_existing_no_new_params_still_works(
        self,
        log_capture_factory,
    ) -> None:
        """Existing @logged usage without new params works unchanged."""

        class Svc(LoggingMixin):
            """Test service with traditional @logged usage."""

            __slots__ = ()

            @logged(event=test_const.EVENT_PROCESS)
            def traditional_method(self, value: int) -> int:
                return value * 2

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.traditional_method(21)

        assert result == 42
        assert len(collector.records) >= 1
        assert any(
            rec.getMessage() == test_const.EVENT_PROCESS_START
            for rec in collector.records
        )

    def test_logged_existing_with_payload_from_result_still_works(
        self,
        log_capture_factory,
    ) -> None:
        """Existing @logged with payload_from_result still works."""

        def extract_payload(result: int) -> dict[str, object]:
            return {"value": result}

        class Svc(LoggingMixin):
            """Test service with traditional payload_from_result."""

            __slots__ = ()

            @logged(
                test_const.EVENT_PROCESS,
                payload_from_result=extract_payload,
            )
            def compute(self, x: int) -> int:
                return x * 3

        svc = Svc()
        collector = log_capture_factory(svc)
        result = svc.compute(14)

        assert result == 42
        end_records = [
            rec
            for rec in collector.records
            if rec.getMessage() == test_const.EVENT_PROCESS_END
        ]
        assert len(end_records) == 1
        assert end_records[0].__dict__["value"] == 42

    def test_logged_class_level_existing_behavior_unchanged(
        self,
        log_capture_factory,
    ) -> None:
        """Existing class-level @logged without new params works unchanged."""

        @logged(event=test_const.EVENT_PROCESS)
        class Svc(LoggingMixin):
            """Test service with traditional class-level @logged."""

            __slots__ = ()

            def method1(self) -> str:
                return "one"

            def method2(self) -> str:
                return "two"

        svc = Svc()
        collector = log_capture_factory(svc)

        result1 = svc.method1()
        result2 = svc.method2()

        assert result1 == "one"
        assert result2 == "two"
        assert len(collector.records) >= 2
        assert any(
            rec.getMessage() == f"{test_const.EVENT_PROCESS}.method1.start"
            for rec in collector.records
        )
        assert any(
            rec.getMessage() == f"{test_const.EVENT_PROCESS}.method2.start"
            for rec in collector.records
        )
