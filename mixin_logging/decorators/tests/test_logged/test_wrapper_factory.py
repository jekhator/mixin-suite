"""Direct tests for WrapperFactory: covers static/class method branches and extraction paths."""

from __future__ import annotations

import asyncio
import logging

import pytest

from mixin_logging.decorators.logged._wrapper_factory import WrapperFactory
from mixin_logging.decorators.logged.logged_objects import LoggedContainer
from mixin_logging.tests.helpers import _RecordCollector


class TestWrapperFactoryStaticSync:
    """Tests for sync static method wrapping (for_static_or_class=True, async=False)."""

    def test_sync_static_basic(self) -> None:
        """Sync static wrapper executes and returns correct value."""

        def method(x: int) -> int:
            return x * 2

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, None, False, for_static_or_class=True,
            class_module_name="test_wrapper", class_name="TestClass"
        )

        result = wrapped(5)  # type: ignore
        assert result == 10

    def test_sync_static_with_payload_from_request_exception(self) -> None:
        """Sync static handles extraction exception without re-raising."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("TestClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def method(text: str) -> int:
            return len(text)

        def extract_bad(text: str) -> dict[str, object]:
            return 1 / 0  # type: ignore

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, extract_bad, False,
            for_static_or_class=True,
            class_module_name="test_wrapper",
            class_name="TestClass"
        )

        result = wrapped("hello")  # type: ignore
        assert result == 5

        logger.removeHandler(collector)
        assert len(collector.records) >= 1
        assert any("extraction.failure" in r.getMessage() for r in collector.records)

    def test_sync_static_with_payload_from_request_non_dict(self) -> None:
        """Sync static handles non-dict return from extraction."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("TestClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def method(text: str) -> int:
            return len(text)

        def extract_bad(text: str) -> object:
            return "not-a-dict"

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, extract_bad, False,  # type: ignore
            for_static_or_class=True,
            class_module_name="test_wrapper",
            class_name="TestClass"
        )

        result = wrapped("hello")  # type: ignore
        assert result == 5

        logger.removeHandler(collector)
        assert len(collector.records) >= 1

    def test_sync_static_raises_exception(self) -> None:
        """Sync static wrapper logs error event when method raises."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("TestClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def method() -> None:
            raise ValueError("test error")

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, None, False,
            for_static_or_class=True,
            class_module_name="test_wrapper",
            class_name="TestClass"
        )

        with pytest.raises(ValueError):
            wrapped()  # type: ignore

        logger.removeHandler(collector)
        error_records = [r for r in collector.records if r.getMessage() == "op.error"]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "ValueError"

    def test_sync_static_with_timed(self) -> None:
        """Sync static wrapper includes latency_ms in error event when timed=True."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("TestClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        def method() -> None:
            raise RuntimeError("error")

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, None, True,
            for_static_or_class=True,
            class_module_name="test_wrapper",
            class_name="TestClass"
        )

        with pytest.raises(RuntimeError):
            wrapped()  # type: ignore

        logger.removeHandler(collector)
        error_records = [r for r in collector.records if r.getMessage() == "op.error"]
        assert len(error_records) == 1
        assert "latency_ms" in error_records[0].__dict__


class TestWrapperFactoryStaticAsync:
    """Tests for async static method wrapping (for_static_or_class=True, async=True)."""

    def test_async_static_basic(self) -> None:
        """Async static wrapper executes and returns correct value."""

        async def method(x: int) -> int:
            await asyncio.sleep(0)
            return x * 2

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, None, False,
            for_static_or_class=True,
            class_module_name="test_wrapper",
            class_name="TestClass"
        )

        result = asyncio.run(wrapped(5))  # type: ignore
        assert result == 10

    def test_async_static_with_payload_from_request_exception(self) -> None:
        """Async static handles extraction exception without re-raising."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("TestClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        async def method(text: str) -> int:
            await asyncio.sleep(0)
            return len(text)

        def extract_bad(text: str) -> dict[str, object]:
            return 1 / 0  # type: ignore

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, extract_bad, False,
            for_static_or_class=True,
            class_module_name="test_wrapper",
            class_name="TestClass"
        )

        result = asyncio.run(wrapped("hello"))  # type: ignore
        assert result == 5

        logger.removeHandler(collector)
        assert len(collector.records) >= 1
        assert any("extraction.failure" in r.getMessage() for r in collector.records)

    def test_async_static_raises_exception(self) -> None:
        """Async static wrapper logs error event when method raises."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("TestClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        async def method() -> None:
            await asyncio.sleep(0)
            raise ValueError("test error")

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, None, False,
            for_static_or_class=True,
            class_module_name="test_wrapper",
            class_name="TestClass"
        )

        with pytest.raises(ValueError):
            asyncio.run(wrapped())  # type: ignore

        logger.removeHandler(collector)
        error_records = [r for r in collector.records if r.getMessage() == "op.error"]
        assert len(error_records) == 1
        assert error_records[0].__dict__["error_type"] == "ValueError"

    def test_async_static_with_payload_from_request_non_dict(self) -> None:
        """Async static handles non-dict return from extraction."""
        collector = _RecordCollector()
        logger = logging.getLogger("test_wrapper").getChild("TestClass")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)

        async def method(text: str) -> int:
            await asyncio.sleep(0)
            return len(text)

        def extract_bad(text: str) -> object:
            return "not-a-dict"

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, method, None, None, extract_bad, False,  # type: ignore
            for_static_or_class=True,
            class_module_name="test_wrapper",
            class_name="TestClass"
        )

        result = asyncio.run(wrapped("hello"))  # type: ignore
        assert result == 5

        logger.removeHandler(collector)
        assert len(collector.records) >= 1


class TestWrapperFactoryInstanceSync:
    """Tests for instance sync method wrapping (for_static_or_class=False, async=False)."""

    def test_instance_sync_with_payload_from_result_non_dict(self) -> None:
        """Instance sync handles non-dict return from result extraction."""
        from mixin_logging import LoggingMixin

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self) -> int:
                return 42

        def extract_bad(r: object) -> object:
            return "not-a-dict"

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, Svc.process, extract_bad, None, None, False  # type: ignore
        )

        svc = Svc()
        result = wrapped(svc)  # type: ignore
        assert result == 42

    def test_instance_sync_with_payload_from_result_exception(self) -> None:
        """Instance sync handles result extraction exception gracefully."""
        from mixin_logging import LoggingMixin

        class Svc(LoggingMixin):
            __slots__ = ()

            def process(self) -> int:
                return 42

        def extract_bad(r: object) -> dict[str, object]:
            return 1 / 0  # type: ignore

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, Svc.process, extract_bad, None, None, False  # type: ignore
        )

        svc = Svc()
        result = wrapped(svc)  # type: ignore
        assert result == 42


class TestWrapperFactoryInstanceAsync:
    """Tests for instance async method wrapping (for_static_or_class=False, async=True)."""

    def test_instance_async_with_payload_from_result_non_dict(self) -> None:
        """Instance async handles non-dict return from result extraction."""
        from mixin_logging import LoggingMixin

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self) -> int:
                await asyncio.sleep(0)
                return 42

        def extract_bad(r: object) -> object:
            return "not-a-dict"

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, Svc.process, extract_bad, None, None, False  # type: ignore
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc))  # type: ignore
        assert result == 42

    def test_instance_async_with_payload_from_result_exception(self) -> None:
        """Instance async handles result extraction exception gracefully."""
        from mixin_logging import LoggingMixin

        class Svc(LoggingMixin):
            __slots__ = ()

            async def process(self) -> int:
                await asyncio.sleep(0)
                return 42

        def extract_bad(r: object) -> dict[str, object]:
            return 1 / 0  # type: ignore

        container = LoggedContainer("op")
        wrapped = WrapperFactory.wrap_callable(
            container, Svc.process, extract_bad, None, None, False  # type: ignore
        )

        svc = Svc()
        result = asyncio.run(wrapped(svc))  # type: ignore
        assert result == 42
